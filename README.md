# Name based proxy server

This image is a named based proxy server.  By defining appropriate
environment variables, you can have it do host name based mapping to
foward to different server processes.

The design point is to multiplex a single port 80 to different
back-end processes.

This is what Apache Server calls "Named Virtual Hosts" and NGINX calls
"server blocks".

## Usage

The proxy consists of 2 docker containers:

1) a priviledged container that subscribes to docker events and generates an NGINX configuration file (and a few other files)
2) an NGINX container that uses the generated file to proxy traffic to other containers

Note that you must configure notifications correct for nginx to be reloaded on configuration changes

## Deploying the proxy/updater combination

The two containers must be deployed on a single host and be linked by
volumes.  One way to do that is with the following docker-compose.yml
file:

     proxy:
       image: nginx
       volumes:
        - /etc/nginx/conf.d
        - /usr/share/nginx/html
       ports:
         - "80:80"
       labels:
         - proxy.notify
          
     updater:
       build: .
       cap_drop:
          - ALL
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
       volumes_from:
         - proxy

The down side of this file is that the proxy must be redeployed any time the exposed ports change.

Alternatively, you could use this stanza for the proxy:

     proxy:
       image: nginx
       volumes:
        - /etc/nginx/conf.d
        - /usr/share/nginx/html
       net: host

This configuration will allow dynamic selection of listening ports but
may cause nginx start-up problems if ports are already bound.

## Configuring proxies

Traffic is proxied acording to container metadata as expressed in docker labels.

The label "proxy.host" is used as a hostname which proxies to a
certain container.  This should be a FQDN (fully qualified domain name
-- e.g. "foo.example.com")

The label "proxy.ports" contsists of a space separated list to which
to proxy.  Each entry can be either a port to be proxied, or a pair of
"src:dst" for a source port and destination port.

Example:

     docker run -d --label proxy.host=foo.example.com --label proxy.ports="5000 81:82 80" nginx

Creates an entry so that traffic received going to "foo.example.com"
on port 5000 is proxied to the container on port 5000, traffic
received to that name on port 81 is proxied to the container's port 82
and traffic received on port 80 is proxied to port 80.

## Configuring notifications

For each container labeled 'proxy.notify' with no value, the updater
will invoke "kill -HUP 1" inside that container.  If the
'proxy.notify' label has a value, that value is taken as a command to
run inside the container to notify of configuration changes.


## Load Balancing

Note that several container may specifiy that they handle traffic for
the same name and port combination.  This is a supported
configuration.  The received traffic will be load-balanced between the
containers subscribing to the same end point using nginx's "ip_hash"
sticky traffic mechanism.

There is no connection draining on exit, so if you terminate a
container subscribed to a given endpoint, the traffic will go to a
different endpoint without regard to session state.



## Legacy configuration via environment variables

Docker labels is the preferred method of specifying proxy
configuration and notification.

In order to support the legacy configuration method, the updater
container configuration will also be updated in response to certain
environment variable settings.

Using e.g. docker-compose.override.yml, try something like this:

 updater:
   environment:
     DOMAIN: example.com
     __build: jenkins:8080
     __web: webserver:80
     __dashboard: dashboard:5000
     NOTIFY:  docker run proxy kill -HUP 1

This will have the proxy server listen on port 80, and when it is
called as "build.example.com" (e.g. "curl build.example.com" it will
forward traffic to the named docker container named 'jenkins' port
8080.

When called as "web.example.com", traffic will be forwarded to the
linked docker container referred to as 'dashboard' on port 5000.

The 'NOTIFY' environment variable can specify a command to run when
configuration changes.

Note that this allows the implementation containers ports to remain
unexposed on the host.


