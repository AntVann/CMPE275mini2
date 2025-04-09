#include "basecamp_service_impl.h"
#include <chrono>
#include <iostream>
#include <random>
#include <sstream>

namespace basecamp {

BasecampServiceImpl::BasecampServiceImpl()
    : rng_(std::random_device()()),
      dist_(1, 0xFFFFFF) {  // Start from 1 to avoid empty strings
}

BasecampServiceImpl::~BasecampServiceImpl() {
}

void BasecampServiceImpl::HandleSendMessage(
    grpc::ServerContext* context,
    const MessageRequest* request,
    MessageResponse* response,
    std::function<void(grpc::Status)> callback) {
    
    // Generate a message ID and store the message
    std::string message_id;
    bool success = StoreMessage(*request, &message_id);
    
    // Set the response
    response->set_success(success);
    response->set_message_id(message_id);
    response->set_timestamp(GetCurrentTimestamp());
    
    if (!success) {
        response->set_error_message("Failed to store message");
    }
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

void BasecampServiceImpl::HandleSubscribeToUpdates(
    grpc::ServerContext* context,
    const SubscriptionRequest* request,
    grpc::ServerWriter<UpdateResponse>* writer,
    std::function<void(grpc::Status)> callback) {
    
    // Store the subscription
    {
        std::lock_guard<std::mutex> lock(mutex_);
        auto& topics = subscriptions_[request->subscriber_id()];
        topics.clear();
        for (const auto& topic : request->topics()) {
            topics.push_back(topic);
        }
    }
    
    // Send initial updates for each topic
    for (const auto& topic : request->topics()) {
        UpdateResponse update;
        update.set_topic(topic);
        update.set_content("Subscribed to " + topic);
        update.set_timestamp(GetCurrentTimestamp());
        
        if (!writer->Write(update)) {
            break;
        }
    }
    
    // Simulate sending periodic updates
    int count = 0;
    while (!context->IsCancelled() && count < 10) {
        std::this_thread::sleep_for(std::chrono::seconds(1));
        
        for (const auto& topic : request->topics()) {
            UpdateResponse update;
            update.set_topic(topic);
            update.set_content("Update " + std::to_string(count) + " for " + topic);
            update.set_timestamp(GetCurrentTimestamp());
            
            if (!writer->Write(update)) {
                break;
            }
        }
        
        count++;
    }
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

void BasecampServiceImpl::HandleSendMultipleMessages(
    grpc::ServerContext* context,
    grpc::ServerReader<MessageRequest>* reader,
    BatchResponse* response,
    std::function<void(grpc::Status)> callback) {
    
    MessageRequest request;
    int success_count = 0;
    int failure_count = 0;
    
    // Process each message
    while (reader->Read(&request)) {
        std::string message_id;
        bool success = StoreMessage(request, &message_id);
        
        if (success) {
            success_count++;
            response->add_message_ids(message_id);
        } else {
            failure_count++;
        }
    }
    
    // Set the response
    response->set_success_count(success_count);
    response->set_failure_count(failure_count);
    
    if (failure_count > 0) {
        response->set_error_message("Failed to store " + std::to_string(failure_count) + " messages");
    }
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

void BasecampServiceImpl::HandleChat(
    grpc::ServerContext* context,
    grpc::ServerReaderWriter<ChatMessage, ChatMessage>* stream,
    std::function<void(grpc::Status)> callback) {
    
    ChatMessage message;
    
    // Read and echo messages
    while (stream->Read(&message)) {
        // Echo the message back
        ChatMessage response;
        response.set_sender_id("server");
        response.set_content("Echo: " + message.content());
        response.set_timestamp(GetCurrentTimestamp());
        
        if (!stream->Write(response)) {
            break;
        }
    }
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

std::string BasecampServiceImpl::GenerateMessageId() {
    std::lock_guard<std::mutex> lock(mutex_);
    
    // Generate a random message ID
    std::stringstream ss;
    ss << "msg_" << std::hex << dist_(rng_);
    
    // Ensure the message ID is not empty
    std::string message_id = ss.str();
    if (message_id.empty() || message_id == "msg_") {
        message_id = "msg_" + std::to_string(GetCurrentTimestamp());
    }
    
    return message_id;
}

int64_t BasecampServiceImpl::GetCurrentTimestamp() {
    return std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
}

bool BasecampServiceImpl::StoreMessage(const MessageRequest& message, std::string* message_id) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    // Generate a message ID
    *message_id = GenerateMessageId();
    
    // Store the message
    messages_[*message_id] = message;
    
    return true;
}

}  // namespace basecamp
