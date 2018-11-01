#!/bin/sh
set -e

HUB_CONNECTION_STRING=$1
DEVICE_ID=$2
CONNECTION_STRING=$3
CR_NAME=$4
CR_USERNAME=$5
CR_PWD=$6
IP_ADDRESS=$(ip addr show dev wlan0 | egrep inet[^6] | awk '{ print $2 }')

echo "installing ntpdate"
sudo apt-get install ntpdate -y >/dev/null 2>&1
echo "synchronizing system time"
sudo ntpdate -v time.windows.com >/dev/null 2>&1

# Install Moby and send IP to device twin
echo "getting Moby"
curl -L https://aka.ms/moby-engine-armhf-latest -o moby_engine.deb && sudo dpkg -i ./moby_engine.deb
curl -L https://aka.ms/moby-cli-armhf-latest -o moby_cli.deb && sudo dpkg -i ./moby_cli.deb
sudo apt-get install -f
sleep 10;
sudo docker run --name iot-device-register-ip -e "HUB_CONNECTION_STRING=${HUB_CONNECTION_STRING}" -e "DEVICE_ID=${DEVICE_ID}" -e "DEVICE_IP_ADDRESS=${IP_ADDRESS}" --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

# Install the IoT Edge Security Daemon
echo "install the IoT Edge Security Daemon"
curl -L https://aka.ms/libiothsm-std-linux-armhf-latest -o libiothsm-std.deb && sudo dpkg -i ./libiothsm-std.deb
curl -L https://aka.ms/iotedged-linux-armhf-latest -o iotedge.deb && sudo dpkg -i ./iotedge.deb
sudo apt-get install -f

# Setup IoT Edge runtime
echo "setting up Azure IoT Edge runtime"
sudo systemctl stop iotedge
sudo sed -i -e 's@<ADD DEVICE CONNECTION STRING HERE>@'"${CONNECTION_STRING}"'@g' /etc/iotedge/config.yaml

sleep 10;

echo "starting the IoT Edge runtime"
sudo systemctl start iotedge

# Send completed status to device twin
sudo docker run --name iot-device-register-ip -e "HUB_CONNECTION_STRING=${HUB_CONNECTION_STRING}" -e "DEVICE_ID=${DEVICE_ID}" -e "STATUS=Completed" --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

