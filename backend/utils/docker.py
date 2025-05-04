import subprocess
import platform


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
