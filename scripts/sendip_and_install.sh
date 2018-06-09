#!/bin/sh
set -e

HUB_CONNECTION_STRING=$1
DEVICE_ID=$2
CONNECTION_STRING=$3
CR_NAME=$4
CR_USERNAME=$5
CR_PWD=$6
IP_ADDRESS=$(ip addr show dev wlan0 | egrep inet[^6] | awk '{ print $2 }')

# Install Docker and send IP to device twin
echo "getting docker"
sudo curl -fsSL get.docker.com -o get-docker.sh
sleep 10;
echo "installing docker"
sudo sh get-docker.sh
sudo docker run --name iot-device-register-ip -e "HUB_CONNECTION_STRING=${HUB_CONNECTION_STRING}" -e "DEVICE_ID=${DEVICE_ID}" -e "DEVICE_IP_ADDRESS=${IP_ADDRESS}" --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

# Install pip and Azure IoT Edge runtime CTL
echo "installing pip"
sudo apt-get install python2.7-dev libffi-dev libssl-dev -y
sudo apt-get install python-pip -y
sudo pip install --upgrade pip
sudo pip install setuptools
sudo pip install -U cryptography idna
echo "installing Azure IoT Edge runtime CTL"
sudo pip install -U azure-iot-edge-runtime-ctl

# Setup IoT Edge runtime
echo "setting up Azure IoT Edge runtime"
sudo iotedgectl setup --connection-string "${CONNECTION_STRING}" --nopass --image microsoft/azureiotedge-agent:1.0.0-preview022-linux-arm32v7
if [ ! -z "$CR_NAME" ] # Assumes other CR arguments are also set
then
    sudo iotedgectl login --address "${CR_NAME}.azurecr.io" --username $CR_USERNAME --password $CR_PWD
fi
echo "starting Azure IoT Edge runtime"
sudo iotedgectl start

# Send completed status to device twin
sudo docker run --name iot-device-register-ip -e "HUB_CONNECTION_STRING=${HUB_CONNECTION_STRING}" -e "DEVICE_ID=${DEVICE_ID}" -e "STATUS=Completed" --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

# Cleanup
rm get-docker.sh
