from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from threading import Thread
import os
import subprocess
import uuid
import psutil
import platform

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "https://pass.birdflop.com"])
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173", "https://pass.birdflop.com"])

UPLOAD_FOLDER = "/tmp/scripts"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

MAX_USERS = 20
num_cpus = os.cpu_count() or 1
memory_mb = psutil.virtual_memory().total // (1024 * 1024)

cpu_per_user = round(num_cpus / MAX_USERS, 2)
memory_per_user = round(memory_mb / MAX_USERS, 2)


def setup_isolated_network(network_name="isolated_net"):
    try:
        # Check if the network exists
        subprocess.run(
            ["docker", "network", "inspect", network_name],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError:
        # Network doesn't exist, so create it
        print(f"Creating network {network_name}...")
        subprocess.run(
            [
                "docker",
                "network",
                "create",
                "--driver",
                "bridge",
                "--opt",
                "com.docker.network.bridge.enable_icc=false",  # Disable inter-container communication
                network_name,
            ],
            check=True,
        )
        print(f"Network {network_name} created successfully.")

    if platform.system() != "Linux":
        print("Skipping iptables setup as it is only supported on Linux.")
        return

    try:
        # Get the bridge name for the Docker network
        network_id = subprocess.run(
            ["docker", "network", "inspect", "-f", "{{.Id}}", network_name],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()[:12]

        # Add iptables rule to block communication with the host
        subprocess.run(
            ["iptables", "-I", "DOCKER-USER", "-i", f"br-{network_id}", "-o", "docker0", "-j", "DROP"],
            check=True,
        )
        print(f"Blocked host communication for network {network_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to block host communication: {str(e)}")


@app.route("/upload", methods=["POST"])
def upload_script():
    # Check if a file is included
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".py"):
        return jsonify({"error": "Invalid file type. Only .py files are allowed"}), 400

    script_name = f"{uuid.uuid4()}.py"
    script_path = os.path.join(UPLOAD_FOLDER, script_name)
    file.save(script_path)
    container_name = f"script-runner-{uuid.uuid4()}"

    try:
        # Run the Docker container with the uploaded script
        process = subprocess.Popen(
            [
                "docker",
                "run",
                "--name",
                container_name,
                "--rm",  # Remove the container after it exits
                "--network=isolated_net",  # prevent containers from accessing other containers or host, but allows internet
                "--cap-drop=ALL",  # prevent a bunch of admin linux stuff
                "--user=1000:1000",  # login as a non-root user
                # Security profiles
                "--security-opt",
                "no-new-privileges",  # prevent container from gaining priviledge
                # "--security-opt",
                # "seccomp",  # restricts syscalls
                # Resource limits
                "--cpus",
                str(cpu_per_user),
                "--memory",
                f"{memory_per_user}m",
                # TODO: bandwidth limit
                # TODO: disk limit, perhaps by making everything read-only and adding a volume?
                "-v",
                f"{script_path}:/app/script.py:ro",  # mount script as read-only
                "python-3.11-runner",
                "python",
                "/app/script.py",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )



        def stream_output(stream, tag):
            for line in iter(stream.readline, ""):
                socketio.emit("log", {"type": tag, "message": line.strip()})
            stream.close()

        # Start threads to stream stdout and stderr
        Thread(target=stream_output, args=(process.stdout, "stdout"), daemon=True).start()
        Thread(target=stream_output, args=(process.stderr, "stderr"), daemon=True).start()


        process.wait()

        return jsonify({"message": "Script execution complete"}), 200

    except subprocess.CalledProcessError as e:
        # Handle errors from the container
        return jsonify({"error": str(e)}), 500

    finally:
        # Clean up the uploaded script
        if os.path.exists(script_path):
            os.remove(script_path)


if __name__ == "__main__":
    setup_isolated_network()
    app.run(host="0.0.0.0", port=5555)
