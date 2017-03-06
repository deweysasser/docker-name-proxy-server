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
    assert-success "Resetting containers" docker rm -f $cleanup
    cleanup=""
}

pause() {
    echo 'Pausing'
    read
}

fail() {
    failed=$(($failed + 1))
#    pause
}

push() {
    local name="$1"
    shift
    eval "$name=\"\${$name} $*\""
}

drun() {
    name="$1-$$"
    shift
    docker run --name $name "$@" >/dev/nul
    push cleanup $name
}

normalize() {
    sed -e 's/\(nginx.*\)-[0-9]*/\1/g' -e 's/[0-9]\+\.[0-9]\+\.[0-9]\+\.[0-9]\+/0.0.0.0/g'
}

assert-success() {
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
	fail
    fi
}

assert-failure() {
    name="$1" ; shift
    dir=$(echo $name | tr ' ' _)
    results="test/results/$dir.txt"

    echo -n "$name..."
    "$@" 2>&1 > $results
    if [ $? -ne 0 ] ; then
	echo PASS
    else
	echo FAIL
	cat $results
	fail
    fi
}

assert-equal() {
    name="$1"; shift
    expected="$1"; shift

    echo -n "$name..."

    result=$("$@")

    if [ "$expected" == "$result" ]; then
	echo PASS
    else
	echo FAIL
	echo "  expected [$expected], got [$result]"
	fail
    fi
}

assert-not-equal() {
    name="$1"; shift
    expected="$1"; shift

    echo -n "$name..."

    result=$("$@")

    if [ "$expected" != "$result" ]; then
	echo PASS
    else
	echo FAIL
	echo "  expected [$expected], got [$result]"
	fail
    fi
}

assert-contains() {
    name="$1"; shift
    expected="$1"; shift

    echo -n "$name..."

    result=$("$@")

    if echo "$result" | grep -q "$expected"; then
	echo PASS
    else
	echo FAIL
	echo "  expected [$expected] in [$result]"
	fail
    fi
}

assert-not-contains() {
    name="$1"; shift
    expected="$1"; shift

    echo -n "$name..."

    result=$("$@")

    if ! echo "$result" | grep -q "$expected"; then
	echo PASS
    else
	echo FAIL
	echo "  expected [$expected] in [$result]"
	fail
    fi
}

nginx() {
    drun nginx-$(echo $1 | tr ' ' _) -d --label proxy.host=$1 nginx bash -c "echo $1 > /usr/share/nginx/html/index.html; nginx -g \"daemon off;\""
}


nginx host1
nginx host2

push cleanup updater-$$
assert-success "Running Update Process" docker run -d --name updater-$$ -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy 

sleep 3

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage1.txt
assert-success "Test Startup config" diff test/{output,expected}/stage1.txt 

nginx host3

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage2.txt
assert-success "Test Dynamic config" diff test/{output,expected}/stage2.txt


cleanup

push cleanup updater-$$
assert-success "Running Updater with Domain" docker run -d --name updater-$$ -e DOMAIN=example.com -v /var/run/docker.sock:/var/run/docker.sock name-based-proxy 

sleep 1

nginx host3
nginx host4.foobar.com

sleep 1

docker exec updater-$$ cat /etc/nginx/conf.d/proxy.conf | normalize > test/output/stage3.txt
assert-success "Test With Domain" diff test/{output,expected}/stage3.txt

push cleanup nginx-$$
assert-success "Starting proxy service" docker run -d --volumes-from updater-$$ --name nginx-$$ -P nginx > /dev/null

port=$(docker port nginx-$$ 80 | awk -F: '{print $2}')


assert-equal "Correct host3/short" host3 curl -s -H "Host: host3" $HOSTIP:$port
#assert-contains "Host List" "li" curl -s -H "Host: missing" $HOSTIP:$port
assert-not-equal "Do not find missing host" missing curl -s -H "Host: missing" $HOSTIP:$port
assert-equal "Correct host3/long" host3 curl -s -H "Host: host3.example.com" $HOSTIP:$port
assert-equal "Correct host4/long" host4.foobar.com curl -s -H "Host: host4.foobar.com" $HOSTIP:$port
assert-equal "Correct host4/short" host4.foobar.com curl -s -H "Host: host4" $HOSTIP:$port

#echo Address is $HOSTIP:$port
#pause



exit $failed