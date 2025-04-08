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

1. Build the server and client components on each computer.
2. Start the server on the designated server computers with appropriate IP addresses.
3. Configure the clients to connect to the server addresses.

For example, to set up the overlay configuration described in the requirements (AB, BC, BD, CE, and DE, where {A,B} are on computer 1 and {C,D,E} are on computer 2):

1. On computer 1:
   - Start process A as a server: `./basecamp_server --address 0.0.0.0:50051`
   - Start process B as both a server and client:
     - As a server: `./basecamp_server --address 0.0.0.0:50052`
     - As a client connecting to A: `./basecamp_client --address localhost:50051`

2. On computer 2:
   - Start process C as both a server and client:
     - As a server: `./basecamp_server --address 0.0.0.0:50053`
     - As a client connecting to B: `./basecamp_client --address <computer1-ip>:50052`
   - Start process D as both a server and client:
     - As a server: `./basecamp_server --address 0.0.0.0:50054`
     - As a client connecting to B: `./basecamp_client --address <computer1-ip>:50052`
   - Start process E as both a server and client:
     - As a server: `./basecamp_server --address 0.0.0.0:50055`
     - As a client connecting to C: `./basecamp_client --address localhost:50053`
     - As a client connecting to D: `./basecamp_client --address localhost:50054`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
