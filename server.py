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
        

file_registry = {}  # filename -> { 'size': int, 'peers': { peer_ip: [chunk_numbers] } }


def handle_client(client_socket):
    request = client_socket.recv(1024).decode('utf-8')
    print(f'Received: {request}')

    command, *args = request.split('|')

    if command == 'Register Request':
        num_files = int(args[0])
        files_info = args[1:]
        for i in range(0, len(files_info), 2):
            file_name, file_size = files_info[i:i+2]
            if file_name not in file_registry:
                file_registry[file_name] = {'size': int(file_size), 'peers': {}}
            # Each peer starts as a source of all chunks since they own the file
            num_chunks = -(-int(file_size) // CHUNK_SIZE)  # Calculate the total number of chunks for the file
            file_registry[file_name]['peers'][client_socket.getpeername()] = list(range(num_chunks))

        client_socket.send(b'ACK')

    elif command == 'File List Request':
        files = '|'.join(file_registry.keys())
        client_socket.send(files.encode('utf-8'))

    elif command == 'File Locations Request':
        file_name = args[0]
        if file_name in file_registry:
            peers_data = []
            for peer, chunks in file_registry[file_name]['peers'].items():
                peer_str = f"{peer[0]}:{peer[1]}|{'|'.join(map(str, chunks))}"
                peers_data.append(peer_str)
            client_socket.send('|'.join(peers_data).encode('utf-8'))
        else:
            client_socket.send(b'NOT FOUND')
            
    # ... (rest of your code)

    client_socket.close()


if __name__ == "__main__":
    start_server()
    handle_client()

