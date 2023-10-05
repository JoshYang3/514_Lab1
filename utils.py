import socket
import threading

def send_message(socket, message):
    message_encoded = message.encode('utf-8')
    socket.send(message_encoded)

def receive_message(socket):
    message_encoded = socket.recv(1024)
    message = message_encoded.decode('utf-8')
    return message

def divide_file(file_path, chunk_size):
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

def assemble_from_chunks(chunks, output_file):
    with open(output_file, 'wb') as f:
        for chunk in chunks:
            f.write(chunk)
