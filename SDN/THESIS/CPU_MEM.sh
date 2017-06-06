#!/bin/sh

while sleep 1; do
    echo -n `date +%H:%M:%S`
    ps --no-headers -o '%cpu,%mem' -p $1;
done
