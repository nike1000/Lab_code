import socket
from thread import *
import requests
import yaml
import json
import networkx as nx

clisock_dict = {}

def threadWork(client):
    while True:
        msg  = readLine(client)

        if msg == 'exit':
            break
        elif msg == 'system_name':
            # if prefix message is system_name, readline again to get system_name
            msg  = readLine(client)
            clisock_dict[msg] = client
        else:
            # path forwarding query, the message must be "src_mac,dst_mac"
            print 'Client send:' + msg
            src_mac, dst_mac = msg.split(',')
            fp = path_request(src_mac, dst_mac)

            # after path calculated, return each path_node to corresponding controller system_name
            for path_node in fp:
                system_name = path_node['controller']
                clisock_dict[system_name].sendall(json.dumps(path_node) + '\n')

    client.close()

def readLine(sock):
    line = ''
    while True:
        part = sock.recv(1)
        if part != '\n':
            line += part
        elif part == '\n':
            break
    return line


def path_request(src_mac, dst_mac):

    GENERIC_URL_SWITCHES = 'http://140.113.216.237:8080/Generic_LLDP_Module/rest/switches'
    GENERIC_URL_LINKS = 'http://140.113.216.237:8080/Generic_LLDP_Module/rest/links'
    GENERIC_URL_HOSTS = 'http://140.113.216.237:8080/Generic_LLDP_Module/rest/hosts'
    session = requests.Session()

    mac_to_dpid = {}

    G = nx.DiGraph()

    response = session.get(GENERIC_URL_SWITCHES)
    data = yaml.safe_load(response.text)

    for system_name in data:
        for dpid in data[system_name]:
            # dpid as key, system_name as node attribute
            G.add_node(dpid, system_name = system_name)

            # recode hw_addr belong to which dpid
            for port in data[system_name][dpid]['port']:
                hw_addr = data[system_name][dpid]['port'][port]['hw_addr']
                mac_to_dpid[hw_addr] = dpid


    response = session.get(GENERIC_URL_LINKS)
    data = yaml.safe_load(response.text)

    for link in data:
        src_node = data[link]['src_port']['dpid']
        dst_node = data[link]['dst_port']['dpid']
        src_outport = data[link]['src_port']['port_no']
        dst_inport = data[link]['dst_port']['port_no']

        # edge from src dpid to dst dpid, src_outport is link src port_no, dst_inport is link dst port_no
        G.add_edge(src_node, dst_node, src_outport = src_outport, dst_inport = dst_inport)


    response = session.get(GENERIC_URL_HOSTS)
    data = yaml.safe_load(response.text)

    for host in data:
        mac_to_dpid[host] = host

        # node key is host hw_addr
        G.add_node(host, system_name = data[host]['belong_system'])

        # direct graph, two links
        G.add_edge(data[host]['dpid'], host, src_outport = data[host]['port_no'], dst_inport = '1')
        G.add_edge(host, data[host]['dpid'], src_outport = '1', dst_inport = data[host]['port_no'])

    try:
        source = mac_to_dpid[src_mac]
        target = mac_to_dpid[dst_mac]

        #print json.dumps(G.adj, indent=4, sort_keys=True) + '\n'

        # calculate shortest path and resversed path node
        path = nx.shortest_path(G, source = source, target = target)
        path = path[::-1]
    except:
        return []

    # full path
    fp = []
    for idx, val in enumerate(path):
        if idx > 0 and idx < len(path) - 1:
            prev_item = path[idx - 1]
            item = path[idx]
            next_item = path[idx + 1]

            path_node = {}
            path_node['controller'] = G.node[item]['system_name']
            path_node['dpid'] = item
            path_node['out-port'] = G.get_edge_data(item, prev_item)['src_outport']
            path_node['in-port'] = G.get_edge_data(next_item, item)['dst_inport']
            path_node['eth_src'] = src_mac
            path_node['eth_dst'] = dst_mac
            fp.append(path_node.copy())

    print json.dumps(fp, indent=4, sort_keys=True) + '\n'
    return fp


def Socket_Server():

    host = ''
    port = 30000

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(50)

    while True:
        (csock, adr) = sock.accept()
        print "Client Info: ", csock, adr
        start_new_thread(threadWork, (csock,))

    sock.close()

if __name__ == '__main__':
    #src_mac = '8e:98:5a:f4:9e:46'
    #dst_mac = '2a:fc:a4:b2:c9:cf'
    #path_request(src_mac, dst_mac)
    #print '======================='
    #path_request(dst_mac, src_mac)
    print "Forwarding Application Start!"
    Socket_Server()
