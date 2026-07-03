import os

# Real flag injected at runtime by the platform via the FLAG env var.
FLAG = os.environ.get("FLAG", "r3ctf{test_flag}")
