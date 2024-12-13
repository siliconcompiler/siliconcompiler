#!/usr/bin/env bash
# SiliconCompiler Replay Setup
# Design: {{ design }}
# Jobname: {{ jobname }}
# Date: {{ date }}

if ! [ "${BASH_SOURCE[0]}" -ef "$0" ];
then
    echo "${BASH_SOURCE[0]} must be executed"
    return 1
fi

_help() {
cat <<EOF
{{ description }}
Usage: $0 -dir=DIR
                    # Directory to use for extraction, defaults to "./replay"
       $0 -venv=DIR
                    # Name of virtual environment, defaults to "venv"
       $0 -print_tools
                    # Print tool version and exit
       $0 -extract_only
                    # Only extract the files
       $0 -setup_only
                    # Only setup the runtime environment
       $0 -assert_python
                    # Require python versions match
       $0 -help
                    # Print this help information
EOF
}

_print_tools() {
cat <<EOF{% for line in tools %}
{{ line }}{% endfor %}
EOF
}

path=$(realpath replay)
venv="venv"
extract_only="no"
setup_only="no"
assert_python="no"

while [ "$#" -gt 0 ]; do
    case "${1}" in
        -h|-help)
            _help
            exit 0
            ;;
        -extract_only)
            extract_only="yes"
            ;;
        -setup_only)
            setup_only="yes"
            ;;
        -assert_python)
            assert_python="yes"
            ;;
        -print_tools)
            _print_tools
            exit 0
            ;;
        -dir=*)
            path=$(realpath ${1#-dir=})
            ;;
        -venv=*)
            venv=${1#-venv=}
            ;;
        *)
            echo "Unknown option: ${1}" >&2
            _help
            exit 1
            ;;
    esac
    shift 1
done

# Create output path
mkdir -p "$path"

# Change to output path directory
cd "$path"

# Add gitignore
echo "*" > .gitignore

# Extract files
read -r -d '' SCRIPT << PythonScript{% for line in script %}
{{ line }}{% endfor %}
PythonScript

echo "$SCRIPT" | base64 --decode | gunzip > replay.py
chmod +x replay.py

read -r -d '' MANIFEST << Manifest{% for line in manifest %}
{{ line }}{% endfor %}
Manifest

echo "$MANIFEST" | base64 --decode | gunzip > sc_manifest.json

cat > requirements.txt << PythonRequirements{% for line in requirements %}
{{ line }}{% endfor %}
PythonRequirements

if [ "$extract_only" == "yes" ]; then
    exit 0
fi

if [ "$(python3 -V)" != "Python {{ pythonversion }}" ]; then
    echo "Python version mismatch: $(python3 -V) != {{ pythonversion }}"

    if [ "$assert_python" == "yes" ]; then
        exit 1
    fi
fi

python3 -m venv $venv --clear

. $venv/bin/activate
pip3 install -r requirements.txt

echo "To enable run environment: . $path/$venv/bin/activate"
echo "To replay: $path/replay.py"

if [ "$setup_only" == "yes" ]; then
    exit 0
fi

./replay.py
