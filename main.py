import http.server
import socketserver
import socket
import multiprocessing
import json
import os
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from pymongo import MongoClient

PORT = 3000
SOCKET_PORT = 5000

# MongoDB setup
client = MongoClient('mongodb://mongo:27017/')
db = client['message_db']
collection = db['messages']

# Custom HTTP Request Handler
class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/":
            self.path = "/templates/index.html"
        elif parsed_path.path == "/message.html":
            self.path = "/templates/message.html"
        elif parsed_path.path.startswith("/static/"):
            self.path = self.path[1:]  # Remove leading '/'
        else:
            self.path = "/templates/error.html"
            self.send_response(404)

        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path == "/submit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            post_data = parse_qs(post_data)

            username = post_data.get('username', [''])[0]
            message = post_data.get('message', [''])[0]
            data = json.dumps({
                'username': username,
                'message': message
            })

            try:
                # Send data to socket server
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(data.encode('utf-8'), ('localhost', SOCKET_PORT))
                sock.close()

                self.send_response(302)
                self.send_header('Location', '/message.html')
                self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(f"<html><body><h1>500 Internal Server Error</h1><p>{str(e)}</p></body></html>".encode('utf-8'))

# Start HTTP Server in a separate thread
def start_http_server():
    handler = CustomHTTPRequestHandler
    httpd = socketserver.TCPServer(("", PORT), handler)
    print(f"Serving HTTP on port {PORT}")
    httpd.serve_forever()

# Socket server setup
def start_socket_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', SOCKET_PORT))
    print(f"Socket server listening on port {SOCKET_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)
        data_dict = json.loads(data.decode('utf-8'))
        data_dict['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        collection.insert_one(data_dict)

if __name__ == "__main__":
   # запускаємо HTTP сервер
    http_process = multiprocessing.Process(target=start_http_server)
    http_process.start()

    # запускаємо socket сервер
    socket_process = multiprocessing.Process(target=start_socket_server)
    socket_process.start()

    # чекаємо на запуск обох процесів
    http_process.join()
    socket_process.join()
