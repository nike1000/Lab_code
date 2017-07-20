#!/bin/sh

SESSION="Demo"
PASSWD=`cat sudo_passwd`

#echo "$(date +%H:%M:%S)"

echo "======================================================================="
echo "Topology Discovery and Forwarding in Hybrid Software Defined Networking"
echo "Present by: kshuang"
echo "Professor: sctsai"
echo "2017.07.19 NCTUCS"
echo "======================================================================="

tmux -2 new-session -d -s $SESSION

tmux rename-window -t $SESSION:1 "mininet"
tmux new-window -t $SESSION:2 -n "controller1"
tmux new-window -t $SESSION:3 -n "controller2"

tmux select-window -t $SESSION:1

echo "====> Tmux Init"

sleep 10

tmux select-window -t $SESSION:2
tmux send-keys "ssh 192.168.89.121" C-m
tmux send-keys "ryu-manager /home/kshuang/Lab_code/SDN/THESIS/RYU_Forwarding.py /home/kshuang/Lab_code/SDN/THESIS/Final_code_for_Thesis/Generic_Agent.py" C-m

echo "===> Controller 1 Start up"

sleep 15

tmux select-window -t $SESSION:3
tmux send-keys "ssh 192.168.89.122" C-m
tmux send-keys "ryu-manager /home/kshuang/Lab_code/SDN/THESIS/RYU_Forwarding.py /home/kshuang/Lab_code/SDN/THESIS/Final_code_for_Thesis/Generic_Agent.py" C-m

echo "===> Controller 2 Start up"

sleep 10

echo "===> Prepare for Data Plane"

tmux select-window -t $SESSION:1
sleep 1
tmux send-keys "sudo mn -c" C-m
tmux send-keys $PASSWD C-m
sleep 3
tmux send-keys "sudo /home/kshuang/Lab_code/SDN/THESIS/topo/Topo_Generator.py /home/kshuang/Lab_code/SDN/THESIS/topo/Thesis_exp/demo_topo.txt" C-m

echo "===> Data Plane Created"

#sleep 40

#tmux send-keys "pingall" C-m
