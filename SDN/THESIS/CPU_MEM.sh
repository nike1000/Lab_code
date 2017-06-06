#!/bin/sh

pid=`pgrep ryu-manager`

while sleep 1; do
    echo -n `date +%H:%M:%S`
    ps --no-headers -o '%cpu,%mem' -p $pid;
done
