# RYU_ODL_LLDP

**multi_ctrl_topo.py**

  * A mininet topo base on hw3_net.py
  * connect to multi controller, first 3 to ODL, other to RYU
  * `$ sudo ./multi_ctrl_topo.py 6`

**multi_ctrl_links_wsgi.py**

  * A wsgi for ryu, odl and cross links
  * `/ryulink/{dpid}`
  * `/odllink`
  * `/crosslink/{dpid}`
  * `$ ryu-manager --ofp-tcp-listen-port 6634 /path/to/multi_ctrl_links_wsgi.py`

**simple_switch_13.py**

  * Ryu Sample code, can run together with multi_ctrl_links_wsgi.py
  * `$ ryu-manager --ofp-tcp-listen-port 6634 /path/to/multi_ctrl_links_wsgi.py /path/to/simple_switch_13.py`
