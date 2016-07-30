#!/usr/bin/env python2

"""
2016.07.29,second homework from lab
2 host 1 switch with secure failmode
remote controller with Openflow protocol

$ sudo python hw2_net.py or sudo ./hw2_net.py
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
    #switch = net.addSwitch("s1", switch=OVSSwitch, protocols = 'OpenFlow15', failMode = 'standalone')
    switch = net.addSwitch("s1", switch=OVSSwitch, protocols = 'OpenFlow15', failMode = 'secure')
    
    info("Create Links.\n")
    # let host connect to switch port 3 and 4
    net.addLink(lefthost, switch, port2=3)
    net.addLink(righthost, switch, port2=4)

    info("Build and start network.\n")
    net.build()
    net.start()
    
    info("Run mininet CLI.\n")
    CLI(net)


if __name__ == '__main__':
    setLogLevel('info')
    MininetTopo()
