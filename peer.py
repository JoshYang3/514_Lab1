import socket
import threading
import file_utils  # Import the file_utils module

def connect_to_server(server_ip, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    return client_socket

def register_files(client_socket, files):
    file_info = '|'.join(f'{file["name"]}|{file["size"]}' for file in files)
    message = f'Register Request|{len(files)}|{file_info}'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)

def request_file_list(client_socket):
    message = 'File List Request'
    try:
        client_socket.send(message.encode('utf-8'))
        response = client_socket.recv(1024).decode('utf-8')
        print(response)
    except ConnectionResetError:
        print("Connection was reset. The server might have closed the connection.")
        return
    except BrokenPipeError:
        print("Broken pipe. The server might have closed the connection.")
        return

def disconnect(client_socket):
    message = 'Disconnect'
    client_socket.send(message.encode('utf-8'))
    response = client_socket.recv(1024).decode('utf-8')
    print(response)

def send_chunk(socket, chunk):
    socket.sendall(len(chunk).to_bytes(4, byteorder='big'))
    socket.sendall(chunk)

def receive_chunk(socket):
    chunk_size = int.from_bytes(socket.recv(4), byteorder='big')
    chunk = socket.recv(chunk_size)
    return chunk

def display_menu():
    print("1. Register files")
    print("2. Request file list")
    print("3. Download file")
    print("4. Exit")

def main():
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    server_ip = '127.0.0.1'
    server_port = 9999
    client_socket.connect((server_ip, server_port))

    while True:
        display_menu()  # Display the menu at the start of each loop iteration
        user_input = input("Enter the number of your choice: ")

        if user_input == '1':
            # ... (code to register files)
            files = [
                {"name": "file1.txt", "size": 12345},
                {"name": "file2.txt", "size": 67890}
            ]
            register_files(client_socket, files)
        
        elif user_input == '2':
            # ... (code to request file list)
            request_file_list(client_socket)
        
        elif user_input == '3':
            # ... (code to download file)
            file_name = input("Enter the name of the file to download: ")
            # Assume download_file is a function you've defined to handle file downloading
            download_file(client_socket, file_name)
        
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
    #client_socket = connect_to_server("127.0.0.1", 9999)  # use the correct IP and port
    #files = [{"name": "test1", "size": 12345}]  # example files list
    #register_files(client_socket, files)
    #request_file_list(client_socket)
    
