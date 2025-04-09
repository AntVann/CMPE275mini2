cmake_minimum_required(VERSION 3.10)
project(Basecamp VERSION 1.0)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Find required packages
find_package(Threads REQUIRED)
find_package(Protobuf REQUIRED)
find_package(gRPC CONFIG REQUIRED)
find_package(Boost REQUIRED COMPONENTS system filesystem)

# Add nlohmann/json (header-only library)
include(FetchContent)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.2
)
FetchContent_MakeAvailable(json)

# Include directories
include_directories(${CMAKE_CURRENT_BINARY_DIR})
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${Boost_INCLUDE_DIRS})

# Generate protobuf and gRPC files
set(PROTO_FILES
    ${CMAKE_CURRENT_SOURCE_DIR}/proto/basecamp.proto
)

# Get the directory where the proto files are located
get_filename_component(PROTO_PATH "${CMAKE_CURRENT_SOURCE_DIR}/proto" ABSOLUTE)

# Set output directories for generated files
set(PROTO_SRC_DIR "${CMAKE_CURRENT_BINARY_DIR}/proto-gen")
set(PROTO_GRPC_DIR "${CMAKE_CURRENT_BINARY_DIR}/grpc-gen")

# Create directories for generated files
file(MAKE_DIRECTORY ${PROTO_SRC_DIR})
file(MAKE_DIRECTORY ${PROTO_GRPC_DIR})

# Custom command to generate protobuf and gRPC files
add_custom_command(
    OUTPUT 
        "${PROTO_SRC_DIR}/basecamp.pb.cc"
        "${PROTO_SRC_DIR}/basecamp.pb.h"
        "${PROTO_GRPC_DIR}/basecamp.grpc.pb.cc"
        "${PROTO_GRPC_DIR}/basecamp.grpc.pb.h"
    COMMAND ${Protobuf_PROTOC_EXECUTABLE}
        --proto_path=${PROTO_PATH}
        --cpp_out=${PROTO_SRC_DIR}
        ${PROTO_FILES}
    COMMAND ${Protobuf_PROTOC_EXECUTABLE}
        --proto_path=${PROTO_PATH}
        --grpc_out=${PROTO_GRPC_DIR}
        --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
        ${PROTO_FILES}
    DEPENDS ${PROTO_FILES}
    COMMENT "Generating protobuf and gRPC files"
)

# Add generated files to a custom target
add_custom_target(
    proto_gen
    DEPENDS 
        "${PROTO_SRC_DIR}/basecamp.pb.cc"
        "${PROTO_SRC_DIR}/basecamp.pb.h"
        "${PROTO_GRPC_DIR}/basecamp.grpc.pb.cc"
        "${PROTO_GRPC_DIR}/basecamp.grpc.pb.h"
)

# Add subdirectories
add_subdirectory(src/server)
add_subdirectory(src/cpp_client)
add_subdirectory(tests/unit)
add_subdirectory(tests/integration)

# Enable testing
enable_testing()
