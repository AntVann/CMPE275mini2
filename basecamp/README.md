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
- CMake build system for C++ components
- Unit and integration testing

## Directory Structure

```
basecamp/
├── cmake/                  # CMake modules and configuration
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
./build/src/server/basecamp_server [--address <address>]
```

By default, the server listens on `0.0.0.0:50051`.

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
   python scripts/setup_overlay.py --computer 1 --remote-ip <computer2-ip>
   ```

   On computer 2:
   ```bash
   python scripts/setup_overlay.py --computer 2 --remote-ip <computer1-ip>
   ```

   The setup script will automatically start all the necessary processes with the correct configuration:
   - On computer 1: processes A and B
   - On computer 2: processes C, D, and E

   The overlay configuration will be set up as described in the requirements:
   - AB: Process B on computer 1 connects to process A on computer 1
   - BC: Process C on computer 2 connects to process B on computer 1
   - BD: Process D on computer 2 connects to process B on computer 1
   - CE: Process E on computer 2 connects to process C on computer 2
   - DE: Process E on computer 2 connects to process D on computer 2

4. To stop all processes, press Ctrl+C in the terminal where the setup script is running.

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
