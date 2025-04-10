#include "basecamp_service_impl.h"
#include <chrono>
#include <iostream>
#include <random>
#include <sstream>
#include <fstream>
#include <algorithm>
#include <filesystem>
#include <future>

namespace basecamp {

BasecampServiceImpl::BasecampServiceImpl(const std::string& node_id, const std::string& config_path)
    : node_id_(node_id),
      rng_(std::random_device()()),
      dist_(1, 0xFFFFFF) {  // Start from 1 to avoid empty strings
    
    // Load configuration
    LoadConfig(config_path);
    
    // Initialize shared memory
    InitSharedMemory();
    
    // Initialize test data
    InitializeTestData();
    
    // Connect to peers
    ConnectToPeers();
    
    std::cout << "BasecampServiceImpl initialized for node " << node_id_ << std::endl;
    std::cout << "Data range: [" << data_range_[0] << ", " << data_range_[1] << "]" << std::endl;
    std::cout << "Is portal: " << (is_portal_ ? "yes" : "no") << std::endl;
    std::cout << "Connected to " << peers_.size() << " peers" << std::endl;
}

BasecampServiceImpl::~BasecampServiceImpl() {
    // Clean up shared memory
    if (shared_memory_) {
        shared_memory_->destroy<SharedMemoryMap>("DataMap");
        bip::shared_memory_object::remove(shared_memory_key_.c_str());
    }
    
    if (shared_memory_mutex_) {
        bip::named_mutex::remove(std::string(shared_memory_key_ + "_mutex").c_str());
    }
}

void BasecampServiceImpl::LoadConfig(const std::string& config_path) {
    try {
        // Read the configuration file
        std::ifstream config_file(config_path);
        if (!config_file.is_open()) {
            std::cerr << "Failed to open config file: " << config_path << std::endl;
            throw std::runtime_error("Failed to open config file");
        }
        
        // Parse the JSON
        config_ = json::parse(config_file);
        
        // Check if the node exists in the configuration
        if (!config_["nodes"].contains(node_id_)) {
            std::cerr << "Node " << node_id_ << " not found in configuration" << std::endl;
            throw std::runtime_error("Node not found in configuration");
        }
        
        // Get the data range for this node
        auto& node_config = config_["nodes"][node_id_];
        data_range_ = {node_config["data_range"][0], node_config["data_range"][1]};
        
        // Check if this node is the portal
        is_portal_ = (config_["portal"] == node_id_);
        
        // Get shared memory configuration
        shared_memory_key_ = config_["shared_memory_key"];
        
        // Get cache configuration
        cache_size_ = config_["cache_size"];
        cache_ttl_seconds_ = config_["cache_ttl_seconds"];
        
        std::cout << "Configuration loaded successfully" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error loading configuration: " << e.what() << std::endl;
        throw;
    }
}

void BasecampServiceImpl::InitSharedMemory() {
    try {
        // Remove any existing shared memory with the same name
        bip::shared_memory_object::remove(shared_memory_key_.c_str());
        bip::named_mutex::remove(std::string(shared_memory_key_ + "_mutex").c_str());
        
        // Create shared memory
        shared_memory_ = std::make_unique<bip::managed_shared_memory>(
            bip::create_only, shared_memory_key_.c_str(), 65536);
        
        // Create named mutex for synchronization
        shared_memory_mutex_ = std::make_unique<bip::named_mutex>(
            bip::create_only, std::string(shared_memory_key_ + "_mutex").c_str());
        
        // Create the map in shared memory
        ShmemAllocator alloc_inst(shared_memory_->get_segment_manager());
        data_map_ = shared_memory_->construct<SharedMemoryMap>("DataMap")(std::less<int>(), alloc_inst);
        
        std::cout << "Shared memory initialized successfully" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error initializing shared memory: " << e.what() << std::endl;
        throw;
    }
}

void BasecampServiceImpl::InitializeTestData() {
    // Generate some test data within this node's data range
    for (int key = data_range_[0]; key <= data_range_[1]; key++) {
        DataItem item = CreateRandomDataItem(key);
        StoreDataInSharedMemory(key, item);
    }
    
    std::cout << "Test data initialized successfully" << std::endl;
}

DataItem BasecampServiceImpl::CreateRandomDataItem(int key) {
    DataItem item;
    item.set_key(key);
    item.set_source_node(node_id_);
    item.set_timestamp(GetCurrentTimestamp());
    
    // Set random data type
    static const std::vector<std::string> data_types = {"user", "product", "transaction", "event", "log"};
    item.set_data_type(data_types[key % data_types.size()]);
    
    // Add some metadata
    (*item.mutable_metadata())["created_by"] = node_id_;
    (*item.mutable_metadata())["version"] = "1.0";
    
    // Set a random value type based on the key
    switch (key % 5) {
        case 0: {
            // String value
            item.set_string_value("String value for key " + std::to_string(key) + " from " + node_id_);
            break;
        }
        case 1: {
            // Double value
            item.set_double_value(key * 1.5);
            break;
        }
        case 2: {
            // Boolean value
            item.set_bool_value(key % 2 == 0);
            break;
        }
        case 3: {
            // Nested object
            NestedObject* obj = new NestedObject();
            obj->set_name("Object_" + std::to_string(key));
            obj->add_tags("tag1");
            obj->add_tags("tag2");
            (*obj->mutable_properties())["property1"] = "value1";
            (*obj->mutable_properties())["property2"] = "value2";
            obj->set_created_at(GetCurrentTimestamp() - 3600000);  // 1 hour ago
            obj->set_updated_at(GetCurrentTimestamp());
            item.set_allocated_object_value(obj);
            break;
        }
        case 4: {
            // Binary value
            std::string binary_data = "Binary data for key " + std::to_string(key);
            item.set_binary_value(binary_data);
            break;
        }
    }
    
    return item;
}

void BasecampServiceImpl::ConnectToPeers() {
    try {
        // Get the list of peers for this node
        auto& node_config = config_["nodes"][node_id_];
        auto& connects_to = node_config["connects_to"];
        
        // Connect to each peer
        for (const auto& peer_id : connects_to) {
            std::string peer_id_str = peer_id;
            
            // Skip if the peer is not in the configuration
            if (!config_["nodes"].contains(peer_id_str)) {
                std::cerr << "Peer " << peer_id_str << " not found in configuration" << std::endl;
                continue;
            }
            
            // Get the peer's address
            auto& peer_config = config_["nodes"][peer_id_str];
            int peer_port = peer_config["port"];
            
            // Determine the peer's IP address based on the computer
            std::string peer_ip = "127.0.0.1";  // Default to localhost
            
            // Create the peer's address
            std::string peer_address = peer_ip + ":" + std::to_string(peer_port);
            
            // Create a channel to the peer
            auto channel = grpc::CreateChannel(peer_address, grpc::InsecureChannelCredentials());
            
            // Create a stub
            auto stub = BasecampService::NewStub(channel);
            
            // Store the peer information
            PeerInfo peer_info;
            peer_info.address = peer_address;
            peer_info.stub = std::move(stub);
            peers_[peer_id_str] = std::move(peer_info);
            
            std::cout << "Connected to peer " << peer_id_str << " at " << peer_address << std::endl;
        }
    } catch (const std::exception& e) {
        std::cerr << "Error connecting to peers: " << e.what() << std::endl;
        throw;
    }
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
    
    // Start timing the processing
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Set a timeout for the entire operation
    auto timeout = std::chrono::milliseconds(4000);  // 4 seconds timeout
    
    MessageRequest request;
    int success_count = 0;
    int failure_count = 0;
    
    // Process each message with a timeout
    while (reader->Read(&request)) {
        // Check if we've exceeded the timeout
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
        
        if (elapsed >= timeout) {
            std::cerr << "Timeout processing multiple messages" << std::endl;
            break;
        }
        
        // Process the message
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
    
    // Set the processing time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
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

void BasecampServiceImpl::HandleQueryData(
    grpc::ServerContext* context,
    const QueryRequest* request,
    QueryResponse* response,
    std::function<void(grpc::Status)> callback) {
    
    // Only the portal node can handle client queries
    if (!is_portal_) {
        response->set_success(false);
        response->set_error_message("This node is not the portal");
        callback(grpc::Status::OK);
        return;
    }
    
    // Start timing the query
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Set a timeout for the entire operation
    auto timeout = std::chrono::milliseconds(4000);  // 4 seconds timeout
    
    // Set the query ID and timestamp
    response->set_query_id(request->query_id());
    response->set_timestamp(GetCurrentTimestamp());
    
    // Check if the result is in the cache
    bool cache_hit = CheckCache(*request, response);
    if (cache_hit) {
        // Set the processing time
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
        response->set_processing_time(duration.count());
        
        // Call the callback with OK status
        callback(grpc::Status::OK);
        return;
    }
    
    // Query local data
    QueryLocalData(*request, response);
    
    // Check if we've exceeded the timeout
    auto now = std::chrono::high_resolution_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
    
    if (elapsed < timeout) {
        // Query peers
        QueryPeers(*request, response);
    } else {
        std::cerr << "Timeout exceeded, skipping peer queries" << std::endl;
    }
    
    // Set success flag
    response->set_success(true);
    
    // Set the processing time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    response->set_processing_time(duration.count());
    
    // Add the result to the cache
    AddToCache(request->query_id(), *response);
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

void BasecampServiceImpl::HandleGatherData(
    grpc::ServerContext* context,
    const DataRequest* request,
    DataResponse* response,
    std::function<void(grpc::Status)> callback) {
    
    // Start timing the processing
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Set the request ID and timestamp
    response->set_request_id(request->request_id());
    response->set_timestamp(GetCurrentTimestamp());
    response->set_responder_id(node_id_);
    
    // Update the route path
    std::string route_path = request->route_path();
    if (!route_path.empty()) {
        route_path += "->";
    }
    route_path += node_id_;
    response->set_route_path(route_path);
    
    // Add this node to the contributing nodes
    response->add_contributing_nodes(node_id_);
    
    // Process the request locally
    ProcessForwardedRequest(*request, response);
    
    // Forward the request to peers if needed
    if (request->forward_to_peers()) {
        // Create a copy of the request for forwarding
        DataRequest forwarded_request = *request;
        
        // Increment the hop count
        forwarded_request.set_hop_count(request->hop_count() + 1);
        
        // Update the route path
        forwarded_request.set_route_path(route_path);
        
        // Add this node to the visited nodes
        forwarded_request.add_visited_nodes(node_id_);
        
        // Only forward if we haven't reached the maximum hop count
        if (forwarded_request.hop_count() < forwarded_request.max_hops()) {
            ForwardRequestToPeers(forwarded_request, response);
        }
    }
    
    // Set success flag
    response->set_success(true);
    
    // Set the processing time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    response->set_processing_time(duration.count());
    
    // Call the callback with OK status
    callback(grpc::Status::OK);
}

void BasecampServiceImpl::ProcessForwardedRequest(const DataRequest& request, DataResponse* response) {
    // Check if the key is in this node's data range
    int key = request.key();
    bool in_range = false;
    
    if (request.query_type() == "exact") {
        in_range = (key >= data_range_[0] && key <= data_range_[1]);
    } else if (request.query_type() == "range") {
        // Check if any part of the range overlaps with this node's data range
        int range_start = request.range_start();
        int range_end = request.range_end();
        in_range = (range_start <= data_range_[1] && range_end >= data_range_[0]);
    } else if (request.query_type() == "all") {
        in_range = true;
    }
    
    if (!in_range) {
        // This node doesn't have the requested data
        return;
    }
    
    // Query the data
    if (request.query_type() == "exact") {
        // Exact key query
        DataItem item;
        bool found = RetrieveDataFromSharedMemory(key, &item);
        
        if (found) {
            *response->add_data_items() = item;
        }
    } else if (request.query_type() == "range") {
        // Range query
        int range_start = std::max(request.range_start(), data_range_[0]);
        int range_end = std::min(request.range_end(), data_range_[1]);
        
        for (int k = range_start; k <= range_end; k++) {
            DataItem item;
            bool found = RetrieveDataFromSharedMemory(k, &item);
            
            if (found) {
                *response->add_data_items() = item;
            }
        }
    } else if (request.query_type() == "all") {
        // All data in this node's range
        for (int k = data_range_[0]; k <= data_range_[1]; k++) {
            DataItem item;
            bool found = RetrieveDataFromSharedMemory(k, &item);
            
            if (found) {
                *response->add_data_items() = item;
            }
        }
    }
}

void BasecampServiceImpl::ForwardRequestToPeers(const DataRequest& request, DataResponse* aggregated_response) {
    // Create a vector to store the futures
    std::vector<std::future<void>> futures;
    std::mutex response_mutex;
    
    // For each peer
    for (const auto& [peer_id, peer_info] : peers_) {
        // Skip peers that have already been visited
        bool already_visited = false;
        for (const auto& visited : request.visited_nodes()) {
            if (visited == peer_id) {
                already_visited = true;
                break;
            }
        }
        
        if (already_visited) {
            continue;
        }
        
        // Only forward to peers that might have the data
        bool should_forward = false;
        
        if (request.query_type() == "exact") {
            // Check if the peer's data range contains the key
            auto& peer_config = config_["nodes"][peer_id];
            int peer_range_start = peer_config["data_range"][0];
            int peer_range_end = peer_config["data_range"][1];
            
            should_forward = (request.key() >= peer_range_start && request.key() <= peer_range_end);
        } else if (request.query_type() == "range") {
            // Check if the peer's data range overlaps with the query range
            auto& peer_config = config_["nodes"][peer_id];
            int peer_range_start = peer_config["data_range"][0];
            int peer_range_end = peer_config["data_range"][1];
            
            should_forward = (request.range_start() <= peer_range_end && request.range_end() >= peer_range_start);
        } else if (request.query_type() == "all") {
            // Always forward for "all" queries
            should_forward = true;
        }
        
        if (!should_forward) {
            continue;
        }
        
        // Create a future to forward the request to this peer
        auto future = std::async(std::launch::async, [this, peer_id, &peer_info, &request, aggregated_response, &response_mutex]() {
            // Create a context with a longer timeout
            grpc::ClientContext context;
            context.set_deadline(std::chrono::system_clock::now() + std::chrono::milliseconds(5000));
            
            // Create a response
            DataResponse peer_response;
            
            try {
                // Send the request with a timeout
                grpc::Status status = peer_info.stub->GatherData(&context, request, &peer_response);
                
                // Check if the request was successful
                if (!status.ok()) {
                    std::cerr << "Error forwarding request to peer " << peer_id << ": " << status.error_message() << std::endl;
                    return;
                }
                
                // Check if the peer processed the request successfully
                if (!peer_response.success()) {
                    std::cerr << "Peer " << peer_id << " error: " << peer_response.error_message() << std::endl;
                    return;
                }
                
                // Lock the mutex before updating the aggregated response
                std::lock_guard<std::mutex> lock(response_mutex);
                
                // Add the peer's data items to the aggregated response
                for (const auto& item : peer_response.data_items()) {
                    *aggregated_response->add_data_items() = item;
                }
                
                // Add the peer's contributing nodes to the aggregated response
                for (const auto& node : peer_response.contributing_nodes()) {
                    aggregated_response->add_contributing_nodes(node);
                }
            } catch (const std::exception& e) {
                std::cerr << "Exception forwarding request to peer " << peer_id << ": " << e.what() << std::endl;
            }
        });
        
        futures.push_back(std::move(future));
    }
    
    // Wait for all futures to complete with a timeout
    auto start_time = std::chrono::high_resolution_clock::now();
    auto timeout = std::chrono::milliseconds(4000);  // 4 seconds timeout
    
    for (auto& future : futures) {
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
        
        if (elapsed >= timeout) {
            std::cerr << "Timeout waiting for peer responses" << std::endl;
            break;
        }
        
        auto remaining = timeout - elapsed;
        auto status = future.wait_for(remaining);
        
        if (status != std::future_status::ready) {
            std::cerr << "Timeout waiting for a peer response" << std::endl;
        }
    }
}

void BasecampServiceImpl::QueryLocalData(const QueryRequest& request, QueryResponse* response) {
    // Check if the key is in this node's data range
    int key = request.key();
    bool in_range = false;
    
    if (request.query_type() == "exact" || request.query_type() == "write") {
        in_range = (key >= data_range_[0] && key <= data_range_[1]);
    } else if (request.query_type() == "range") {
        // Check if any part of the range overlaps with this node's data range
        int range_start = request.range_start();
        int range_end = request.range_end();
        in_range = (range_start <= data_range_[1] && range_end >= data_range_[0]);
    } else if (request.query_type() == "all") {
        in_range = true;
    }
    
    if (!in_range) {
        // This node doesn't have the requested data
        return;
    }
    
    // Query or write the data
    if (request.query_type() == "exact") {
        // Exact key query
        DataItem item;
        bool found = RetrieveDataFromSharedMemory(key, &item);
        
        if (found) {
            *response->add_results() = item;
        }
    } else if (request.query_type() == "write") {
        // Write operation
        DataItem item;
        item.set_key(key);
        item.set_string_value(request.string_param());
        item.set_source_node(node_id_);
        item.set_timestamp(GetCurrentTimestamp());
        item.set_data_type("string");
        (*item.mutable_metadata())["created_by"] = node_id_;
        (*item.mutable_metadata())["version"] = "1.0";
        
        bool success = StoreDataInSharedMemory(key, item);
        
        if (success) {
            *response->add_results() = item;
        }
    } else if (request.query_type() == "range") {
        // Range query
        int range_start = std::max(request.range_start(), data_range_[0]);
        int range_end = std::min(request.range_end(), data_range_[1]);
        
        for (int k = range_start; k <= range_end; k++) {
            DataItem item;
            bool found = RetrieveDataFromSharedMemory(k, &item);
            
            if (found) {
                *response->add_results() = item;
            }
        }
    } else if (request.query_type() == "all") {
        // All data in this node's range
        for (int k = data_range_[0]; k <= data_range_[1]; k++) {
            DataItem item;
            bool found = RetrieveDataFromSharedMemory(k, &item);
            
            if (found) {
                *response->add_results() = item;
            }
        }
    }
}

void BasecampServiceImpl::QueryPeers(const QueryRequest& request, QueryResponse* response) {
    // Create a data request
    DataRequest data_request;
    data_request.set_request_id(request.query_id());
    data_request.set_requester_id(node_id_);
    data_request.set_key(request.key());
    data_request.set_query_type(request.query_type());
    data_request.set_range_start(request.range_start());
    data_request.set_range_end(request.range_end());
    data_request.set_timestamp(GetCurrentTimestamp());
    data_request.set_hop_count(0);
    data_request.set_max_hops(3);  // Allow up to 3 hops
    data_request.set_route_path(node_id_);
    data_request.set_forward_to_peers(true);  // Enable forwarding
    data_request.add_visited_nodes(node_id_);
    
    // Add context to the request
    (*data_request.mutable_query_context())["origin"] = "portal";
    (*data_request.mutable_query_context())["client_id"] = request.client_id();
    
    // Create a vector to store the futures
    std::vector<std::future<void>> futures;
    std::mutex response_mutex;
    
    // For each peer
    for (const auto& [peer_id, peer_info] : peers_) {
        // Only query peers that might have the data
        bool should_query = false;
        
        if (request.query_type() == "exact") {
            // Check if the peer's data range contains the key
            auto& peer_config = config_["nodes"][peer_id];
            int peer_range_start = peer_config["data_range"][0];
            int peer_range_end = peer_config["data_range"][1];
            
            should_query = (request.key() >= peer_range_start && request.key() <= peer_range_end);
        } else if (request.query_type() == "range") {
            // Check if the peer's data range overlaps with the query range
            auto& peer_config = config_["nodes"][peer_id];
            int peer_range_start = peer_config["data_range"][0];
            int peer_range_end = peer_config["data_range"][1];
            
            should_query = (request.range_start() <= peer_range_end && request.range_end() >= peer_range_start);
        } else if (request.query_type() == "all" || request.query_type() == "write") {
            // Always query for "all" and "write" queries
            should_query = true;
        }
        
        if (!should_query) {
            continue;
        }
        
        // Create a future to send the request to this peer
        auto future = std::async(std::launch::async, [this, peer_id, &peer_info, &data_request, response, &response_mutex]() {
            // Create a context with a longer timeout
            grpc::ClientContext context;
            context.set_deadline(std::chrono::system_clock::now() + std::chrono::milliseconds(5000));
            
            // Create a response
            DataResponse data_response;
            
            try {
                // Send the request with a timeout
                grpc::Status status = peer_info.stub->GatherData(&context, data_request, &data_response);
                
                // Check if the request was successful
                if (!status.ok()) {
                    std::cerr << "Error querying peer " << peer_id << ": " << status.error_message() << std::endl;
                    return;
                }
                
                // Check if the peer processed the request successfully
                if (!data_response.success()) {
                    std::cerr << "Peer " << peer_id << " error: " << data_response.error_message() << std::endl;
                    return;
                }
                
                // Lock the mutex before updating the response
                std::lock_guard<std::mutex> lock(response_mutex);
                
                // Add the results to the response
                for (const auto& item : data_response.data_items()) {
                    *response->add_results() = item;
                }
            } catch (const std::exception& e) {
                std::cerr << "Exception querying peer " << peer_id << ": " << e.what() << std::endl;
            }
        });
        
        futures.push_back(std::move(future));
    }
    
    // Wait for all futures to complete with a timeout
    auto start_time = std::chrono::high_resolution_clock::now();
    auto timeout = std::chrono::milliseconds(4000);  // 4 seconds timeout
    
    for (auto& future : futures) {
        auto now = std::chrono::high_resolution_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time);
        
        if (elapsed >= timeout) {
            std::cerr << "Timeout waiting for peer responses" << std::endl;
            break;
        }
        
        auto remaining = timeout - elapsed;
        auto status = future.wait_for(remaining);
        
        if (status != std::future_status::ready) {
            std::cerr << "Timeout waiting for a peer response" << std::endl;
        }
    }
}

bool BasecampServiceImpl::CheckCache(const QueryRequest& request, QueryResponse* response) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    
    // Clean expired cache entries
    CleanCache();
    
    // Check if the query is in the cache
    for (const auto& entry : query_cache_) {
        if (entry.query_id == request.query_id()) {
            // Check if the entry is expired
            if (entry.isExpired(cache_ttl_seconds_)) {
                continue;
            }
            
            // Copy the cached response
            *response = entry.response;
            response->set_from_cache(true);
            
            return true;
        }
    }
    
    return false;
}

void BasecampServiceImpl::AddToCache(const std::string& query_id, const QueryResponse& response) {
    std::lock_guard<std::mutex> lock(cache_mutex_);
    
    // Clean expired cache entries
    CleanCache();
    
    // Check if the cache is full
    if (query_cache_.size() >= static_cast<size_t>(cache_size_)) {
        // Remove the oldest entry
        query_cache_.pop_front();
    }
    
    // Add the new entry
    CacheEntry entry;
    entry.query_id = query_id;
    entry.response = response;
    entry.timestamp = std::chrono::system_clock::now();
    query_cache_.push_back(entry);
}

void BasecampServiceImpl::CleanCache() {
    // Remove expired entries
    auto now = std::chrono::system_clock::now();
    query_cache_.erase(
        std::remove_if(
            query_cache_.begin(),
            query_cache_.end(),
            [this, now](const CacheEntry& entry) {
                auto age = std::chrono::duration_cast<std::chrono::seconds>(now - entry.timestamp).count();
                return age > cache_ttl_seconds_;
            }
        ),
        query_cache_.end()
    );
}

bool BasecampServiceImpl::StoreDataInSharedMemory(int key, const DataItem& item) {
    try {
        // Serialize the data item
        std::string serialized = SerializeDataItem(item);
        
        // Lock the mutex
        bip::scoped_lock<bip::named_mutex> lock(*shared_memory_mutex_);
        
        // Store the data
        data_map_->insert_or_assign(key, serialized);
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error storing data in shared memory: " << e.what() << std::endl;
        return false;
    }
}

bool BasecampServiceImpl::RetrieveDataFromSharedMemory(int key, DataItem* item) {
    try {
        // Lock the mutex
        bip::scoped_lock<bip::named_mutex> lock(*shared_memory_mutex_);
        
        // Find the data
        auto it = data_map_->find(key);
        if (it == data_map_->end()) {
            return false;
        }
        
        // Deserialize the data item
        *item = DeserializeDataItem(it->second);
        
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Error retrieving data from shared memory: " << e.what() << std::endl;
        return false;
    }
}

std::string BasecampServiceImpl::SerializeDataItem(const DataItem& item) {
    // Use Protocol Buffers to serialize the data item
    return item.SerializeAsString();
}

DataItem BasecampServiceImpl::DeserializeDataItem(const std::string& serialized) {
    // Use Protocol Buffers to deserialize the data item
    DataItem item;
    item.ParseFromString(serialized);
    return item;
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
