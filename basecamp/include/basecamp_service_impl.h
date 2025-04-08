#ifndef BASECAMP_SERVICE_IMPL_H
#define BASECAMP_SERVICE_IMPL_H

#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <random>
#include <thread>
#include <grpcpp/grpcpp.h>
#include "proto-gen/basecamp.pb.h"
#include "grpc-gen/basecamp.grpc.pb.h"

namespace basecamp {

class BasecampServiceImpl final : public BasecampService::AsyncService {
public:
    BasecampServiceImpl();
    ~BasecampServiceImpl();

    // Handles a SendMessage RPC call
    void HandleSendMessage(
        grpc::ServerContext* context,
        const MessageRequest* request,
        MessageResponse* response,
        std::function<void(grpc::Status)> callback);

    // Handles a SubscribeToUpdates RPC call
    void HandleSubscribeToUpdates(
        grpc::ServerContext* context,
        const SubscriptionRequest* request,
        grpc::ServerWriter<UpdateResponse>* writer,
        std::function<void(grpc::Status)> callback);

    // Handles a SendMultipleMessages RPC call
    void HandleSendMultipleMessages(
        grpc::ServerContext* context,
        grpc::ServerReader<MessageRequest>* reader,
        BatchResponse* response,
        std::function<void(grpc::Status)> callback);

    // Handles a Chat RPC call
    void HandleChat(
        grpc::ServerContext* context,
        grpc::ServerReaderWriter<ChatMessage, ChatMessage>* stream,
        std::function<void(grpc::Status)> callback);

private:
    // Generate a unique message ID
    std::string GenerateMessageId();

    // Get current timestamp
    int64_t GetCurrentTimestamp();

    // Store a message
    bool StoreMessage(const MessageRequest& message, std::string* message_id);

    // Mutex for thread safety
    std::mutex mutex_;

    // In-memory storage for messages
    std::unordered_map<std::string, MessageRequest> messages_;

    // In-memory storage for subscriptions
    std::unordered_map<std::string, std::vector<std::string>> subscriptions_;

    // Random number generator for message IDs
    std::mt19937 rng_;
    std::uniform_int_distribution<int> dist_;
};

}  // namespace basecamp

#endif  // BASECAMP_SERVICE_IMPL_H
