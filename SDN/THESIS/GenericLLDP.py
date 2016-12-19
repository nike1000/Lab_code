#!/usr/bin/env python
# -*- coding: utf8 -*-
# 2016.12.14 kshuang

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import lldp
from ryu.lib.packet import packet
from ryu import utils
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from webob import Response
import json
import socket
import urllib2
import base64

SYSTEM_NAME = 'ryu:1'
INSTANCE_NAME = 'ryu:1'
linkurl = '/link/{dpid}'
borderurl = '/border/{dpid}'

class GenericLLDP(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}
    links = {}
    borders = {}

    def __init__(self, *args, **kwargs):
        super(GenericLLDP, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(wsgiAPI, {INSTANCE_NAME: self})

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_LLDP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 65535, match, actions)

        for stat in ev.msg.body:
            if stat.port_no < ofproto.OFPP_MAX:
                self.send_lldp_packet(datapath, stat.port_no, stat.hw_addr)

    def add_flow(self, datapath, priority, match, actions):
        ofp = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, command=ofp.OFPFC_ADD, match=match, instructions=inst)
        datapath.send_msg(mod)

    def send_lldp_packet(self, datapath, port_no, hw_addr):
        ofp = datapath.ofproto
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_LLDP, src=hw_addr, dst=lldp.LLDP_MAC_NEAREST_BRIDGE))

        tlv_chassis_id = lldp.ChassisID(subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED, chassis_id=self.format_dpid(str(datapath.id)))
        tlv_port_id = lldp.PortID(subtype=lldp.PortID.SUB_LOCALLY_ASSIGNED, port_id=self.format_port(str(port_no)))
        tlv_ttl = lldp.TTL(ttl=10)
        tlv_sysname = lldp.SystemName(system_name=SYSTEM_NAME)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_sysname, tlv_end)
        pkt.add_protocol(lldp.lldp(tlvs))

        pkt.serialize()

        data = pkt.data
        parser = datapath.ofproto_parser
        actions = [parser.OFPActionOutput(port=port_no)]
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofp.OFP_NO_BUFFER, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        port = msg.match['in_port']
        pkt = packet.Packet(data=msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)

        if not pkt_ethernet:
            return

        pkt_lldp = pkt.get_protocol(lldp.lldp)
        if pkt_lldp:
            if self.lldp_format_check(pkt_lldp):
                ryu_src_dpid = pkt_lldp.tlvs[0].chassis_id
                ryu_src_port = pkt_lldp.tlvs[1].port_id
                ryu_src_sysname = pkt_lldp.tlvs[3].system_name
                ryu_dst_dpid = self.format_dpid(str(datapath.id))
                ryu_dst_port = self.format_port(str(port))
                ryu_dst_sysname = SYSTEM_NAME
                self.links[ryu_src_dpid+":"+ryu_src_port] = {
                        "src":{
                            "dpid":ryu_src_dpid,
                            "port_no":ryu_src_port,
                            "system_name":ryu_src_sysname
                            },
                        "dst":{
                            "dpid":ryu_dst_dpid,
                            "port_no":ryu_dst_port,
                            "system_name":ryu_dst_sysname
                            }
                        }
                print self.links

    def format_dpid(self, dpid):
        return dpid.zfill(16)

    def format_port(self, port):
        return port.zfill(6)

    def lldp_format_check(self, pkt_lldp):
        return (pkt_lldp.tlvs[0].subtype == lldp.ChassisID.SUB_LOCALLY_ASSIGNED and
                len(pkt_lldp.tlvs[0].chassis_id) == 16 and
                pkt_lldp.tlvs[1].subtype == lldp.ChassisID.SUB_LOCALLY_ASSIGNED and
                len(pkt_lldp.tlvs[1].port_id) == 6)

class wsgiAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(wsgiAPI, self).__init__(req, link, data, **config)
        self.myryu_instance = data[INSTANCE_NAME]

    @route('link', linkurl, methods=['GET'])
    def list_self_connect(self, req, **kwargs):
        instance = self.myryu_instance
        dpid = self.format_port(kwargs['dpid'])

        if dpid == 0:
            dplink = instance.links.items()
            body = json.dumps(dplink, indent=4, sort_keys=True) + '\n'
            return Response(content_type='application/json', body=body)
        else:
            dplink = []
            for key, value in instance.links.iteritems():
                if key.startswith(dpid):
                    dplink.append(value)
            body = json.dumps(dplink, indent=4, sort_keys=True) + '\n'
            return Response(content_type='application/json', body=body)

    def format_dpid(self, dpid):
        return dpid.zfill(16)

    def format_port(self, port):
        return port.zfill(6)
