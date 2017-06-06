#!/bin/sh

pid=`pgrep ryu-manager`

while sleep 1; do
    echo -n `date +%H:%M:%S`
    echo -n " "
    #ps --no-headers -o '%cpu,%mem' -p $pid;
    top -b -p $pid -n 1 | grep ryu-manager | sed 's/  */ /g' | awk '{print $9, $10}'
done
