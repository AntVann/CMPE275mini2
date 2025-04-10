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
import threading

# Add the Python client directory to the path
script_dir = os.path.dirname(os.path.abspath(__file__))
python_client_dir = os.path.abspath(
    os.path.join(script_dir, "..", "src", "python_client")
)
sys.path.append(python_client_dir)

# Try to import the Python client and proto modules
try:
    from basecamp_client import BasecampClient
    from proto import basecamp_pb2
    from proto import basecamp_pb2_grpc
except ImportError:
    # If the import fails, try to generate the Python code from the proto file
    print(
        "Failed to import BasecampClient or proto modules. Trying to generate Python code from proto file..."
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

        # Try to import the Python client and proto modules again
        sys.path.append(output_dir)
        from basecamp_client import BasecampClient
        from proto import basecamp_pb2
        from proto import basecamp_pb2_grpc
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
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
        print(f"Received message from {message.sender_id}: {message.content}")

    # Define a function to generate messages
    messages_sent = 0
    responses_received = 0

    # Create an event to signal when we've received responses
    response_event = threading.Event()

    # Override the callback to count responses
    def counting_callback(message):
        nonlocal responses_received
        print(f"Received message from {message.sender_id}: {message.content}")
        responses_received += 1
        if responses_received >= messages_sent:
            response_event.set()

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
        success = client.start_chat(sender_id, counting_callback, get_next_message)

        # Print the result
        if success:
            print(f"Successfully started chat for {sender_id}")
            print(f"Sent {messages_sent} messages")
            print("Waiting for responses for 10 seconds...")

            # Wait for responses with a timeout
            response_event.wait(10)

            if responses_received > 0:
                print(f"Received {responses_received} responses")
            else:
                print("No responses received within the timeout period")
        else:
            print(f"Failed to start chat for {sender_id}")

        return success
    except Exception as e:
        print(f"Failed to start chat for {sender_id}: {e}")
        return False


def test_query_data(
    server_address, query_type="exact", key=None, range_start=None, range_end=None
):
    """Test querying data from the server."""
    print(f"Testing query_data to server at {server_address}...")

    # Create a client
    client = BasecampClient(server_address)

    # Generate a random query ID
    query_id = f"query_{generate_random_id()}"
    client_id = f"client_{generate_random_id()}"

    try:
        # Create a query request
        request = basecamp_pb2.QueryRequest(
            query_id=query_id, client_id=client_id, timestamp=int(time.time() * 1000)
        )

        # Set the query type and parameters
        request.query_type = query_type
        if query_type == "exact":
            request.key = key or random.randint(0, 999)
        elif query_type == "range":
            request.range_start = range_start or random.randint(0, 499)
            request.range_end = range_end or (
                request.range_start + random.randint(50, 200)
            )
        elif query_type == "write":
            request.key = key or random.randint(0, 999)
            request.string_param = f"Test value for key {request.key} at {time.time()}"
        # For "all" query, no additional parameters are needed

        # Send the query with a longer timeout
        response = client.stub.QueryData(request, timeout=client.timeout * 10)

        # Print the result
        print(f"Query ID: {response.query_id}")
        print(f"Success: {response.success}")
        print(f"From cache: {response.from_cache}")
        print(f"Processing time: {response.processing_time} ms")
        print(f"Results: {len(response.results)} items")

        # Print the first few results
        for i, item in enumerate(response.results[:5]):
            print(f"  Result {i}: Key={item.key}, Source={item.source_node}")

            # Print the value based on its type
            if item.HasField("string_value"):
                print(f"    String value: {item.string_value}")
            elif item.HasField("double_value"):
                print(f"    Double value: {item.double_value}")
            elif item.HasField("bool_value"):
                print(f"    Boolean value: {item.bool_value}")
            elif item.HasField("object_value"):
                obj = item.object_value
                print(f"    Object: {obj.name}")
                print(f"    Tags: {', '.join(obj.tags)}")
                print(f"    Properties: {obj.properties}")
            elif item.HasField("binary_value"):
                print(f"    Binary value: {len(item.binary_value)} bytes")

            # Print metadata
            if item.metadata:
                print(f"    Metadata: {item.metadata}")

            print(f"    Data type: {item.data_type}")
            print(f"    Timestamp: {item.timestamp}")

        if len(response.results) > 5:
            print(f"  ... and {len(response.results) - 5} more")

        # Run the query again to test caching with a longer timeout
        print("\nRunning the same query again to test caching...")
        response = client.stub.QueryData(request, timeout=client.timeout * 10)
        print(f"From cache: {response.from_cache}")
        print(f"Processing time: {response.processing_time} ms")

        return True
    except Exception as e:
        print(f"Failed to query data: {e}")
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
        choices=["send", "subscribe", "multiple", "chat", "query", "all"],
        default="all",
        help="Test to run (default: all)",
    )
    parser.add_argument(
        "--query-type",
        choices=["exact", "range", "all", "write"],
        default="exact",
        help="Type of query to run (default: exact)",
    )
    parser.add_argument(
        "--key",
        type=int,
        help="Key to query (for exact queries)",
    )
    parser.add_argument(
        "--range-start",
        type=int,
        help="Start of range (for range queries)",
    )
    parser.add_argument(
        "--range-end",
        type=int,
        help="End of range (for range queries)",
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

    if args.test == "query" or args.test == "all":
        test_query_data(
            server_address,
            query_type=args.query_type,
            key=args.key,
            range_start=args.range_start,
            range_end=args.range_end,
        )

    print("\nAll tests completed.")


if __name__ == "__main__":
    main()
