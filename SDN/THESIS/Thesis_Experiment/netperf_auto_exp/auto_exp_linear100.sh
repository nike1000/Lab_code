#!/bin/sh

SESSION="0"
HOSTNAME=`echo "$HOST" | awk -F '.' '{print $1}'`
PASSWD=`cat sudo_passwd`

Result_Dir="/home/kshuang/Thesis_data/netperf_1G/linear100/"

repeat=$1

if [ -z "$1" ]; then
    repeat=3
fi


for count in `seq 1 $repeat` ;do
    echo "$(date +%H:%M:%S)    Repeat:$count"

    Result_iperf="linear100_$count"
    Result_CSV="csv_linear100_$count"

    tmux -2 new-session -d -s $SESSION

    tmux rename-window -t $SESSION:1 $HOSTNAME

    tmux send-keys "sudo mn -c" C-m
    tmux send-keys $PASSWD C-m

    tmux new-window -t $SESSION:2 -n "controller"
    tmux split-window -h
    tmux split-window -v
    tmux select-pane -t 0
    tmux split-window -v

    tmux select-pane -t 0
    tmux send-keys "ssh 192.168.89.121" C-m
    tmux send-keys "ryu-manager --observe-links /usr/local/lib/python2.7/dist-packages/ryu/app/gui_topology/gui_topology.py /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py" C-m

    sleep 1

    tmux select-pane -t 1
    tmux send-keys "ssh 192.168.89.122" C-m
    tmux send-keys "ryu-manager --observe-links /usr/local/lib/python2.7/dist-packages/ryu/app/gui_topology/gui_topology.py /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py" C-m

    sleep 1

    tmux select-pane -t 2
    tmux send-keys "ssh 192.168.89.123" C-m
    tmux send-keys "ryu-manager --observe-links /usr/local/lib/python2.7/dist-packages/ryu/app/gui_topology/gui_topology.py /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py" C-m

    sleep 1

    tmux select-pane -t 3
    tmux send-keys "ssh 192.168.89.124" C-m
    tmux send-keys "ryu-manager --observe-links /usr/local/lib/python2.7/dist-packages/ryu/app/gui_topology/gui_topology.py /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py" C-m

    tmux select-window -t $SESSION:1
    sleep 1
    tmux send-keys "sudo /home/kshuang/Lab_code/SDN/THESIS/topo/Topo_Generator.py /home/kshuang/Lab_code/SDN/THESIS/topo/Thesis_exp/linear100.txt" C-m
    sleep 30
    tmux send-keys "h1 netserver" C-m
    sleep 3
    tmux send-keys "h2 netperf -H 10.0.0.1 -I 95 -l 95 -D 1 -t TCP_STREAM -- -m 256 > $Result_Dir$Result_iperf" C-m
    sleep 105
    tmux send-keys "h1 pgrep netserver | xargs kill -9" C-m

    tmux new-window -t $SESSION:3
    tmux send-keys "ssh 192.168.89.121" C-m
    tmux send-keys "pgrep ryu-manager | xargs kill -s INT" C-m
    tmux send-keys "exit" C-m

    tmux new-window -t $SESSION:4
    tmux send-keys "ssh 192.168.89.122" C-m
    tmux send-keys "pgrep ryu-manager | xargs kill -s INT" C-m
    tmux send-keys "exit" C-m

    tmux new-window -t $SESSION:5
    tmux send-keys "ssh 192.168.89.123" C-m
    tmux send-keys "pgrep ryu-manager | xargs kill -s INT" C-m
    tmux send-keys "exit" C-m

    tmux new-window -t $SESSION:6
    tmux send-keys "ssh 192.168.89.124" C-m
    tmux send-keys "pgrep ryu-manager | xargs kill -s INT" C-m
    tmux send-keys "exit" C-m

    sleep 5

    tmux select-window -t $SESSION:1

    cat $Result_Dir$Result_iperf | grep 'Interim result' | awk '{print $3}' > $Result_Dir$Result_CSV

    tmux kill-session -t $SESSION

    tmux -2 new-session -d -s $SESSION
    sleep 1
    tmux send-keys "pgrep netserver | sudo xargs kill -9" C-m
    sleep 1
    tmux send-keys $PASSWD C-m
    tmux send-keys "sudo mn -c" C-m
    sleep 10

    tmux kill-session -t $SESSION

done
