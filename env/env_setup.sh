#!/bin/bash

LOC_PACKAGE_DIR=/search/odin/online_package
tfpkg="tensorflow-1.2.0rc0-cp27-cp27mu-linux_x86_64.whl"
pip="pip-9.0.1.tar.gz"
cudnn="cudnn-8.0-linux-x64-v5.1.tgz"
cuda="cuda-repo-rhel7-7-5-local-7.5-18.x86_64.rpm"
bash="node_bashrc"

while read -u10 line 
do
    if [[ ${line:0:1} = "#" ]]
    then
        continue
    fi
	##################################################
	#           Copy important pkgs to nodes         # 
	##################################################
	#./send_pkgs.expect $line $LOC_PACKAGE_DIR/$tfpkg  
	#./send_pkgs.expect $line $LOC_PACKAGE_DIR/$pip 
	#./send_pkgs.expect $line $LOC_PACKAGE_DIR/$cuda 
	#./send_pkgs.expect $line $LOC_PACKAGE_DIR/$cudnn 
	#./send_pkgs.expect $line $LOC_PACKAGE_DIR/$bash 

	##################################################
	#                 Instal CUDA                    # 
	##################################################
	#./cuda_install.expect $line $cudnn $cuda 

	##################################################
	#     Install pip and Tensorflow Package         #
	##################################################
	#./tf_install.expect $line $pip $tfpkg

	######################################@###########
	#         Clone TFWorkshop repo       @#         #
	######################################@###########
	./clone.expect $line

done 10< nodes
