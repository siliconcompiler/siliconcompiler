set -e
IFS=',' read -r -a scripts <<< "$1"
for script in "${scripts[@]}"; do
    chmod +x ./${script}
    ./${script}
    rm -rf $SC_BUILD/deps
done
