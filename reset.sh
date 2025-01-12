#!/bin/bash
if [ $# -eq 1 ];then
    if [ "$1" = "-v" ];then
        rm -r volumes
        cp -r .volumes_start volumes
    fi
fi
rm -r logs
mkdir logs
#for i in 1 2 3 4 5 6 7 8 9 10;do
#    mkdir logs/node$i
#done
rm .conf
docker kill $(docker ps -q)
docker rm $(docker ps -a -q)

