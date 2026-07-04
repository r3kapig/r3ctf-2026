#!/bin/sh

# drop the entrypoint script once loaded
rm -f /home/sage/docker-entrypoint.sh

# forward TCP:9999 into a SageMath session per connection
socat -v -s TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork EXEC:"sage -python /home/sage/task.py"
