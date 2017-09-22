import unittest
import random
import docker
import time
import re

random.seed()
number=random.randrange(10000)
client = docker.from_env()

def normalize(string):
    return re.sub("[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+", "0.0.0.0", re.sub("(nginx.*)-[0-9]+", "\\1", string))


class ProxyTestCase(unittest.TestCase):
    def setUp(self):
        self._containers=[]

    def drun(self, image, name=None, **kwargs):
        if name is None:
            name = image
        name = "{name}-{number}".format(name=name, number=number)

        c = client.containers.run(image, name=name, detach=True,**kwargs)
        self._containers.append(c)
        return c

    def nginx(self, hostname):
        name="nginx-{hostname}".format(hostname=re.sub("[^a-zA-Z0-9]", "_", hostname))
        return self.drun("nginx", name=name, command="bash -c 'echo {hostname} > /usr/share/nginx/html/index.html; nginx -g \"daemon off;\"'".format(hostname=hostname), labels={"proxy.host": hostname})

    def tearDown(self):
        for c in self._containers:
            c.kill()
            c.remove(v=True, force=True)


    def assertMatchesFile(self, filename, string):
        with open(filename) as f:
            contents=f.read()
            self.assertEquals(contents, string)
            


class TestBasic(ProxyTestCase):
    def test_basic(self):
        '''Testing something'''
        self.nginx("host1")
        self.nginx("host2")
        updater = self.drun("name-based-proxy", name="updater", volumes={"/var/run/docker.sock":"/var/run/docker.sock"})
        time.sleep(3)
        conf = normalize(updater.exec_run("cat /etc/nginx/conf.d/proxy.conf"))
        self.assertMatchesFile("test/expected/stage1.txt", conf)



        

