#!/bin/bash

NGINX_SERVER="root@10.153.58.67 chatbot@2017online"
DEST_DIR=/search/odin/offline/TFWorkshop

while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
    DEST=${line%% *} 
    echo " ===========================  Sync and restart "$DEST" ==================================="
    ssh $DEST "cd $DEST_DIR; git config --global user.email 'lihangyu@sogou-inc.com'" 
    ssh $DEST "cd $DEST_DIR; git config --global user.name 'Nick'" 
	ssh ./sync.expect $DEST_DIR	
#./start.expect ${line} 
done 10< nodes 

DEST=${NGINX_SERVER%% *} 
scp nginx.conf $DEST:/etc/nginx/
ssh $DEST "cd $DEST_DIR; sh env/start_nginx.sh"
