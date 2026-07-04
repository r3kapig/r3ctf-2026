FROM python:3.12-alpine

RUN apk add --no-cache socat \
    && pip install --no-cache-dir cryptography

ENV CHECKER_PORT=31337 \
    CODES_FILE=/shared/codes.json \
    TEAM_API_URL=https://ctf2026.r3kapig.com/api/game/1/team/query \
    FLAG_PREFIX=r3ctf \
    FLAG_TEMPLATE=speedrun_mc_r3ctf_q6le8rxq \
    FLAG_KEY=sBMu9o4ZIMWF9LusIYi8WlTc36JRMwN5 \
    INVALID_MESSAGE="INVALID CODE" \
    CHECKER_SCRIPT=/app/check_code.py

COPY checker/check_code.py /app/check_code.py
COPY checker/uuid_stego.py /app/uuid_stego.py
COPY shared/codes.json /shared/codes.json

EXPOSE 31337

CMD ["sh", "-lc", "exec socat \"TCP-LISTEN:${CHECKER_PORT},reuseaddr,fork\" EXEC:\"python ${CHECKER_SCRIPT}\",stderr"]
