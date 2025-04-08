#!/usr/bin/env python3

"""
Script to help set up the overlay configuration for Basecamp.

This script helps set up the overlay configuration described in the requirements:
AB, BC, BD, CE, and DE, where {A,B} are on computer 1 and {C,D,E} are on computer 2.
"""

import argparse
import subprocess
import sys
import time
import os
import signal
import threading
from typing import List, Dict, Optional

# Define the processes and their connections
PROCESSES = {
    "A": {"computer": 1, "port": 50051, "connects_to": []},
    "B": {"computer": 1, "port": 50052, "connects_to": ["A"]},
    "C": {"computer": 2, "port": 50053, "connects_to": ["B"]},
    "D": {"computer": 2, "port": 50054, "connects_to": ["B"]},
    "E": {"computer": 2, "port": 50055, "connects_to": ["C", "D"]},
}

# Store the running processes
running_processes: Dict[str, subprocess.Popen] = {}
stop_event = threading.Event()


def get_server_command(process_id: str, ip: str) -> List[str]:
    """Get the command to start a server process."""
    process = PROCESSES[process_id]
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

    return [server_path, "--address", f"{ip}:{port}"]


def get_client_command(process_id: str, connect_to: str, ip: str) -> List[str]:
    """Get the command to start a client process connecting to another process."""
    connect_process = PROCESSES[connect_to]
    connect_ip = (
        ip
        if connect_process["computer"] == PROCESSES[process_id]["computer"]
        else args.remote_ip
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

    return [client_path, "--address", f"{connect_ip}:{connect_port}"]


def start_process(process_id: str, computer: int, ip: str) -> None:
    """Start a process (server and clients if needed)."""
    process = PROCESSES[process_id]

    # Only start processes for the specified computer
    if process["computer"] != computer:
        return

    # Start the server
    server_cmd = get_server_command(process_id, ip)
    print(f"Starting server for process {process_id}: {' '.join(server_cmd)}")

    server_process = subprocess.Popen(
        server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
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
        client_cmd = get_client_command(process_id, connect_to, ip)
        print(
            f"Starting client for process {process_id} connecting to {connect_to}: {' '.join(client_cmd)}"
        )

        client_process = subprocess.Popen(
            client_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
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

    args = parser.parse_args()

    try:
        # Start processes for the specified computer
        for process_id, process in PROCESSES.items():
            if process["computer"] == args.computer:
                start_process(process_id, args.computer, args.ip)

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
