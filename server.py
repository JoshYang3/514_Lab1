### CSE514 Lab 1: P2P File Sharing ###

import socket
import threading

# Used to store the addresses of all connected peers
connected_peers = []

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
chunk_registry = {}


def handle_client(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')                  # Receive the request from the client
            if not request:
                print(f"Client {client_addr} has disconnected.")
                for peer in connected_peers:
                    if(peer['addr'] == client_addr):
                        connected_peers.remove(peer)
                for i in connected_peers:
                    print(i)
                break
            print(f'Received: {request}')

            command, *args = request.split('|')                                 # Split the request into command and arguments

            if command == 'Register Request':
                files_info = args[1:-1]
                peer_port = int(args[-1])  # Extract the peer's port number
                peer_ip = client_addr[0]   # Extract the peer's IP address from client_addr

                for i in range(0, len(files_info), 2):
                    file_name, file_size = files_info[i:i+2]

                    # Create an entry if it doesn't exist
                    if file_name not in file_registry:
                        file_registry[file_name] = {'size': int(file_size), 'peers': []}

                    # Append the peer (IP and port) to the list of peers, if it's not already there
                    peer_info = (peer_ip, peer_port)
                    if peer_info not in file_registry[file_name]['peers']:
                        file_registry[file_name]['peers'].append(peer_info)     # Store the file info in a dictionary
                client_socket.send(b'File Registed')

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

            elif command == 'Disconnect':
                for peer in connected_peers:
                    if(peer['addr'] == client_addr):
                        connected_peers.remove(peer)
                for i in connected_peers:
                    print(i)
                print(f"Received disconnect command from client {client_addr}.")
                break  # Exit the loop

            elif command == 'Connected Peers Request':
                peers_list = '|'.join([f'{peer["current_peer_port"]}' for peer in connected_peers])
                client_socket.send(peers_list.encode('utf-8'))
            elif command == 'Peer Register':
                current_peer_port = args[-1]
                print(f"current_peer_port: {current_peer_port}")
                connected_peers.append({'current_peer_port':current_peer_port, 'addr': client_addr})  # Add the connected peer to the set
                for i in connected_peers:
                    print(i)
                client_socket.send(b'Peer Port Registered')
            elif command == 'Register Chunk':
                chunk_name, peer_port = args
                peer_ip = client_addr[0]
                peer_info = (peer_ip, int(peer_port))

                # Create an entry if it doesn't exist
                if chunk_name not in file_registry:
                    print("Chunk not found\n")
                
                # Append the peer (IP and port) to the list of peers, if it's not already there
                if peer_info not in file_registry[chunk_name]['peers']:
                    file_registry[chunk_name]['peers'].append(peer_info)
                client_socket.send(b'Chunk Registered')


    except Exception as e:
        print(f"Error occurred with client {client_addr}: {e}")
    finally:
        client_socket.close()



if __name__ == "__main__":
    start_server()

