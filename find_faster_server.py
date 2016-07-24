# coding: utf-8

import urllib2
import time
import os
import sys
import subprocess
import json
import socket
from copy import deepcopy

from config_ss import remote_server, ss_dir, ss_servers_path


class Shadowsocks(object):
    # "ss_privoxy.exe"
    process_name = "Shadowsocks.exe"
    
    def __init__(self, path=".", servers_path=".\\servers.txt"):
        self.ss = path + "\\Shadowsocks.exe"
        self.conf_path = path + "\\gui-config.json"
        self.servers_path = servers_path
        self.conf_json = {}

    @classmethod
    def kill(cls):
        kill_cmd_prefix = "taskkill /IM %s /T /F"
        while True:
            os.system(kill_cmd_prefix % (cls.process_name,))
            time.sleep(0.5)

            tl = os.popen('WMIC PROCESS get Caption').readlines()
            for p in tl:
                p = p.strip()
                if p == cls.process_name:
                    break
            else:
                return

    def start(self):
        while True:
            ss = subprocess.Popen([self.ss, ], shell=True, stdin=None, 
                        stdout=None, stderr=None, close_fds=True)
            time.sleep(0.3) 
            tl = os.popen('WMIC PROCESS get Caption').readlines()
            for p in tl:
                p = p.strip()
                if p == self.process_name:
                    return

    def get_servers(self):
        servers = []
        with open(self.servers_path) as f:
            for line in f:
                line = line.strip()
                servers.append(line)
        return servers
    
    def get_server_by_index(self, index):
        if index > -1 and index < self.servers_num:
            return self.conf_json['configs'][index]['server']    
        else:
            raise ValueError("index %s is invalid" % (index,))
    @property
    def servers_num(self):
        return len(self.conf_json['configs'])

    def set_default_server(self, index):
        self.load_conf()
        if index > -1 and index < self.servers_num:
            self.kill()
            self.conf_json['index'] = index
            self.dump_conf()
            self.start()
        else:
            raise ValueError("index %s is invalid" % (index,))

    def load_conf(self):
        with open(self.conf_path, 'r') as f:
            self.conf_json = json.loads(f.read())

    def dump_conf(self):
        with open(self.conf_path, 'w') as f:
            json.dump(self.conf_json, f, indent=4)

    def add_servers(self):
        servers =  self.get_servers()
        self.load_conf()

        for each in servers:
            for e in self.conf_json['configs']:
                if each == e['server']:
                    break
            else:
                s = deepcopy(remote_server)
                s['server'] = each
                self.conf_json['configs'].append(s)
        self.dump_conf()


class SetFastServer(object):
    def __init__(self, ss_path=".", servers_path=".\\servers.txt", 
                    proxy_conf={'ip': '127.0.0.1', "port":1080}):
        self.ss = Shadowsocks(ss_path, servers_path)
        self.url_weights = [("http://www.google.com", 0.4),
                            ("http://stackoverflow.com", 0.3),
                            ("http://www.youtobe.com", 0.2),
                            ("https://www.facebook.com", 0.1),
                            ]
        proxy_address = "%(ip)s:%(port)s" % proxy_conf 
        
        proxy_handler = urllib2.ProxyHandler({"http": proxy_address,
                                      "https": proxy_address,
                                      })
        opener = urllib2.build_opener(proxy_handler)
        urllib2.install_opener(opener)

    def metric(self):
        times = 3
        index = 0
        for url, w in self.url_weights:
            total = 0
            for _ in range(times):
                beg = time.time()
                try:
                    resp = urllib2.urlopen(url, timeout=10)
                except urllib2.URLError as ex:
                    print "urlopen error:%s" % (str(ex),)
                except socket.timeout as ex:
                    print "urlopen error:%s" % (str(ex),)
                end = time.time()

                elapse = end - beg
                total += elapse
            avg = total / times
            index += avg * w
        return index

    def run(self):
        self.ss.add_servers()
        
        min_index = 0 
        min_delay = 10000
        results = []
        for i in range(0, self.ss.servers_num):
            self.ss.set_default_server(i)
            ret = self.metric()
            results.append((self.ss.get_server_by_index(i), ret, i))
            if ret < min_delay:
                min_index = i
                min_delay = ret
        
        print_formate = "%-40s %-10s %5s" 
        title = print_formate % ("server","deplay","index")
        print title
        for s, d, i in results:
            print print_formate % (s, d, i)    

        print "the server will set default is:"
        print print_formate % (self.ss.get_server_by_index(min_index), min_delay, min_index)
        self.ss.set_default_server(min_index)

if __name__ == "__main__":
   sfs = SetFastServer(ss_dir, ss_servers_path)
   sfs.run()
