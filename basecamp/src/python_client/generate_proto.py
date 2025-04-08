#!/usr/bin/env python3

import os
import subprocess
import sys


def generate_proto(proto_file, output_dir):
    """Generate Python code from a proto file."""
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Generate the Python code
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
