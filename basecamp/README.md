# Basecamp

Basecamp is a distributed system consisting of multiple processes (A, B, C, D, E) communicating via gRPC across multiple computers. The system is designed to demonstrate asynchronous communication between trusted servers.

## Features

- C++ server implementation with asynchronous processing
- C++ client implementation
- Python client implementation
- Support for various RPC types:
  - Simple RPC (SendMessage)
  - Server streaming RPC (SubscribeToUpdates)
  - Client streaming RPC (SendMultipleMessages)
  - Bidirectional streaming RPC (Chat)
  - Query RPC (QueryData) for distributed data retrieval
- Shared memory for efficient data storage and retrieval
- Caching mechanism for query results
- Dynamic overlay configuration from JSON file
- CMake build system for C++ components
- Unit and integration testing

## Directory Structure

```
basecamp/
├── cmake/                  # CMake modules and configuration
├── configs/                # Configuration files
│   └── topology.json       # Overlay network configuration
├── include/                # Header files
├── src/                    # Source files
│   ├── server/             # C++ server implementation
│   ├── cpp_client/         # C++ client implementation
│   └── python_client/      # Python client implementation
├── proto/                  # Protocol buffer definitions
├── tests/                  # Test files
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
└── scripts/                # Utility scripts
```

## Prerequisites

### For C++ Components

- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.10 or higher
- gRPC and Protocol Buffers
- Boost libraries (for shared memory and interprocess communication)
- nlohmann/json (for JSON parsing)
- Google Test (for running tests)

### For Python Client

- Python 3.6 or higher
- gRPC Python packages (see `src/python_client/requirements.txt`)

## Building

### Building C++ Components

1. Create a build directory:

```bash
mkdir -p build
cd build
```

2. Configure with CMake:

```bash
cmake ..
```

3. Build:

```bash
cmake --build .
```

### Setting Up Python Client

1. Install dependencies:

```bash
cd src/python_client
pip install -r requirements.txt
```

2. Generate Python code from proto file:

```bash
python generate_proto.py
```

## Running

### Running the Server

```bash
./build/src/server/basecamp_server [--address <address>] [--node-id <node-id>] [--config <config-path>]
```

Parameters:
- `--address`: The address to listen on (default: `0.0.0.0:50051`)
- `--node-id`: The ID of this node in the overlay network (default: `A`)
- `--config`: Path to the configuration file (default: `../configs/topology.json`)

### Running the C++ Client

```bash
./build/src/cpp_client/basecamp_client [--address <address>]
```

By default, the client connects to `localhost:50051`.

### Running the Python Client

```bash
cd src/python_client
python basecamp_client.py [--address <address>]
```

By default, the client connects to `localhost:50051`.

## Testing

### Running Unit Tests

```bash
cd build
ctest -R basecamp_unit_tests
```

### Running Integration Tests

```bash
cd build
ctest -R basecamp_integration_tests
```

## Testing Communication

You can use the `test_communication.py` script to test communication between processes:

```bash
python scripts/test_communication.py <server-address> [--test <test-type>]
```

Parameters:
- `server-address`: The address of the server to test (e.g., `127.0.0.1:50051`)
- `--test`: The type of test to run (choices: `send`, `subscribe`, `multiple`, `chat`, `query`, `all`; default: `all`)

For query tests, additional parameters are available:
- `--query-type`: The type of query to run (choices: `exact`, `range`, `all`; default: `exact`)
- `--key`: The key to query (for exact queries)
- `--range-start`: The start of the range (for range queries)
- `--range-end`: The end of the range (for range queries)

Example:
```bash
# Test all communication types
python scripts/test_communication.py 127.0.0.1:50051

# Test only query functionality with an exact key query
python scripts/test_communication.py 127.0.0.1:50051 --test query --query-type exact --key 42

# Test only query functionality with a range query
python scripts/test_communication.py 127.0.0.1:50051 --test query --query-type range --range-start 100 --range-end 200
```

## Deployment

To deploy the system across multiple computers:

1. Build the server and client components on each computer using the build script:
   ```bash
   python scripts/build.py
   ```

2. Find the IP address of each computer using the provided script:
   ```bash
   python scripts/get_ip.py
   ```
   This will display the IP address that should be used as the `--remote-ip` parameter when running the setup script on the other computer.

   If the script shows an incorrect IP address (e.g., if you have multiple network interfaces), you can run:
   ```bash
   python scripts/get_ip.py --all
   ```
   This will display all available IP addresses, and you can choose the correct one.

3. Use the setup script to start all processes according to the overlay configuration:

   On computer 1:
   ```bash
   python scripts/setup_overlay.py --computer 1 --remote-ip <computer2-ip> [--config <config-path>]
   ```

   On computer 2:
   ```bash
   python scripts/setup_overlay.py --computer 2 --remote-ip <computer1-ip> [--config <config-path>]
   ```

   The setup script will automatically start all the necessary processes with the correct configuration based on the topology.json file.

4. To stop all processes, press Ctrl+C in the terminal where the setup script is running.

## Configuration

The system uses a JSON configuration file to define the overlay network topology. The default configuration file is located at `configs/topology.json`.

Example configuration:
```json
{
  "nodes": {
    "A": {
      "computer": 1,
      "port": 50051,
      "connects_to": ["B"],
      "data_range": [0, 199]
    },
    "B": {
      "computer": 1,
      "port": 50052,
      "connects_to": ["A", "C", "D"],
      "data_range": [200, 399]
    },
    "C": {
      "computer": 2,
      "port": 50053,
      "connects_to": ["B", "E"],
      "data_range": [400, 599]
    },
    "D": {
      "computer": 2,
      "port": 50054,
      "connects_to": ["B", "E"],
      "data_range": [600, 799]
    },
    "E": {
      "computer": 2,
      "port": 50055,
      "connects_to": ["C", "D"],
      "data_range": [800, 999]
    }
  },
  "portal": "A",
  "shared_memory_key": "basecamp_shared_memory",
  "cache_size": 100,
  "cache_ttl_seconds": 300
}
```

Configuration parameters:
- `nodes`: A dictionary of nodes in the overlay network
  - `computer`: The computer number (1 or 2) where this node runs
  - `port`: The port number for this node's server
  - `connects_to`: An array of node IDs that this node connects to
  - `data_range`: The range of keys that this node is responsible for
- `portal`: The ID of the node that serves as the portal (entry point) for client queries
- `shared_memory_key`: The key for the shared memory segment
- `cache_size`: The maximum number of entries in the query cache
- `cache_ttl_seconds`: The time-to-live for cache entries in seconds

## Shared Memory and Caching

The system uses shared memory for efficient data storage and retrieval within each node. This allows for fast access to data without the overhead of network communication.

The caching mechanism stores query results to improve performance for repeated queries. The cache has a configurable size and time-to-live (TTL) for entries.

## Query Types

The system supports three types of queries:

1. **Exact Query**: Retrieves a single data item by key
2. **Range Query**: Retrieves all data items within a specified key range
3. **All Query**: Retrieves all data items from all nodes

Queries are processed as follows:
1. The client sends a query to the portal node (A)
2. The portal node checks its cache for the query result
3. If the result is not in the cache, the portal node:
   - Checks its local data for matching items
   - Forwards the query to its peers
   - Aggregates the results from all peers
   - Caches the result for future queries
4. The portal node returns the result to the client

### Manual Deployment (Alternative)

If you prefer to start each process manually instead of using the setup script, you can do so as follows:

1. On computer 1:
   - Start process A as a server: `./build/src/server/basecamp_server --address 0.0.0.0:50051`
   - Start process B as both a server and client:
     - As a server: `./build/src/server/basecamp_server --address 0.0.0.0:50052`
     - As a client connecting to A: `./build/src/cpp_client/basecamp_client --address localhost:50051`

2. On computer 2:
   - Start process C as both a server and client:
     - As a server: `./build/src/server/basecamp_server --address 0.0.0.0:50053`
     - As a client connecting to B: `./build/src/cpp_client/basecamp_client --address <computer1-ip>:50052`
   - Start process D as both a server and client:
     - As a server: `./build/src/server/basecamp_server --address 0.0.0.0:50054`
     - As a client connecting to B: `./build/src/cpp_client/basecamp_client --address <computer1-ip>:50052`
   - Start process E as both a server and client:
     - As a server: `./build/src/server/basecamp_server --address 0.0.0.0:50055`
     - As a client connecting to C: `./build/src/cpp_client/basecamp_client --address localhost:50053`
     - As a client connecting to D: `./build/src/cpp_client/basecamp_client --address localhost:50054`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
