sudo apt-get update
sudo apt-get install -y build-essential cmake libboost-dev
mkdir -p thirdparty
git clone https://github.com/microsoft/SEAL.git thirdparty/seal
git -C thirdparty/seal checkout 02a5c345a48281da2cdd382daec0ece02a3fae3f
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DSEAL_BUILD_DEPS=OFF \
  -DSEAL_USE_MSGSL=OFF \
  -DSEAL_USE_ZLIB=OFF \
  -DSEAL_USE_ZSTD=OFF \
  -DSEAL_USE_INTEL_HEXL=OFF \
  -DSEAL_BUILD_EXAMPLES=OFF \
  -DSEAL_BUILD_TESTS=OFF \
  -DSEAL_BUILD_BENCH=OFF \
  -DSEAL_BUILD_SEAL_C=OFF
cmake --build build -j --target he_server
./build/he_server
