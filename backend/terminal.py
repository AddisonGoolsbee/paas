# terminal.py

import os
import pty
import fcntl
import struct
import termios
import logging
import select
import subprocess
import time

from flask import request, current_app
from flask_socketio import SocketIO
from flask_login import current_user

from .docker import attach_to_container, spawn_container

socketio: SocketIO = None  # will be assigned in init
# each user gets a single container. But if they have multiple tabs open, each session will get its own sid (resize properties etc)
# user_id → container info
user_containers = {}
# sid → container info + fd
session_map = {}


def init_terminal(socketio_instance):
    global socketio
    socketio = socketio_instance
    _register_handlers()


def _register_handlers():
    socketio.on_event("connect", handle_connect)
    socketio.on_event("disconnect", handle_disconnect)
    socketio.on_event("pty-input", handle_pty_input)
    socketio.on_event("resize", handle_resize)


def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def read_and_forward_pty_output(sid, is_authed):
    if not is_authed:
        return

    max_read_bytes = 1024 * 20
    fd = session_map[sid]["fd"]
    try:
        while True:
            socketio.sleep(0.01)
            if fd:
                try:
                    data_ready, _, _ = select.select([fd], [], [], 0)
                    if data_ready:
                        output = os.read(fd, max_read_bytes).decode(errors="ignore")
                        socketio.emit("pty-output", {"output": output}, to=sid)
                except (OSError, ValueError):
                    break
    finally:
        logging.info(f"Stopping read thread for {sid}")


def handle_pty_input(data):
    if not current_user.is_authenticated:
        return "Unauthorized", 401

    sid = request.sid
    if sid in session_map:
        fd = session_map[sid]["fd"]
        os.write(fd, data["input"].encode())


def handle_resize(data):
    if not current_user.is_authenticated:
        return

    sid = request.sid
    if sid in session_map:
        fd = session_map[sid]["fd"]
        set_winsize(fd, data["rows"], data["cols"])


def handle_connect():
    if not current_user.is_authenticated:
        logging.warning("unauthenticated user tried to connect")
        return "Unauthorized", 401

    user_id = current_user.id
    sid = request.sid
    logging.info(f"client {sid} connected")

    if user_id in user_containers:
        container_info = user_containers[user_id]
        proc, fd = attach_to_container(container_info["container_name"])
        logging.info(f"Reusing container for user {user_id}")
    else:
        master_fd, slave_fd = pty.openpty()
        container_name = f"user-container-{user_id}"
        proc = spawn_container(user_id, slave_fd, container_name)
        fd = master_fd
        user_containers[user_id] = {"child_pid": proc.pid, "container_name": container_name}
        logging.info(f"Spawned new container for user {user_id}, pid {proc.pid}")

    session_map[sid] = {"fd": fd, "user_id": user_id}
    socketio.start_background_task(read_and_forward_pty_output, sid, True)


def handle_disconnect():
    time.sleep(1)

    sid = request.sid
    session = session_map.get(sid)
    if session:
        user_id = session["user_id"]
        try:
            os.close(session["fd"])
        except Exception as e:
            logging.warning(f"Error closing PTY for {sid}: {e}")
        del session_map[sid]
        logging.info(f"Cleaned up session for {sid}")

        if user_id not in [s["user_id"] for s in session_map.values()]:
            info = user_containers.get(user_id)
            if info:
                container_name = info["container_name"]
                try:
                    result = subprocess.run(
                        ["docker", "exec", container_name, "pgrep", "-x", "bash"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    logging.info(f"Result: {result.returncode}")
                    if result.returncode != 0:
                        subprocess.run(["docker", "rm", "-f", container_name], check=True)
                        del user_containers[user_id]
                        logging.info(f"Removed idle container {container_name}")
                except Exception as e:
                    logging.warning(f"Error checking/removing container {container_name}: {e}")


__all__ = ["init_terminal", "user_containers"]
