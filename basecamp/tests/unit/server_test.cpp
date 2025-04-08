#include <gtest/gtest.h>
#include <grpcpp/grpcpp.h>
#include <grpcpp/test/mock_stream.h>
#include "basecamp_service_impl.h"

using ::testing::_;
using ::testing::Return;
using ::testing::SetArgPointee;
using grpc::testing::MockClientReader;
using grpc::testing::MockClientWriter;
using grpc::testing::MockClientReaderWriter;

namespace basecamp {

class BasecampServiceTest : public ::testing::Test {
protected:
    void SetUp() override {
        service_ = std::make_unique<BasecampServiceImpl>();
    }

    std::unique_ptr<BasecampServiceImpl> service_;
};

// Test sending a message
TEST_F(BasecampServiceTest, SendMessage) {
    // Create a request
    MessageRequest request;
    request.set_sender_id("test_sender");
    request.set_receiver_id("test_receiver");
    request.set_content("Test message");
    request.set_timestamp(123456789);
    
    // Create a response
    MessageResponse response;
    
    // Create a context
    grpc::ServerContext context;
    
    // Call the method
    bool success = false;
    service_->HandleSendMessage(
        &context,
        &request,
        &response,
        [&success](grpc::Status status) {
            success = status.ok();
        });
    
    // Check the response
    EXPECT_TRUE(success);
    EXPECT_TRUE(response.success());
    EXPECT_FALSE(response.message_id().empty());
    EXPECT_GT(response.timestamp(), 0);
    EXPECT_TRUE(response.error_message().empty());
}

// Test subscribing to updates
TEST_F(BasecampServiceTest, SubscribeToUpdates) {
    // Create a request
    SubscriptionRequest request;
    request.set_subscriber_id("test_subscriber");
    request.add_topics("topic1");
    request.add_topics("topic2");
    
    // Create a context
    grpc::ServerContext context;
    
    // Create a mock writer
    class MockServerWriter : public grpc::ServerWriter<UpdateResponse> {
    public:
        MockServerWriter(grpc::ServerContext* context) : grpc::ServerWriter<UpdateResponse>(context) {}
        
        MOCK_METHOD1(Write, bool(const UpdateResponse& response));
    };
    
    MockServerWriter writer(&context);
    
    // Expect at least two writes (one for each topic)
    EXPECT_CALL(writer, Write(_)).WillRepeatedly(Return(true));
    
    // Call the method
    bool success = false;
    service_->HandleSubscribeToUpdates(
        &context,
        &request,
        &writer,
        [&success](grpc::Status status) {
            success = status.ok();
        });
    
    // Check the result
    EXPECT_TRUE(success);
}

// Test sending multiple messages
TEST_F(BasecampServiceTest, SendMultipleMessages) {
    // Create a context
    grpc::ServerContext context;
    
    // Create a mock reader
    class MockServerReader : public grpc::ServerReader<MessageRequest> {
    public:
        MockServerReader(grpc::ServerContext* context) : grpc::ServerReader<MessageRequest>(context) {}
        
        MOCK_METHOD1(Read, bool(MessageRequest* request));
    };
    
    MockServerReader reader(&context);
    
    // Set up the reader to return three messages
    MessageRequest request1, request2, request3;
    request1.set_sender_id("test_sender");
    request1.set_receiver_id("test_receiver1");
    request1.set_content("Test message 1");
    request1.set_timestamp(123456789);
    
    request2.set_sender_id("test_sender");
    request2.set_receiver_id("test_receiver2");
    request2.set_content("Test message 2");
    request2.set_timestamp(123456790);
    
    request3.set_sender_id("test_sender");
    request3.set_receiver_id("test_receiver3");
    request3.set_content("Test message 3");
    request3.set_timestamp(123456791);
    
    EXPECT_CALL(reader, Read(_))
        .WillOnce(DoAll(SetArgPointee<0>(request1), Return(true)))
        .WillOnce(DoAll(SetArgPointee<0>(request2), Return(true)))
        .WillOnce(DoAll(SetArgPointee<0>(request3), Return(true)))
        .WillOnce(Return(false));
    
    // Create a response
    BatchResponse response;
    
    // Call the method
    bool success = false;
    service_->HandleSendMultipleMessages(
        &context,
        &reader,
        &response,
        [&success](grpc::Status status) {
            success = status.ok();
        });
    
    // Check the response
    EXPECT_TRUE(success);
    EXPECT_EQ(response.success_count(), 3);
    EXPECT_EQ(response.failure_count(), 0);
    EXPECT_EQ(response.message_ids_size(), 3);
    EXPECT_TRUE(response.error_message().empty());
}

// Test chat
TEST_F(BasecampServiceTest, Chat) {
    // Create a context
    grpc::ServerContext context;
    
    // Create a mock stream
    class MockServerReaderWriter : public grpc::ServerReaderWriter<ChatMessage, ChatMessage> {
    public:
        MockServerReaderWriter(grpc::ServerContext* context) : grpc::ServerReaderWriter<ChatMessage, ChatMessage>(context) {}
        
        MOCK_METHOD1(Read, bool(ChatMessage* message));
        MOCK_METHOD1(Write, bool(const ChatMessage& message));
    };
    
    MockServerReaderWriter stream(&context);
    
    // Set up the stream to read two messages and expect two responses
    ChatMessage message1, message2;
    message1.set_sender_id("test_sender");
    message1.set_content("Test message 1");
    message1.set_timestamp(123456789);
    
    message2.set_sender_id("test_sender");
    message2.set_content("Test message 2");
    message2.set_timestamp(123456790);
    
    EXPECT_CALL(stream, Read(_))
        .WillOnce(DoAll(SetArgPointee<0>(message1), Return(true)))
        .WillOnce(DoAll(SetArgPointee<0>(message2), Return(true)))
        .WillOnce(Return(false));
    
    EXPECT_CALL(stream, Write(_))
        .WillRepeatedly(Return(true));
    
    // Call the method
    bool success = false;
    service_->HandleChat(
        &context,
        &stream,
        [&success](grpc::Status status) {
            success = status.ok();
        });
    
    // Check the result
    EXPECT_TRUE(success);
}

}  // namespace basecamp

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
