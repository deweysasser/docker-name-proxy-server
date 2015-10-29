# Name based proxy server

This image is a named based proxy server.  By defining appropriate
environment variables, you can have it do host name based mapping to
foward to different server processes.

The design point is to multiplex a single port 80 to different
back-end processes.

This is what Apache Server calls "Named Virtual Hosts" and NGINX calls
"server blocks".

## Usage

Using e.g. docker-compose, try something like this:

     proxyserver:
       build: .
       ports:
         - 80:80
       links:
         - webserver:service
         - jenkins:build
         - dashboard:dashboard
       environment:
         DOMAIN: example.com
         __build: build:8080
         __web: service:80
         __dashboard: dashboard:5000

This will have the proxy server listen on port 80, and when it is
called as "build.example.com" (e.g. "curl build.example.com" it will
forward traffic to the linked docker container referred to internally
as 'build' on port 8080 (which is linked to a container named 'jenkins').

When called as "web.example.com", traffic will be forwarded to the
linked docker container referred to as 'dashboard' on port 5000.

Note that this allows the implementation containers ports to remain
unexposed on the host.

