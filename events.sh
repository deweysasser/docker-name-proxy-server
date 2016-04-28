#!/bin/bash

# Purpose: consume docker events and do interesting things

# Run once initially
`dirname $0`/build-proxy-config.py > /etc/nginx/conf.d/proxy.conf

docker events -f type=container -f event=die -f event=start | while read time ID LINE ; do
    echo "id $ID: $LINE"
    `dirname $0`/build-proxy-config.py > /etc/nginx/conf.d/proxy.conf
done