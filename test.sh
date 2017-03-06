#!/bin/bash

trap 'cleanup' 0
failed=0

mkdir -p test/{output,results}

if [ -n "$DOCKER_HOST" ] ; then
    HOSTIP=$(echo $DOCKER_HOST | awk -F: '{print $1}')
else
    HOSTIP=127.0.0.1
fi

cleanup() {
    echo Cleaning Up
    docker rm -f $cleanup >/dev/null
    cleanup=""
}

push() {
    name="$1"
    shift
    eval "$name=\"\${$name} $*\""
}

run() {
    name="$1-$$"
    shift
    docker run --name $name "$@" >/dev/nul
    push cleanup $name
}

normalize() {
    sed -e 's/\(nginx.*\)-[0-9]*/\1/g' -e 's/[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/0.0.0.0/g'
}

dotest() {
    name="$1" ; shift
    dir=$(echo $name | tr ' ' _)
    results="test/results/$dir.txt"

    echo -n "$name..."
    "$@" 2>&1 > $results
    if [ $? -eq 0 ] ; then
	echo PASS
    else
	echo FAIL
	cat $results
	failed=$(($failed + 1))
    fi
}

nginx() {
    run nginx-$(echo $1 | tr ' ' _) -d --label proxy.host=$1 nginx bash -c "echo $1 > /usr/local/nginx/html/index.html; nginx -g \"daemon off;\""
}


echo "Running hosting targets"
nginx host1
nginx host2

echo "Running updater"
push cleanup updater-$$
docker run -d --name updater-$$ -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy > /dev/null

sleep 2

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage1.txt
dotest "Test Startup" diff test/{output,expected}/stage1.txt 

nginx host3

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage2.txt
dotest "Test Dynamic Pickup" diff test/{output,expected}/stage2.txt


cleanup

echo "Running updater with DOMAIN=example.com"
push cleanup updater-$$
docker run -d --name updater-$$ -e DOMAIN=example.com -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy > /dev/null

sleep 1

nginx host3
nginx host4.foobar.com

sleep 1

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage3.txt
dotest "Test With Domain" diff test/{output,expected}/stage3.txt

echo "Starting up nginx" 
push cleanup nginx-$$
docker run -d --volumes-from updater-$$ --name nginx-$$ -P nginx > /dev/null

port=$(docker port nginx-$$ 80 | awk -F: '{print $2}')

echo Address is $HOSTIP:$port

exit $failed