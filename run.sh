#!/bin/bash

SERVER=0
NODES=0
NUMBER=0
NODE_NAME=""

if [ -f .conf ];then
    NUMBER=$(wc -w < .conf)
fi

echo "$NUMBER NODE/S are running."

while test $# -gt 0; do
  case "$1" in
    -h|--help)
      echo "$package - attempt to capture frames"
      echo " "
      echo "$package [options] application [arguments]"
      echo " "
      echo "options:"
      echo "-h, --help                show brief help"
      echo "-s, --server              specify server run"
      echo "-n, --nodes=NUM           specify number of nodes to run (default=5)"
      echo "-nn, --nodes name=NAME    specify name of node to run (e.g. 'node4')"
      exit 0
      ;;
    -s)
      shift
      if [ $# -gt 0 ];then
        if [ $1 -eq 1 ];then
            export SERVER=$1
        else
            echo "ERROR: -s only require number 1!"
            exit 1
        fi
      else
        echo "ERROR: -s only require number 1!"
        exit 1
      fi
      shift
      ;;
    -n)
      shift
      if test $# -gt 0; then
        if [ $1  -lt 1 ] || [ $1 -gt 10 ];then
            echo "ERROR: -n number out of [0;10]!"
            exit 1
        else
            n=$(($NUMBER+$1))
            if [ $n -lt 11 ];then
                export NODES=$1
            else
                echo "ERROR: -n number out of [0;10]!"
                exit 1
            fi
        fi
      else
        echo "ERROR: -n require a number!"
        exit 1
      fi
      shift
      ;;
    -nn)
      shift
      if test $# -eq 1; then
        export NODE_NAME=$1
      else
        echo "ERROR: -nn require a name node!"
        exit 1
      fi
      shift
      ;;
    *)
      break
      ;;
  esac
done

if [ $SERVER -eq 1 ];then
    echo "RUN SERVER"
    konsole --geometry 500x350+0+0 -p tabtitle='SERVER' -e docker compose run --rm --name server server &
    time=$((5+$NODES))    
    sleep $time
fi

echo "RUN $NODES NODE/S"
count=0
for ((i=1; i<=10; i++)); do
    if [ $count -lt $NODES ];then
        if ! grep -q node$i ".conf";then  
            x=$((($i % 4)*482))
            if [ $i -lt 4 ];then
                y=0
            elif [ $i -lt 8 ];then
                y=380
            else
                y=760
            fi
            konsole --geometry 480x350+$x+$y -p tabtitle='node'$i -e docker compose run --rm --name node$i node$i &
            let count++
            echo node$i >> .conf
        fi
    else
        break
    fi    
done 

if ! grep -q $NODE_NAME ".conf";then  
    echo "RUN $NODE_NAME"   
    konsole -p tabtitle=$NODE_NAME -e docker compose run --rm --name $NODE_NAME $NODE_NAME &
    echo $NODE_NAME >> .conf
else
    echo "ERROR! $NODE_NAME is already running"
    exit 1
fi

