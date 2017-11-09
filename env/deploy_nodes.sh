#!/bin/bash


if [ $# -ne 3 ]
then
	echo "Usage: ./$0 service schedule"
	exit
else
	SERVICE=$1	
	SCHEDULE=$2
fi

while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    DEST=${line%% *} 
	WORKSHOP_DIR=${line##* }
	if [ ! -d $WORKSHOP_DIR ]
	then
		./install.expect ${line}
	else
    	echo "Synchronize "$DEST"..."
		./sync.expect $line
	fi	
done 10< nodes

cd ../servers
echo "Deploying tensorflow_serving out-of-box models..."
python service_schedules.py --schedule_name=$1
