#include <gtest/gtest.h>
#include <grpcpp/grpcpp.h>
#include <grpcpp/test/mock_stream.h>
#include "basecamp_client.h"

using ::testing::_;
using ::testing::Return;
using ::testing::SetArgPointee;
using grpc::testing::MockClientReader;
using grpc::testing::MockClientWriter;
using grpc::testing::MockClientReaderWriter;

namespace basecamp {

// Mock class for the gRPC stub
class MockBasecampServiceStub : public BasecampService::StubInterface {
public:
    MOCK_METHOD3(SendMessage, grpc::Status(grpc::ClientContext* context, const MessageRequest& request, MessageResponse* response));
    MOCK_METHOD2(SubscribeToUpdates, std::unique_ptr<grpc::ClientReader<UpdateResponse>>(grpc::ClientContext* context, const SubscriptionRequest& request));
    MOCK_METHOD2(SendMultipleMessages, std::unique_ptr<grpc::ClientWriter<MessageRequest>>(grpc::ClientContext* context, BatchResponse* response));
    MOCK_METHOD1(Chat, std::unique_ptr<grpc::ClientReaderWriter<ChatMessage, ChatMessage>>(grpc::ClientContext* context));
};

class BasecampClientTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create a mock stub
        mock_stub_ = std::make_unique<MockBasecampServiceStub>();
        
        // Create a client with a mock channel
        client_ = std::make_unique<BasecampClient>("localhost:50051");
        
        // Replace the stub with our mock
        client_->stub_ = mock_stub_.get();
    }

    std::unique_ptr<MockBasecampServiceStub> mock_stub_;
    std::unique_ptr<BasecampClient> client_;
};

// Test sending a message
TEST_F(BasecampClientTest, SendMessage) {
    // Set up the mock to return a successful response
    MessageResponse response;
    response.set_success(true);
    response.set_message_id("test_message_id");
    response.set_timestamp(123456789);
    
    EXPECT_CALL(*mock_stub_, SendMessage(_, _, _))
        .WillOnce(DoAll(SetArgPointee<2>(response), Return(grpc::Status::OK)));
    
    // Call the method
    std::string message_id;
    bool result = client_->SendMessage("test_sender", "test_receiver", "Test message", &message_id);
    
    // Check the result
    EXPECT_TRUE(result);
    EXPECT_EQ(message_id, "test_message_id");
}

// Test subscribing to updates
TEST_F(BasecampClientTest, SubscribeToUpdates) {
    // Set up the mock to return a reader
    auto mock_reader = std::make_unique<MockClientReader<UpdateResponse>>();
    
    EXPECT_CALL(*mock_stub_, SubscribeToUpdates(_, _))
        .WillOnce(Return(std::move(mock_reader)));
    
    // Call the method
    bool result = client_->SubscribeToUpdates(
        "test_subscriber",
        {"topic1", "topic2"},
        [](const UpdateResponse& update) {
            // Do nothing
        });
    
    // Check the result
    EXPECT_TRUE(result);
}

// Test sending multiple messages
TEST_F(BasecampClientTest, SendMultipleMessages) {
    // Set up the mock to return a writer
    auto mock_writer = std::make_unique<MockClientWriter<MessageRequest>>();
    
    EXPECT_CALL(*mock_stub_, SendMultipleMessages(_, _))
        .WillOnce(Return(std::move(mock_writer)));
    
    // Call the method
    std::vector<MessageRequest> messages;
    MessageRequest request1, request2;
    request1.set_sender_id("test_sender");
    request1.set_receiver_id("test_receiver1");
    request1.set_content("Test message 1");
    request1.set_timestamp(123456789);
    
    request2.set_sender_id("test_sender");
    request2.set_receiver_id("test_receiver2");
    request2.set_content("Test message 2");
    request2.set_timestamp(123456790);
    
    messages.push_back(request1);
    messages.push_back(request2);
    
    BatchResponse response;
    bool result = client_->SendMultipleMessages(messages, &response);
    
    // Check the result
    EXPECT_TRUE(result);
}

// Test starting a chat session
TEST_F(BasecampClientTest, StartChat) {
    // Set up the mock to return a stream
    auto mock_stream = std::make_unique<MockClientReaderWriter<ChatMessage, ChatMessage>>();
    
    EXPECT_CALL(*mock_stub_, Chat(_))
        .WillOnce(Return(std::move(mock_stream)));
    
    // Call the method
    bool result = client_->StartChat(
        "test_sender",
        [](const ChatMessage& message) {
            // Do nothing
        },
        [](ChatMessage* message) {
            return false;  // Stop the chat immediately
        });
    
    // Check the result
    EXPECT_TRUE(result);
}

}  // namespace basecamp

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
