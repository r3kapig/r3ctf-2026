FROM python:3.11-bookworm

RUN pip install kubernetes_asyncio docker PyNaCl cryptography

WORKDIR /app

ADD ./* /app/

CMD ["python", "controller.py"]
