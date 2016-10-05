#!/usr/bin/env python
# -*- coding: utf8 -*-

"""
2016.07.31
2 host n switch, topo is link, with failmode setting

h1--s1--...--sn--h2

$ sudo python hw3_net.py [switchnum] or sudo ./hw3_net.py [switchnum]
"""

import sys
from mininet.log import setLogLevel, info
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController, OVSSwitch

def MininetTopo(switchnum):
    # 存放 switch 參照
    switchlist = []

    # 產生一個 Mininet Object
    net = Mininet()

    # 在 Mininet 中加入兩個 hosts
    info("Create host nodes.\n")
    h1 = net.addHost("h1")
    h2 = net.addHost("h2")
    h3 = net.addHost("h3")
    
    info("Create switch node.\n")
    
    # 連接至 remote controller, 6633 為 Ryu controller 預設 port
    info("Connect to controller node.\n")
    c1 = net.addController(name='c1',controller=RemoteController,ip='192.168.89.129',port=6633)
    c2 = net.addController(name='c2',controller=RemoteController,ip='192.168.89.130',port=6634)

    # count = 1
    # while count <= int(switchnum):
        # # switch name 設為 s1, s2, s3...
        # switchname = "s" + str(count)
        # # 加入新的 switch, switch 種類使用 OVSSwitch (即 OpenvSwitch) 取代預設的 Linux OVSKernelSwitch, OpenFlow protocol 使用 1.3 版, 最後將參照存放進 list
        # switchlist.append(net.addSwitch(switchname, switch=OVSSwitch, protocols='OpenFlow13', failMode='secure'))
        # count+=1

    s1 = net.addSwitch('s1', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s2 = net.addSwitch('s2', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s3 = net.addSwitch('s3', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s4 = net.addSwitch('s4', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s5 = net.addSwitch('s5', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s6 = net.addSwitch('s6', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s7 = net.addSwitch('s7', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s8 = net.addSwitch('s8', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')
    s9 = net.addSwitch('s9', switch=OVSSwitch, protocols='OpenFlow13', failMode='secure')

    # 加入 link, 串起 h1 和 s1
    info("Create Links.\n")
    net.addLink(s1,h1)
    net.addLink(s1,s2)
    net.addLink(s2,s3)
    net.addLink(s2,s5)
    net.addLink(s3,s4)
    net.addLink(s3,s8)
    net.addLink(s4,h2)
    net.addLink(s5,s6)
    net.addLink(s5,s7)
    net.addLink(s6,h3)
    net.addLink(s8,s9)
    
    # s2 之後每台 switch 和前一台連接
    # count=1
    # while count <= int(switchnum)-1:
        # net.addLink(switchlist[count-1],switchlist[count])
        # count+=1

    # 加入 link, 串起 sn 和 h2
    #net.addLink(righthost, switchlist[len(switchlist)-1])

    info("build and start.\n")
    # 建立 topo
    net.build()
    c1.start()
    c2.start()
    
    # switchlist[0].start([c1])
    # switchlist[1].start([c1])
    # switchlist[2].start([c1])
    # switchlist[3].start([c2])
    # switchlist[4].start([c2])
    # switchlist[5].start([c2])
    
    s1.start([c1])
    s2.start([c1])
    s3.start([c1])
    s4.start([c1])
    s5.start([c2])
    s6.start([c2])
    s7.start([c2])
    s8.start([c2])
    s9.start([c2])


    # 啟動 switches 和 controller
    #net.start()
    # 進入 Command Line Interface
    CLI(net)


if __name__ == '__main__':
    setLogLevel('info')

    # 取得參數為建立 switch 數量, 預設為 1
    if len(sys.argv) > 2:
        print "Too much argv!!"
        sys.exit(0)
    elif len(sys.argv) == 2:    
        MininetTopo(sys.argv[1])
    else:
        MininetTopo(1)

