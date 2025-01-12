#!/bin/bash
if [ $# -eq 1 ];then
    if [ "$1" = "-nr" ];then
        docker build --rm -t server -f server/Dockerfile . 
        docker build --rm -t node -f node/Dockerfile .
    else
        docker rmi $(docker images -a -q)
        docker build --rm -t server -f server/Dockerfile . 
        docker build --rm -t node -f node/Dockerfile .
    fi
else
    docker rmi $(docker images -a -q)
    docker build --rm -t server -f server/Dockerfile . 
    docker build --rm -t node -f node/Dockerfile .
fi
