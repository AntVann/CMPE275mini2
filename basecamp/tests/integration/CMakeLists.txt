# Find GTest package
find_package(GTest REQUIRED)

set(TEST_SOURCES
    integration_test.cpp
)

# Add the test executable
add_executable(basecamp_integration_tests ${TEST_SOURCES})

# Add dependencies
add_dependencies(basecamp_integration_tests proto_gen)

# Include directories
target_include_directories(basecamp_integration_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/../../include
    ${PROTO_SRC_DIR}
    ${PROTO_GRPC_DIR}
    ${GTEST_INCLUDE_DIRS}
)

# Link libraries
target_link_libraries(basecamp_integration_tests
    ${Protobuf_LIBRARIES}
    gRPC::grpc++
    Threads::Threads
    ${GTEST_LIBRARIES}
    gtest
    gtest_main
)

# Add the generated protobuf and gRPC files
target_sources(basecamp_integration_tests PRIVATE
    ${PROTO_SRC_DIR}/basecamp.pb.cc
    ${PROTO_GRPC_DIR}/basecamp.grpc.pb.cc
)

# Add test
add_test(NAME basecamp_integration_tests COMMAND basecamp_integration_tests)
