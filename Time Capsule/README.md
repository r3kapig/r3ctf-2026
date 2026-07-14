# Time Capsule

- **Author:** WhiteDragonQwQ
- **Submissions:** 61
- **Solves:** 11

## Description

In the far future of digital archaeology, Earth's own ruins have long been
exhausted. But the legacy of the pre-AI era still drifts silently in
geosynchronous orbit—satellite debris, derelict space servers, all waiting to
be explored. A new breed of professionals has emerged: the **Cyber Hunters**.

Today, a storage facility designated UMA-R3 was hauled into the ship and
dismantled. Among the piles of ancient hardware, one hard drive was carefully
connected to a reader. Inside rested data in countless formats: voice logs,
manuscript documents, network packet captures, encrypted archives, even a 3D
voxel renderer. They appeared chaotic, yet they all seemed to lead back to one
source—a secret group calling themselves the **Streamlivers**.

The only immediately readable file on the drive is a short letter, its
signature long since lost:

> *"If you are reading these words, congratulations—you have already set foot
> on the path we walked. Every piece of data here is a lock, guarding what
> remains of human curiosity. AI understands frames, but we live in the
> stream. Seek four keys to six secrets hidden in spe￥&@*（￥&@（*#&￥*@（&#&@#*#*&￥.
> What we leave behind is not merely a puzzle, but a way of thinking that has
> long been forgotten."*

**Recover the final flag from the data fragments of UMA-R3.**

Technically, this is a self-contained multi-stage forensics puzzle: players
extract `attachment.7z` and work entirely offline. The satellite logs carry
hints via zero-width Unicode whitespace characters (e.g. `200A|200E|200B`)
and spectral clues in the `.wav` voice logs; the packet capture and the ~106
password-locked zips in `COMPRESSED_DATA/` (each holding a `part_N.bin`
fragment) form a decryption chain whose recovered fragments are finally
reassembled and viewed with the bundled `VoxelEditor.html` 3D voxel renderer.
The flag is static and obtained purely from the data.

## Files

- `attachment.7z` — packed player handout (~57 MB). Extract with
  `7zz x attachment.7z` to get the `attachment/` directory.
- `attachment/` — extracted handout contents:
  - `attachment/README.md` — the in-universe letter / README shipped inside
    the forensic drive image.
  - `attachment/satellitelog/` — satellite log fragments: two `.txt` logs
    (one embedding zero-width character hints) and a `.pcap` capture.
  - `attachment/RECORD/` — `.wav` voice logs (spectral analysis material).
  - `attachment/COMPRESSED_DATA/` — ~106 password-protected `.zip` archives
    named after sci-fi movies, each containing a `part_N.bin` fragment.
  - `attachment/Secret.png` — image artifact from the drive.
  - `attachment/VoxelEditor.html` — standalone HTML 3D voxel renderer/viewer.

## Deployment

Static attachment — no remote service, no image to build, no flag injection.
Players download and extract `attachment.7z` and analyze the data offline:

```sh
7zz x attachment.7z
```

The flag is static and recovered by solving the puzzle chain; there is
nothing to deploy beyond hosting the attachment.
