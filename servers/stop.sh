#!/bin/bash
if [ $# -ne 0 ]
then
    SERVICE=$1
	NAME=$2
    echo "[Kill Port $PORT]"
    ps aux | grep Servers.py | grep -v "grep" | grep "--service=$SERVICE" | grep "--schedule=$NAME" | awk '{print $2}' | xargs -t -I {} kill {}
else
    echo "[Kill All]"
    ps aux | grep Servers.py | grep -v "grep" | awk '{print $2}' | xargs -t -I {} kill {}
fi
