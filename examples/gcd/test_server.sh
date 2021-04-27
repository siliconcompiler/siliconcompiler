#!/bin/bash
mkdir -p ./build/gcd
mkdir ./local_server_work

# Start a local sc-server in a background task.
sc-server -nfs_mount ./local_server_work -cluster local &
SERVER_PID=$!

# Run a remote sc job targeting localhost as the 'remote'.
sc ./examples/gcd/gcd.v \
  -design gcd \
  -target freepdk45 \
  -asic_diesize "0 0 100.13 100.8" \
  -asic_coresize "10.07 11.2 90.25 91" \
  -constraint examples/gcd/constraint.sdc \
  -remote localhost

# Kill the temporary local sc-server process.
kill $SERVER_PID

if [ -f "./build/gcd/job1/export/outputs/gcd.gds" ]; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
