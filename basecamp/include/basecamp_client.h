#ifndef BASECAMP_CLIENT_H
#define BASECAMP_CLIENT_H

#include <memory>
#include <string>
#include <thread>
#include <grpcpp/grpcpp.h>
#include "proto-gen/basecamp.pb.h"
#include "grpc-gen/basecamp.grpc.pb.h"

namespace basecamp {

class BasecampClient {
public:
    // Constructor that takes a server address
    BasecampClient(const std::string& server_address);
    
    // Destructor
    ~BasecampClient();

    // Send a message to another process
    bool SendMessage(const std::string& sender_id, 
                     const std::string& receiver_id, 
                     const std::string& content,
                     std::string* message_id = nullptr);

    // Subscribe to updates from specific topics
    bool SubscribeToUpdates(const std::string& subscriber_id,
                           const std::vector<std::string>& topics,
                           std::function<void(const UpdateResponse&)> callback);

    // Send multiple messages in a batch
    bool SendMultipleMessages(const std::vector<MessageRequest>& messages,
                             BatchResponse* response = nullptr);

    // Start a chat session
    bool StartChat(const std::string& sender_id,
                  std::function<void(const ChatMessage&)> receive_callback,
                  std::function<bool(ChatMessage*)> get_next_message);

    // Get the current timestamp
    static int64_t GetCurrentTimestamp();

private:
    // The gRPC channel and stub
    std::unique_ptr<BasecampService::Stub> stub_;
    std::shared_ptr<grpc::Channel> channel_;

    // Thread for handling streaming responses
    std::unique_ptr<std::thread> subscription_thread_;
    std::unique_ptr<std::thread> chat_thread_;

    // Flag to indicate if the client is running
    bool running_;
};

}  // namespace basecamp

#endif  // BASECAMP_CLIENT_H
