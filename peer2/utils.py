import socket
import threading

def send_message(socket, message):
    message_encoded = message.encode('utf-8')
    socket.send(message_encoded)

def receive_message(socket):
    message_encoded = socket.recv(1024)
    message = message_encoded.decode('utf-8')
    return message
