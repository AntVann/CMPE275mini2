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
#include <queue>
#include <functional>
#include <atomic>
#include <condition_variable>
#include <fstream>
#include <nlohmann/json.hpp>
#include <boost/interprocess/managed_shared_memory.hpp>
#include <boost/interprocess/containers/map.hpp>
#include <boost/interprocess/allocators/allocator.hpp>
#include <boost/interprocess/sync/named_mutex.hpp>
#include <grpcpp/grpcpp.h>
#include "proto-gen/basecamp.pb.h"
#include "grpc-gen/basecamp.grpc.pb.h"

// For convenience
using json = nlohmann::json;
namespace bip = boost::interprocess;

namespace basecamp {

// Cache entry for query results
struct CacheEntry {
    std::string query_id;
    QueryResponse response;
    std::chrono::time_point<std::chrono::system_clock> timestamp;
    
    bool isExpired(int ttl_seconds) const {
        auto now = std::chrono::system_clock::now();
        auto age = std::chrono::duration_cast<std::chrono::seconds>(now - timestamp).count();
        return age > ttl_seconds;
    }
};

// Shared memory data structure for key-value pairs
typedef std::pair<const int, std::string> SharedMemoryValue;
typedef bip::allocator<SharedMemoryValue, bip::managed_shared_memory::segment_manager> ShmemAllocator;
typedef bip::map<int, std::string, std::less<int>, ShmemAllocator> SharedMemoryMap;

class BasecampServiceImpl final : public BasecampService::AsyncService {
public:
    BasecampServiceImpl(const std::string& node_id, const std::string& config_path);
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

    // Handles a QueryData RPC call
    void HandleQueryData(
        grpc::ServerContext* context,
        const QueryRequest* request,
        QueryResponse* response,
        std::function<void(grpc::Status)> callback);
    
    // Handles a GatherData RPC call
    void HandleGatherData(
        grpc::ServerContext* context,
        const DataRequest* request,
        DataResponse* response,
        std::function<void(grpc::Status)> callback);

private:
    // Node identifier
    std::string node_id_;
    
    // Configuration
    json config_;
    std::vector<int> data_range_;
    bool is_portal_;
    std::string shared_memory_key_;
    int cache_size_;
    int cache_ttl_seconds_;
    
    // Connected peers
    struct PeerInfo {
        std::string address;
        std::unique_ptr<BasecampService::Stub> stub;
    };
    std::unordered_map<std::string, PeerInfo> peers_;
    
    // Shared memory
    std::unique_ptr<bip::managed_shared_memory> shared_memory_;
    std::unique_ptr<bip::named_mutex> shared_memory_mutex_;
    SharedMemoryMap* data_map_;
    
    // Cache for query results
    std::mutex cache_mutex_;
    std::deque<CacheEntry> query_cache_;
    
    // Load configuration from file
    void LoadConfig(const std::string& config_path);
    
    // Initialize shared memory
    void InitSharedMemory();
    
    // Initialize data (for testing)
    void InitializeTestData();
    
    // Connect to peers
    void ConnectToPeers();
    
    // Query local data
    void QueryLocalData(const QueryRequest& request, QueryResponse* response);
    
    // Query data from peers
    void QueryPeers(const QueryRequest& request, QueryResponse* response);
    
    // Forward a data request to peers
    void ForwardRequestToPeers(const DataRequest& request, DataResponse* aggregated_response);
    
    // Process a forwarded request
    void ProcessForwardedRequest(const DataRequest& request, DataResponse* response);
    
    // Create a data item with random data of different types
    DataItem CreateRandomDataItem(int key);
    
    // Check cache for query results
    bool CheckCache(const QueryRequest& request, QueryResponse* response);
    
    // Add result to cache
    void AddToCache(const std::string& query_id, const QueryResponse& response);
    
    // Clean expired cache entries
    void CleanCache();
    
    // Store data in shared memory
    bool StoreDataInSharedMemory(int key, const DataItem& item);
    
    // Retrieve data from shared memory
    bool RetrieveDataFromSharedMemory(int key, DataItem* item);
    
    // Convert between DataItem and string for shared memory storage
    std::string SerializeDataItem(const DataItem& item);
    DataItem DeserializeDataItem(const std::string& serialized);
    
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
