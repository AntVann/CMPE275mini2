#!/usr/bin/env python3

"""
Script to get the IP address of the computer.

This script helps find the IP address of the computer, which can be used
as the --remote-ip parameter when running setup_overlay.py.
"""

import socket
import argparse
import subprocess
import sys
import platform


def get_ip_address():
    """Get the IP address of the computer."""
    # Try to get the IP address by connecting to a public DNS server
    try:
        # This doesn't actually establish a connection, but it helps determine
        # which interface would be used to connect to an external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback method
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)


def get_all_ip_addresses():
    """Get all IP addresses of the computer."""
    ip_addresses = []

    # Get all network interfaces
    if platform.system() == "Windows":
        # On Windows, use ipconfig
        try:
            output = subprocess.check_output("ipconfig", text=True)
            for line in output.split("\n"):
                if "IPv4 Address" in line:
                    ip = line.split(":")[-1].strip()
                    ip_addresses.append(ip)
        except Exception as e:
            print(f"Error running ipconfig: {e}")
    else:
        # On Unix-like systems, use ifconfig or ip addr
        try:
            if (
                subprocess.run(["which", "ifconfig"], capture_output=True).returncode
                == 0
            ):
                output = subprocess.check_output(["ifconfig"], text=True)
                for line in output.split("\n"):
                    if "inet " in line and "127.0.0.1" not in line:
                        ip = line.split("inet ")[1].split(" ")[0]
                        ip_addresses.append(ip)
            else:
                output = subprocess.check_output(["ip", "addr"], text=True)
                for line in output.split("\n"):
                    if "inet " in line and "127.0.0.1" not in line:
                        ip = line.split("inet ")[1].split("/")[0]
                        ip_addresses.append(ip)
        except Exception as e:
            print(f"Error getting IP addresses: {e}")

    return ip_addresses


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Get the IP address of the computer.")
    parser.add_argument("--all", action="store_true", help="Show all IP addresses")

    args = parser.parse_args()

    if args.all:
        ip_addresses = get_all_ip_addresses()
        print("\nAll IP addresses:")
        for i, ip in enumerate(ip_addresses, 1):
            print(f"{i}. {ip}")
        print(
            "\nUse one of these IP addresses as the --remote-ip parameter when running setup_overlay.py on the other computer."
        )
    else:
        ip = get_ip_address()
        print(f"\nYour IP address: {ip}")
        print(
            "\nUse this IP address as the --remote-ip parameter when running setup_overlay.py on the other computer."
        )
        print(
            "If this is not the correct IP address, run with --all to see all available IP addresses."
        )


if __name__ == "__main__":
    main()
