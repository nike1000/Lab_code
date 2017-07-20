#!/bin/sh

while true; do
    curl -s http://140.113.216.237:8080/Generic_LLDP_Module/rest/links | python -m json.tool >> link.txt
    echo '-----------------------------------------------------\n' >> link.txt
    sleep 5
done
