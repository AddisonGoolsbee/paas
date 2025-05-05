import os
import pty
import subprocess
import platform
import logging

import psutil

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


def spawn_container(user_id, slave_fd, container_name):
    cmd = [
        "docker",
        "run",
        "--name",
        container_name,
        "--hostname",
        "paas",
        "-i",
        "-t",
        # TODO: delete the container once you exit and nothing is running (maybe just --rm)
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
        f"/tmp/paas_uploads/{user_id}:/app",
        "paas",
        "bash",
    ]

    proc = subprocess.Popen(cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
    return proc


def attach_to_container(container_name):
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        ["docker", "exec", "-it", container_name, "bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
    )
    return proc, master_fd


def cleanup_containers(user_containers):
    for info in user_containers.values():
        name = info["container_name"]
        logging.info(f"Stopping and removing container {name}")
        try:
            subprocess.run(["docker", "rm", "-f", name], check=True)
        except subprocess.CalledProcessError as e:
            logging.warning(f"Failed to remove container {name}: {e}")
