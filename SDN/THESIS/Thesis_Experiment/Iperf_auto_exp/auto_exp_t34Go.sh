#!/bin/sh

SESSION="0"
HOSTNAME=`echo "$HOST" | awk -F '.' '{print $1}'`
PASSWD=`cat sudo_passwd`

Result_Dir="/home/kshuang/Thesis_data/Iperf_1G/tree3-4Go/"

repeat=$1

if [ -z "$1" ]; then
    repeat=3
fi


for count in `seq 1 $repeat` ;do
    echo "$(date +%H:%M:%S)    Repeat:$count"

    Result_iperf="tree3-4_Go$count"
    Result_CSV="csv_tree3-4_Go$count"

    tmux -2 new-session -d -s $SESSION

    tmux rename-window -t $SESSION:1 $HOSTNAME

    tmux send-keys "sudo mn -c" C-m
    tmux send-keys $PASSWD C-m

    tmux new-window -t $SESSION:2 -n "controller"
    tmux split-window -h

    tmux select-pane -t 0
    tmux send-keys "ssh 192.168.89.121" C-m
    tmux send-keys "ryu-manager /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py /home/kshuang/Lab_code/SDN/THESIS/RYU_APP_mix.py" C-m

    sleep 1

    tmux select-pane -t 1
    tmux send-keys "ssh 192.168.89.122" C-m
    tmux send-keys "ryu-manager /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py /home/kshuang/Lab_code/SDN/THESIS/RYU_APP_mix.py" C-m

    sleep 1

    tmux split-window -v
    tmux send-keys "ssh 192.168.89.123" C-m
    tmux send-keys "ryu-manager /home/kshuang/Lab_code/SDN/THESIS/RYU_example/simple_switch_13.py /home/kshuang/Lab_code/SDN/THESIS/RYU_APP_mix.py" C-m

    tmux select-window -t $SESSION:1
    sleep 1
    tmux send-keys "sudo /home/kshuang/Lab_code/SDN/THESIS/topo/Topo_Generator.py /home/kshuang/Lab_code/SDN/THESIS/topo/Thesis_exp/tree3-4.txt" C-m
    sleep 30
    tmux send-keys "h1 iperf -D -s -p 5555 -i 1" C-m
    sleep 3
    tmux send-keys "h2 iperf -c 10.0.0.1 -p 5555 -i 1 -t 90 -m > $Result_Dir$Result_iperf" C-m
    sleep 100
    tmux send-keys "h1 pgrep iperf | xargs kill" C-m
    sleep 1
    tmux send-keys "h2 pgrep iperf | xargs kill" C-m

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

    sleep 5

    tmux select-window -t $SESSION:1

    cat $Result_Dir$Result_iperf | grep 'sec' | tr - ' ' | awk '{print $8}' > $Result_Dir$Result_CSV

    tmux kill-session -t $SESSION

    tmux -2 new-session -d -s $SESSION
    tmux send-keys "sudo mn -c" C-m
    tmux send-keys $PASSWD C-m

    tmux kill-session -t $SESSION

done
