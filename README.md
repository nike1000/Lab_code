# Lab_code

## SDN

### HW1

  * Install mininet
  * mininet script:
    * 1 switch, 2 host
    * set fail mode to switch: secure/standalone

  * pingall under secure and standalone fail mode
  * understand different between secure and standalone fail mode

### HW2

  * Install Ryu
  * Write a ryu app:
    * controller set two flow entries to each switch
      - packet come in from port A packet out to port B
      - packet come in from port B packet out to port A 
  * Modify HW1 mininet script ,connect to remote controller

### HW3

  * Mininet:
    * Modify Mininet script from HW2, switches connect as a link,hosts connect to head and tail switch, user can assign the number of switches when execute script
    * This new mininet script should work well with HW2 ryuapp

  * Ryu:
    * controller set a flow entry to each switch
      - when receive packet type is LLDP, send to controller
    * controller let switches send LLDP packet out to all normal active port after switch connect to controller
    * controller need packet in handler to handle lldp packet from switch
    * design a data structure to store lldp result

### HW4

  * learn how to write and use Ryu RESTful API
  * use RESTful API to GET HW3 LLDP topo

### RYU_ODL_LLDP

  * Test for multi controller and try to get topo between different controller
  * base on HW3 mininet topo and HW4 Ryu app
