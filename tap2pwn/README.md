# tap2pwn

- **Author:** __readfsdword
- **Submissions:** 9
- **Solves:** 3

## Description

The year is 2020.

Every shitty Onetap v3 config is packed with a million bloated, pasted JSes and resold for hundreds of dollars.

Behind every pasted placebo "resolver", rainbow watermark, and $200 config was a scripting engine nobody bothered to threat-model.

Could you have been the one to turn the paste economy against itself, putting an end to the grift?

Let's find out…

You can view an example of RCE [here](https://drive.google.com/file/d/16_wDv8ehgogdtuFB8M02t7MlyO4YgH_9/view?usp=sharing).

Requirements for the RCE demo:

- Send your exploit as **one `.js` file**
- The game must continue to function normally after the RCE demonstration (popcalc)
- No bruteforcing — only **3** attempts allowed per team

**NOTE: ALL PARTS OF THE ATTACHMENTS WERE DOWNLOADED FROM SHADY SOURCES. RUN AT YOUR OWN RISK.**

Technically: a game-hack scripting-engine pwn — the player crafts a single
JavaScript file that achieves RCE inside the Onetap v3 scripting engine and
demonstrates it (popcalc) without breaking the game. Exploits are submitted
per team via ticket (3 attempts).

## Files

- `attachment/links.txt` — download links for the player handout (hosted
  externally; archive password `tap2pwn`) and the RCE demo video.
- `checker.rx` — platform flag checker (static flag), copied from the
  ret2shell export.

## Deployment

No container or remote service is deployed from this repo — the challenge is
driven by the external attachment plus per-team exploit submission via
ticket on the ret2shell platform (score rule: initial 1000 / minimum 100 /
decay 30).

- **Flag:** `r3ctf{d34th_2_scr1pt_k1ddies}` (static; see `checker.rx`)
