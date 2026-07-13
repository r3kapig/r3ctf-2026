FROM debian:bookworm-slim

COPY r3chat-client_1.0.0_amd64.deb /tmp/r3chat-client.deb

RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb xauth dumb-init ca-certificates curl gcc libc6-dev \
      libgtk-3-0 libnotify4 libnss3 libxss1 libxtst6 xdg-utils \
      libatspi2.0-0 libuuid1 libsecret-1-0 libasound2 libgbm1 libxrandr2 \
      libatk1.0-0 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 \
      libxfixes3 libxkbcommon0 libpango-1.0-0 libcairo2 libcups2 \
      libglib2.0-0 libx11-xcb1 libxcb-dri3-0 libgdk-pixbuf-2.0-0 \
 && dpkg -i /tmp/r3chat-client.deb \
 && rm -f /tmp/r3chat-client.deb \
 && rm -rf /var/lib/apt/lists/*

COPY readflag.c /tmp/readflag.c
RUN gcc -O2 -o /readflag /tmp/readflag.c \
 && chown root:root /readflag && chmod 4755 /readflag \
 && rm /tmp/readflag.c

RUN chown -R root:root /opt/R3Chat \
 && find /opt/R3Chat -type d -exec chmod 0555 {} + \
 && find /opt/R3Chat -type f -exec chmod 0444 {} + \
 && chmod 0555 /opt/R3Chat/r3chat-client /opt/R3Chat/chrome-sandbox

RUN useradd -m -u 1001 bot

ENV R3CHAT_BOT=1 \
    R3CHAT_HOST=127.0.0.1 \
    R3CHAT_PORT=8443 \
    ELECTRON_DISABLE_SANDBOX=1

COPY entrypoint.sh /entrypoint.sh
RUN chown root:root /entrypoint.sh && chmod 0555 /entrypoint.sh
ENTRYPOINT ["dumb-init", "--", "/entrypoint.sh"]
