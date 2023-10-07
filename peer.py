import socket
import threading
import os
import file_utils  # Import the file_utils module

### For connecting to the server ###
def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    return client_socket

def register_files(client_socket, files):
    file_info = '|'.join(f'{file["name"]}|{file["size"]}' for file in files)
    message = f'Register Request|{len(files)}|{file_info}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')

def request_file_list(client_socket):
    message = 'File List Request'
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        print(response, end='\n\n')
    except ConnectionResetError:
        print("Connection was reset. The server might have closed the connection\n\n.")
        return
    except BrokenPipeError:
        print("Broken pipe. The server might have closed the connection.\n\n")
        return

def disconnect(client_socket):
    message = 'Disconnect'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response, end='\n\n')

def send_chunk(socket, chunk):
    socket.sendall(len(chunk).to_bytes(4, byteorder='big'))
    socket.sendall(chunk)

def receive_chunk(socket):
    chunk_size = int.from_bytes(socket.recv(4), byteorder='big')
    chunk = socket.recv(chunk_size)
    return chunk

def request_file_locations(client_socket, file_name):
    message = f'File Locations Request|{file_name}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    return response.split('|')  # Assume the response is a list of IPs and ports.

### For other peers connecting ###
def start_peer_server(port=1111):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', port))
    server_socket.listen(5)

    while True:
        client_sock, addr = server_socket.accept()
        client_handler = threading.Thread(target=handle_peer_request, args=(client_sock, addr))
        client_handler.start()
        

def get_files_in_current_directory():
    files_info = []
    directory_path = os.path.dirname(os.path.abspath(__file__))

    for filename in os.listdir(directory_path):
        filepath = os.path.join(directory_path, filename)
        
        if os.path.isfile(filepath):
            file_size = os.path.getsize(filepath)
            files_info.append({
                'name': filename,
                'size': file_size,
            })

    return files_info

file_list = get_files_in_current_directory() # A dictionary to store file info and chunks
#file_list = {} 

def handle_peer_request(client_socket, request_file):
    try:
        while True:
            request = client_socket.recv(1024).decode('utf-8')
            if not request:  # client might have disconnected
                print(f"Client {client_addr} has disconnected.\n\n")
                break
            print(f'Received: {request}\n\n')

            command, *args = request.split('|')

            if command == 'File Chunk Request':
                request_file = args[0]  # Filename is extracted from the request
                if request_file in file_list:
                    with open(request_file, 'rb') as file:
                        # Here, for simplicity, we're sending the entire file. 
                        # If you want to send only chunks, you'll need to modify this.
                        file_data = file.read()
                        send_chunk(client_socket, file_data)
                else:
                    # Inform the requesting peer that we don't have the file.
                    error_message = "File not found."
                    client_socket.send(error_message.encode('utf-8'))
            client_socket.close()
    except Exception as e:
        print(f"Error handling peer request: {e}\n\n")
    finally:
        client_socket.close()

### For downloading files ###
def download_file_from_peer(file_name, peer_ip, peer_port):
    peer_socket = connect_to_server(peer_ip, peer_port)  # Reuse the connect_to_server function
    message = f'File Chunk Request|{file_name}'
    peer_socket.send(message.encode('utf-8'))
    
    chunk = receive_chunk(peer_socket)
    # ... save chunk or process it
    peer_socket.close()

### For user menu ###
def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file from peer")
    print("4. Exit")

### Main function ###
def main():
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    server_ip = '127.0.0.1'
    server_port = 9999
    peer_ip = '127.0.0.1'
    client_socket.connect((server_ip, server_port))

    while True:
        display_menu()  # Display the menu at the start of each loop iteration
        user_input = input("Enter the number of your choice: ")

        if user_input == '1':
            # ... (code to register files)
            '''files = [
                {"name": "file1.txt", "size": 12345},
                {"name": "file2.txt", "size": 67890}
            ]'''
            register_files(client_socket, file_list)
        
        elif user_input == '2':
            # ... (code to request file list)
            request_file_list(client_socket)
        
        elif user_input == '3':
            # ... (code to download file)
            peer_port = int(input("Enter the port of the peer to download from: "))
            file_name = input("Enter the name of the file to download: ")
            # Assume download_file is a function you've defined to handle file downloading
            download_file_from_peer(file_name, peer_ip, peer_port)
        
        elif user_input == '4':
            print("Disconnecting...")
            disconnect(client_socket)
            break  # Exit the loop
        
        else:
            print("Invalid choice, please try again.")

    # Disconnect from the server
    #print("Closing connection...")
    #client_socket.close()

    '''# Create a list of files to register
    files = [
        {"name": "file1.txt", "size": 12345},
        {"name": "file2.txt", "size": 67890}
    ]

    file_path = 'file1.txt'
    chunks = file_utils.divide_file(file_path, 1024)
    for chunk in chunks:
        send_chunk(client_socket, chunk)

    # Call the register_files function
    register_files(client_socket, files)
    request_file_list(client_socket)

    # Close the socket when done
    client_socket.close()'''

if __name__ == "__main__":
    main()

    
