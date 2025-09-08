#!/bin/bash
# Kill Python processes script for Git Bash/WSL

echo "Killing all Python processes..."

# Get Python process IDs
python_pids=$(tasklist.exe | grep -i python | awk '{print $2}')

if [ -n "$python_pids" ]; then
    echo "Found Python processes: $python_pids"
    
    for pid in $python_pids; do
        # Remove any non-numeric characters
        clean_pid=$(echo "$pid" | tr -d '\r\n' | grep -o '[0-9]*')
        
        if [ -n "$clean_pid" ]; then
            echo "Killing PID: $clean_pid"
            taskkill.exe /F /PID "$clean_pid" >/dev/null 2>&1
        fi
    done
    
    echo "✓ Python processes terminated"
else
    echo "- No Python processes found"
fi

echo
echo "Done! You can now restart the server safely."