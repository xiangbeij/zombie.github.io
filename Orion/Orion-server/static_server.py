#!/usr/bin/env python3
"""
Orion All-in-One Server
Static file server (Vue dist) + reverse proxy to Flask API
All on port 3000, proxies API requests to 5188
"""
import socket
import threading
import http.client
import os

HOST = '0.0.0.0'
PORT = 5189
API_PORT = 5188
DIST_DIR = os.environ.get('DIST_DIR', os.path.join(os.path.dirname(__file__), 'dist'))

print(f"[*] Orion server starting on port {PORT}")
print(f"[*] API backend: localhost:{API_PORT}")
print(f"[*] Static files: {DIST_DIR}")

CUSTOM_MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.css': 'text/css',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.ico': 'image/x-icon',
    '.json': 'application/json',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
}


def handle_client(client_sock, client_addr):
    """Handle one client connection."""
    try:
        # Read full request (may need multiple recv for POST with body)
        request = b''
        while True:
            chunk = client_sock.recv(16384)
            request += chunk
            if not chunk or b'\r\n\r\n' in request:
                # Check if we have all data based on Content-Length
                header_end = request.find(b'\r\n\r\n')
                if header_end != -1:
                    header_section = request[:header_end].decode('utf-8', errors='replace')
                    content_length = None
                    for line in header_section.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            try:
                                content_length = int(line.split(':')[1].strip())
                            except:
                                pass
                    if content_length is not None:
                        body_start = header_end + 4
                        body_received = len(request) - body_start
                        if body_received >= content_length:
                            break
                    else:
                        break
                else:
                    break
            if len(request) > 1024 * 1024:  # 1MB limit
                break
    except Exception as e:
        print(f"[!] recv error {client_addr}: {e}")
        client_sock.close()
        return

    if not request:
        client_sock.close()
        return

    # Parse request line
    try:
        text = request.decode('utf-8', errors='replace')
    except:
        client_sock.close()
        return

    lines = text.split('\r\n')
    if not lines:
        client_sock.close()
        return

    parts = lines[0].split(' ')
    if len(parts) < 2:
        client_sock.close()
        return

    method, path = parts[0], parts[1]

    # Proxy API requests to Flask backend
    if (path.startswith('/api') or path.startswith('/scan') or
        path.startswith('/batch') or path.startswith('/schedule') or
        path.startswith('/report') or path.startswith('/tasks') or
        path.startswith('/stats') or path.startswith('/rules') or
        path == '/health'):
        proxy_to_api(client_sock, method, path, request)
    else:
        serve_static(client_sock, method, path)


def proxy_to_api(client_sock, method, path, raw_request):
    """Forward request to Flask API server."""
    try:
        # Extract headers - stop BEFORE the body (after \r\n\r\n)
        header_end = raw_request.find(b'\r\n\r\n')
        headers_text = raw_request[:header_end].decode('utf-8', errors='replace')
        body = raw_request[header_end + 4:] if header_end != -1 else b''

        headers = {}
        for line in headers_text.split('\r\n')[1:]:  # skip request line
            if ':' in line:
                k, v = line.split(':', 1)
                k = k.strip().lower()
                if k not in ('host', 'connection', 'proxy-connection',
                              'transfer-encoding'):
                    headers[k.strip()] = v.strip()

        # Connect and forward
        conn = http.client.HTTPConnection('127.0.0.1', API_PORT, timeout=60)
        conn.request(method, path, body=body if body else None, headers=headers)
        resp = conn.getresponse()

        # Read response
        resp_body = resp.read()
        if isinstance(resp_body, str):
            resp_body = resp_body.encode('utf-8')

        status = f"HTTP/1.1 {resp.status} {resp.reason}\r\n"
        hdr_lines = ''.join(f"{k}: {v}\r\n" for k, v in resp.getheaders())
        response = (status + hdr_lines + "\r\n").encode() + resp_body
        client_sock.sendall(response)
        conn.close()

    except Exception as e:
        print(f"[!] Proxy error: {e}")
        try:
            conn.close()
        except:
            pass
        try:
            client_sock.sendall(
                b'HTTP/1.1 502 Bad Gateway\r\n'
                b'Content-Length: 0\r\n'
                b'Connection: close\r\n\r\n'
            )
        except:
            pass


def serve_static(client_sock, method, path):
    """Serve static files from DIST_DIR."""
    if path == '/':
        path = '/index.html'

    # Security: prevent path traversal
    path = os.path.normpath(path).lstrip('/')
    if '..' in path:
        send_error(client_sock, 403, 'Forbidden')
        return

    file_path = os.path.join(DIST_DIR, path)

    if os.path.isfile(file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            ct = CUSTOM_MIME.get(ext, 'application/octet-stream')
            with open(file_path, 'rb') as f:
                content = f.read()

            resp = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {ct}\r\n"
                f"Content-Length: {len(content)}\r\n"
                f"Cache-Control: public, max-age=3600\r\n"
                f"Server: Orion\r\n"
                f"\r\n"
            ).encode() + content
            client_sock.sendall(resp)
        except Exception as e:
            send_error(client_sock, 500, f'Error: {e}')
    else:
        # SPA fallback: return index.html
        index_path = os.path.join(DIST_DIR, 'index.html')
        if os.path.isfile(index_path):
            try:
                with open(index_path, 'rb') as f:
                    content = f.read()
                resp = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(content)}\r\n"
                    f"Server: Orion\r\n"
                    f"\r\n"
                ).encode() + content
                client_sock.sendall(resp)
            except:
                send_error(client_sock, 500, 'Error')
        else:
            send_error(client_sock, 404, 'Not Found')


def send_error(client_sock, code, message):
    body = f'<html><body><h1>{code} {message}</h1></body></html>'.encode()
    try:
        client_sock.sendall(
            f"HTTP/1.1 {code} {message}\r\n"
            f"Content-Type: text/html\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"\r\n".encode() + body
        )
    except:
        pass


class ThreadedTCPServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(100)
        print(f"[+] Listening on http://{host}:{port}")

    def serve_forever(self):
        while True:
            try:
                client_sock, client_addr = self.sock.accept()
                t = threading.Thread(
                    target=handle_client,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                t.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[!] Accept error: {e}")


if __name__ == '__main__':
    ThreadedTCPServer(HOST, PORT).serve_forever()
