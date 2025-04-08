#include "basecamp_client.h"
#include <chrono>
#include <iostream>
#include <thread>

namespace basecamp {

BasecampClient::BasecampClient(const std::string& server_address)
    : running_(true) {
    // Create a channel to the server
    channel_ = grpc::CreateChannel(server_address, grpc::InsecureChannelCredentials());
    
    // Create a stub
    stub_ = BasecampService::NewStub(channel_);
}

BasecampClient::~BasecampClient() {
    running_ = false;
    
    // Wait for threads to finish
    if (subscription_thread_ && subscription_thread_->joinable()) {
        subscription_thread_->join();
    }
    
    if (chat_thread_ && chat_thread_->joinable()) {
        chat_thread_->join();
    }
}

bool BasecampClient::SendMessage(
    const std::string& sender_id,
    const std::string& receiver_id,
    const std::string& content,
    std::string* message_id) {
    
    // Create a request
    MessageRequest request;
    request.set_sender_id(sender_id);
    request.set_receiver_id(receiver_id);
    request.set_content(content);
    request.set_timestamp(GetCurrentTimestamp());
    
    // Create a response
    MessageResponse response;
    
    // Create a context
    grpc::ClientContext context;
    
    // Send the request
    grpc::Status status = stub_->SendMessage(&context, request, &response);
    
    // Check if the request was successful
    if (!status.ok()) {
        std::cerr << "Error sending message: " << status.error_message() << std::endl;
        return false;
    }
    
    // Check if the server processed the request successfully
    if (!response.success()) {
        std::cerr << "Server error: " << response.error_message() << std::endl;
        return false;
    }
    
    // Set the message ID if requested
    if (message_id) {
        *message_id = response.message_id();
    }
    
    return true;
}

bool BasecampClient::SubscribeToUpdates(
    const std::string& subscriber_id,
    const std::vector<std::string>& topics,
    std::function<void(const UpdateResponse&)> callback) {
    
    // Create a request
    SubscriptionRequest request;
    request.set_subscriber_id(subscriber_id);
    for (const auto& topic : topics) {
        request.add_topics(topic);
    }
    
    // Create a context
    auto context = std::make_shared<grpc::ClientContext>();
    
    // Create a reader
    auto reader = stub_->SubscribeToUpdates(context.get(), request);
    
    // Start a thread to read updates
    subscription_thread_ = std::make_unique<std::thread>([this, reader, callback, context]() {
        UpdateResponse update;
        
        while (running_ && reader->Read(&update)) {
            // Call the callback with the update
            callback(update);
        }
        
        // Check if there was an error
        grpc::Status status = reader->Finish();
        if (!status.ok()) {
            std::cerr << "Error subscribing to updates: " << status.error_message() << std::endl;
        }
    });
    
    return true;
}

bool BasecampClient::SendMultipleMessages(
    const std::vector<MessageRequest>& messages,
    BatchResponse* response) {
    
    // Create a context
    grpc::ClientContext context;
    
    // Create a writer
    auto writer = stub_->SendMultipleMessages(&context, response ? *response : BatchResponse());
    
    // Send each message
    for (const auto& message : messages) {
        if (!writer->Write(message)) {
            std::cerr << "Error sending message" << std::endl;
            return false;
        }
    }
    
    // Close the writer
    writer->WritesDone();
    
    // Check if there was an error
    grpc::Status status = writer->Finish();
    if (!status.ok()) {
        std::cerr << "Error sending multiple messages: " << status.error_message() << std::endl;
        return false;
    }
    
    return true;
}

bool BasecampClient::StartChat(
    const std::string& sender_id,
    std::function<void(const ChatMessage&)> receive_callback,
    std::function<bool(ChatMessage*)> get_next_message) {
    
    // Create a context
    auto context = std::make_shared<grpc::ClientContext>();
    
    // Create a stream
    auto stream = stub_->Chat(context.get());
    
    // Start a thread to handle the chat
    chat_thread_ = std::make_unique<std::thread>([this, stream, sender_id, receive_callback, get_next_message, context]() {
        // Create a thread to read messages
        auto read_thread = std::thread([this, stream, receive_callback]() {
            ChatMessage message;
            
            while (running_ && stream->Read(&message)) {
                // Call the callback with the message
                receive_callback(message);
            }
        });
        
        // Send messages
        ChatMessage message;
        message.set_sender_id(sender_id);
        
        while (running_ && get_next_message(&message)) {
            message.set_timestamp(GetCurrentTimestamp());
            
            if (!stream->Write(message)) {
                std::cerr << "Error sending chat message" << std::endl;
                break;
            }
        }
        
        // Close the stream
        stream->WritesDone();
        
        // Wait for the read thread to finish
        read_thread.join();
        
        // Check if there was an error
        grpc::Status status = stream->Finish();
        if (!status.ok()) {
            std::cerr << "Error in chat: " << status.error_message() << std::endl;
        }
    });
    
    return true;
}

int64_t BasecampClient::GetCurrentTimestamp() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

}  // namespace basecamp
