from flask import Blueprint, request
from flask_login import current_user
import os

upload_bp = Blueprint("upload", __name__)


@upload_bp.route("/upload", methods=["POST"])
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


@upload_bp.route("/upload-folder", methods=["POST"])
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
