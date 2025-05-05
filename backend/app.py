#!/usr/bin/env python3
import argparse
import subprocess
import pty
import os
import select
import termios
import struct
import fcntl
import logging
import sys
import atexit
import signal
import time

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import LoginManager, current_user

from .auth import auth_bp, load_user
from .docker import attach_to_container, cleanup_containers, setup_isolated_network, spawn_container

logging.getLogger("werkzeug").setLevel(logging.ERROR)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for localhost/dev

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")
app.register_blueprint(auth_bp)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN_DEV")
CORS(app, origins=[FRONTEND_ORIGIN], supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=[FRONTEND_ORIGIN], manage_session=False)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(load_user)

# each user gets a single container. But if they have multiple tabs open, each session will get its own sid (resize properties etc)
# sid → {"child_pid": ..., "fd": ..., "container_name": ...}
session_map = {}
# user_id → container info
user_containers = {}


def set_winsize(fd, row, col, xpix=0, ypix=0):
    logging.debug("setting window size with termios")
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
                    break  # FD closed or invalid
    finally:
        logging.info(f"Stopping read thread for {sid}")


@socketio.on("pty-input")
def pty_input(data):
    if not current_user.is_authenticated:
        return "Unauthorized", 401

    sid = request.sid
    if sid in session_map:
        fd = session_map[sid]["fd"]
        os.write(fd, data["input"].encode())


@socketio.on("resize")
def resize(data):
    if not current_user.is_authenticated:
        return

    sid = request.sid
    if sid in session_map:
        fd = session_map[sid]["fd"]
        set_winsize(fd, data["rows"], data["cols"])


@app.route("/upload", methods=["POST"])
def upload():
    if not current_user.is_authenticated:
        return "Unauthorized", 401

    user_id = current_user.id
    upload_dir = f"/tmp/paas_uploads/{user_id}"
    os.makedirs(upload_dir, exist_ok=True)

    files = request.files.getlist("files")
    if not files:
        return "No files provided", 400
    for f in files:
        f.save(os.path.join(upload_dir, f.filename))

    return "File uploaded successfully", 200


@app.route("/upload-folder", methods=["POST"])
def upload_folder():
    if not current_user.is_authenticated:
        return "Unauthorized", 401

    user_id = current_user.id
    upload_dir = f"/tmp/paas_uploads/{user_id}"
    os.makedirs(upload_dir, exist_ok=True)

    files = request.files.getlist("files")
    if not files:
        return "No files provided", 400

    for f in files:
        safe_path = os.path.normpath(os.path.join(upload_dir, f.filename))
        if not safe_path.startswith(upload_dir):
            continue  # prevent directory traversal
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        f.save(safe_path)

    return "Folder uploaded successfully", 200


@socketio.on("connect")
def connect():
    if not current_user.is_authenticated:
        logging.warning("unauthenticated user tried to connect")
        return "Unauthorized", 401

    user_id = current_user.id
    sid = request.sid
    logging.info(f"client {sid} connected")

    # Reuse existing container if present
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


@socketio.on("disconnect")
def disconnect():
    # wait to prevent reload problems
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

        # If no other sessions for this user, check container status
        if user_id not in [s["user_id"] for s in session_map.values()]:
            info = user_containers.get(user_id)
            if info:
                container_name = info["container_name"]
                try:
                    # Check if anything is still running in container
                    result = subprocess.run(
                        ["docker", "exec", container_name, "pgrep", "-x", "bash"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    logging.info(f"Result: {result.returncode}")
                    if result.returncode != 0:
                        # No bash process = container idle, safe to remove
                        subprocess.run(["docker", "rm", "-f", container_name], check=True)
                        del user_containers[user_id]
                        logging.info(f"Removed idle container {container_name}")
                except Exception as e:
                    logging.warning(f"Error checking/removing container {container_name}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default=5555, type=int)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(levelname)s (%(funcName)s:%(lineno)s) %(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if args.debug else logging.INFO,
    )
    logging.info(f"serving on http://{args.host}:{args.port}")

    atexit.register(cleanup_containers, user_containers)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    setup_isolated_network()
    os.makedirs("/tmp/paas_uploads", exist_ok=True)
    socketio.run(app, debug=args.debug, port=args.port, host=args.host)


if __name__ == "__main__":
    main()
