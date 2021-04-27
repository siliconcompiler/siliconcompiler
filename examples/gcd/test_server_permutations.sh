#!/bin/bash
mkdir -p ./build/gcd
mkdir ./local_server_work
GCD_DIR=`dirname "$0"`

# Start a local sc-server in a background task.
sc-server -nfs_mount ./local_server_work -cluster local &
SERVER_PID=$!

# Run a remote sc job targeting localhost as the 'remote'.
sc $GCD_DIR/gcd.v \
  -design gcd \
  -target freepdk45 \
  -asic_diesize "0 0 100.13 100.8" \
  -asic_coresize "10.07 11.2 90.25 91" \
  -constraint $GCD_DIR/constraint.sdc \
  -permutations $GCD_DIR/2jobs.py \
  -remote localhost

# Kill the temporary local sc-server process.
kill $SERVER_PID

if [[ -f "./[0-9a-f]*/gcd/job1/export/outputs/gcd.gds" ]] && \
   [[ -f "./[0-9a-f]*/gcd/job2/export/outputs/gcd.gds" ]]; then
  echo "Success!"
  exit 0
fi
echo "Fail :("
exit 1
