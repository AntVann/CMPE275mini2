#!/usr/bin/env python3

import os
import subprocess
import sys


def generate_proto(proto_file, output_dir):
    """Generate Python code from a proto file."""
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Try to use grpc_tools.protoc
        print("Trying to generate Python code using grpc_tools.protoc...")
        subprocess.check_call(
            [
                "python",
                "-m",
                "grpc_tools.protoc",
                "--proto_path=" + os.path.dirname(proto_file),
                "--python_out=" + output_dir,
                "--grpc_python_out=" + output_dir,
                proto_file,
            ]
        )
    except (ImportError, subprocess.CalledProcessError) as e:
        print(f"Failed to use grpc_tools.protoc: {e}")
        print("Falling back to using protoc and grpc_python_plugin from MSYS2/MinGW...")

        # Check if we're on Windows and MSYS2/MinGW is available
        msys2_path = "C:/msys64/ucrt64"
        if os.path.exists(msys2_path):
            # Use protoc and grpc_python_plugin from MSYS2/MinGW
            protoc_path = os.path.join(msys2_path, "bin", "protoc.exe")
            grpc_plugin_path = os.path.join(msys2_path, "bin", "grpc_python_plugin.exe")

            if os.path.exists(protoc_path) and os.path.exists(grpc_plugin_path):
                subprocess.check_call(
                    [
                        protoc_path,
                        f"--proto_path={os.path.dirname(proto_file)}",
                        f"--python_out={output_dir}",
                        f"--grpc_python_out={output_dir}",
                        f"--plugin=protoc-gen-grpc_python={grpc_plugin_path}",
                        proto_file,
                    ]
                )
            else:
                print(
                    f"Could not find protoc or grpc_python_plugin in {msys2_path}/bin"
                )
                print(
                    "Please install grpcio-tools using pip or install protoc and grpc_python_plugin"
                )
                sys.exit(1)
        else:
            print("MSYS2/MinGW not found at C:/msys64/ucrt64")
            print(
                "Please install grpcio-tools using pip or install protoc and grpc_python_plugin"
            )
            sys.exit(1)

    # Create an __init__.py file to make the directory a package
    with open(os.path.join(output_dir, "__init__.py"), "w") as f:
        pass

    print(f"Generated Python code from {proto_file} in {output_dir}")


if __name__ == "__main__":
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the root directory of the project
    root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

    # Get the proto file
    proto_file = os.path.join(root_dir, "proto", "basecamp.proto")

    # Get the output directory
    output_dir = os.path.join(script_dir, "proto")

    # Generate the Python code
    generate_proto(proto_file, output_dir)
