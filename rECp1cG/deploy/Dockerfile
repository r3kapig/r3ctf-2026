FROM public.ecr.aws/ubuntu/ubuntu:24.04

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates python3 python-is-python3 socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 ctf

WORKDIR /home/ctf
COPY challenge.py secret.py ./

RUN chown -R root:root /home/ctf \
    && chmod 555 /home/ctf \
    && chmod 444 /home/ctf/challenge.py /home/ctf/secret.py

USER ctf
EXPOSE 9999

CMD ["socat", "-T", "910", "TCP-LISTEN:9999,reuseaddr,fork", "EXEC:python -u challenge.py,stderr"]
