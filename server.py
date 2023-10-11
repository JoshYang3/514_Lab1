### CSE514 Lab 1: P2P File Sharing ###

import socket
import threading

# Used to start the peer's server functionality
def start_server(port=9999):
    print("Starting server...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)           # Create a socket object
    server_socket.bind(('0.0.0.0', port))                                       # Bind to the port
    server_socket.listen(5)                                                     # Listen for 5 maximum incoming connections
    print(f'Server listening on port {port}')

    while True:
        print("Waiting for a new connection...") 
        client_sock, addr = server_socket.accept()                              # Establish connection with client
        print(f'Connection from {addr}')
        client_handler = threading.Thread(target=handle_client, args=(client_sock, addr))  # pass addr to the function
        client_handler.start()
        

file_registry = {}                                                              # A dictionary to store all the files and their info

def handle_client(client_socket, client_addr):
    client_port = client_addr[1]

    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')                  # Receive the request from the client
            if not request:                                                     # client might have disconnected
                print(f"Client {client_addr} has disconnected.")
                break
            print(f'Received: {request}')

            command, *args = request.split('|')                                 # Split the request into command and arguments

            if command == 'Register Request':
                num_files = int(args[0])
                peer_port = int(args[1])
                files_info = args[2:]

                for i in range(num_files):
                    file_name = files_info[i * 2]
                    file_size = int(files_info[i * 2 + 1])

                    # Create an entry if it doesn't exist
                    if file_name not in file_registry:
                        file_registry[file_name] = {'size': int(file_size), 'peers': []}

                    # Append the peer (IP and port) to the list of peers, if it's not already there
                    peer_info = (client_addr[0], peer_port)
                    if peer_info not in file_registry[file_name]['peers']:
                        file_registry[file_name]['peers'].append(peer_info)     # Store the file info in a dictionary
                client_socket.send(b'ACK')
            elif command == 'File List Request':
                if(file_registry == {}):                                        # If the file list is empty
                    client_socket.send('File registry is empty'.encode('utf-8'))
                else:                                                           # If the file list is not empty
                    # Send the file list and its associated peers
                    file_list_with_peers = '|'.join(f'{filename} (size: {file_info["size"]}) from peers: {", ".join([f"{peer[0]}:{peer[1]}" for peer in file_info["peers"]])}' for filename, file_info in file_registry.items())
                    client_socket.send(file_list_with_peers.encode('utf-8'))               # Send the list of files to the client
            elif command == 'File Locations Request':
                file_name = args[0]  # Extract the filename from the request arguments
                if file_name in file_registry:
                    # Extract peers (port numbers) that have the requested file
                    peers_with_file = '|'.join(map(str, file_registry[file_name]['peers']))
                    response = f"{file_name}|{peers_with_file}"
                    client_socket.send(response.encode('utf-8'))
                else:
                    client_socket.send('File not found.\n'.encode('utf-8'))
            elif command == 'Chunk Notification':
                file_name, chunk_index, chunk_size = args[0], int(args[1]), int(args[2])
                chunk_name = f"{file_name}.chunk{chunk_index}"
                
                # Add the peer to the list of peers that have this chunk
                if chunk_name not in file_registry:
                    file_registry[chunk_name] = {'size': chunk_size, 'peers': []}

                
                peer_info = (client_addr[0], client_port)
                if peer_info not in file_registry[chunk_name]['peers']:
                    file_registry[chunk_name]['peers'].append(peer_info)

                client_socket.send(b'Chunk Registered Successfully')

            elif command == 'Disconnect':
                print(f"Received disconnect command from client {client_addr}.")
                break  # Exit the loop
    except Exception as e:
        print(f"Error occurred with client {client_addr}: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_server()

