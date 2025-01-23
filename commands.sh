#!/bin/bash

: "${FPS:=60}"
: "${SIZE:=1920x1080}"
: "${BITRATE:=4096}"
: "${GOPSIZE:=1}"
: "${CHANNEL:=161}"
: "${TXPOWER_OVERRIDE:=1}"
: "${STBC:=0}"
: "${LDPC:=0}"
: "${MCS_INDEX:=1}"
: "${FEC_K:=8}"
: "${FEC_N:=12}"
: "${BANDWIDTH:=20}"

read_wfb_config() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 'cat /etc/wfb.conf'
    echo "Reading WFB configuration"
}

read_majestic_config() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 'cat /etc/majestic.yaml'
    echo "Reading majestic configuration"
}

update_fps() {
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i \"/video0:/,/video1:/ s/fps: [0-9]*/fps: $FPS/\" /etc/majestic.yaml"
echo "setting camera fps to $FPS"
}

update_size() {
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i \"/video0:/,/video1:/ s/size: [0-9x]*/size: $SIZE/\" /etc/majestic.yaml"
echo "setting camera resolution to $SIZE"
}

update_bitrate() {
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i \"/video0:/,/video1:/ s/bitrate: [0-9x]*/bitrate: $BITRATE/\" /etc/majestic.yaml"
echo "setting camera resolution to $BITRATE"
}

update_gopSize() {
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i \"/video0:/,/video1:/ s/gopSize: [0-9x]*/gopSize: $GOPSIZE/\" /etc/majestic.yaml"
echo "setting camera resolution to $GOPSIZE"
}

# Function to update channel
update_channel() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^channel=/ s/=.*/=$CHANNEL/' /etc/wfb.conf"
    echo "Setting channel to $CHANNEL"
}

# Function to update driver_txpower_override
update_txpower_override() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^driver_txpower_override=/ s/=.*/=$TXPOWER_OVERRIDE/' /etc/wfb.conf"
    echo "Setting driver txpower override to $TXPOWER_OVERRIDE"
}

# Function to update stbc
update_stbc() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^stbc=/ s/=.*/=$STBC/' /etc/wfb.conf"
    echo "Setting STBC to $STBC"
}

# Function to update ldpc
update_ldpc() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^ldpc=/ s/=.*/=$LDPC/' /etc/wfb.conf"
    echo "Setting LDPC to $LDPC"
}

# Function to update mcs_index
update_mcs_index() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^mcs_index=/ s/=.*/=$MCS_INDEX/' /etc/wfb.conf"
    echo "Setting MCS index to $MCS_INDEX"
}

# Function to update fec_k
update_fec_k() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^fec_k=/ s/=.*/=$FEC_K/' /etc/wfb.conf"
    echo "Setting FEC K to $FEC_K"
}

# Function to update fec_n
update_fec_n() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^fec_n=/ s/=.*/=$FEC_N/' /etc/wfb.conf"
    echo "Setting FEC N to $FEC_N"
}

update_bandwidth() {
    sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 "sed -i '/^bandwidth=/ s/=.*/=$BANDWIDTH/' /etc/wfb.conf"
    echo "Setting Bandwidth to $BANDWIDTH"
}


update_restart_majestic(){
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 '/etc/init.d/S95majestic restart'
echo "restarting majestic..."
}

update_restart_wfb(){
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 '/etc/init.d/S98datalink stop;/etc/init.d/S98datalink start'
echo "restarting wfb..."
}

update_reboot(){
sshpass -p '12345' ssh -o StrictHostKeyChecking=no root@10.5.0.10 'reboot'
echo "rebooting camera..."
}
