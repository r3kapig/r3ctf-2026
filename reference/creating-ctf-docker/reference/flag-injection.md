# Flag injection reference

How a platform-supplied flag gets from the deploy environment into the challenge, and how to keep it from leaking where it shouldn't. The platform injects the flag as the **`FLAG` environment variable** at `docker run`/`docker-compose` time.

## The standard resolution + scrub block

Use this at the top of `service/docker-entrypoint.sh`. It reads `$FLAG`, then **overwrites it with `no_FLAG`** so the challenge process cannot leak it via `env` or `/proc/<pid>/environ`. If `FLAG` is unset (e.g. a local run without `-e`), it falls back to a test placeholder so the container still starts.

```sh
if [ -n "$FLAG" ]; then
    INSERT_FLAG="$FLAG"
    export FLAG=no_FLAG
    FLAG=no_FLAG
else
    INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
fi
```

## Delivery models — pick by intended exploit

### 1. File `/flag` (RCE / escape reads it)

```sh
echo "$INSERT_FLAG" | tee /flag
chmod 744 /flag          # world-readable; player RCE → cat /flag
# or, pwn-style inside the jail:
echo "$INSERT_FLAG" | tee /home/$user/flag
chmod 744 /home/$user/flag   # group ctf readable
```
Use when the intended solve is **code execution / jail escape** that can read the filesystem. Seen in: template pwn/flask/pyjail, r3ctf `evalgelist`, `storybook` (`644`), `safenotepro` (`744`).

### 2. Root-only / randomized file (privesc / exploit required)

```sh
flag_file="/root/flag_$(head -c 32 /dev/urandom | tr -cd 'a-f0-9').txt"
echo -n "$INSERT_FLAG" > "$flag_file"
chmod 400 "$flag_file"       # root-only
unset FLAG                   # scrub
```
Use when the player lands an unprivileged shell and must **escalate** to read the flag. Randomizing the name forces directory discovery / real privesc. Seen in: r3ctf `mohomi`, `nobrackets` (md5 name), `pigsay` (uuid name).

Pair with a `setuid` reader when the app user must never touch the flag file directly:
```dockerfile
COPY src/readflag.c /src/readflag.c
RUN gcc /src/readflag.c -o /readflag && chmod u+s /readflag
```
```c
// readflag.c — setuid root, prints /flag to stdout
int main(){ setuid(0); setgid(0);
  char b[0x100]; int fd=open("/flag",O_RDONLY);
  int n=read(fd,b,sizeof b); write(1,b,n); }
```
Seen in: r3ctf `notawebchal` (PHP `disable_functions` escape → run `/readflag`).

### 3. Bot-only file / cookie / localStorage (XSS exfil)

Keep the flag **out of the app container entirely** and give it only to the headless bot:
```sh
# app entrypoint
unset FLAG                  # app never sees it
apache2-foreground
```
```js
// bot (separate container, gets FLAG)
const flag = process.env.FLAG ?? 'flag{test_flag}';
await browser.setCookie({ name: 'flag', value: flag, domain: 'localhost' });
// or: await page.evaluate(f => localStorage.setItem('flag', f), flag);
```
Or, single-container, write it readable only by the bot user:
```sh
echo -n "$FLAG" > /flag
chown bot:bot /flag && chmod 400 /flag
unset FLAG
```
Seen in: r3ctf `silentprofit` (cookie), `r3note` (localStorage, bot-only file).

### 4. Database row (SQLi reads it)

```bash
if [[ -z $FLAG_COLUMN ]]; then FLAG_COLUMN="flag"; fi
if [[ -z $FLAG_TABLE  ]]; then FLAG_TABLE="flag";  fi
mysql -u root -p123456 -e "
USE ctf;
create table $FLAG_TABLE (id varchar(300),data varchar(300));
insert into $FLAG_TABLE values('$FLAG_COLUMN','$INSERT_FLAG');
"
```
Use for **SQL-injection** web challenges. `FLAG_TABLE`/`FLAG_COLUMN` are overridable so the author can hide the location. **Warning:** the template DB entrypoints do **not** scrub the env var — a PHP process can still read `getenv('FLAG')`. Scrub it yourself after the insert if env reads are in scope. Seen in: template `web-lamp-php80`/`web-lnmp-php73`.

### 5. CLI argv → generated artifact (stego / misc)

```sh
python3 /app/server.py "$INSERT_FLAG"   # flag passed as argv
```
```python
flag = sys.argv[1]   # server.py embeds it into a PNG (LSB) and serves over HTTP
```
Use when the flag is **transformed into an artifact** the player must recover. No `/flag` file written. Seen in: template `misc-lsb-dynamic`.

### 6. Runtime env read (quiz / crypto / solve-gated)

The entrypoint does nothing with the flag; the app reads it live:
```python
flag = os.getenv("FLAG")            # crypto
flag = os.environ.get("FLAG", "r3ctf{dummy_flag}")
```
Use when the flag is **printed/returned only after the player solves** the task (crypto proof, forensics quiz, pwn that prints on success). **Caveat:** the flag stays in the process environment. Only safe if the app cannot be tricked into reading env/files. Most r3ctf crypto and forensics challenges use this deliberately. Do **not** use it for a challenge where arbitrary file/env read is the vulnerability class.

### 7. Gated HTTP reveal (blockchain)

The flag never touches the chain or a file; a proxy returns it only when the on-chain `isSolved()` is true:
```python
(result,) = abi.decode(["bool"], web3.eth.call(
    {"to": chall_addr, "data": web3.keccak(text="isSolved()")[:4], "from": user_addr}))
if result:
    return "Challenge solved!\nFlag: " + os.environ.get("FLAG", "flag{contact_admin}") + "\n"
```
Seen in: r3ctf `miniagent`, `signin`.

### 8. Embed into app config (game servers / plugins)

```bash
if [ "$FLAG" ]; then
  sed -i "2s/.*/flag: $FLAG/" plugins/R3Craft/config.yml
  unset FLAG
fi
```
Seen in: r3ctf `r3craft`/`r4craft` (flag inside a Minecraft plugin YAML; the jail is the game mode).

## Scrubbing rules

- **Always scrub** (`unset FLAG` or overwrite to `no_FLAG`) after writing the flag to a file/DB/config — unless the app itself reads `FLAG` live (models 6/7).
- **Scrub before starting the long-running service**, and before any `rm -rf /docker-entrypoint.sh` cleanup (otherwise the cleanup after `sleep infinity` never runs).
- If the app legitimately needs `FLAG` in env, **ensure no code path can read env or arbitrary files**, or you have handed players the flag.

## Decision quick-table

| Intended solve | Delivery | Flag perms | Scrub env? |
|---|---|---|---|
| RCE / jail escape | `/flag` file | `744` / group-readable | yes |
| Privesc / kernel/heap exploit | root-only randomized file | `400` root | yes |
| PHP sandbox escape | root-only file + `setuid /readflag` | `400` root | yes |
| XSS exfil | bot-only cookie/localStorage/file | bot-only `400` | yes (from app) |
| SQL injection | DB row | n/a | yes (recommend) |
| Stego / misc transform | argv → artifact | n/a | yes |
| Crypto / forensics quiz | env, printed on solve | n/a | no (by design) |
| Blockchain | gated HTTP reveal | n/a | no (proxy reads live) |
