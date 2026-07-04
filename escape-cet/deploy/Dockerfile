FROM ubuntu:24.04

RUN useradd -m -d /home/ctf -s /bin/bash ctf \
    && mkdir -p /home/ctf/challenge

COPY bin/encryptor /home/ctf/encryptor
COPY bin/tdocker-server /usr/local/bin/tdocker-server
COPY bin/drop-exec /usr/local/bin/drop-exec
COPY entrypoint.sh /root/entrypoint.sh
COPY start.sh /root/start.sh
COPY challenge/ /home/ctf/challenge/
COPY environment/ /home/ctf/environment/
COPY run_challenge.sh /home/ctf/run_challenge.sh

RUN chown -R root:root /home/ctf/challenge /home/ctf/environment \
    && chown root:root /home/ctf /home/ctf/encryptor /home/ctf/run_challenge.sh \
        /usr/local/bin/tdocker-server /usr/local/bin/drop-exec /root/entrypoint.sh /root/start.sh \
    && chmod 755 /home/ctf /home/ctf/encryptor /home/ctf/run_challenge.sh \
        /usr/local/bin/tdocker-server /usr/local/bin/drop-exec \
    && chmod 755 /home/ctf/challenge/tcet \
    && chmod 700 /root/entrypoint.sh /root/start.sh \
    && touch /flag \
    && chown root:ctf /flag \
    && chmod 444 /flag

EXPOSE 9999

ENTRYPOINT ["/root/entrypoint.sh"]
