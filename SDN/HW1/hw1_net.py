#!/usr/bin/env python2

"""
2016.07.28,first homework from lab
2 host 1 switch with failmode setting

$ sudo python hw1_net.py or sudo ./hw1_net.py
"""


from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI

def MininetTopo():
    net = Mininet()

    info("Create host nodes.\n")
    lefthost = net.addHost("h1")
    righthost = net.addHost("h2")
    
    info("Create switch node.\n")
    switch = net.addSwitch("s1", failMode = 'standalone')
    #switch = net.addSwitch("s1", failMode = 'secure')
    
    info("Create Links.\n")
    net.addLink(lefthost, switch)
    net.addLink(righthost, switch)

    info("Build and start network.\n")
    net.build()
    net.start()
    
    info("Run mininet CLI.\n")
    CLI(net)


if __name__ == '__main__':
    setLogLevel('info')
    MininetTopo()
