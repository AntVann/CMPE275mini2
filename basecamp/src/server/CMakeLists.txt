set(SERVER_SOURCES
    server_main.cpp
    basecamp_service_impl.cpp
)

set(SERVER_HEADERS
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include/basecamp_service_impl.h
)

# Add the server executable
add_executable(basecamp_server ${SERVER_SOURCES} ${SERVER_HEADERS})

# Add dependencies
add_dependencies(basecamp_server proto_gen)

# Include directories
target_include_directories(basecamp_server PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
    ${PROTO_SRC_DIR}
    ${PROTO_GRPC_DIR}
)

# Link libraries
target_link_libraries(basecamp_server
    ${Protobuf_LIBRARIES}
    gRPC::grpc++
    gRPC::grpc++_reflection
    Threads::Threads
    ${Boost_LIBRARIES}
    nlohmann_json::nlohmann_json
)

# Add the generated protobuf and gRPC files
target_sources(basecamp_server PRIVATE
    ${PROTO_SRC_DIR}/basecamp.pb.cc
    ${PROTO_GRPC_DIR}/basecamp.grpc.pb.cc
)
