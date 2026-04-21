FROM node:18-alpine

WORKDIR /app

# Python dependencies (requests for Libra scan engine, others for API)
RUN apk add --no-cache python3 py3-pip py3-requests \
    && pip3 install --no-cache-dir --break-system-packages flask flask-cors apscheduler reportlab

ENV DIST_DIR=/app/dist
ENV PYTHONPATH=/app

# Copy pre-built Vue dist
COPY Libra-web/dist/ /app/dist/

# Copy Libra backend (with __init__.py for proper packages)
COPY Libra.py /app/Libra.py
COPY Libra.db /app/Libra.db
COPY Config/ /app/Config/
COPY Framework/ /app/Framework/
COPY Moudle/ /app/Moudle/
COPY ORM/ /app/ORM/
COPY Tools/ /app/Tools/

# API server
COPY Libra-server/app_batch.py /app/Libra-server/app_batch.py
COPY Libra-server/serve.py /app/serve.py

EXPOSE 3000 5188

CMD sh -c 'echo "PYTHONPATH=$PYTHONPATH" && python3 /app/Libra-server/app_batch.py > /app/libra_api.log 2>&1 & sleep 3 && python3 /app/serve.py'
