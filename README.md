ARCHIVED
========

This project is no longer maintained.  

The world has changed substantially since I wrote this.  I'm currently using [Traefik](https://traefik.io/) to fill this need.

This should be considered deprecated.

---

# Name based proxy server

Multiplex multiple docker web server containers through a single IP,
distinguished by hostname defines by labels on docker containers.

Also, in conjunction with the above or independently, set Route 53
host entries according to the hostnames.

The design point is to multiplex a single port 80 to different
back-end containers.

This is what Apache Server calls "Named Virtual Hosts" and NGINX calls
"server blocks".

See "Motivation" section for an other projects and an explanation of
why I wrote this.

This tool can additionally update Route 53 host names with the IP of
the current host or instance.

Because you run containers where hostname mapping is desirable but you
cannot proxy the protocol through NGINX, this container also updates
Route53 based on different labels which are independent of the proxy
hostnames.

## Usage

The proxy consists of 2 docker containers:

1) a priviledged container that subscribes to docker events and
   generates an NGINX configuration file (and a few other files)

2) an NGINX container that uses the generated file to proxy traffic to
   other containers

Note that you must configure notifications correctly for nginx to be
reloaded on configuration changes

## Deploying the proxy/updater combination

The two containers must be deployed on a single host and share a data
volume by volumes.  

One way to do that is with the following docker-compose.yml file:

     proxy:
       image: nginx
       volumes:
        - /etc/nginx/conf.d
        - /usr/share/nginx/html
       ports:
         - "80:80"
       labels:
         - proxy.notify=/etc/init.d/nginx reload
          
     updater:
       build: .
       cap_drop:
          - ALL
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock
       volumes_from:
         - proxy

The down side of this file is that the proxy must be redeployed any
time the exposed ports change.

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

Traffic is proxied acording to container metadata as expressed in
docker labels.

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

If you do not specify proxy.ports, it defaults to port 80.

## Configuring notifications

For each container labeled 'proxy.notify' with no value, the updater
will invoke "kill -HUP 1" inside that container.  If the
'proxy.notify' label has a value, that value is taken as a command to
run inside the container to notify of configuration changes.

## Updating Route 53

When run with command line argument "--route53", the container will
attempt to update the appropriate Route 53 zone for the name in the
proxy.host (or environment) labels.

In this mode it uses one of the following credentials:

  * the priviledges of the host or container (if an appropriate IAM
    role is set)
  * the contents of ~/.aws/credentials (by default there are none)
  * the values specified by command line arguments --key and --secret
    for AWS credenitals
  * environemnt variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

The IP address can be encoded on the commad line (with --my-ip <IP>),
introspected using a public IP address service (--public-ip-service),
or introspected using AWS metadata service.  The the last case, the
"--aws-external-ip" flag specifies using the external, public IP of
the instance and "--aws-internal-ip" flag specifies using the local,
internal IP of the instance.  The default is to use a public web
service to determine the external IP address.

In all cases, if updating Route 53 fails, the program will continue to
attempt other updates.

The following IAM policy must be in effect for the credentials used to
update Route53:

     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Sid": "Stmt1485728091000",
                 "Effect": "Allow",
                 "Action": [
                     "route53:ListHostedZones",
                     "route53:ListResourceRecordSets",
                     "route53:ChangeResourceRecordSets"
                 ],
                 "Resource": [
                     "*"
                 ]
             }
         ]
     }

### Configuring DNS entries independent of proxies

If you have a container which NGINX cannot proxy, instead of using the
'proxy.host' label, you can use 'dns.hostname'.  If this update
container is run with "--route53", all values of "dns.hostname" will
be collected and pushed into route53 the same as the values of
"proxy.host".


## Load Balancing

Note that several container may specifiy that they handle traffic for
the same name and port combination.  This is a supported
configuration.  The received traffic will be load-balanced between the
containers subscribing to the same end point using nginx's "ip_hash"
sticky traffic mechanism.

There is no connection draining on exit, so if you terminate a
container subscribed to a given endpoint, the traffic will go to a
different endpoint without regard to session state.

## Short names vs FQDNs:  redirection vs direct service

By default, the proxy is configured so that both the short
(non-qualified names) and the long name are forwarded to the back-end
server container.

So, if you have a server with the `proxy.host` label
`www.example.com`, both 'http://www.example.com' and 'http://www' will
be directly forwarded to that container.

If, instead, you run the container/script with the option
`--redirect-shortnames`, instead of forwarding the request directly,
the proxy will return a 301 permanent redirect of the short name to
the long name.

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


## Motivation

This system is largely inspirted by
https://github.com/jwilder/nginx-proxy.  The reason I wrote this,
instead of just using jwilder's excellent image, is a difference in
assumptions.

He assumes that any exposed port should be proxied.  My package allows
translations of proxied ports.

For example, the standard "jenkins" docker images exposes (and
services requests on) port 8080.  I wish port 80 proxied to that port.
At the time this was written, his package could not accomplish that.

Also, at the time this was originally written, his package did not
document a way to run the monitor process and proxy process in
separate containers.  Running proxy and monitor (i.e. something which
has access to the docker socket) in the same container is not a great
idea.

## Contributing

See the file HACKING.md for information on how to contribute to this
project.
