import socket
import threading
import os
import random
import file_utils  # Import the file_utils module
from time import sleep


### For connecting to the server ###
# Used to connect to the server
def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Create a socket object
    client_socket.connect((server_ip, server_port))              # Connect to the server
    return client_socket                                         # Return the socket object

# Used to register files with the server
def register_files(client_socket, files, peer_port = 2222):
    file_info = '|'.join(f'{filename}|{file_detail["size"]}' for filename, file_detail in files.items())
    message = f'Register Request|{len(files)}|{peer_port}|{file_info}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')

# Used to request the list of files from the server
def request_file_list(client_socket):
    message = 'File List Request'                                # Create the message to send to the server
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(4096).decode('utf-8')  # increased buffer size just in case
        print("Available files:")
        for file_info in response.split('|'):
            print(f" - {file_info}")
        print()
    except ConnectionResetError:                                 # Handle the case where the server closes the connection
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:                                      # Handle the case where the server closes the connection
        print("Broken pipe. The server might have closed the connection.\n\n")
        return

# Used to disconnect from the server
def disconnect(client_socket):
    message = 'Disconnect'                                       # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')

# Used to send a chunk of data over the socket
def send_chunk(socket, chunk):
    socket.sendall(len(chunk).to_bytes(4, byteorder='big'))      # Send the size of the chunk first
    socket.sendall(chunk)                                        # Send the chunk

# Used to receive a chunk of data from the socket
def receive_chunk(socket):
    chunk_size = int.from_bytes(socket.recv(4), byteorder='big')
    chunk = b""
    while len(chunk) < chunk_size:
        part = socket.recv(chunk_size - len(chunk))
        if not part:
            break  # socket connection broken
        chunk += part
    return chunk

# Used to search for files in the file registry, assume the response is a list of IPs and ports.
def request_file_locations(client_socket, file_name): 
    message = f'File Locations Request|{file_name}'             # Create the message to send to the server
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    
    if 'File not found.' in response:
        print(f"The file '{file_name}' was not found on the server.\n")
        return []

    file_info, *peers_ports = response.split('|')
    print(f"File '{file_info}' is available at the following peer ports: {', '.join(peers_ports)}\n")
    return peers_ports                                          # Assume the response is a list of IPs and ports.

### For other peers connecting ###
running = True
# Used to start the peer's server functionality in a separate thread
def start_peer_server(port=2222):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)
    server_socket.settimeout(1)  # Set a timeout of 1 second

    while running:
        try:
            client_sock, addr = server_socket.accept()
            client_handler = threading.Thread(target=handle_peer_request, args=(client_sock, addr))
            client_handler.start()
        except socket.timeout:
            pass

    server_socket.close()

CHUNK_SIZE = 50 * 1024  # Define a size for the chunks 50 kB
# Used to tell the server that what file chunks we have
def get_files_in_current_directory():
    files_info = {}
    directory_path = os.path.dirname(os.path.abspath(__file__))
    exclude_files = ['utils.py', 'file_utils.py', 'peer.py']

    for filename in os.listdir(directory_path):
        if filename in exclude_files:
            continue

        filepath = os.path.join(directory_path, filename)
        
        if os.path.isfile(filepath):
            file_size = os.path.getsize(filepath)
            chunks_count = file_size // CHUNK_SIZE + (1 if file_size % CHUNK_SIZE else 0)
            files_info[filename] = {
                'path': filepath,
                'size': file_size,
                'chunks_count': chunks_count
            }

    return files_info


file_list = get_files_in_current_directory()                    # A dictionary to store file info and chunks

# Used to handle requests from other peers
def handle_peer_request(client_socket, client_addr):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:                                     # client might have disconnected
                #print(f"Client {client_addr} has disconnected.\n\n")
                break
            #print(f'Received: {request}\n\n')

            command, *args = request.split('|')                 # Split the request into command and arguments
            #CHUNK_SIZE = 4096  # Define a size for the chunks (e.g., 4KB)
            if command == 'File Size Request':
                request_file = args[0]
                file_info = file_list.get(request_file)
                if file_info:
                    file_size = str(file_info['size'])
                    client_socket.send(file_size.encode('utf-8'))
                else:
                    client_socket.send(b'0')
            # In handle_peer_request:
            elif command == 'File Chunk Request':
                request_file, chunk_index = args
                chunk_index = int(chunk_index)
                file_info = file_list.get(request_file)
                if file_info:
                    with open(file_info['path'], 'rb') as file:
                        file.seek(chunk_index * CHUNK_SIZE)
                        file_data = file.read(CHUNK_SIZE)
                        send_chunk(client_socket, file_data)
                else:
                    client_socket.send("File not found.".encode('utf-8'))  # Send an error message if the file isn't found            # Send empty chunk to indicate end of file
            
    except Exception as e:                                      # Handle any errors that might occur
        print(f"Error handling peer request: {e}\n\n")
    finally:                                                    # Close the socket when done
        client_socket.close()

### For downloading files ###
# Used to know the size of the file we want to download
def request_file_size_from_peer(peer_ip, peer_port, file_name):
    peer_socket = connect_to_server(peer_ip, peer_port)
    message = f'File Size Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    file_size = int(peer_socket.recv(1024).decode('utf-8'))  # Expect the file size as a plain number
    peer_socket.close()
    return file_size


# Used to download a file from a peer
'''def download_file_from_peer(file_name, peer_ip, peer_port, chunk_count):
    file_size = request_file_size_from_peer(peer_ip, peer_port, file_name)
    peer_socket = connect_to_server(peer_ip, peer_port)
    downloaded_size = 0

    for i in range(chunk_count):
        chunk_name = f"{file_name}.chunk{i + 1}"
        register_chunk_with_server(peer_socket, chunk_name)
        print(f"Requested chunk {i + 1} for {file_name} from {peer_ip}:{peer_port}")
        with open(file_name, 'wb') as f:  # Just 'wb' since we're writing chunks in order
            message = f'File Chunk Request|{file_name}|{i}'  # Request chunk by index
            peer_socket.send(message.encode('utf-8'))
            chunk = receive_chunk(peer_socket)
            if not chunk:
                break
            downloaded_size += len(chunk)
            progress = (downloaded_size / file_size) * 100
            print(f"Download Progress: {progress:.2f}%")
            f.write(chunk)
            sleep(30)
            
    print(f"Downloaded {file_name} from {peer_ip}:{peer_port}\n")
    peer_socket.close()'''
def download_file_from_peer(file_name, peer_ip, peer_port, chunk_count, client_socket):
    chunks_to_download = list(range(chunk_count))
    random.shuffle(chunks_to_download)

    for chunk in chunks_to_download:
        print(f"Downloading chunk {chunk + 1} for {file_name} from {peer_ip}:{peer_port}")
        download_chunk_from_peer(file_name, chunk, peer_ip, peer_port, client_socket)


def download_chunk_from_peer(file_name, chunk_index, peer_ip, peer_port, client_socket):
    peer_socket = connect_to_server(peer_ip, peer_port)
    message = f'File Chunk Request|{file_name}|{chunk_index}'
    peer_socket.send(message.encode('utf-8'))
    chunk = receive_chunk(peer_socket)
    if chunk:
        # Append the chunk to the file.
        with open(file_name, 'ab') as f:
            f.write(chunk)

        # Notify the server that we have this chunk now
        notify_server_of_chunk(client_socket, file_name, chunk_index, len(chunk))
    sleep(30)
    peer_socket.close()


def notify_server_of_chunk(client_socket, file_name, chunk_index, chunk_size):
    message = f'Chunk Notification|{file_name}|{chunk_index}|{chunk_size}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)




### For user menu ###
# Used to display the menu
def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file from peer")
    print("4. Request file locations from server")
    print("5. Exit")

### Main function ###
def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   # Create a socket object

    # Connect to the server
    server_ip = '127.0.0.1'
    server_port = 9999
    peer_ip = '127.0.0.1'
    client_socket.connect((server_ip, server_port))

    # Start the peer's server functionality in a separate thread
    threading.Thread(target=start_peer_server).start()
    
    while True:
        display_menu()                                                  # Display the menu at the start of each loop iteration
        user_input = input("Enter the number of your choice: ")

        if user_input == '1':
            register_files(client_socket, file_list, peer_port=2222)
        
        elif user_input == '2':
            request_file_list(client_socket)
        
        elif user_input == '3':
            peer_port = int(input("Enter the port of the peer to download from: "))
            file_name = input("Enter the name of the file to download: ")
            file_size = request_file_size_from_peer(peer_ip, peer_port, file_name)
            chunk_count = file_size // CHUNK_SIZE
            if file_size % CHUNK_SIZE:
                chunk_count += 1
            download_file_from_peer(file_name, peer_ip, peer_port, chunk_count, client_socket)
            #download_file_from_peer(file_name, peer_ip, peer_port)
        
        elif user_input == '4':
            file_name = input("Enter the name of the file you want to locate: ")
            request_file_locations(client_socket, file_name)
        
        elif user_input == '5':
            print("Disconnecting...")
            global running
            running = False  # Signal the peer server to stop
            disconnect(client_socket)
            break  # Exit the loop
        
        else:
            print("Invalid choice, please try again.")

    # Disconnect from the server
    client_socket.close()

if __name__ == "__main__":
    main()

    
