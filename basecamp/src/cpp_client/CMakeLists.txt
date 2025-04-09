set(CLIENT_SOURCES
    client_main.cpp
    basecamp_client.cpp
)

set(CLIENT_HEADERS
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include/basecamp_client.h
)

# Add the client executable
add_executable(basecamp_client ${CLIENT_SOURCES} ${CLIENT_HEADERS})

# Add dependencies
add_dependencies(basecamp_client proto_gen)

# Include directories
target_include_directories(basecamp_client PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
    ${PROTO_SRC_DIR}
    ${PROTO_GRPC_DIR}
)

# Link libraries
target_link_libraries(basecamp_client
    ${Protobuf_LIBRARIES}
    gRPC::grpc++
    Threads::Threads
    ${Boost_LIBRARIES}
    nlohmann_json::nlohmann_json
)

# Add the generated protobuf and gRPC files
target_sources(basecamp_client PRIVATE
    ${PROTO_SRC_DIR}/basecamp.pb.cc
    ${PROTO_GRPC_DIR}/basecamp.grpc.pb.cc
)
