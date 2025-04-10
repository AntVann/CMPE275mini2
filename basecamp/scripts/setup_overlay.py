#!/usr/bin/env python3

"""
Script to help set up the overlay configuration for Basecamp.

This script reads the overlay configuration from a JSON file and sets up the processes
according to the configuration.
"""

import argparse
import subprocess
import sys
import time
import os
import signal
import threading
import json
from typing import List, Dict, Optional

# Store the running processes
running_processes: Dict[str, subprocess.Popen] = {}
stop_event = threading.Event()


def get_server_command(process_id: str, ip: str, config_path: str) -> List[str]:
    """Get the command to start a server process."""
    # Load the configuration
    with open(config_path, "r") as f:
        config = json.load(f)

    # Get the process configuration
    process = config["nodes"][process_id]
    port = process["port"]

    # Determine the path to the server executable
    server_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "build", "src", "server", "basecamp_server"
        )
    )

    # Add .exe extension on Windows
    if sys.platform == "win32":
        server_path += ".exe"

    # Check if the server executable exists
    if not os.path.exists(server_path):
        print(f"Server executable not found at {server_path}")
        print("Checking alternative paths...")

        # Try to find the executable in the current directory
        alt_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "src", "server", "basecamp_server"
            )
        )
        if sys.platform == "win32":
            alt_path += ".exe"

        if os.path.exists(alt_path):
            print(f"Found server executable at {alt_path}")
            server_path = alt_path
        else:
            print(f"Server executable not found at {alt_path} either")
            print("Please make sure you have built the project using scripts/build.py")
            sys.exit(1)

    return [server_path, "--address", f"{ip}:{port}", "--node-id", process_id]


def get_client_command(
    process_id: str, connect_to: str, ip: str, config_path: str
) -> List[str]:
    """Get the command to start a client process connecting to another process."""
    # Load the configuration
    with open(config_path, "r") as f:
        config = json.load(f)

    # Get the process configurations
    process = config["nodes"][process_id]
    connect_process = config["nodes"][connect_to]

    connect_ip = (
        ip if connect_process["computer"] == process["computer"] else args.remote_ip
    )
    connect_port = connect_process["port"]

    # Determine the path to the client executable
    client_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "build",
            "src",
            "cpp_client",
            "basecamp_client",
        )
    )

    # Add .exe extension on Windows
    if sys.platform == "win32":
        client_path += ".exe"

    # Check if the client executable exists
    if not os.path.exists(client_path):
        print(f"Client executable not found at {client_path}")
        print("Checking alternative paths...")

        # Try to find the executable in the current directory
        alt_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "..", "src", "cpp_client", "basecamp_client"
            )
        )
        if sys.platform == "win32":
            alt_path += ".exe"

        if os.path.exists(alt_path):
            print(f"Found client executable at {alt_path}")
            client_path = alt_path
        else:
            print(f"Client executable not found at {alt_path} either")
            print("Please make sure you have built the project using scripts/build.py")
            sys.exit(1)

    return [client_path, "--address", f"{connect_ip}:{connect_port}"]


def start_process(
    process_id: str, computer: int, ip: str, remote_ip: str, config_path: str
) -> None:
    """Start a process (server and clients if needed)."""
    # Load the configuration
    with open(config_path, "r") as f:
        config = json.load(f)

    # Get the process configuration
    process = config["nodes"][process_id]

    # Only start processes for the specified computer
    if process["computer"] != computer:
        return

    # Start the server
    server_cmd = get_server_command(process_id, ip, config_path)
    print(f"Starting server for process {process_id}: {' '.join(server_cmd)}")

    # Set the REMOTE_IP environment variable for the server process
    env = os.environ.copy()
    env["REMOTE_IP"] = remote_ip
    print(f"Setting REMOTE_IP={remote_ip} for server process {process_id}")

    server_process = subprocess.Popen(
        server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
    )
    running_processes[f"{process_id}_server"] = server_process

    # Start a thread to read and print the server output
    def read_output():
        while not stop_event.is_set():
            line = server_process.stdout.readline()
            if not line:
                break
            print(f"[{process_id} Server] {line.strip()}")

    threading.Thread(target=read_output, daemon=True).start()

    # Wait for the server to start
    time.sleep(1)

    # Start clients to connect to other processes
    for connect_to in process["connects_to"]:
        client_cmd = get_client_command(process_id, connect_to, ip, config_path)
        print(
            f"Starting client for process {process_id} connecting to {connect_to}: {' '.join(client_cmd)}"
        )

        client_process = subprocess.Popen(
            client_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        running_processes[f"{process_id}_client_{connect_to}"] = client_process

        # Start a thread to read and print the client output
        def read_client_output():
            while not stop_event.is_set():
                line = client_process.stdout.readline()
                if not line:
                    break
                print(f"[{process_id} Client to {connect_to}] {line.strip()}")

        threading.Thread(target=read_client_output, daemon=True).start()


def stop_all_processes() -> None:
    """Stop all running processes."""
    stop_event.set()

    for name, process in running_processes.items():
        print(f"Stopping {name}...")
        if sys.platform == "win32":
            process.terminate()
        else:
            process.send_signal(signal.SIGTERM)

    # Wait for processes to terminate
    for name, process in running_processes.items():
        try:
            process.wait(timeout=5)
            print(f"{name} stopped.")
        except subprocess.TimeoutExpired:
            print(f"Forcibly killing {name}...")
            process.kill()


def copy_dlls_if_needed() -> None:
    """Copy necessary DLLs to the executable directories if on Windows."""
    if sys.platform != "win32":
        return

    # Check if we're using MSYS2/MinGW
    msys2_path = "C:/msys64/ucrt64"
    if not os.path.exists(msys2_path):
        return

    # Get the paths to the server and client executables
    server_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "build", "src", "server")
    )
    client_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "build", "src", "cpp_client")
    )

    # Create the directories if they don't exist
    os.makedirs(server_dir, exist_ok=True)
    os.makedirs(client_dir, exist_ok=True)

    # List of DLLs to copy
    dlls = [
        "libssl-3-x64.dll",
        "libcrypto-3-x64.dll",
        "libz.dll",
        "libgcc_s_seh-1.dll",
        "libstdc++-6.dll",
        "libwinpthread-1.dll",
    ]

    # Copy the DLLs to the server and client directories
    for dll in dlls:
        dll_path = os.path.join(msys2_path, "bin", dll)
        if os.path.exists(dll_path):
            print(f"Copying {dll} to server and client directories...")
            try:
                import shutil

                shutil.copy2(dll_path, server_dir)
                shutil.copy2(dll_path, client_dir)
            except Exception as e:
                print(f"Error copying {dll}: {e}")
        else:
            print(f"Warning: {dll} not found in {msys2_path}/bin")


def main() -> None:
    """Main function."""
    global args

    parser = argparse.ArgumentParser(
        description="Set up the Basecamp overlay configuration."
    )
    parser.add_argument(
        "--computer",
        type=int,
        choices=[1, 2],
        required=True,
        help="Which computer this script is running on (1 or 2)",
    )
    parser.add_argument(
        "--ip",
        default="0.0.0.0",
        help="IP address to bind the servers to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--remote-ip", required=True, help="IP address of the remote computer"
    )
    parser.add_argument(
        "--config",
        default="../configs/topology.json",
        help="Path to the configuration file (default: ../configs/topology.json)",
    )

    args = parser.parse_args()

    # Copy necessary DLLs if on Windows
    copy_dlls_if_needed()

    try:
        # Load the configuration
        with open(args.config, "r") as f:
            config = json.load(f)

        # Start processes for the specified computer
        for process_id, process in config["nodes"].items():
            if process["computer"] == args.computer:
                start_process(
                    process_id, args.computer, args.ip, args.remote_ip, args.config
                )

        print("\nAll processes started. Press Ctrl+C to stop.\n")

        # Keep the script running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping all processes...")
        stop_all_processes()
        print("All processes stopped.")


if __name__ == "__main__":
    main()
