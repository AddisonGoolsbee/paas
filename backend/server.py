from flask import Flask, request, jsonify
import os
import subprocess
import uuid
from flask_cors import CORS


app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "https://pass.birdflop.com"])
UPLOAD_FOLDER = "/tmp/scripts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/upload", methods=["POST"])
def upload_script():
    # Check if a file is included
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]

    # Generate a unique file name
    file_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.py")
    file.save(file_path)

    try:
        # Run the uploaded script
        result = subprocess.run(["python3", file_path], capture_output=True, text=True, check=True)
        return jsonify({"stdout": result.stdout, "stderr": result.stderr})
    except subprocess.CalledProcessError as e:
        return jsonify({"stdout": e.stdout, "stderr": e.stderr, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)
