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
    lefthost = net.addHost("h1")
    righthost = net.addHost("h2")
    
    info("Create switch node.\n")

    count = 1
    while count <= int(switchnum):
        # switch name 設為 s1, s2, s3...
        switchname = "s" + str(count)
        # 加入新的 switch, switch 種類使用 OVSSwitch (即 OpenvSwitch) 取代預設的 Linux OVSKernelSwitch, OpenFlow protocol 使用 1.3 版, 最後將參照存放進 list
        switchlist.append(net.addSwitch(switchname, switch=OVSSwitch, protocols='OpenFlow13', failMode='secure'))
        count+=1
    
    # 連接至 remote controller, 6633 為 Ryu controller 預設 port
    info("Connect to controller node.\n")
    net.addController(name='c1',controller=RemoteController,ip='192.168.1.22',port=6633)

    # 加入 link, 串起 h1 和 s1
    info("Create Links.\n")
    net.addLink(lefthost, switchlist[0])
    
    # s2 之後每台 switch 和前一台連接
    count=1
    while count <= int(switchnum)-1:
        net.addLink(switchlist[count-1],switchlist[count])
        count+=1

    # 加入 link, 串起 sn 和 h2
    net.addLink(righthost, switchlist[len(switchlist)-1])

    info("build and start.\n")
    # 建立 topo
    net.build()
    # 啟動 switches 和 controller
    net.start()
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

