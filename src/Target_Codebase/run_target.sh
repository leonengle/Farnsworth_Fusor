#!/bin/bash
# Wrapper script to run target_main.py with proper environment for GPIO

cd /home/mdali/Farnsworth_Fusor/src/Target_Codebase

# Activate venv
source /home/mdali/Farnsworth_Fusor/venv/bin/activate

# Ensure we have access to /proc and /dev
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Run the target main script
exec /home/mdali/Farnsworth_Fusor/venv/bin/python3 /home/mdali/Farnsworth_Fusor/src/Target_Codebase/target_main.py

