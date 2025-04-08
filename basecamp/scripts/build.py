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


def build_cpp_components(build_dir, build_type, clean, skip_tests=False):
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

    # Use MinGW Makefiles generator on Windows, default on other platforms
    if platform.system() == "Windows":
        cmake_cmd.append("-G")
        cmake_cmd.append("MinGW Makefiles")

    # Add MSYS2 paths for Windows
    if platform.system() == "Windows":
        # Check if we're using MSYS2/MinGW
        msys2_path = "C:/msys64/ucrt64"
        if os.path.exists(msys2_path):
            print("Detected MSYS2/MinGW environment, adding paths for dependencies")

            # Convert build_path to use forward slashes to avoid escape character issues
            cmake_build_path = build_path.replace("\\", "/")

            # Create a temporary CMake file to avoid Protobuf target conflicts
            temp_cmake_file = os.path.join(build_path, "FindProtobuf.cmake")
            with open(temp_cmake_file, "w") as f:
                f.write("""
# Custom FindProtobuf.cmake to avoid target conflicts
set(Protobuf_FOUND TRUE)
set(Protobuf_INCLUDE_DIR "C:/msys64/ucrt64/include")
set(Protobuf_LIBRARIES "C:/msys64/ucrt64/lib/libprotobuf.dll.a")
set(Protobuf_PROTOC_EXECUTABLE "C:/msys64/ucrt64/bin/protoc.exe")
set(Protobuf_VERSION "5.28.3")
""")

            # Add paths for dependencies and compilers
            cmake_cmd.extend(
                [
                    f"-DCMAKE_MODULE_PATH={cmake_build_path}",
                    f"-DZLIB_INCLUDE_DIR={msys2_path}/include",
                    f"-DZLIB_LIBRARY={msys2_path}/lib/libz.dll.a",
                    f"-DCMAKE_C_COMPILER={msys2_path}/bin/gcc.exe",
                    f"-DCMAKE_CXX_COMPILER={msys2_path}/bin/g++.exe",
                    f"-DOPENSSL_ROOT_DIR={msys2_path}",
                    f"-DOPENSSL_INCLUDE_DIR={msys2_path}/include",
                    f"-DOPENSSL_CRYPTO_LIBRARY={msys2_path}/lib/libcrypto.dll.a",
                    f"-DOPENSSL_SSL_LIBRARY={msys2_path}/lib/libssl.dll.a",
                ]
            )

            # Generate protobuf and gRPC files manually before CMake runs
            print("Generating protobuf and gRPC files manually...")
            proto_path = os.path.join(project_root, "proto")
            proto_file = os.path.join(proto_path, "basecamp.proto")
            proto_gen_dir = os.path.join(build_path, "proto-gen")
            grpc_gen_dir = os.path.join(build_path, "grpc-gen")

            # Create output directories
            os.makedirs(proto_gen_dir, exist_ok=True)
            os.makedirs(grpc_gen_dir, exist_ok=True)

            # Run protoc to generate protobuf files
            protoc_cmd = [
                f"{msys2_path}/bin/protoc.exe",
                f"--proto_path={proto_path}",
                f"--cpp_out={proto_gen_dir}",
                proto_file,
            ]
            run_command(protoc_cmd)

            # Run protoc with grpc plugin to generate gRPC files
            grpc_cmd = [
                f"{msys2_path}/bin/protoc.exe",
                f"--proto_path={proto_path}",
                f"--grpc_out={grpc_gen_dir}",
                f"--plugin=protoc-gen-grpc={msys2_path}/bin/grpc_cpp_plugin.exe",
                proto_file,
            ]
            run_command(grpc_cmd)

    run_command(cmake_cmd, cwd=build_path)

    # Build
    if skip_tests:
        # Build only the server and client, skip tests
        print("Skipping tests as requested")
        build_cmd = [
            "cmake",
            "--build",
            ".",
            "--target",
            "basecamp_server",
            "basecamp_client",
        ]
    else:
        # Build everything
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
    parser.add_argument("--skip-tests", action="store_true", help="Skip building tests")

    args = parser.parse_args()

    # Build C++ components if requested
    if not args.python_only:
        build_cpp_components(
            args.build_dir, args.build_type, args.clean, args.skip_tests
        )

    # Set up Python client if requested
    if not args.cpp_only:
        setup_python_client()

    print("\nBuild completed successfully!")


if __name__ == "__main__":
    main()
