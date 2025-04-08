#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include "basecamp_client.h"

using namespace basecamp;

// Function to display a menu and get user input
int displayMenu() {
    std::cout << "\nBasecamp Client Menu:" << std::endl;
    std::cout << "1. Send a message" << std::endl;
    std::cout << "2. Subscribe to updates" << std::endl;
    std::cout << "3. Send multiple messages" << std::endl;
    std::cout << "4. Start a chat session" << std::endl;
    std::cout << "5. Exit" << std::endl;
    std::cout << "Enter your choice: ";
    
    int choice;
    std::cin >> choice;
    std::cin.ignore(); // Clear the newline character
    
    return choice;
}

// Function to send a message
void sendMessage(BasecampClient& client) {
    std::string sender_id, receiver_id, content;
    
    std::cout << "Enter sender ID: ";
    std::getline(std::cin, sender_id);
    
    std::cout << "Enter receiver ID: ";
    std::getline(std::cin, receiver_id);
    
    std::cout << "Enter message content: ";
    std::getline(std::cin, content);
    
    std::string message_id;
    bool success = client.SendMessage(sender_id, receiver_id, content, &message_id);
    
    if (success) {
        std::cout << "Message sent successfully with ID: " << message_id << std::endl;
    } else {
        std::cout << "Failed to send message" << std::endl;
    }
}

// Function to subscribe to updates
void subscribeToUpdates(BasecampClient& client) {
    std::string subscriber_id;
    std::vector<std::string> topics;
    
    std::cout << "Enter subscriber ID: ";
    std::getline(std::cin, subscriber_id);
    
    std::cout << "Enter topics (one per line, empty line to finish):" << std::endl;
    while (true) {
        std::string topic;
        std::getline(std::cin, topic);
        
        if (topic.empty()) {
            break;
        }
        
        topics.push_back(topic);
    }
    
    bool success = client.SubscribeToUpdates(
        subscriber_id,
        topics,
        [](const UpdateResponse& update) {
            std::cout << "Received update for topic '" << update.topic()
                      << "': " << update.content() << std::endl;
        });
    
    if (success) {
        std::cout << "Subscribed to updates successfully" << std::endl;
        std::cout << "Press enter to return to the menu..." << std::endl;
        std::string line;
        std::getline(std::cin, line);
    } else {
        std::cout << "Failed to subscribe to updates" << std::endl;
    }
}

// Function to send multiple messages
void sendMultipleMessages(BasecampClient& client) {
    std::string sender_id;
    std::vector<MessageRequest> messages;
    
    std::cout << "Enter sender ID: ";
    std::getline(std::cin, sender_id);
    
    std::cout << "Enter messages (receiver and content, empty line to finish):" << std::endl;
    while (true) {
        std::string receiver_id, content;
        
        std::cout << "Enter receiver ID (empty to finish): ";
        std::getline(std::cin, receiver_id);
        
        if (receiver_id.empty()) {
            break;
        }
        
        std::cout << "Enter message content: ";
        std::getline(std::cin, content);
        
        MessageRequest request;
        request.set_sender_id(sender_id);
        request.set_receiver_id(receiver_id);
        request.set_content(content);
        request.set_timestamp(BasecampClient::GetCurrentTimestamp());
        
        messages.push_back(request);
    }
    
    BatchResponse response;
    bool success = client.SendMultipleMessages(messages, &response);
    
    if (success) {
        std::cout << "Sent " << response.success_count() << " messages successfully" << std::endl;
        if (response.failure_count() > 0) {
            std::cout << "Failed to send " << response.failure_count() << " messages" << std::endl;
        }
    } else {
        std::cout << "Failed to send messages" << std::endl;
    }
}

// Function to start a chat session
void startChat(BasecampClient& client) {
    std::string sender_id;
    
    std::cout << "Enter sender ID: ";
    std::getline(std::cin, sender_id);
    
    // Flag to indicate if the chat is running
    bool chat_running = true;
    
    // Start the chat
    bool success = client.StartChat(
        sender_id,
        [](const ChatMessage& message) {
            std::cout << message.sender_id() << ": " << message.content() << std::endl;
        },
        [&chat_running](ChatMessage* message) {
            std::string content;
            std::cout << "Enter message (empty to exit): ";
            std::getline(std::cin, content);
            
            if (content.empty()) {
                chat_running = false;
                return false;
            }
            
            message->set_content(content);
            return true;
        });
    
    if (success) {
        std::cout << "Chat session started successfully" << std::endl;
        std::cout << "Enter messages (empty line to exit)" << std::endl;
        
        // Wait for the chat to finish
        while (chat_running) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    } else {
        std::cout << "Failed to start chat session" << std::endl;
    }
}

int main(int argc, char** argv) {
    // Default server address
    std::string server_address = "localhost:50051";
    
    // Parse command line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--address" && i + 1 < argc) {
            server_address = argv[++i];
        }
    }
    
    // Create a client
    BasecampClient client(server_address);
    
    // Display the menu and handle user input
    while (true) {
        int choice = displayMenu();
        
        switch (choice) {
            case 1:
                sendMessage(client);
                break;
            case 2:
                subscribeToUpdates(client);
                break;
            case 3:
                sendMultipleMessages(client);
                break;
            case 4:
                startChat(client);
                break;
            case 5:
                std::cout << "Exiting..." << std::endl;
                return 0;
            default:
                std::cout << "Invalid choice" << std::endl;
                break;
        }
    }
    
    return 0;
}
