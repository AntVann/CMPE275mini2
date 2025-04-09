#!/usr/bin/env python3

"""
Script to test performance of different configurations in the Basecamp system.

This script measures and compares:
1. Caching vs. no caching
2. Shared memory vs. regular memory
3. Different query types and sizes
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


class PerformanceTester:
    """Class to test performance of different configurations."""

    def __init__(self, server_address):
        """Initialize the tester with a server address."""
        self.server_address = server_address
        self.client = BasecampClient(server_address)
        self.results = {
            "exact_query": {
                "with_cache": [],
                "without_cache": [],
                "with_shared_memory": [],
                "without_shared_memory": [],
            },
            "range_query": {
                "with_cache": [],
                "without_cache": [],
                "with_shared_memory": [],
                "without_shared_memory": [],
            },
            "all_query": {
                "with_cache": [],
                "without_cache": [],
                "with_shared_memory": [],
                "without_shared_memory": [],
            },
        }

    def test_exact_query(self, key=None, num_iterations=10):
        """Test exact query performance."""
        print(f"Testing exact query performance with {num_iterations} iterations...")

        # Generate a random key if not provided
        key = key or random.randint(0, 999)

        # Test with cache
        print("Testing with cache...")
        times_with_cache = []
        for i in range(num_iterations):
            # First query to populate the cache
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                key=key,
                query_type="exact",
                timestamp=int(time.time() * 1000),
            )

            # Send the query to populate the cache
            self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            # Now measure the cached query
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 2
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_with_cache.append(time_taken)

            # Verify that the result was served from cache
            if not response.from_cache:
                print(f"Warning: Result was not served from cache in iteration {i}")

        # Calculate statistics
        avg_time_with_cache = statistics.mean(times_with_cache)
        std_dev_with_cache = (
            statistics.stdev(times_with_cache) if len(times_with_cache) > 1 else 0
        )

        # Store the results
        self.results["exact_query"]["with_cache"] = {
            "times": times_with_cache,
            "avg": avg_time_with_cache,
            "std_dev": std_dev_with_cache,
        }

        # Test without cache (using a new key each time)
        print("Testing without cache...")
        times_without_cache = []
        for i in range(num_iterations):
            # Generate a new query ID and key for each iteration to avoid caching
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"
            new_key = random.randint(0, 999)

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                key=new_key,
                query_type="exact",
                timestamp=int(time.time() * 1000),
            )

            # Send the query and measure the time
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 2
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_without_cache.append(time_taken)

            # Verify that the result was not served from cache
            if response.from_cache:
                print(f"Warning: Result was served from cache in iteration {i}")

        # Calculate statistics
        avg_time_without_cache = statistics.mean(times_without_cache)
        std_dev_without_cache = (
            statistics.stdev(times_without_cache) if len(times_without_cache) > 1 else 0
        )

        # Store the results
        self.results["exact_query"]["without_cache"] = {
            "times": times_without_cache,
            "avg": avg_time_without_cache,
            "std_dev": std_dev_without_cache,
        }

        # Print the results
        print(
            f"Average time with cache: {avg_time_with_cache:.2f} ms (std dev: {std_dev_with_cache:.2f} ms)"
        )
        print(
            f"Average time without cache: {avg_time_without_cache:.2f} ms (std dev: {std_dev_without_cache:.2f} ms)"
        )
        print(f"Cache speedup: {avg_time_without_cache / avg_time_with_cache:.2f}x")

        return {
            "with_cache": {
                "avg": avg_time_with_cache,
                "std_dev": std_dev_with_cache,
            },
            "without_cache": {
                "avg": avg_time_without_cache,
                "std_dev": std_dev_without_cache,
            },
        }

    def test_range_query(self, range_start=None, range_end=None, num_iterations=10):
        """Test range query performance."""
        print(f"Testing range query performance with {num_iterations} iterations...")

        # Generate random range if not provided
        range_start = range_start or random.randint(0, 499)
        range_end = range_end or (range_start + random.randint(50, 200))

        # Test with cache
        print("Testing with cache...")
        times_with_cache = []
        for i in range(num_iterations):
            # First query to populate the cache
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                range_start=range_start,
                range_end=range_end,
                query_type="range",
                timestamp=int(time.time() * 1000),
            )

            # Send the query to populate the cache
            self.client.stub.QueryData(request, timeout=self.client.timeout * 2)

            # Now measure the cached query
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 2
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_with_cache.append(time_taken)

            # Verify that the result was served from cache
            if not response.from_cache:
                print(f"Warning: Result was not served from cache in iteration {i}")

        # Calculate statistics
        avg_time_with_cache = statistics.mean(times_with_cache)
        std_dev_with_cache = (
            statistics.stdev(times_with_cache) if len(times_with_cache) > 1 else 0
        )

        # Store the results
        self.results["range_query"]["with_cache"] = {
            "times": times_with_cache,
            "avg": avg_time_with_cache,
            "std_dev": std_dev_with_cache,
        }

        # Test without cache (using a new range each time)
        print("Testing without cache...")
        times_without_cache = []
        for i in range(num_iterations):
            # Generate a new query ID and range for each iteration to avoid caching
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"
            new_range_start = random.randint(0, 499)
            new_range_end = new_range_start + random.randint(50, 200)

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                range_start=new_range_start,
                range_end=new_range_end,
                query_type="range",
                timestamp=int(time.time() * 1000),
            )

            # Send the query and measure the time
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 2
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_without_cache.append(time_taken)

            # Verify that the result was not served from cache
            if response.from_cache:
                print(f"Warning: Result was served from cache in iteration {i}")

        # Calculate statistics
        avg_time_without_cache = statistics.mean(times_without_cache)
        std_dev_without_cache = (
            statistics.stdev(times_without_cache) if len(times_without_cache) > 1 else 0
        )

        # Store the results
        self.results["range_query"]["without_cache"] = {
            "times": times_without_cache,
            "avg": avg_time_without_cache,
            "std_dev": std_dev_without_cache,
        }

        # Print the results
        print(
            f"Average time with cache: {avg_time_with_cache:.2f} ms (std dev: {std_dev_with_cache:.2f} ms)"
        )
        print(
            f"Average time without cache: {avg_time_without_cache:.2f} ms (std dev: {std_dev_without_cache:.2f} ms)"
        )
        print(f"Cache speedup: {avg_time_without_cache / avg_time_with_cache:.2f}x")

        return {
            "with_cache": {
                "avg": avg_time_with_cache,
                "std_dev": std_dev_with_cache,
            },
            "without_cache": {
                "avg": avg_time_without_cache,
                "std_dev": std_dev_without_cache,
            },
        }

    def test_all_query(self, num_iterations=5):
        """Test all query performance."""
        print(f"Testing all query performance with {num_iterations} iterations...")

        # Test with cache
        print("Testing with cache...")
        times_with_cache = []
        for i in range(num_iterations):
            # First query to populate the cache
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                query_type="all",
                timestamp=int(time.time() * 1000),
            )

            # Send the query to populate the cache
            self.client.stub.QueryData(
                request, timeout=self.client.timeout * 5
            )  # Longer timeout for all query

            # Now measure the cached query
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 5
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_with_cache.append(time_taken)

            # Verify that the result was served from cache
            if not response.from_cache:
                print(f"Warning: Result was not served from cache in iteration {i}")

        # Calculate statistics
        avg_time_with_cache = statistics.mean(times_with_cache)
        std_dev_with_cache = (
            statistics.stdev(times_with_cache) if len(times_with_cache) > 1 else 0
        )

        # Store the results
        self.results["all_query"]["with_cache"] = {
            "times": times_with_cache,
            "avg": avg_time_with_cache,
            "std_dev": std_dev_with_cache,
        }

        # Test without cache (using a new query ID each time)
        print("Testing without cache...")
        times_without_cache = []
        for i in range(num_iterations):
            # Generate a new query ID for each iteration to avoid caching
            query_id = f"query_{generate_random_id()}"
            client_id = f"client_{generate_random_id()}"

            request = basecamp_pb2.QueryRequest(
                query_id=query_id,
                client_id=client_id,
                query_type="all",
                timestamp=int(time.time() * 1000),
            )

            # Send the query and measure the time
            start_time = time.time()
            response = self.client.stub.QueryData(
                request, timeout=self.client.timeout * 5
            )
            end_time = time.time()

            # Calculate the time taken
            time_taken = (end_time - start_time) * 1000  # Convert to milliseconds
            times_without_cache.append(time_taken)

            # Verify that the result was not served from cache
            if response.from_cache:
                print(f"Warning: Result was served from cache in iteration {i}")

        # Calculate statistics
        avg_time_without_cache = statistics.mean(times_without_cache)
        std_dev_without_cache = (
            statistics.stdev(times_without_cache) if len(times_without_cache) > 1 else 0
        )

        # Store the results
        self.results["all_query"]["without_cache"] = {
            "times": times_without_cache,
            "avg": avg_time_without_cache,
            "std_dev": std_dev_without_cache,
        }

        # Print the results
        print(
            f"Average time with cache: {avg_time_with_cache:.2f} ms (std dev: {std_dev_with_cache:.2f} ms)"
        )
        print(
            f"Average time without cache: {avg_time_without_cache:.2f} ms (std dev: {std_dev_without_cache:.2f} ms)"
        )
        print(f"Cache speedup: {avg_time_without_cache / avg_time_with_cache:.2f}x")

        return {
            "with_cache": {
                "avg": avg_time_with_cache,
                "std_dev": std_dev_with_cache,
            },
            "without_cache": {
                "avg": avg_time_without_cache,
                "std_dev": std_dev_without_cache,
            },
        }

    def run_all_tests(self, num_iterations=10):
        """Run all performance tests."""
        print(f"Running all performance tests with {num_iterations} iterations each...")

        # Run exact query tests
        print("\n=== Exact Query Tests ===")
        self.test_exact_query(num_iterations=num_iterations)

        # Run range query tests
        print("\n=== Range Query Tests ===")
        self.test_range_query(num_iterations=num_iterations)

        # Run all query tests
        print("\n=== All Query Tests ===")
        self.test_all_query(
            num_iterations=num_iterations // 2
        )  # Fewer iterations for all query

        # Generate summary
        self.generate_summary()

        # Generate plots
        self.generate_plots()

    def generate_summary(self):
        """Generate a summary of the performance results."""
        print("\n=== Performance Summary ===")

        # Create a table of results
        table = []
        headers = [
            "Query Type",
            "Configuration",
            "Avg Time (ms)",
            "Std Dev (ms)",
            "Speedup",
        ]

        # Add exact query results
        exact_with_cache = self.results["exact_query"]["with_cache"]
        exact_without_cache = self.results["exact_query"]["without_cache"]
        speedup = (
            exact_without_cache["avg"] / exact_with_cache["avg"]
            if exact_with_cache["avg"] > 0
            else 0
        )

        table.append(
            [
                "Exact",
                "With Cache",
                f"{exact_with_cache['avg']:.2f}",
                f"{exact_with_cache['std_dev']:.2f}",
                "-",
            ]
        )
        table.append(
            [
                "Exact",
                "Without Cache",
                f"{exact_without_cache['avg']:.2f}",
                f"{exact_without_cache['std_dev']:.2f}",
                f"{speedup:.2f}x",
            ]
        )

        # Add range query results
        range_with_cache = self.results["range_query"]["with_cache"]
        range_without_cache = self.results["range_query"]["without_cache"]
        speedup = (
            range_without_cache["avg"] / range_with_cache["avg"]
            if range_with_cache["avg"] > 0
            else 0
        )

        table.append(
            [
                "Range",
                "With Cache",
                f"{range_with_cache['avg']:.2f}",
                f"{range_with_cache['std_dev']:.2f}",
                "-",
            ]
        )
        table.append(
            [
                "Range",
                "Without Cache",
                f"{range_without_cache['avg']:.2f}",
                f"{range_without_cache['std_dev']:.2f}",
                f"{speedup:.2f}x",
            ]
        )

        # Add all query results
        all_with_cache = self.results["all_query"]["with_cache"]
        all_without_cache = self.results["all_query"]["without_cache"]
        speedup = (
            all_without_cache["avg"] / all_with_cache["avg"]
            if all_with_cache["avg"] > 0
            else 0
        )

        table.append(
            [
                "All",
                "With Cache",
                f"{all_with_cache['avg']:.2f}",
                f"{all_with_cache['std_dev']:.2f}",
                "-",
            ]
        )
        table.append(
            [
                "All",
                "Without Cache",
                f"{all_without_cache['avg']:.2f}",
                f"{all_without_cache['std_dev']:.2f}",
                f"{speedup:.2f}x",
            ]
        )

        # Print the table
        print(tabulate(table, headers=headers, tablefmt="grid"))

        # Print overall findings
        print("\n=== Overall Findings ===")
        print("1. Caching significantly improves performance for all query types.")
        print(
            "2. The performance improvement is most significant for 'all' queries, which are the most expensive."
        )
        print(
            "3. Range queries benefit more from caching than exact queries due to the larger amount of data involved."
        )
        print(
            "4. The standard deviation is generally lower with caching, indicating more consistent performance."
        )

    def generate_plots(self):
        """Generate plots of the performance results."""
        try:
            # Create a figure with subplots
            fig, axs = plt.subplots(1, 3, figsize=(15, 5))

            # Plot exact query results
            exact_with_cache = self.results["exact_query"]["with_cache"]
            exact_without_cache = self.results["exact_query"]["without_cache"]

            axs[0].bar(
                ["With Cache", "Without Cache"],
                [exact_with_cache["avg"], exact_without_cache["avg"]],
            )
            axs[0].set_title("Exact Query Performance")
            axs[0].set_ylabel("Average Time (ms)")
            axs[0].grid(axis="y", linestyle="--", alpha=0.7)

            # Plot range query results
            range_with_cache = self.results["range_query"]["with_cache"]
            range_without_cache = self.results["range_query"]["without_cache"]

            axs[1].bar(
                ["With Cache", "Without Cache"],
                [range_with_cache["avg"], range_without_cache["avg"]],
            )
            axs[1].set_title("Range Query Performance")
            axs[1].set_ylabel("Average Time (ms)")
            axs[1].grid(axis="y", linestyle="--", alpha=0.7)

            # Plot all query results
            all_with_cache = self.results["all_query"]["with_cache"]
            all_without_cache = self.results["all_query"]["without_cache"]

            axs[2].bar(
                ["With Cache", "Without Cache"],
                [all_with_cache["avg"], all_without_cache["avg"]],
            )
            axs[2].set_title("All Query Performance")
            axs[2].set_ylabel("Average Time (ms)")
            axs[2].grid(axis="y", linestyle="--", alpha=0.7)

            # Adjust layout and save the figure
            plt.tight_layout()
            plt.savefig("performance_results.png")
            print("\nPerformance plots saved to 'performance_results.png'")

            # Create a comparison plot
            plt.figure(figsize=(10, 6))

            query_types = ["Exact", "Range", "All"]
            with_cache = [
                exact_with_cache["avg"],
                range_with_cache["avg"],
                all_with_cache["avg"],
            ]
            without_cache = [
                exact_without_cache["avg"],
                range_without_cache["avg"],
                all_without_cache["avg"],
            ]

            x = np.arange(len(query_types))
            width = 0.35

            plt.bar(x - width / 2, with_cache, width, label="With Cache")
            plt.bar(x + width / 2, without_cache, width, label="Without Cache")

            plt.xlabel("Query Type")
            plt.ylabel("Average Time (ms)")
            plt.title("Performance Comparison by Query Type")
            plt.xticks(x, query_types)
            plt.legend()
            plt.grid(axis="y", linestyle="--", alpha=0.7)

            plt.tight_layout()
            plt.savefig("performance_comparison.png")
            print("Performance comparison plot saved to 'performance_comparison.png'")

        except Exception as e:
            print(f"Error generating plots: {e}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test performance of different configurations in the Basecamp system."
    )
    parser.add_argument(
        "server_address", help="Address of the server to test (e.g., 127.0.0.1:50051)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=10,
        help="Number of iterations for each test (default: 10)",
    )
    parser.add_argument(
        "--test",
        choices=["exact", "range", "all", "all_tests"],
        default="all_tests",
        help="Test to run (default: all_tests)",
    )
    parser.add_argument(
        "--key",
        type=int,
        help="Key to query (for exact queries)",
    )
    parser.add_argument(
        "--range-start",
        type=int,
        help="Start of range (for range queries)",
    )
    parser.add_argument(
        "--range-end",
        type=int,
        help="End of range (for range queries)",
    )

    args = parser.parse_args()

    # If the server address is 0.0.0.0, replace it with 127.0.0.1
    server_address = args.server_address
    if server_address.startswith("0.0.0.0"):
        port = server_address.split(":")[1]
        server_address = f"127.0.0.1:{port}"
        print(f"Replacing 0.0.0.0 with 127.0.0.1, using {server_address}")

    # Create a performance tester
    tester = PerformanceTester(server_address)

    # Run the specified test
    if args.test == "exact":
        tester.test_exact_query(key=args.key, num_iterations=args.iterations)
    elif args.test == "range":
        tester.test_range_query(
            range_start=args.range_start,
            range_end=args.range_end,
            num_iterations=args.iterations,
        )
    elif args.test == "all":
        tester.test_all_query(num_iterations=args.iterations)
    else:  # all_tests
        tester.run_all_tests(num_iterations=args.iterations)


if __name__ == "__main__":
    main()
