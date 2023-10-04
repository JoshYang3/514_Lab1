### CSE514 Lab 1: P2P File Sharing ###

import socket
import threading

def start_server(port=9999):
    print("Starting server...")  # Add this line
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    print(f'Server listening on port {port}')

    while True:
        print("Waiting for a new connection...")  # Add this line
        client_sock, addr = server_socket.accept()
        print(f'Connection from {addr}')
        client_handler = threading.Thread(target=handle_client, args=(client_sock,))
        client_handler.start()
        
def handle_client(client_socket):
    request = client_socket.recv(1024).decode('utf-8')
    print(f'Received: {request}')
    # Depending on the request, you might want to handle different types of messages
    # For simplicity, sending an acknowledgement back
    client_socket.send(b'ACK')
    client_socket.close()

if __name__ == "__main__":
    start_server()
    handle_client()

