#!/bin/bash

set -e

if [ "$FLAG" ]; then
  sed -i "1s/.*/flag: $FLAG/" plugins/R3Reach/config.yml
  unset FLAG
fi

java -Xms1G -Xmx2G -jar paper-26.2-40.jar nogui
