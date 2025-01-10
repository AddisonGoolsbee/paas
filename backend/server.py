from flask import Flask, request, jsonify
import os
import subprocess
import uuid
from flask_cors import CORS
import re


app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "https://pass.birdflop.com"])
UPLOAD_FOLDER = "/tmp/scripts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def install_dependencies_from_script(script_path):
    with open(script_path, "r") as file:
        content = file.read()

    # Extract imported modules
    imports = re.findall(r"^import (\w+)|^from (\w+)", content, re.MULTILINE)
    modules = {mod[0] or mod[1] for mod in imports}

    # Install modules
    for module in modules:
        try:
            subprocess.run(["pip", "install", module], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to install {module}")


@app.route("/upload", methods=["POST"])
def upload_script():
    # Check if a file is included
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    script_name = f"{uuid.uuid4()}.py"
    script_path = os.path.join(UPLOAD_FOLDER, script_name)
    file.save(script_path)
    container_name = f"script-runner-{uuid.uuid4()}"

    try:
        # Run the Docker container with the uploaded script
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "-v", f"{script_path}:/app/script.py:ro",
                "python-3.11-runner",
                "python", "/app/script.py"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        # Return stdout and stderr
        return jsonify({
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except subprocess.CalledProcessError as e:
        # Handle errors from the container
        return jsonify({
            "stdout": e.stdout,
            "stderr": e.stderr,
            "error": str(e)
        }), 500

    finally:
        # Clean up the uploaded script
        if os.path.exists(script_path):
            os.remove(script_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)
