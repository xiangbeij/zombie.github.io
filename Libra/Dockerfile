FROM node:18-alpine

WORKDIR /app

# 安装 Python（API 服务用）
RUN apk add --no-cache python3 py3-pip

# 复制源码
COPY Libra-web/package*.json ./
RUN npm install --silent

COPY Libra-web/ ./
RUN npm run build

# 复制 Libra 后端
COPY Libra-server/ /app/Libra-server/
COPY Libra.py /app/Libra.py
COPY Libra.db /app/Libra.db
COPY Config /app/Config
COPY Framework /app/Framework
COPY Moudle /app/Moudle
COPY ORM /app/ORM
COPY Tools /app/Tools

# Python 依赖
RUN pip3 install --no-cache-dir flask flask-cors apscheduler reportlab

# 暴露端口
EXPOSE 3000 5188

# 启动：API + Vue 前端同端口（用简单代理）
# 先启动 API，再启动静态文件服务
CMD python3 /app/Libra-server/app_batch.py & \
    sleep 2 && \
    python3 -c "
import http.server, socketserver, os, threading, socket

PORT = 3000
API_PORT = 5188
DIST = '/app/Libra-web/dist'

# Simple proxy to API
def proxy_handler(conn, addr):
    try:
        request = conn.recv(8192)
        if not request: return
        # Check if API request
        if b'GET /api' in request or b'POST /api' in request or b'GET /scan' in request or \
           b'GET /batch' in request or b'POST /batch' in request or \
           b'GET /schedule' in request or b'POST /schedule' in request or \
           b'GET /report' in request or b'GET /tasks' in request or \
           b'GET /stats' in request or b'GET /rules' in request or \
           b'GET /health' in request:
            # Proxy to API
            api = socket.socket()
            api.settimeout(30)
            api.connect(('127.0.0.1', API_PORT))
            api.sendall(request)
            resp = b''
            while True:
                try:
                    chunk = api.recv(4096)
                    if not chunk: break
                    resp += chunk
                    if b'\r\n\r\n' in resp:
                        header_end = resp.index(b'\r\n\r\n')
                        for line in resp[:header_end].decode().split('\r\n'):
                            if line.lower().startswith('content-length:'):
                                cl = int(line.split(':')[1].strip())
                                if len(resp) - header_end - 4 >= cl:
                                    conn.sendall(resp)
                                    api.close()
                                    return
                except socket.timeout:
                    break
            if resp: conn.sendall(resp)
            api.close()
        else:
            # Serve static
            path = request.split(b' ')[1].decode()
            if path == '/': path = '/index.html'
            path = os.path.normpath(path).lstrip('/')
            if '..' in path:
                conn.sendall(b'HTTP/1.1 403 Forbidden\r\n\r\n')
                return
            file_path = os.path.join(DIST, path)
            if os.path.isfile(file_path):
                ext = os.path.splitext(file_path)[1].lower()
                ct = {'html':'text/html','js':'application/js','css':'text/css','svg':'image/svg+xml','png':'image/png','ico':'image/x-icon'}
                with open(file_path,'rb') as f: body = f.read()
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: {ct.get(ext,\"application/octet-stream\")}\r\nContent-Length: {len(body)}\r\n\r\n'.encode() + body
                conn.sendall(resp)
            else:
                # SPA fallback
                with open(os.path.join(DIST,'index.html'),'rb') as f: body = f.read()
                resp = f'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\n\r\n'.encode() + body
                conn.sendall(resp)
    except: pass
    finally:
        try: conn.close()
        except: pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

server = ThreadedTCPServer(('', PORT), None)
server.request_handler = proxy_handler
print(f'Libra server running on :{PORT} -> API:{API_PORT}')
server.serve_forever()
"
