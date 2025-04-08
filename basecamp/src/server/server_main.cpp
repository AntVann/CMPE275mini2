#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <grpcpp/grpcpp.h>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <grpcpp/server_context.h>
#include "basecamp_service_impl.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;

// Class to handle asynchronous server operations
class AsyncBasecampServer {
public:
    AsyncBasecampServer(const std::string& server_address)
        : server_address_(server_address), shutdown_(false) {}

    ~AsyncBasecampServer() {
        Shutdown();
    }

    // Start the server
    void Start() {
        // Build the server
        ServerBuilder builder;
        builder.AddListeningPort(server_address_, grpc::InsecureServerCredentials());
        
        // Register the service
        builder.RegisterService(&service_);
        
        // Create the completion queue
        cq_ = builder.AddCompletionQueue();
        
        // Build and start the server
        server_ = builder.BuildAndStart();
        std::cout << "Server listening on " << server_address_ << std::endl;

        // Start handling requests
        HandleRpcs();
    }

    // Shutdown the server
    void Shutdown() {
        if (!shutdown_) {
            shutdown_ = true;
            server_->Shutdown();
            cq_->Shutdown();
            
            // Wait for the server to shutdown
            if (server_thread_.joinable()) {
                server_thread_.join();
            }
        }
    }

private:
    // Handle all RPCs
    void HandleRpcs() {
        server_thread_ = std::thread([this]() {
            // Create a new CallData instance for each RPC
            new CallData(&service_, cq_.get());
            
            void* tag;
            bool ok;
            
            while (true) {
                // Wait for a new event
                if (!cq_->Next(&tag, &ok)) {
                    break;
                }
                
                // Process the event
                if (ok) {
                    static_cast<CallData*>(tag)->Proceed();
                }
            }
        });
    }

    // Class to handle a single RPC
    class CallData {
    public:
        CallData(basecamp::BasecampServiceImpl* service, grpc::CompletionQueue* cq)
            : service_(service), cq_(cq), status_(CREATE) {
            Proceed();
        }

        void Proceed() {
            if (status_ == CREATE) {
                status_ = PROCESS;
                
                // Request a new RPC
                // Use the same completion queue for both new calls and notifications
                grpc::ServerCompletionQueue* notification_cq = static_cast<grpc::ServerCompletionQueue*>(cq_);
                service_->RequestSendMessage(&ctx_, &request_, &responder_, cq_, notification_cq, this);
            } else if (status_ == PROCESS) {
                // Create a new CallData instance for the next request
                new CallData(service_, cq_);
                
                // Process the request
                std::string message_id;
                bool success = true;
                std::string error_message;
                
                // Set the response
                response_.set_success(success);
                response_.set_message_id(message_id);
                response_.set_timestamp(std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::system_clock::now().time_since_epoch()).count());
                if (!error_message.empty()) {
                    response_.set_error_message(error_message);
                }
                
                // Finish the RPC
                status_ = FINISH;
                responder_.Finish(response_, Status::OK, this);
            } else {
                // We're done with this RPC
                delete this;
            }
        }

    private:
        basecamp::BasecampServiceImpl* service_;
        grpc::CompletionQueue* cq_;
        ServerContext ctx_;
        
        // Request and response objects
        basecamp::MessageRequest request_;
        basecamp::MessageResponse response_;
        
        // Responder for the RPC
        grpc::ServerAsyncResponseWriter<basecamp::MessageResponse> responder_{&ctx_};
        
        // Status of the RPC
        enum CallStatus { CREATE, PROCESS, FINISH };
        CallStatus status_;
    };

    std::string server_address_;
    basecamp::BasecampServiceImpl service_;
    std::unique_ptr<Server> server_;
    std::unique_ptr<grpc::ServerCompletionQueue> cq_;
    std::thread server_thread_;
    bool shutdown_;
};

int main(int argc, char** argv) {
    // Default server address
    std::string server_address = "0.0.0.0:50051";
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--address" && i + 1 < argc) {
            server_address = argv[++i];
        }
    }
    
    // Create and start the server
    AsyncBasecampServer server(server_address);
    server.Start();
    
    // Wait for the server to shutdown
    std::cout << "Press enter to shutdown the server..." << std::endl;
    std::string line;
    std::getline(std::cin, line);
    
    // Shutdown the server
    server.Shutdown();
    
    return 0;
}
