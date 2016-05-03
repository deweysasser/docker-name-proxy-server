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

def container_ids():
    return [x['Id'] for x in cli.containers()]


def collect_host_tuples(ids):
    def ext(l, value):
        l.extend(value)
        return l

    return reduce(ext, filter(None, map(collect_host_tuple, ids)), [])


def collect_host_tuple(id):
    container = cli.inspect_container(id)
    ip=container['NetworkSettings']['IPAddress']
    if not 'Labels' in container['Config']: return None
    labels=container['Config']['Labels']

    if "proxy.host" in labels:
        name=labels["proxy.host"]
        def port(p):
            (host_port, container_port) = p.split(":")
            return (name, host_port, ip, container_port)
        r = map(port, labels["proxy.ports"].split())
        return r

def upstream(file, tuples):
    for key, group in itertools.groupby(tuples, lambda x: x[0]):
        print >> file,  "upstream {} {{ ".format(to_token(key))
        for t in group:
            print >> file,  "   server {};".format(t[1])
        print >> file,  "}\n"

def listen(file, ports):
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
        [("{}:{}".format(x[0],x[1]), "{}:{}".format(x[2],x[3])) for x in forward]
        )

    listen(file, set([x[1] for x in forward]))


    servers = set([(x[0], x[1]) for x in forward])

    server(file, servers)

def generate_html(file, forward):
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
    
    
        
def main():    
    forward=collect_host_tuples(container_ids())
    forward.sort(key=lambda x: (x[0], x[1]))

    with open("/etc/nginx/conf.d/proxy.conf", "w") as f:
        generate(f, forward)

    with open("/usr/share/nginx/html/index.html", "w") as f:
        generate_html(f, forward)

if __name__ == "__main__":
    main()
