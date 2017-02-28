#!/usr/bin/env python
# -*- coding: utf8 -*-
# 2017.02.27 kshuang

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import lldp
from ryu.lib.packet import packet
from ryu import utils
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.lib import dpid as dpid_lib
from ryu.lib import hub
from webob import Response
import requests
import json
import socket
import urllib2
import base64
import yaml
import datetime

REGISTER_URL_BASE = 'http://140.113.216.237:8080/Generic_LLDP_Module/rest/register?ctrl_type='
CTRL_TYPE = 'ryu'
INSTANCE_NAME = 'ryu'
linkurl = '/link/{dpid}'
borderurl = '/border/{dpid}'

class GenericLLDP(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}
    links = {}
    borders = {}
    mac_to_port = {}
    SYSTEM_NAME = ''

    def __init__(self, *args, **kwargs):
        super(GenericLLDP, self).__init__(*args, **kwargs)

        # GET SYSTEM_NAME from Generic_LLDP_Module
        response = requests.get(REGISTER_URL_BASE+CTRL_TYPE)
        data = yaml.safe_load(response.text)
        self.SYSTEM_NAME = data['ctrl_id']

        # register wsgi RESTful API
        wsgi = kwargs['wsgi']
        wsgi.register(wsgiAPI, {INSTANCE_NAME: self})

        # use thread to do regular LLDP task
        self.datapaths = {}
        self.lldp_thread = hub.spawn(self._lldp_thread)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.logger.debug('register datapath: %016x', datapath.id)
                self.datapaths[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                self.logger.debug('unregister datapath: %016x', datapath.id)
                del self.datapaths[datapath.id]

    def _lldp_thread(self):
        while True:
            self.links = {}
            for dp in self.datapaths.values():
                ofp = dp.ofproto
                ofp_parser = dp.ofproto_parser
                req = ofp_parser.OFPPortDescStatsRequest(dp, 0, ofp.OFPP_ANY)
                dp.send_msg(req)
            hub.sleep(5);

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_LLDP)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.add_flow(datapath, 65535, match, actions)

        dpid = self.format_dpid(str(datapath.id))
        self.mac_to_port.setdefault(dpid, {})
        for stat in ev.msg.body:
            if stat.port_no < ofproto.OFPP_MAX:
                self.mac_to_port[dpid][stat.hw_addr] = self.format_port(str(stat.port_no))

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
        tlv_sysname = lldp.SystemName(system_name=self.SYSTEM_NAME)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_sysname, tlv_end)
        pkt.add_protocol(lldp.lldp(tlvs))

        pkt.serialize()

        data = pkt.data
        parser = datapath.ofproto_parser

        actions = []
        dpid = self.format_dpid(str(datapath.id))
        for src in self.mac_to_port[dpid]:
            actions.append(parser.OFPActionSetField(eth_src="00:00:00:00:00:"+self.mac_to_port[dpid][src][-2:]))
            actions.append(parser.OFPActionOutput(port=int(self.mac_to_port[dpid][src])))

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
                #ryu_src_port = self.mac_to_port[ryu_src_dpid][pkt_ethernet.src]
                ryu_src_port = self.format_port(pkt_ethernet.src[-2:])
                ryu_src_sysname = pkt_lldp.tlvs[3].system_name
                ryu_dst_dpid = self.format_dpid(str(datapath.id))
                ryu_dst_port = self.format_port(str(port))
                ryu_dst_sysname = self.SYSTEM_NAME
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.links[ryu_src_dpid+":"+ryu_src_port] = {
                        "datetime": timestamp,
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
                print json.dumps(self.links, indent=4, sort_keys=True) + '\n'

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
