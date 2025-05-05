#!/usr/bin/env python3
import argparse
import atexit
import logging
import os
import signal
import sys

from dotenv import load_dotenv

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # Only for localhost/dev
load_dotenv()
logging.getLogger("werkzeug").setLevel(logging.ERROR)

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_login import LoginManager

from .auth import auth_bp, load_user
from .upload import upload_bp
from .terminal import init_terminal, user_containers
from .docker import cleanup_containers, setup_isolated_network


app = Flask(__name__, template_folder=".", static_folder=".", static_url_path="")
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN_DEV")
CORS(app, origins=[FRONTEND_ORIGIN], supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins=[FRONTEND_ORIGIN], manage_session=False)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.user_loader(load_user)

app.register_blueprint(auth_bp)
app.register_blueprint(upload_bp)
init_terminal(socketio)


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
