#!/usr/bin/python

import os
import re
import docker
import json
import itertools
import boto3
import argparse
import urllib2
import collections

Record=collections.namedtuple('Record', 'hostname, port, container_ip, container_port, container_name')

if 'DOMAIN' in os.environ:
    DOMAIN=os.environ['DOMAIN']
else:
    DOMAIN=None

if 'MAX_UPLOAD_SIZE' in os.environ:
    MAX_UPLOAD_SIZE = os.environ['MAX_UPLOAD_SIZE']
else:
    MAX_UPLOAD_SIZE = '100m'

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

def collect_nonproxy_hosts(id):
    '''Return information about a specific container, or None if the container has no labels'''
    container = cli.inspect_container(id)
    ip=container['NetworkSettings']['IPAddress']
    cname=container['Name'][1:]
    if not 'Labels' in container['Config']: return None
    labels=container['Config']['Labels']

    if "dns.hostname" in labels:
        name=labels["dns.hostname"]
        return name

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
            return Record(expand_hostname(name), host_port, ip, container_port, cname)
        if not "proxy.ports" in labels:
            return [Record(expand_hostname(name), "80", ip, "80", cname)]

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

def generate_server_redirect(file, from_name, to_name, host_port=80):
    '''Generate a server block listening for requests to from_name and redirect them to to-name'''
    print >> file, '''
server {{
  listen  {host_port};
  server_name {from_name};
  rewrite ^/(.*)$ http://{to_name}/$1 permanent;
}}

'''.format(from_name=from_name, to_name=to_name, host_port=host_port)


def server(file, tuples, redirect_shortnames=False):
    for t in tuples:
        shortname=t[0].split('.',1)[0]
        name=t[0]
        host_port=t[1]

        names = name
        if name != shortname:
            if redirect_shortnames:
                generate_server_redirect(file, shortname, name, host_port=host_port)
            else:
                names = " ".join([name, shortname])
        print >> file,  '''
server {{
  listen  {host_port};
  server_name {name};
  client_max_body_size {max_size};

  location / {{
      proxy_pass http://{upstream};
      proxy_redirect default;

      proxy_set_header   Host             $host;
      proxy_set_header   X-Real-IP        $remote_addr;
      proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
   }}
}}

'''.format(name=names, host_port=host_port, max_size=MAX_UPLOAD_SIZE, upstream=to_token("{}:{}".format(t[0],t[1])))

def default_server(file, ports):
    for p in ports:
        print >> file,  '''
server {{
  listen  {host_port};
  server_name _;

  location / {{
      root /usr/share/nginx/html;
   }}
}}

'''.format(host_port=p)


def to_token(name):
    regexp = re.compile("[^a-zA-Z0-9_]")
    return regexp.sub("_", name)

def expand_hostname(name):
    '''Expand hostname by adding DOMAIN unless hostname is already FQDN'''
    if name.count('.') > 1:
        return name
    elif DOMAIN:
        return name + "." + os.environ['DOMAIN']
    else:
        return name

def generate(file, forward, redirect_shortnames=False):

    upstream(file,
        [("{}:{}".format(x.hostname,x.port), "{}:{}".format(x.container_ip,x.container_port), x.container_name) for x in forward]
        )

    ports = set([x.port for x in forward])
#    listen(file, ports)

    default_server(file, ports)

    servers = set([(x.hostname, x.port) for x in forward])

    server(file, servers, redirect_shortnames=redirect_shortnames)

def generate_html(file, forward):
    '''Generate the HTML file which is displayed when no valid name is given'''
    seen=dict()

    def out(x):
        text = "{}:{}".format(x.hostname,x.port)
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
                l.append( Record(hostname,
                           "80",
                           container_ip,
                           container_port,
                           container_name))

    return l

def collect_notifications(containers):
    '''Collect the notification commands for the running containers.

    RETURN a list of (container-id, command)'''

    results=[]

    if "NOTIFY" in os.environ:
        results.append((os.environ["NOTIFY"], "/bin/kill -HUP 1"))

    for cid in containers:
        container = cli.inspect_container(cid)
        if not 'Labels' in container['Config']: return None
        labels=container['Config']['Labels']

        if "proxy.notify" in labels:
            cmd=labels['proxy.notify']
            if cmd is None or cmd == '':
                results.append((cid, "/bin/kill -HUP 1"))
            else:
                results.append((cid, cmd))

    return results            

def generate_notify_command(file, notifications):
    '''Generate the shell script full of notification commands'''
    for n in notifications:
        print >>file, "docker exec {id} {command}".format(id=n[0], command=n[1])

def get_host_ip(args):
    '''Get the AWS host IP.  

    Use 'args' to determine exact behavior:
       * args.my_ip is set, return it
       * args.aws_public_ip is True, return public instance IP retrieved from AWS instance metadata service
       * args.aws_local_ip is True, return local (private) instance IP retrieved from AWS instance metadata service
       * otherwise, return the public IP as determined by an Internet IP address reporting service

       if no IP can be found or the web call fails, the method will raise an exception'''


    if args.my_ip is not None:
        ip = args.my_ip
    elif args.aws_public_ip:
        ip = urllib2.urlopen("http://169.254.169.254/latest/meta-data/public-ipv4").read()
    elif args.aws_local_ip:
        ip = urllib2.urlopen("http://169.254.169.254/latest/meta-data/local-ipv4").read()
    else:
        ip = urllib2.urlopen("http://ipv4bot.whatismyipaddress.com").read()

    if ip is None:
        raise Exception("Can't get IP")
    return ip

def get_zone_id(client, domain):
    '''Return the Route 53 zone id for the given 'domain'
    '''
    response = client.list_hosted_zones()
    
    name=domain
    if not name.endswith("."):
        name = domain + "."
        
    zones = [x for x in response['HostedZones'] 
             if x['Name'] == name]
    
    if len(zones) < 1:
        raise Exception("Can't find existing zone for %s" % domain)
    
    return zones[0]['Id']

def update_route53(args, names, ip):
    '''Update Route 53 for all the names given to the specified ip'''

    if args.key:
        # Credentials are specified on the command line (or environment)
        client = boto3.client(
            'route53',
            aws_access_key_id=args.key,
            aws_secret_access_key=args.secret,
            )
    else:
        # In case we can use the ~/.aws/credentials file
        client = boto3.client('route53')

    for name in names:
        try:
            hostname, domain = name.split(".", 1)
            zone_id = get_zone_id(client, domain)

            if zone_id:
                print "Updating %s to %s in zone %s" % (name, ip, zone_id)
                response = client.change_resource_record_sets(
                    HostedZoneId=zone_id,
                    ChangeBatch={
                        "Comment": 'Automatically created entry for docker service',
                        "Changes": [
                            {
                                "Action": "UPSERT",
                                "ResourceRecordSet": {
                                    "Name": name,
                                    "Type": 'A',
                                    "TTL": 300,
                                    "ResourceRecords": [
                                        {
                                            "Value": ip
                                            },
                                        ],
                                    }
                                },
                            ]
                        }
                    )
        except Exception as e:
            print "ERROR while updating {} to {}: {}".format(name, ip, e)
        
def main():    
    '''Collect proxy information from all containers and from the
       environment and generate the appropriate nginx configuration
       files'''

    parser = argparse.ArgumentParser()

    parser.add_argument("--route53", action='store_true', help="True if we should update Route 53")
    parser.add_argument("--key", help="AWS key to use", default=os.getenv('AWS_ACCESS_KEY_ID'))
    parser.add_argument("--secret", help="AWS secret to use", default=os.getenv('AWS_SECRET_ACCESS_KEY'))
    parser.add_argument("--aws-public-ip", action='store_true', help="Update Route 53 with public IP")
    parser.add_argument("--aws-local-ip", action='store_true', help="Update Route 53 with local IP")
    parser.add_argument("--timeout", help="NGINX Proxy Timeout", default=30)
    parser.add_argument("--redirect-shortnames", help="Redirect short names to the full names instead of just answering for them", action='store_true')
    
    parser.add_argument("--my-ip", help="Use the given IP instead of the discovered one")
#    parser.add_argument("--public-ip-service", action='store_true', help="Use a public IP service (whatismyip.com) to determine public IP")

    args = parser.parse_args()

    containers = cli.containers()
    ids = container_ids(containers)

    forward=collect_host_tuples(ids)

    forward.extend(collect_from_environment(containers)) 
    forward.sort(key=lambda x: (x.hostname, x.port))

    with open("/etc/nginx/conf.d/proxy.conf", "w") as f:
        generate(f, forward, redirect_shortnames=args.redirect_shortnames)

    with open("/usr/share/nginx/html/index.html", "w") as f:
        generate_html(f, forward)

    with open("/etc/proxy/notify.sh", "w") as f:
        generate_notify_command(f, collect_notifications(ids))

    if args.route53:
        ip=get_host_ip(args)
        proxy_names = [x[0] for x in forward]
        route53_names = filter(None, map(collect_nonproxy_hosts, ids))

        print "Adding proxy names {} and route53 names {}".format(proxy_names, route53_names)
        update_route53(args, proxy_names + route53_names, ip)

if __name__ == "__main__":
    main()
