#!/bin/bash
PID=$(pgrep -f "python.*run.py")
if [ -n "$PID" ]; then
    echo "✅ Server is running (PID: $PID)"
    echo "🌐 http://localhost:5700"
else
    echo "❌ Server is not running"
fi
