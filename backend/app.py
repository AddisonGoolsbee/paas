#!/usr/bin/env python3
import argparse
import uuid
import pty
import os
import select
import termios
import struct
import fcntl
import shlex
import logging
import sys

from flask import Flask, redirect, request
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv

from .utils.docker import attach_to_container, setup_isolated_network, spawn_container

logging.getLogger("werkzeug").setLevel(logging.ERROR)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for localhost/dev
load_dotenv()

app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="")
app.config["SECRET_KEY"] = "secret!"
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173"], manage_session=False)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5555/callback"

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id_, email):
        self.id = id_
        self.email = email


users = {}


@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)


@app.route("/login")
def login():
    google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=["openid", "email", "profile"])
    auth_url, _ = google.authorization_url(
        "https://accounts.google.com/o/oauth2/auth", access_type="offline", prompt="select_account"
    )
    return redirect(auth_url)


@app.route("/callback")
def callback():
    google = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=REDIRECT_URI)
    google.fetch_token(
        "https://oauth2.googleapis.com/token",
        client_secret=GOOGLE_CLIENT_SECRET,
        authorization_response=request.url,
    )
    user_info = google.get("https://www.googleapis.com/oauth2/v2/userinfo").json()
    user = User(user_info["id"], user_info["email"])
    users[user.id] = user
    login_user(user)
    return redirect("http://localhost:5173/terminal")


@app.route("/logout")
def logout():
    logout_user()
    return redirect("http://localhost:5173")


@app.route("/me")
def me():
    if current_user.is_authenticated:
        return {"email": current_user.email}
    return {"error": "unauthenticated"}, 401


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
        return

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


@socketio.on("connect")
def connect():
    if not current_user.is_authenticated:
        logging.warning("unauthenticated user tried to connect")
        return False

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

        proc = spawn_container(sid, master_fd, slave_fd, container_name)
        fd = master_fd
        user_containers[user_id] = {"child_pid": proc.pid, "container_name": container_name}
        logging.info(f"Spawned new container for user {user_id}, pid {proc.pid}")

    session_map[sid] = {"fd": fd, "user_id": user_id}
    socketio.start_background_task(read_and_forward_pty_output, sid, True)


@socketio.on("disconnect")
def disconnect():
    sid = request.sid
    session = session_map.get(sid)
    if session:
        try:
            os.close(session["fd"])
        except Exception as e:
            logging.warning(f"Error closing PTY for {sid}: {e}")
        del session_map[sid]
        logging.info(f"Cleaned up session for {sid}")


def main():
    setup_isolated_network()

    parser = argparse.ArgumentParser(
        description=("A fully functional terminal in your browser. " "https://github.com/cs01/pyxterm.js"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-p", "--port", default=5555, help="port to run server on", type=int)
    parser.add_argument(
        "--host",
        default="localhost",
        help="host to run server on (use 0.0.0.0 to allow access from other hosts)",
    )
    parser.add_argument("--debug", action="store_true", help="debug the server")
    parser.add_argument("--command", default="bash", help="Command to run in the terminal")
    parser.add_argument(
        "--cmd-args",
        default="",
        help="arguments to pass to command (i.e. --cmd-args='arg1 arg2 --flag')",
    )
    args = parser.parse_args()
    app.config["cmd"] = [args.command] + shlex.split(args.cmd_args)
    green = "\033[92m"
    end = "\033[0m"
    log_format = green + "pyxtermjs > " + end + "%(levelname)s (%(funcName)s:%(lineno)s) %(message)s"
    logging.basicConfig(
        format=log_format,
        stream=sys.stdout,
        level=logging.DEBUG if args.debug else logging.INFO,
    )
    logging.info(f"serving on http://{args.host}:{args.port}")
    socketio.run(app, debug=args.debug, port=args.port, host=args.host)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


if __name__ == "__main__":
    main()
