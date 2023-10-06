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
        client_handler = threading.Thread(target=handle_client, args=(client_sock, addr))  # pass addr to the function
        client_handler.start()
        

file_registry = {}  # A dictionary to store file info and chunks

def handle_client(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:  # client might have disconnected
                print(f"Client {client_addr} has disconnected.")
                break
            print(f'Received: {request}')

            command, *args = request.split('|')

            if command == 'Register Request':
                # Process file registration
                #num_files = int(args[0])
                files_info = args[1:]
                for i in range(0, len(files_info), 2):
                    file_name, file_size = files_info[i:i+2]
                    file_registry[file_name] = {'size': int(file_size), 'chunks': []}
                client_socket.send(b'ACK')
            elif command == 'File List Request':
                if(file_registry == {}):
                    client_socket.send('File registry is empty'.encode('utf-8'))
                else:
                    file_list = '|'.join(file_registry.keys())
                    client_socket.send(file_list.encode('utf-8'))
            elif command == 'Disconnect':
                print(f"Received disconnect command from client {client_addr}.")
                break  # Exit the loop
    except Exception as e:
        print(f"Error occurred with client {client_addr}: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_server()

