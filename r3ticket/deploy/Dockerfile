FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 ctf

WORKDIR /home/ctf

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY --chown=ctf:ctf chall.py entrypoint.sh run.sh flag.txt ./
RUN chmod 0555 chall.py entrypoint.sh run.sh \
    && chmod 0400 flag.txt

USER ctf

EXPOSE 1337

ENTRYPOINT ["/home/ctf/entrypoint.sh"]
CMD ["socat", "-T", "180", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/home/ctf/run.sh,stderr"]
