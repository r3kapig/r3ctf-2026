#!/bin/sh
# whisper is a multi-service system (backend + judge + Android victim pool).
# There is no single image to build.
#   Production stack (organizers):  cd deploy/deploy && ./run.sh
#   Local repro (players):          7zz x attachment/whisper-local-stack.7z
#                                   cd whisper-local-stack && ./run.sh
set -e
echo "whisper: production deploy -> cd deploy/deploy && ./run.sh"
echo "whisper: local repro       -> 7zz x attachment/whisper-local-stack.7z && cd whisper-local-stack && ./run.sh"
echo "See README.md for details."
