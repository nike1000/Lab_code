# -*- coding: utf8 -*-

"""
2016.07.28,first homework from lab
2 host 1 switch with failmode secure

$ sudo mn --custom ~/mininet/custom/hw1_topo.py --topo mytopo
"""

from mininet.topo import Topo

class MyTopo(Topo):
    "CCIS Lab HW1 mininet topo"

    def __init__(self):
        "Create topo with 2 hosts 1 OpenvSwitch"

        # Initialize topology
        Topo.__init__(self)

        # Add hosts and switches
        lefthost = self.addHost('h1')
        righthost = self.addHost('h2')
        switch = self.addSwitch('s1', failMode = 'secure')
        #switch = self.addSwitch('s1', failMode = 'standalone')

        #Add links
        self.addLink(lefthost, switch)
        self.addLink(righthost, switch)
        
topos = { 'mytopo':( lambda: MyTopo() ) }
