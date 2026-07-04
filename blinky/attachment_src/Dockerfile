# Player build container
#
# It carries the MIPS64 cross-toolchain (+ libstdc++6 so SOC_run_sim can also run
# in here) so you can build -- and optionally run -- your exploit WITHOUT installing
# anything on your host.
#
#   docker build -t blinky-build .
#   # build (default entrypoint): .s -> USER-region image you upload to the server
#   docker run --rm -v "$PWD:/work" blinky-build exploit.s              # -> exploit.{bin,mem}
#   # run locally (override entrypoint): splice with the local kernel + run the sim
#   docker run --rm -v "$PWD:/work" --entrypoint /opt/blinky-build/run_local.sh \
#          blinky-build exploit.mem
#
# The container writes into /work, so bind-mount your working directory there. The
# default entrypoint is build.sh; args are passed straight to it ([src] [out_prefix]).
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        binutils-mips64el-linux-gnuabi64 \
        libstdc++6 \
        python3 \
    && rm -rf /var/lib/apt/lists/*

# Ship the scripts + linker script + local example kernel out of the mounted /work so
# a player can't clobber them by accident. run_local.sh falls back to this baked-in
# example_kernel.mem when splicing a submission for a local run.
COPY build.sh run_local.sh script.ld example_kernel.mem /opt/blinky-build/
RUN chmod +x /opt/blinky-build/build.sh /opt/blinky-build/run_local.sh

WORKDIR /work
ENTRYPOINT ["/opt/blinky-build/build.sh"]
CMD ["exploit.s"]
