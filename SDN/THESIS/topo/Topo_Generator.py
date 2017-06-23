#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
2017.03.22 kshuang

"""

import sys
import time
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print 'Please use: $sudo ./Topo_Generator.py topofile'
        sys.exit(0)
    else:
        ctrl_dict = {}
        ovs_dict = {}
        link = []

        net = Mininet()

        with open(sys.argv[1], 'r') as topo_file:
            for line in topo_file.readlines():
                if line.startswith('controller'):
                    symbol, ctrl, ip, port = line.split(' ')
                    ctrl_dict[ctrl] = net.addController(name = ctrl, controller = RemoteController, ip = ip, port = int(port))
                    print symbol + ', ' + ctrl + ', ' + ip + ', ' + port
                elif line.startswith('ovs'):
                    symbol, ovs, ctrl = line[:-1].split(' ')
                    ovs_dict[ovs] = [net.addSwitch(ovs, switch = OVSSwitch, protocols = 'OpenFlow13', failMode = 'secure'), ctrl]
                    print symbol + ', ' + ovs + ', ' + ctrl
                elif line.startswith('link'):
                    symbol, src, dst = line[:-1].split(' ')
                    link.append([src, dst])
                    net.addLink(ovs_dict.get(src)[0], ovs_dict.get(dst)[0], cls=TCLink, bw=1000)
                    #net.addLink(ovs_dict.get(src)[0], ovs_dict.get(dst)[0])
                    print symbol + ', ' + src + ', ' + dst
                elif line.startswith('host'):
                    symbol, host, ovs = line[:-1].split(' ')
                    h = net.addHost(host)
                    net.addLink(h, ovs_dict.get(ovs)[0])
                    print symbol + ', ' + host + ', ' + ovs
                else:
                    print '--------'

        net.build()

        #for src, dst in link:
        #    net.configLinkStatus(src, dst, 'down')

        for ctrl in ctrl_dict.values():
            ctrl.start()

        for ovs in ovs_dict.values():
            ovs[0].start( [ ctrl_dict.get(ovs[1]) ] )

        #for src, dst in link:
        #    net.configLinkStatus(src, dst, 'up')
        #    time.sleep(5)

        #for src, dst in link:
        #    net.configLinkStatus(src, dst, 'down')
        #    time.sleep(5)

        CLI(net)
