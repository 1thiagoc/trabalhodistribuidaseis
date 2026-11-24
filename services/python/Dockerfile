FROM python:3.12-slim

WORKDIR /app

COPY services/python/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY contracts /app/contracts
COPY services/python /app

# Gera os stubs Protobuf/gRPC a partir do contrato compartilhado
RUN python -m grpc_tools.protoc \
    -I/app/contracts \
    --python_out=/app \
    --grpc_python_out=/app \
    /app/contracts/music_streaming.proto

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
