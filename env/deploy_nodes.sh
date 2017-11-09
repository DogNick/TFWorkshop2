#!/bin/bash

SERVICE=$1	
SCHEDULE=$2

while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    echo "Synchronize "$DEST"..."
	./sync.expect $line "TFWorkshop"
done 10< nodes

#cd ../servers
#echo "Deploying tensorflow_serving out-of-box models..."
#python service_schedules.py --schedule_name=$SERVICE:$SCHEDULE
