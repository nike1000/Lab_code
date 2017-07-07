#!/usr/bin/env python
# -*- coding: utf8 -*-
# 2017.03.12 kshuang

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import lldp
from ryu.lib.packet import packet
from ryu.lib import hub
import json
import yaml
import sys
import socket
import time
import ast

dpid_to_datapath = {}

class RYU_Forwarding(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(RYU_Forwarding, self).__init__(*args, **kwargs)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = ('140.113.216.236', 30000)
        self.sock.connect(server_address)
        self.sock.sendall('system_name\n')
        self.sock.sendall('ryu:140.113.216.236\n')

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        dpid_to_datapath[datapath.id] = datapath

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(data=msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)

        if not pkt_ethernet:
            return

        if pkt_ethernet.ethertype == int('0x88cc', 16):
            print 'LLDP ethertype'
            return
        else:
            if pkt_ethernet.dst[0:6] == '33:33:':
                return

            if pkt_ethernet.dst == 'ff:ff:ff:ff:ff:ff':
                out_port = ofproto.OFPP_FLOOD
                actions = [parser.OFPActionOutput(out_port)]

                data = None
                if msg.buffer_id == ofproto.OFP_NO_BUFFER:
                    data = msg.data

                out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,in_port=in_port, actions=actions, data=data)
                datapath.send_msg(out)
                return

            print 'packet-In'

            try:
                message = '%s,%s\n' % (pkt_ethernet.src,pkt_ethernet.dst)
                self.sock.sendall(message)
                print message
                print 'server return: \n'

                while True:
                    message = self.readLine(self.sock)

                    if message == 'reply_path_finish':
                        break

                    path_node = ast.literal_eval(message)
                    print path_node

                    match = parser.OFPMatch(in_port = int(path_node['in-port']) ,eth_src = pkt_ethernet.src, eth_dst = pkt_ethernet.dst)
                    #match = parser.OFPMatch(eth_src = pkt_ethernet.src, eth_dst = pkt_ethernet.dst)
                    actions = [parser.OFPActionOutput(int(path_node['out-port']))]
                    self.add_flow(dpid_to_datapath[int(path_node['dpid'])], 1, match, actions)

                out = parser.OFPPacketOut(datapath=datapath, buffer_id = ofproto.OFP_NO_BUFFER, in_port=in_port, actions=actions, data=msg.data)
                datapath.send_msg(out)
            finally:
                print 'end'

    def readLine(self, sock):
        line = ''
        while True:
            part = sock.recv(1)
            if part != '\n':
                line += part
            elif part == '\n':
                break
        return line
