#!/usr/bin/env python
# -*- coding: utf8 -*-
# 2016.08.04 kshuang

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3_parser
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

myryu_instance_name = 'MyRyu'
rlinkurl = '/ryulink/{dpid}'
olinkurl= '/odllink'
clinkurl = '/crosslink/{dpid}'

class MyRyu(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    ryu_links = {}
    ODL2RYU={}
    _CONTEXTS = {'wsgi': WSGIApplication}

    # register wsgi class
    def __init__(self, *args, **kwargs):
        super(MyRyu, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(MyRyuAPI, {myryu_instance_name: self})

    # get event when new switch connect to ryu and do openflow version negotiated
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        self.send_port_stats_request(datapath)

    def send_port_stats_request(self, datapath):
        ofp = datapath.ofproto
        ofp_parser = datapath.ofproto_parser
        req = ofp_parser.OFPPortDescStatsRequest(datapath, 0, ofp.OFPP_ANY)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        
        # LLDP packet to controller
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
        
        tlv_chassis_id = lldp.ChassisID(subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED, chassis_id=str(datapath.id))
        tlv_port_id = lldp.PortID(subtype=lldp.PortID.SUB_LOCALLY_ASSIGNED, port_id=str(port_no))
        tlv_ttl = lldp.TTL(ttl=10)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_end)
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
            self.handle_lldp(datapath, port, pkt_ethernet, pkt_lldp)

    def handle_lldp(self, datapath, port, pkt_ethernet, pkt_lldp):
        # Our LLDP Packet
        if(pkt_lldp.tlvs[0].subtype == lldp.ChassisID.SUB_LOCALLY_ASSIGNED):
            ryu_src_dpid = int(pkt_lldp.tlvs[0].chassis_id)
            ryu_src_port = int(pkt_lldp.tlvs[1].port_id)
            ryu_dst_dpid = int(datapath.id)
            ryu_dst_port = int(port)
            self.ryu_links["openflow:"+str(ryu_src_dpid)+":"+str(ryu_src_port)]={
                    "src":{
                        "dpid":ryu_src_dpid,
                        "port_no":ryu_src_port
                        },
                    "dst":{
                        "dpid":ryu_dst_dpid,
                        "port_no":ryu_dst_port
                        }
                    }
            print self.ryu_links
        # OpenDayLight LLDP Packet
        elif(pkt_lldp.tlvs[0].subtype == lldp.ChassisID.SUB_MAC_ADDRESS):
            odl_dpid = pkt_lldp.tlvs[3].tlv_info
            odl_port = pkt_lldp.tlvs[1].port_id
            ryu_dpid = int(datapath.id)
            ryu_port = int(port)
            self.ODL2RYU[odl_dpid+":"+odl_port]={
                "src":{
                    "source-node":odl_dpid,
                    "source-tp":odl_dpid+":"+odl_port
                    },
                "dst":{
                    "dpid":ryu_dpid,
                    "port_no":ryu_port
                    }
                }
            print self.ODL2RYU

    @set_ev_cls(ofp_event.EventOFPErrorMsg, MAIN_DISPATCHER)
    def error_msg_handler(self, ev):
        msg = ev.msg
        self.logger.debug('OFPErrorMsg received: type=0x%02x code=0x%02x message=%s', msg.type, msg.code, utils.hex_array(msg.data))


class MyRyuAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(MyRyuAPI, self).__init__(req, link, data, **config)
        self.myryu_instance = data[myryu_instance_name]

    @route('ryu_link', rlinkurl, methods=['GET'])
    def list_ryu_connect(self, req, **kwargs):
        myryu = self.myryu_instance
        dpid = int(kwargs['dpid'])

        if dpid == 0:
            links = myryu.ryu_links.items()
            body = json.dumps(links, indent=4, sort_keys=True) + '\n'
            return Response(content_type='application/json', body=body)
        
        re_key="openflow:"+str(dpid)+":"
        links=[]

        for key, value in myryu.ryu_links.iteritems():
            if key.startswith(re_key):
                links.append(value)

        body = json.dumps(links, indent=4, sort_keys=True) + '\n'
        return Response(content_type='application/json', body=body)

    @route('cross_link', clinkurl, methods=['GET'])
    def list_cross_connect(self, req, **kwargs):
        myryu = self.myryu_instance
        dpid = int(kwargs['dpid'])

        if dpid == 0:
            links = myryu.ODL2RYU.items()
            body = json.dumps(links, indent=4, sort_keys=True) + '\n'
            return Response(content_type='application/json', body=body)
        
        re_key="openflow:"+str(dpid)+":"
        links=[]

        for key, value in myryu.ODL2RYU.iteritems():
            if key.startswith(re_key):
                links.append(value)

        body = json.dumps(links, indent=4, sort_keys=True) + '\n'
    
        return Response(content_type='application/json', body=body)
    
    @route('odl_link', olinkurl, methods=['GET'])
    def list_odl_connect(self, req, **kwargs):
        url = "http://192.168.89.129:8181/restconf/operational/network-topology:network-topology"
        user = "admin"
        passwd = "admin"

        passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
        passman.add_password(None, url, user, passwd)
        authhandler = urllib2.HTTPBasicAuthHandler(passman)
        opener = urllib2.build_opener(authhandler)
        urllib2.install_opener(opener)
        pagehandle = urllib2.urlopen(url)
        response = json.load(pagehandle)
        links = response['network-topology']['topology'][0]['link']
        body = json.dumps(links, indent=4, sort_keys=True) + '\n'

        return Response(content_type='application/json', body=body)
