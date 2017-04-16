#!/usr/bin/env python
# -*- coding: utf8 -*-
# 2017.03.12 kshuang

from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import lldp
from ryu.lib.packet import packet
from ryu.lib import hub
import requests
import json
import yaml
import time

GENERIC_URL_BASE = 'http://140.113.216.237:8080/Generic_LLDP_Module/rest'
CTRL_TYPE = ''

class RYU_APP_request(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    SYSTEM_NAME = ''
    LLDP_FORMAT = {}
    session = requests.Session()

    def __init__(self, *args, **kwargs):
        super(RYU_APP_request, self).__init__(*args, **kwargs)

        CTRL_TYPE = raw_input('Please input SDN Controller Type: ')

        while True:
            try:
                # Get SYSTEM_NAME from Generic_LLDP_Module
                response = self.session.post(GENERIC_URL_BASE + '/controllers/regist/' + CTRL_TYPE)
                # if response code not 200, raise an exception
                response.raise_for_status()
                data = yaml.safe_load(response.text)
                self.SYSTEM_NAME = data['system_name']
                self.LLDP_FORMAT = data['LLDP_subtype']
                break
            except Exception as e:
                print e
                time.sleep(5)

        self.datapaths = {}
        self.links = {}

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        datapath = ev.datapath
        # OVS online
        if ev.state == MAIN_DISPATCHER:
            if not datapath.id in self.datapaths:
                self.datapaths[datapath.id] = datapath
                ofproto = datapath.ofproto
                parser = datapath.ofproto_parser
                match = parser.OFPMatch(eth_type = ether_types.ETH_TYPE_LLDP)
                actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
                inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = parser.OFPFlowMod(datapath = datapath, priority = 65535, command = ofproto.OFPFC_ADD, match = match, instructions = inst)
                datapath.send_msg(mod)

                req = parser.OFPPortDescStatsRequest(datapath, 0, ofproto.OFPP_ANY)
                datapath.send_msg(req)

                data = {'system_name': self.SYSTEM_NAME, 'dpid': datapath.id}
                response = self.session.post(GENERIC_URL_BASE + '/switches/' + self.SYSTEM_NAME+'/'+str(datapath.id), json=data)
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.datapaths:
                del self.datapaths[datapath.id]
                response = self.session.delete(GENERIC_URL_BASE + '/switches/' + self.SYSTEM_NAME + '/' + str(datapath.id))

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_hendler(self, ev):
        self.links = {}
        response = self.session.delete(GENERIC_URL_BASE + '/links/' + self.SYSTEM_NAME)
        for dp in self.datapaths.values():
            ofproto = dp.ofproto
            parser = dp.ofproto_parser
            req = parser.OFPPortDescStatsRequest(dp, 0, ofproto.OFPP_ANY)
            dp.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        datapath = ev.msg.datapath
        response = self.session.delete(GENERIC_URL_BASE + '/ports/' + self.SYSTEM_NAME + '/' + str(datapath.id))

        for ofpport in ev.msg.body:
            data = {'dpid': datapath.id, 'hw_addr': ofpport.hw_addr, 'name': ofpport.name, 'port_no': ofpport.port_no}
            response = self.session.post(GENERIC_URL_BASE + '/ports/' + self.SYSTEM_NAME + '/' + str(datapath.id) + '/' + ofpport.name, json=data)
            self.send_lldp_packet(datapath, ofpport.port_no, ofpport.hw_addr)

    def send_lldp_packet(self, datapath, port_no, hw_addr):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype = ether_types.ETH_TYPE_LLDP, src = hw_addr, dst = lldp.LLDP_MAC_NEAREST_BRIDGE))

        tlv_chassis_id = lldp.ChassisID(subtype = self.LLDP_FORMAT['chassis_subtype'], chassis_id = str(datapath.id))
        tlv_port_id = lldp.PortID(subtype = self.LLDP_FORMAT['port_subtype'], port_id = str(port_no))
        tlv_ttl = lldp.TTL(ttl = 10)
        tlv_sysname = lldp.SystemName(system_name = self.SYSTEM_NAME)
        tlv_end = lldp.End()
        tlvs = (tlv_chassis_id, tlv_port_id, tlv_ttl, tlv_sysname, tlv_end)
        pkt.add_protocol(lldp.lldp(tlvs))
        pkt.serialize()

        actions = [parser.OFPActionOutput(port=port_no)]
        out = parser.OFPPacketOut(datapath = datapath, buffer_id = ofproto.OFP_NO_BUFFER, in_port = ofproto.OFPP_CONTROLLER, actions = actions, data = pkt.data)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        pkt = packet.Packet(data=msg.data)
        pkt_ethernet = pkt.get_protocol(ethernet.ethernet)

        if not pkt_ethernet:
            return

        if pkt_ethernet.ethertype != int('0x88cc', 16):
            print 'Not LLDP ethertype'
            return

        pkt_lldp = pkt.get_protocol(lldp.lldp)
        if pkt_lldp:
            # ODL and Ryu encapsulate with lldp
            if self.lldp_format_check(pkt_lldp):
                src_dpid = pkt_lldp.tlvs[0].chassis_id
                src_port = pkt_lldp.tlvs[1].port_id
                src_sysname = pkt_lldp.tlvs[3].system_name
                dst_dpid = str(msg.datapath.id)
                dst_port = str(msg.match['in_port'])
                dst_sysname = self.SYSTEM_NAME

                self.links[src_dpid + ':' + src_port] = {
                        'link_name': src_sysname + ':' + src_dpid + ':' + src_port,
                        'src_system': src_sysname,
                        'src_port': {
                            'dpid': src_dpid,
                            'port_no': src_port
                            },
                        'dst_system': dst_sysname,
                        'dst_port': {
                            'dpid': dst_dpid,
                            'port_no': dst_port
                            }
                        }
                response = self.session.post(GENERIC_URL_BASE + '/links', json=self.links[src_dpid + ':' + src_port])
        else:
            # VMware does not encapsulate with lldp
            vm_pkt = pkt[1].encode('hex')
            print 'Chassis Subtype ' +  str(int(vm_pkt[4:6],16))
            print 'Chassis ID ' + vm_pkt[6:18].decode('hex')
            print 'Port Subtype ' + str(int(vm_pkt[22:24],16))
            print 'Port ID ' + vm_pkt[24:36]
            print 'TTL ' + str(int(vm_pkt[40:44],16))
            print 'Port Description ' + vm_pkt[48:152].decode('hex')
            print 'Systen Name ' + vm_pkt[156:174].decode('hex')
            print 'System Description ' + vm_pkt[178:240].decode('hex')

            Vmware_CS = str(int(vm_pkt[4:6],16))
            VMware_CID = vm_pkt[6:18].decode('hex')
            VMware_PS = str(int(vm_pkt[22:24],16))
            VMware_PID = vm_pkt[24:36]
            VMware_SysDes = vm_pkt[178:240].decode('hex')

            src_dpid = VMware_CID
            src_port = VMware_PID
            src_sysname = VMware_SysDes
            dst_dpid = str(msg.datapath.id)
            dst_port = str(msg.match['in_port'])
            dst_sysname = self.SYSTEM_NAME

            self.links[src_dpid + ':' + src_port] = {
                    'link_name': src_sysname + ':' + src_dpid + ':' + src_port,
                    'src_system': src_sysname,
                    'src_port': {
                        'dpid': src_dpid,
                        'port_no': src_port
                        },
                    'dst_system': dst_sysname,
                    'dst_port': {
                        'dpid': dst_dpid,
                        'port_no': dst_port
                        }
                    }
            response = self.session.post(GENERIC_URL_BASE + '/links', json=self.links[src_dpid + ':' + src_port])

        print json.dumps(self.links, indent=4, sort_keys=True) + '\n'

    def lldp_format_check(self, pkt_lldp):
        if len(pkt_lldp) < 4:
            return False

        if (pkt_lldp.tlvs[0].tlv_type != lldp.LLDP_TLV_CHASSIS_ID or
            pkt_lldp.tlvs[1].tlv_type != lldp.LLDP_TLV_PORT_ID or
            pkt_lldp.tlvs[2].tlv_type != lldp.LLDP_TLV_TTL or
            pkt_lldp.tlvs[-1].tlv_type != lldp.LLDP_TLV_END):
            return False

        if (pkt_lldp.tlvs[0].subtype == lldp.ChassisID.SUB_INTERFACE_NAME and pkt_lldp.tlvs[1].subtype == lldp.PortID.SUB_MAC_ADDRESS):
            # VMware (discard, because of not encapsulate with lldp)
            return True
        elif (pkt_lldp.tlvs[0].subtype == lldp.ChassisID.SUB_LOCALLY_ASSIGNED and pkt_lldp.tlvs[1].subtype == lldp.PortID.SUB_LOCALLY_ASSIGNED):
            # Our Generic
            return True
        else:
            return False
