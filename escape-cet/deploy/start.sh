#!/usr/bin/env bash
set -euo pipefail

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

true_flag=/root/flag
key_file=/home/ctf/key
encryptor=/home/ctf/encryptor
public_flag=/flag

if [[ ! -r "$true_flag" ]]; then
    printf 'internal error: %s is not readable\n' "$true_flag" >&2
    exit 1
fi

if [[ ! -x "$encryptor" ]]; then
    printf 'internal error: %s is not executable\n' "$encryptor" >&2
    exit 1
fi

alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
key=''
for ((i = 0; i < 32; i++)); do
    byte="$(od -An -N1 -tu1 /dev/urandom)"
    key+="${alphabet:$((byte % ${#alphabet})):1}"
done

tmp_key="$(mktemp /tmp/key.XXXXXX)"
printf '%s' "$key" > "$tmp_key"
chown root:ctf "$tmp_key"
chmod 444 "$tmp_key"
mv "$tmp_key" "$key_file"
chown root:ctf "$key_file"
chmod 444 "$key_file"

if [[ "${REDACT_SELFTEST:-0}" == "1" ]]; then
    printf 'redact full key: %s\n' "$key"
    printf 'redact key substring: %s\n' "${key:7:5}"
    printf 'this line mentions sde and must be hidden\n'
fi

encrypted_b64="$("$encryptor" "$key_file" < "$true_flag" | base64 -w 0)"

tmp_flag="$(mktemp /tmp/public-flag.XXXXXX)"
cat > "$tmp_flag" <<EOF
your flag has been hacked by t1d！

encrypted flag (base64):
$encrypted_b64

encryptor: $encryptor
key: $key_file
EOF

chown root:ctf "$tmp_flag"
chmod 444 "$tmp_flag"
mv "$tmp_flag" "$public_flag"
chown root:ctf "$public_flag"
chmod 444 "$public_flag"

exec /usr/local/bin/drop-exec /home/ctf/run_challenge.sh
