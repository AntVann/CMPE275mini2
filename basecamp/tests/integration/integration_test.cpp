#include <gtest/gtest.h>
#include <grpcpp/grpcpp.h>
#include <thread>
#include <chrono>
#include <memory>
#include "basecamp_service_impl.h"
#include "basecamp_client.h"

namespace basecamp {

class BasecampIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Start the server in a separate thread
        server_thread_ = std::thread([this]() {
            // Create a server
            grpc::ServerBuilder builder;
            builder.AddListeningPort("localhost:50052", grpc::InsecureServerCredentials());
            builder.RegisterService(&service_);
            server_ = builder.BuildAndStart();
            
            // Wait for the server to shutdown
            server_->Wait();
        });
        
        // Wait for the server to start
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Create a client
        client_ = std::make_unique<BasecampClient>("localhost:50052");
    }
    
    void TearDown() override {
        // Shutdown the server
        if (server_) {
            server_->Shutdown();
        }
        
        // Wait for the server thread to finish
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }

    BasecampServiceImpl service_;
    std::unique_ptr<grpc::Server> server_;
    std::thread server_thread_;
    std::unique_ptr<BasecampClient> client_;
};

// Test sending a message
TEST_F(BasecampIntegrationTest, SendMessage) {
    // Send a message
    std::string message_id;
    bool result = client_->SendMessage("test_sender", "test_receiver", "Test message", &message_id);
    
    // Check the result
    EXPECT_TRUE(result);
    EXPECT_FALSE(message_id.empty());
}

// Test subscribing to updates
TEST_F(BasecampIntegrationTest, SubscribeToUpdates) {
    // Subscribe to updates
    bool received_update = false;
    bool result = client_->SubscribeToUpdates(
        "test_subscriber",
        {"topic1", "topic2"},
        [&received_update](const UpdateResponse& update) {
            received_update = true;
        });
    
    // Check the result
    EXPECT_TRUE(result);
    
    // Wait for updates
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Check if we received any updates
    EXPECT_TRUE(received_update);
}

// Test sending multiple messages
TEST_F(BasecampIntegrationTest, SendMultipleMessages) {
    // Create messages
    std::vector<MessageRequest> messages;
    MessageRequest request1, request2;
    request1.set_sender_id("test_sender");
    request1.set_receiver_id("test_receiver1");
    request1.set_content("Test message 1");
    request1.set_timestamp(BasecampClient::GetCurrentTimestamp());
    
    request2.set_sender_id("test_sender");
    request2.set_receiver_id("test_receiver2");
    request2.set_content("Test message 2");
    request2.set_timestamp(BasecampClient::GetCurrentTimestamp());
    
    messages.push_back(request1);
    messages.push_back(request2);
    
    // Send the messages
    BatchResponse response;
    bool result = client_->SendMultipleMessages(messages, &response);
    
    // Check the result
    EXPECT_TRUE(result);
    EXPECT_EQ(response.success_count(), 2);
    EXPECT_EQ(response.failure_count(), 0);
    EXPECT_EQ(response.message_ids_size(), 2);
}

// Test chat
TEST_F(BasecampIntegrationTest, Chat) {
    // Start a chat session
    bool received_message = false;
    bool sent_message = false;
    
    bool result = client_->StartChat(
        "test_sender",
        [&received_message](const ChatMessage& message) {
            received_message = true;
        },
        [&sent_message](ChatMessage* message) {
            if (!sent_message) {
                message->set_content("Test message");
                sent_message = true;
                return true;
            }
            return false;  // Stop the chat after sending one message
        });
    
    // Check the result
    EXPECT_TRUE(result);
    
    // Wait for the chat to finish
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    // Check if we sent and received messages
    EXPECT_TRUE(sent_message);
    EXPECT_TRUE(received_message);
}

}  // namespace basecamp

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
