#!/usr/bin/env python3

"""
Script to test communication between processes in the Basecamp overlay.

This script sends a test message to a specified server and verifies the response.
"""

import os
import sys
import argparse
import time
import random
import string

# Add the Python client directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
python_client_dir = os.path.abspath(
    os.path.join(script_dir, "..", "src", "python_client")
)
sys.path.append(python_client_dir)

# Try to import the Python client
try:
    from basecamp_client import BasecampClient
except ImportError:
    # If the import fails, try to generate the Python code from the proto file
    print(
        "Failed to import BasecampClient. Trying to generate Python code from proto file..."
    )

    # Try to import the generate_proto module
    try:
        sys.path.append(os.path.join(python_client_dir))
        from generate_proto import generate_proto

        # Get the proto file
        proto_file = os.path.join(
            os.path.dirname(script_dir), "proto", "basecamp.proto"
        )
        output_dir = os.path.join(python_client_dir, "proto")

        # Generate the Python code
        generate_proto(proto_file, output_dir)

        # Try to import the Python client again
        sys.path.append(output_dir)
        from basecamp_client import BasecampClient
    except ImportError as e:
        print(f"Failed to import BasecampClient: {e}")
        print(
            "Please make sure you have built the project and generated the Python code."
        )
        sys.exit(1)


def generate_random_id(length=8):
    """Generate a random ID."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def test_send_message(server_address, sender_id=None, receiver_id=None, content=None):
    """Test sending a message to a server."""
    print(f"Testing send_message to server at {server_address}...")

    # Create a client
    client = BasecampClient(server_address)

    # Generate random IDs and content if not provided
    sender_id = sender_id or f"sender_{generate_random_id()}"
    receiver_id = receiver_id or f"receiver_{generate_random_id()}"
    content = (
        content or f"Test message from {sender_id} to {receiver_id} at {time.time()}"
    )

    try:
        # Send a message
        message_id = client.send_message(sender_id, receiver_id, content)

        # Print the result
        print(f"Successfully sent message from {sender_id} to {receiver_id}")
        print(f"Message content: {content}")
        print(f"Message ID: '{message_id}'")
        return True
    except Exception as e:
        print(f"Failed to send message from {sender_id} to {receiver_id}: {e}")
        return False


def test_subscribe_to_updates(server_address, subscriber_id=None, topics=None):
    """Test subscribing to updates from a server."""
    print(f"Testing subscribe_to_updates to server at {server_address}...")

    # Create a client
    client = BasecampClient(server_address)

    # Generate a random subscriber ID and topics if not provided
    subscriber_id = subscriber_id or f"subscriber_{generate_random_id()}"
    topics = topics or [f"topic_{generate_random_id()}" for _ in range(3)]

    # Define a callback function to handle updates
    def update_callback(update):
        print(f"Received update: {update}")

    try:
        # Subscribe to updates
        success = client.subscribe_to_updates(subscriber_id, topics, update_callback)

        # Print the result
        if success:
            print(f"Successfully subscribed to updates for {subscriber_id}")
            print(f"Topics: {topics}")
            print("Waiting for updates for 5 seconds...")
            time.sleep(5)
        else:
            print(f"Failed to subscribe to updates for {subscriber_id}")

        return success
    except Exception as e:
        print(f"Failed to subscribe to updates for {subscriber_id}: {e}")
        return False


def test_send_multiple_messages(server_address, num_messages=3):
    """Test sending multiple messages to a server."""
    print(f"Testing send_multiple_messages to server at {server_address}...")

    # Create a client
    client = BasecampClient(server_address)

    # Create messages
    messages = []
    for i in range(num_messages):
        sender_id = f"sender_{generate_random_id()}"
        receiver_id = f"receiver_{generate_random_id()}"
        content = f"Test message {i} from {sender_id} to {receiver_id} at {time.time()}"
        messages.append(
            {"sender_id": sender_id, "receiver_id": receiver_id, "content": content}
        )

    try:
        # Send the messages
        response = client.send_multiple_messages(messages)

        # Print the result
        if response:
            print(f"Successfully sent {response.success_count} messages")
            if response.failure_count > 0:
                print(f"Failed to send {response.failure_count} messages")

            for i, msg in enumerate(messages):
                print(f"Message {i}: from {msg['sender_id']} to {msg['receiver_id']}")
                print(f"Content: {msg['content']}")
            return True
        else:
            print(f"Failed to send messages")
            return False
    except Exception as e:
        print(f"Failed to send multiple messages: {e}")
        return False


def test_chat(server_address, sender_id=None, num_messages=3):
    """Test chat with a server."""
    print(f"Testing start_chat to server at {server_address}...")

    # Create a client
    client = BasecampClient(server_address)

    # Generate a random sender ID if not provided
    sender_id = sender_id or f"sender_{generate_random_id()}"

    # Define a callback function to handle received messages
    def receive_callback(message):
        print(f"Received message: {message}")

    # Define a function to generate messages
    messages_sent = 0

    def get_next_message():
        nonlocal messages_sent
        if messages_sent >= num_messages:
            return None

        content = f"Chat message {messages_sent} from {sender_id} at {time.time()}"
        messages_sent += 1

        print(f"Sending message: {content}")
        return content

    try:
        # Start the chat
        success = client.start_chat(sender_id, receive_callback, get_next_message)

        # Print the result
        if success:
            print(f"Successfully started chat for {sender_id}")
            print(f"Sent {messages_sent} messages")
            print("Waiting for responses for 5 seconds...")
            time.sleep(5)
        else:
            print(f"Failed to start chat for {sender_id}")

        return success
    except Exception as e:
        print(f"Failed to start chat for {sender_id}: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test communication between processes in the Basecamp overlay."
    )
    parser.add_argument(
        "server_address", help="Address of the server to test (e.g., 127.0.0.1:50051)"
    )
    parser.add_argument(
        "--test",
        choices=["send", "subscribe", "multiple", "chat", "all"],
        default="all",
        help="Test to run (default: all)",
    )

    args = parser.parse_args()

    # If the server address is 0.0.0.0, replace it with 127.0.0.1
    server_address = args.server_address
    if server_address.startswith("0.0.0.0"):
        port = server_address.split(":")[1]
        server_address = f"127.0.0.1:{port}"
        print(f"Replacing 0.0.0.0 with 127.0.0.1, using {server_address}")

    # Run the specified test(s)
    if args.test == "send" or args.test == "all":
        test_send_message(server_address)

    if args.test == "subscribe" or args.test == "all":
        test_subscribe_to_updates(server_address)

    if args.test == "multiple" or args.test == "all":
        test_send_multiple_messages(server_address)

    if args.test == "chat" or args.test == "all":
        test_chat(server_address)

    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
