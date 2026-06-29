FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
	bash \
	coreutils \
	python3 \
	qemu-system-x86 \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /opt/r3ctf

COPY attachment/bzImage /opt/r3ctf/bzImage
COPY attachment/flag.txt /opt/r3ctf/flag.txt
COPY attachment/initramfs.cpio.gz /opt/r3ctf/initramfs.cpio.gz
COPY --chmod=0755 attachment/run.sh /opt/r3ctf/run.sh
COPY --chmod=0755 attachment/server.py /opt/r3ctf/server.py

RUN mkdir -p /opt/r3ctf/runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
	PORT=1337 \
	RUN_TIMEOUT_SEC=420

EXPOSE 1337

ENTRYPOINT ["/usr/bin/python3", "/opt/r3ctf/server.py"]
