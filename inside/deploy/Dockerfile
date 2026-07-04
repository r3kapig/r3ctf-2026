FROM sagemath/sagemath:9.6

USER root

# apt mirror (USTC) + socat for service forwarding
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list \
    && sed -i 's@//.*security.ubuntu.com@//mirrors.ustc.edu.cn@g' /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

USER sage

# python deps (used by the challenge)
RUN sage --python -m pip install --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple pycryptodome

# challenge source
COPY --chown=sage:sage src/ /home/sage/
COPY docker-entrypoint.sh /home/sage/docker-entrypoint.sh

EXPOSE 9999

ENTRYPOINT ["/bin/bash", "/home/sage/docker-entrypoint.sh"]
