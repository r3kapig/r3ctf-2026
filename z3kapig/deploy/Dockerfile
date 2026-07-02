FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 ctf

WORKDIR /home/ctf/app

COPY src/requirements.txt /tmp/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libssl-dev openssl socat \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && apt-get purge -y --auto-remove gcc libc6-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && rm /tmp/requirements.txt

COPY --chown=ctf:ctf src/ ./
COPY --chown=ctf:ctf entrypoint.sh run.sh /home/ctf/
RUN chmod 0555 /home/ctf/entrypoint.sh /home/ctf/run.sh \
    && chmod 0400 flag.txt

USER ctf

EXPOSE 1337

ENTRYPOINT ["/home/ctf/entrypoint.sh"]
CMD ["socat", "-T", "900", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/home/ctf/run.sh,stderr"]
