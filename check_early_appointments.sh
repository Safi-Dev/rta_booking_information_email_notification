#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Get Python executable from settings
python3_exe="$(jq '.python3_executable' settings.json | tr -d '"')"

echo "$(date +'[%T] :') Starting early appointment checker in continuous mode..."
echo "$(date +'[%T] :') Press Ctrl+C to stop the script"

# Run the Python script
$python3_exe check_early_appointments.py

echo "$(date +'[%T] :') Script has stopped." 