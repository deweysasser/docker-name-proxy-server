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

1) a priviledged container that subscribes to docker events and generates a configuration file
2) a non-priviledged (other than listening on port 80) container that consumes the generated configuration file and proxies traffic to the appropriate container.

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

## Load Balancing

Note that several container may specifiy that they handle traffice for
the same name and port combination.  This is a supported
configuration.  The received traffic will be load-balanced between the
containers subscribing to the same end point using nginx's "ip_hash"
sticky traffic mechanism.

There is no connection draining on exit, so if you terminate a
container subscribed to a given endpoint, the traffic will go to a
different endpoint without regard to session state.



## Legacy Environment variable support

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

This will have the proxy server listen on port 80, and when it is
called as "build.example.com" (e.g. "curl build.example.com" it will
forward traffic to the named docker container named 'jenkins' port
8080.

When called as "web.example.com", traffic will be forwarded to the
linked docker container referred to as 'dashboard' on port 5000.

Note that this allows the implementation containers ports to remain
unexposed on the host.


# TODO:  Future development possibilities

* have the updater start and restart the proxy.  This will allow the
  system to be run as a single container as well as allowing the
  listening ports on the proxy to be dynamically configured by the
  updater.