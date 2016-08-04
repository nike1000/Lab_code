#!/usr/bin/env python
# -*- coding: utf8 -*-

from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch

def MininetTopo():
    net = Mininet()

    info("Create host nodes.\n")
    lefthost = net.addHost("h1")
    righthost = net.addHost("h2")
    
    info("Create switch node.\n")
    switch = net.addSwitch("s1", switch=OVSSwitch, protocols = 'OpenFlow15', failMode = 'secure')
    #switch = net.addSwitch("s1", switch=OVSSwitch, protocols = 'OpenFlow15', failMode = 'standalone')
    
    info("Connect to controller node.\n")
    net.addController(name='c1',controller=RemoteController,ip='192.168.1.22',port=6633)

    info("Create Links.\n")
    net.addLink(lefthost, switch)
    net.addLink(righthost, switch)

    info("build and start.\n")
    net.build()
    net.start()
    CLI(net)


if __name__ == '__main__':
    setLogLevel('info')
    MininetTopo()
