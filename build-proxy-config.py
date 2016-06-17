#!/usr/bin/python

import os
import re
import docker
import json
import itertools

if 'DOCKER_HOST' in os.environ:
    cli = docker.Client(base_url=os.environ['DOCKER_HOST'])
else:
    cli = docker.Client(base_url='unix://var/run/docker.sock')

def container_ids(c=None):
    containers = cli.containers() if c is None else c
    return [x['Id'] for x in containers]


def collect_host_tuples(ids):
    '''Collect the 4-tuple of (name, port, target-ip, target-port) for each of the given container IDs'''
    def ext(l, value):
        l.extend(value)
        return l

    return reduce(ext, filter(None, map(collect_host_tuple, ids)), [])


def collect_host_tuple(id):
    '''Return information about a specific container, or None if the container has no labels'''
    container = cli.inspect_container(id)
    ip=container['NetworkSettings']['IPAddress']
    cname=container['Name'][1:]
    if not 'Labels' in container['Config']: return None
    labels=container['Config']['Labels']

    if "proxy.host" in labels:
        name=labels["proxy.host"]
        def port(p):
            s = p.split(":")
            if len(s) > 1:
                (host_port, container_port) = s
            else:
                (host_port, container_port) = (p, p)
            return (name, host_port, ip, container_port, cname)
        if not "proxy.ports" in labels:
            return [(name, "80", ip, "80", cname)]

        ports = labels["proxy.ports"].split()
        r = map(port, ports)
        return r

def upstream(file, tuples):
    '''Generate the upstream block for nginx.conf'''
    for key, group in itertools.groupby(tuples, lambda x: x[0]):
        print >> file,  "upstream {} {{ ".format(to_token(key))
        print >> file,  "  ip_hash;"
        for t in group:
            print >> file,  "   server {}; # {}".format(t[1], t[2])
        print >> file,  "}\n"

def listen(file, ports):
    '''Generate the server block for nginx.conf'''
    pass
#    for p in ports:
#        print >> file,  "server {"
#        print >> file,  "  listen {};".format(p)
#        print >> file,  "}"

def server(file, tuples):
    for t in tuples:
        print >> file,  '''
server {{
  listen  {host_port};
  server_name {name};

  location / {{
      proxy_pass http://{upstream};
      proxy_redirect default;

      proxy_set_header   Host             $host;
      proxy_set_header   X-Real-IP        $remote_addr;
      proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
   }}
}}

'''.format(name=t[0], host_port=t[1], upstream=to_token("{}:{}".format(t[0],t[1])))

def to_token(name):
    regexp = re.compile("[^a-zA-Z0-9_]")
    return regexp.sub("_", name)


def generate(file, forward):

    upstream(file,
        [("{}:{}".format(x[0],x[1]), "{}:{}".format(x[2],x[3]), x[4]) for x in forward]
        )

    listen(file, set([x[1] for x in forward]))


    servers = set([(x[0], x[1]) for x in forward])

    server(file, servers)

def generate_html(file, forward):
    '''Generate the HTML file which is displayed when no valid name is given'''
    seen=dict()

    def out(x):
        text = "{}:{}".format(x[0],x[1])
        if text in seen: return
        print >> file, '<li><a href="{url}">{title}</a></li>'.format(url="http://{}".format(text),
                                                                     title=text)
        seen[text]=True
                                                                     

    print >> file, "<ul>"
    map(out, forward)
    print >> file, "</ul>"
    
    
def collect_from_environment(containers):
    '''Collect information from the legacy environment variables'''
    l = list()
    if 'DOMAIN' in os.environ:
        domain=os.environ['DOMAIN']
    else:
        return []

    # Get us a dict of containers by name
    byname=dict()
    for c in containers:
        byname[c['Names'][0]] = c

    for k,v in os.environ.iteritems():
        if k.startswith("__"):
            (container_name, container_port) = v.split(":", 1)
            cname = u"/{}".format(container_name)
            if cname in byname:
                container = cli.inspect_container(byname[cname]['Id'])
                container_ip = container['NetworkSettings']['IPAddress']
                hostname = "{}.{}".format(k[2:], domain)
                l.append( (hostname,
                           "80",
                           container_ip,
                           container_port,
                           container_name))

    return l
        
def main():    
    '''Collect proxy information from all containers and from the
       environment and generate the appropriate nginx configuration
       files'''

    containers = cli.containers()

    forward=collect_host_tuples(container_ids(containers))
    forward.extend(collect_from_environment(containers))
    forward.sort(key=lambda x: (x[0], x[1]))

    with open("/etc/nginx/conf.d/proxy.conf", "w") as f:
        generate(f, forward)

    with open("/usr/share/nginx/html/index.html", "w") as f:
        generate_html(f, forward)

if __name__ == "__main__":
    main()
