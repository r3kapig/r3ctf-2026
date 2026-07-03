FROM python:3.12-slim

WORKDIR /app

COPY attachment/task.py attachment/fhe_core.py attachment/lut ./
COPY attachment/setup ./setup
COPY deploy/secret.py ./secret.py
COPY deploy/wrap.py ./wrap.py

ENV PYTHONUNBUFFERED=1
EXPOSE 1336

CMD ["python3", "/app/wrap.py"]
