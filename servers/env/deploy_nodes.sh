#!/bin/bash

##############################################################
###### Here to assign the service and schedule to deploy #####
##############################################################

WORKSHOP_NAME="TFWorkshop"
SERVICE=generate
SCHEDULE=cvae_posterior_cn

models=`python ../service_schedules.py --schedule_name=$SERVICE:$SCHEDULE --only_print_models=True`

##### syncronize code ######### 
while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    echo "Synchronize "$DEST"..."

	./sync.expect $line $WORKSHOP_NAME 
done 10< nodes



echo "Deploying tensorflow_serving out-of-box models..."
for each in $models 
do
	##### create multi-process get related models and push them to nodes ####
	while read -u10 line 
	do
		if [[ ${line:0:1} = "#" ]]
	    then
	        continue
	    fi
		node_passwd=${line% *}
		dest_dir=${line##* }
	    ( ./send_pkgs.expect $node_passwd $dest_dir ../deployments/$each & )
	
	done 10< nodes
done


