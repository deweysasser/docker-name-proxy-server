#!/bin/bash

trap 'cleanup' 0
failed=0

mkdir -p test/{output,results}

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
    sed -e 's/\(bbox.\)-[0-9]*/\1/g' -e 's/[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/0.0.0.0/g'
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


echo "Running hosting targets"
run bbox1 -d --label proxy.host=host1 busybox sleep 1d
run bbox2 -d --label proxy.host=host2 busybox sleep 1d

echo "Running updater"
docker run -d --name updater-$$ -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy > /dev/null
push cleanup updater-$$

sleep 1

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage1.txt
dotest "Test Startup" diff test/{output,expected}/stage1.txt 

run bbox3 -d --label proxy.host=host3 busybox sleep 1d

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage2.txt
dotest "Test Dynamic Pickup" diff test/{output,expected}/stage2.txt


exit $failed