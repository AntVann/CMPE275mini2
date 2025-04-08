#!/usr/bin/env python3

"""
Script to build the Basecamp project.

This script helps with building the C++ components of the Basecamp project
and setting up the Python client.
"""

import argparse
import os
import subprocess
import sys
import platform


def run_command(command, cwd=None):
    """Run a command and print its output."""
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)


def build_cpp_components(build_dir, build_type, clean):
    """Build the C++ components of the project."""
    # Get the project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Create the build directory if it doesn't exist
    build_path = os.path.join(project_root, build_dir)
    os.makedirs(build_path, exist_ok=True)

    # Clean the build directory if requested
    if clean and os.path.exists(build_path):
        print(f"Cleaning build directory: {build_path}")
        for item in os.listdir(build_path):
            item_path = os.path.join(build_path, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                import shutil

                shutil.rmtree(item_path)

    # Configure with CMake
    cmake_cmd = ["cmake", "..", f"-DCMAKE_BUILD_TYPE={build_type}"]

    # Use Ninja generator if available
    if (
        subprocess.run(["cmake", "--help"], capture_output=True, text=True).stdout.find(
            "Ninja"
        )
        != -1
    ):
        cmake_cmd.append("-GNinja")

    run_command(cmake_cmd, cwd=build_path)

    # Build
    build_cmd = ["cmake", "--build", "."]
    if platform.system() != "Windows":
        # Use multiple cores on non-Windows platforms
        import multiprocessing

        build_cmd.extend(["--", f"-j{multiprocessing.cpu_count()}"])

    run_command(build_cmd, cwd=build_path)

    print(f"\nC++ components built successfully in {build_path}")


def setup_python_client():
    """Set up the Python client."""
    # Get the project root directory
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    python_client_dir = os.path.join(project_root, "src", "python_client")

    # Install dependencies
    print("\nSetting up Python client...")
    run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=python_client_dir,
    )

    # Generate Python code from proto file
    run_command([sys.executable, "generate_proto.py"], cwd=python_client_dir)

    print("\nPython client set up successfully")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build the Basecamp project.")
    parser.add_argument(
        "--build-dir", default="build", help="Build directory (default: build)"
    )
    parser.add_argument(
        "--build-type",
        default="Release",
        choices=["Debug", "Release", "RelWithDebInfo", "MinSizeRel"],
        help="Build type (default: Release)",
    )
    parser.add_argument(
        "--clean", action="store_true", help="Clean the build directory before building"
    )
    parser.add_argument(
        "--cpp-only", action="store_true", help="Only build C++ components"
    )
    parser.add_argument(
        "--python-only", action="store_true", help="Only set up Python client"
    )

    args = parser.parse_args()

    # Build C++ components if requested
    if not args.python_only:
        build_cpp_components(args.build_dir, args.build_type, args.clean)

    # Set up Python client if requested
    if not args.cpp_only:
        setup_python_client()

    print("\nBuild completed successfully!")


if __name__ == "__main__":
    main()
