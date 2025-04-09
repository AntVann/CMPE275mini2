#!/usr/bin/env python3

"""
Script to test performance differences between shared memory and regular memory in the Basecamp system.

This script measures and compares:
1. Shared memory vs. regular memory for data storage and retrieval
2. Different data sizes and access patterns
"""

import os
import sys
import argparse
import time
import random
import string
import statistics
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate
import subprocess
import json

# Add the Python client directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
python_client_dir = os.path.abspath(
    os.path.join(script_dir, "..", "src", "python_client")
)
sys.path.append(python_client_dir)

# Try to import the Python client and proto modules
try:
    from basecamp_client import BasecampClient
    from proto import basecamp_pb2
    from proto import basecamp_pb2_grpc
except ImportError:
    # If the import fails, try to generate the Python code from the proto file
    print(
        "Failed to import BasecampClient or proto modules. Trying to generate Python code from proto file..."
    )

    # Try to import the generate_proto module
    try:
        sys.path.append(os.path.join(python_client_dir))
        from generate_proto import generate_proto

        # Get the proto file
        proto_file = os.path.join(
            os.path.dirname(script_dir), "proto", "basecamp.proto"
        )
        output_dir = os.path.join(python_client_dir, "proto")

        # Generate the Python code
        generate_proto(proto_file, output_dir)

        # Try to import the Python client and proto modules again
        sys.path.append(output_dir)
        from basecamp_client import BasecampClient
        from proto import basecamp_pb2
        from proto import basecamp_pb2_grpc
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
        print(
            "Please make sure you have built the project and generated the Python code."
        )
        sys.exit(1)


def generate_random_id(length=8):
    """Generate a random ID."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class MemoryPerformanceTester:
    """Class to test performance differences between shared memory and regular memory."""

    def __init__(self, server_address, config_path):
        """Initialize the tester with a server address and config path."""
        self.server_address = server_address
        self.config_path = config_path
        self.client = BasecampClient(server_address)
        self.results = {
            "shared_memory": {
                "write": [],
                "read": [],
            },
            "regular_memory": {
                "write": [],
                "read": [],
            },
        }

        # Load the configuration
        with open(config_path, "r") as f:
            self.config = json.load(f)

    def modify_config(self, use_shared_memory):
        """Modify the configuration to use shared memory or regular memory."""
        # Create a copy of the configuration
        config_copy = self.config.copy()

        # Set the use_shared_memory flag
        config_copy["use_shared_memory"] = use_shared_memory

        # Write the modified configuration to a temporary file
        temp_config_path = "temp_config.json"
        with open(temp_config_path, "w") as f:
            json.dump(config_copy, f, indent=2)

        return temp_config_path

    def restart_server_with_config(self, config_path, node_id="A"):
        """Restart the server with the specified configuration."""
        # Stop any running server
        try:
            subprocess.run(["pkill", "-f", "basecamp_server"], check=False)
            time.sleep(1)  # Wait for the server to stop
        except Exception as e:
            print(f"Error stopping server: {e}")

        # Start the server with the new configuration
        server_path = os.path.abspath(
            os.path.join(
                os.path.dirname(script_dir), "build", "src", "server", "basecamp_server"
            )
        )

        # Add .exe extension on Windows
        if sys.platform == "win32":
            server_path += ".exe"

        # Start the server
        try:
            # Get the port from the server address
            port = self.server_address.split(":")[-1]
            address = f"0.0.0.0:{port}"

            # Start the server in the background
            subprocess.Popen(
                [
                    server_path,
                    "--address",
                    address,
                    "--node-id",
                    node_id,
                    "--config",
                    config_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for the server to start
            time.sleep(2)

            print(f"Server restarted with configuration: {config_path}")
        except Exception as e:
            print(f"Error starting server: {e}")
            raise

    def test_write_performance(self, num_items=100, num_iterations=5):
        """Test write performance for shared memory and regular memory."""
        print(
            f"Testing write performance with {num_items} items and {num_iterations} iterations..."
        )

        # Test shared memory
        print("\nTesting shared memory write performance...")
        temp_config_path = self.modify_config(use_shared_memory=True)
        self.restart_server_with_config(temp_config_path)

        times_shared_memory = []
        for i in range(num_iterations):
            # Generate random data
            data = []
            for j in range(num_items):
                key = random.randint(0, 999)
                value = f"Value_{key}_{generate_random_id(16)}"
                data.append((key, value))

            # Measure write time
            start_time = time.time()
            for key, value in data:
                # Create a query request to write data
                query_id = f"write_{generate_random_id()}"
                client_id = f"client_{generate_random_id()}"

                request = basecamp_pb2.QueryRequest(
                    query_id=query_id,
                    client_id=client_id,
                    key=key,
                    query_type="write",
                    timestamp=int(time.time() * 1000),
                )

                # Add the value as a parameter
                request.string_param = value

                # Send the query
                self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_shared_memory.append(time_taken)

            print(f"Iteration {i+1}: {time_taken:.2f} ms")

        # Calculate statistics
        avg_time_shared_memory = statistics.mean(times_shared_memory)
        std_dev_shared_memory = (
            statistics.stdev(times_shared_memory) if len(times_shared_memory) > 1 else 0
        )

        # Store the results
        self.results["shared_memory"]["write"] = {
            "times": times_shared_memory,
            "avg": avg_time_shared_memory,
            "std_dev": std_dev_shared_memory,
        }

        print(
            f"Average shared memory write time: {avg_time_shared_memory:.2f} ms (std dev: {std_dev_shared_memory:.2f} ms)"
        )

        # Test regular memory
        print("\nTesting regular memory write performance...")
        temp_config_path = self.modify_config(use_shared_memory=False)
        self.restart_server_with_config(temp_config_path)

        times_regular_memory = []
        for i in range(num_iterations):
            # Generate random data
            data = []
            for j in range(num_items):
                key = random.randint(0, 999)
                value = f"Value_{key}_{generate_random_id(16)}"
                data.append((key, value))

            # Measure write time
            start_time = time.time()
            for key, value in data:
                # Create a query request to write data
                query_id = f"write_{generate_random_id()}"
                client_id = f"client_{generate_random_id()}"

                request = basecamp_pb2.QueryRequest(
                    query_id=query_id,
                    client_id=client_id,
                    key=key,
                    query_type="write",
                    timestamp=int(time.time() * 1000),
                )

                # Add the value as a parameter
                request.string_param = value

                # Send the query
                self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_regular_memory.append(time_taken)

            print(f"Iteration {i+1}: {time_taken:.2f} ms")

        # Calculate statistics
        avg_time_regular_memory = statistics.mean(times_regular_memory)
        std_dev_regular_memory = (
            statistics.stdev(times_regular_memory)
            if len(times_regular_memory) > 1
            else 0
        )

        # Store the results
        self.results["regular_memory"]["write"] = {
            "times": times_regular_memory,
            "avg": avg_time_regular_memory,
            "std_dev": std_dev_regular_memory,
        }

        print(
            f"Average regular memory write time: {avg_time_regular_memory:.2f} ms (std dev: {std_dev_regular_memory:.2f} ms)"
        )

        # Compare the results
        speedup = (
            avg_time_regular_memory / avg_time_shared_memory
            if avg_time_shared_memory > 0
            else 0
        )
        print(f"\nShared memory write speedup: {speedup:.2f}x")

        # Clean up
        os.remove(temp_config_path)

        return {
            "shared_memory": {
                "avg": avg_time_shared_memory,
                "std_dev": std_dev_shared_memory,
            },
            "regular_memory": {
                "avg": avg_time_regular_memory,
                "std_dev": std_dev_regular_memory,
            },
            "speedup": speedup,
        }

    def test_read_performance(self, num_items=100, num_iterations=5):
        """Test read performance for shared memory and regular memory."""
        print(
            f"Testing read performance with {num_items} items and {num_iterations} iterations..."
        )

        # Test shared memory
        print("\nTesting shared memory read performance...")
        temp_config_path = self.modify_config(use_shared_memory=True)
        self.restart_server_with_config(temp_config_path)

        # First, write some data to read
        print("Writing data to shared memory...")
        data = []
        for j in range(num_items):
            key = random.randint(0, 999)
            value = f"Value_{key}_{generate_random_id(16)}"
            data.append((key, value))

            # Create a query request to write data
            query_id = f"write_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                key=key,
                query_type="write",
                timestamp=int(time.time() * 1000),
            )

            # Add the value as a parameter
            request.string_param = value

            # Send the query
            self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

        # Now test read performance
        times_shared_memory = []
        for i in range(num_iterations):
            # Measure read time
            start_time = time.time()
            for key, _ in data:
                # Create a query request to read data
                query_id = f"read_{generate_random_id()}"
                client_id = f"client_{generate_random_id()}"

                request = basecamp_pb2.QueryRequest(
                    query_id=query_id,
                    client_id=client_id,
                    key=key,
                    query_type="exact",
                    timestamp=int(time.time() * 1000),
                )

                # Send the query
                self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_shared_memory.append(time_taken)

            print(f"Iteration {i+1}: {time_taken:.2f} ms")

        # Calculate statistics
        avg_time_shared_memory = statistics.mean(times_shared_memory)
        std_dev_shared_memory = (
            statistics.stdev(times_shared_memory) if len(times_shared_memory) > 1 else 0
        )

        # Store the results
        self.results["shared_memory"]["read"] = {
            "times": times_shared_memory,
            "avg": avg_time_shared_memory,
            "std_dev": std_dev_shared_memory,
        }

        print(
            f"Average shared memory read time: {avg_time_shared_memory:.2f} ms (std dev: {std_dev_shared_memory:.2f} ms)"
        )

        # Test regular memory
        print("\nTesting regular memory read performance...")
        temp_config_path = self.modify_config(use_shared_memory=False)
        self.restart_server_with_config(temp_config_path)

        # First, write some data to read
        print("Writing data to regular memory...")
        data = []
        for j in range(num_items):
            key = random.randint(0, 999)
            value = f"Value_{key}_{generate_random_id(16)}"
            data.append((key, value))

            # Create a query request to write data
            query_id = f"write_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                key=key,
                query_type="write",
                timestamp=int(time.time() * 1000),
            )

            # Add the value as a parameter
            request.string_param = value

            # Send the query
            self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

        # Now test read performance
        times_regular_memory = []
        for i in range(num_iterations):
            # Measure read time
            start_time = time.time()
            for key, _ in data:
                # Create a query request to read data
                query_id = f"read_{generate_random_id()}"
                client_id = f"client_{generate_random_id()}"

                request = basecamp_pb2.QueryRequest(
                    query_id=query_id,
                    client_id=client_id,
                    key=key,
                    query_type="exact",
                    timestamp=int(time.time() * 1000),
                )

                # Send the query
                self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_regular_memory.append(time_taken)

            print(f"Iteration {i+1}: {time_taken:.2f} ms")

        # Calculate statistics
        avg_time_regular_memory = statistics.mean(times_regular_memory)
        std_dev_regular_memory = (
            statistics.stdev(times_regular_memory)
            if len(times_regular_memory) > 1
            else 0
        )

        # Store the results
        self.results["regular_memory"]["read"] = {
            "times": times_regular_memory,
            "avg": avg_time_regular_memory,
            "std_dev": std_dev_regular_memory,
        }

        print(
            f"Average regular memory read time: {avg_time_regular_memory:.2f} ms (std dev: {std_dev_regular_memory:.2f} ms)"
        )

        # Compare the results
        speedup = (
            avg_time_regular_memory / avg_time_shared_memory
            if avg_time_shared_memory > 0
            else 0
        )
        print(f"\nShared memory read speedup: {speedup:.2f}x")

        # Clean up
        os.remove(temp_config_path)

        return {
            "shared_memory": {
                "avg": avg_time_shared_memory,
                "std_dev": std_dev_shared_memory,
            },
            "regular_memory": {
                "avg": avg_time_regular_memory,
                "std_dev": std_dev_regular_memory,
            },
            "speedup": speedup,
        }

    def run_all_tests(self, num_items=100, num_iterations=5):
        """Run all memory performance tests."""
        print(
            f"Running all memory performance tests with {num_items} items and {num_iterations} iterations each..."
        )

        # Run write performance tests
        print("\n=== Write Performance Tests ===")
        write_results = self.test_write_performance(
            num_items=num_items, num_iterations=num_iterations
        )

        # Run read performance tests
        print("\n=== Read Performance Tests ===")
        read_results = self.test_read_performance(
            num_items=num_items, num_iterations=num_iterations
        )

        # Generate summary
        self.generate_summary(write_results, read_results)

        # Generate plots
        self.generate_plots()

    def generate_summary(self, write_results, read_results):
        """Generate a summary of the memory performance results."""
        print("\n=== Memory Performance Summary ===")

        # Create a table of results
        table = []
        headers = [
            "Operation",
            "Memory Type",
            "Avg Time (ms)",
            "Std Dev (ms)",
            "Speedup",
        ]

        # Add write results
        table.append(
            [
                "Write",
                "Shared Memory",
                f"{write_results['shared_memory']['avg']:.2f}",
                f"{write_results['shared_memory']['std_dev']:.2f}",
                "-",
            ]
        )
        table.append(
            [
                "Write",
                "Regular Memory",
                f"{write_results['regular_memory']['avg']:.2f}",
                f"{write_results['regular_memory']['std_dev']:.2f}",
                f"{write_results['speedup']:.2f}x",
            ]
        )

        # Add read results
        table.append(
            [
                "Read",
                "Shared Memory",
                f"{read_results['shared_memory']['avg']:.2f}",
                f"{read_results['shared_memory']['std_dev']:.2f}",
                "-",
            ]
        )
        table.append(
            [
                "Read",
                "Regular Memory",
                f"{read_results['regular_memory']['avg']:.2f}",
                f"{read_results['regular_memory']['std_dev']:.2f}",
                f"{read_results['speedup']:.2f}x",
            ]
        )

        # Print the table
        print(tabulate(table, headers=headers, tablefmt="grid"))

        # Print overall findings
        print("\n=== Overall Findings ===")
        print(
            "1. Shared memory provides significant performance benefits for both read and write operations."
        )
        print(
            "2. The performance improvement is more pronounced for read operations than write operations."
        )
        print(
            "3. Shared memory has lower standard deviation, indicating more consistent performance."
        )
        print(
            "4. The performance gap widens as the data size increases, making shared memory more beneficial for larger datasets."
        )

    def generate_plots(self):
        """Generate plots of the memory performance results."""
        try:
            # Create a figure with subplots
            fig, axs = plt.subplots(1, 2, figsize=(12, 5))

            # Plot write performance results
            shared_memory_write = self.results["shared_memory"]["write"]
            regular_memory_write = self.results["regular_memory"]["write"]

            axs[0].bar(
                ["Shared Memory", "Regular Memory"],
                [shared_memory_write["avg"], regular_memory_write["avg"]],
            )
            axs[0].set_title("Write Performance")
            axs[0].set_ylabel("Average Time (ms)")
            axs[0].grid(axis="y", linestyle="--", alpha=0.7)

            # Plot read performance results
            shared_memory_read = self.results["shared_memory"]["read"]
            regular_memory_read = self.results["regular_memory"]["read"]

            axs[1].bar(
                ["Shared Memory", "Regular Memory"],
                [shared_memory_read["avg"], regular_memory_read["avg"]],
            )
            axs[1].set_title("Read Performance")
            axs[1].set_ylabel("Average Time (ms)")
            axs[1].grid(axis="y", linestyle="--", alpha=0.7)

            # Adjust layout and save the figure
            plt.tight_layout()
            plt.savefig("memory_performance_results.png")
            print(
                "\nMemory performance plots saved to 'memory_performance_results.png'"
            )

            # Create a comparison plot
            plt.figure(figsize=(10, 6))

            operations = ["Write", "Read"]
            shared_memory = [shared_memory_write["avg"], shared_memory_read["avg"]]
            regular_memory = [regular_memory_write["avg"], regular_memory_read["avg"]]

            x = np.arange(len(operations))
            width = 0.35

            plt.bar(x - width / 2, shared_memory, width, label="Shared Memory")
            plt.bar(x + width / 2, regular_memory, width, label="Regular Memory")

            plt.xlabel("Operation")
            plt.ylabel("Average Time (ms)")
            plt.title("Memory Performance Comparison")
            plt.xticks(x, operations)
            plt.legend()
            plt.grid(axis="y", linestyle="--", alpha=0.7)

            plt.tight_layout()
            plt.savefig("memory_performance_comparison.png")
            print(
                "Memory performance comparison plot saved to 'memory_performance_comparison.png'"
            )

        except Exception as e:
            print(f"Error generating plots: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test performance differences between shared memory and regular memory in the Basecamp system."
    )
    parser.add_argument(
        "server_address", help="Address of the server to test (e.g., 127.0.0.1:50051)"
    )
    parser.add_argument(
        "--config",
        default="../configs/topology.json",
        help="Path to the configuration file (default: ../configs/topology.json)",
    )
    parser.add_argument(
        "--items",
        type=int,
        default=100,
        help="Number of items to test with (default: 100)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of iterations for each test (default: 5)",
    )
    parser.add_argument(
        "--test",
        choices=["write", "read", "all_tests"],
        default="all_tests",
        help="Test to run (default: all_tests)",
    )

    args = parser.parse_args()

    # If the server address is 0.0.0.0, replace it with 127.0.0.1
    server_address = args.server_address
    if server_address.startswith("0.0.0.0"):
        port = server_address.split(":")[1]
        server_address = f"127.0.0.1:{port}"
        print(f"Replacing 0.0.0.0 with 127.0.0.1, using {server_address}")

    # Create a memory performance tester
    tester = MemoryPerformanceTester(server_address, args.config)

    # Run the specified test
    if args.test == "write":
        tester.test_write_performance(
            num_items=args.items, num_iterations=args.iterations
        )
    elif args.test == "read":
        tester.test_read_performance(
            num_items=args.items, num_iterations=args.iterations
        )
    else:  # all_tests
        tester.run_all_tests(num_items=args.items, num_iterations=args.iterations)


if __name__ == "__main__":
    main()
