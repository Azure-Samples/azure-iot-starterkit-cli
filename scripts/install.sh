#!/bin/sh

CONNECTION_STRING=$1

# Install Moby and send IP to device twin
echo "getting Moby"
curl -L https://aka.ms/moby-engine-armhf-latest -o moby_engine.deb && sudo dpkg -i ./moby_engine.deb
curl -L https://aka.ms/moby-cli-armhf-latest -o moby_cli.deb && sudo dpkg -i ./moby_cli.deb
sudo apt-get install -f
sleep 10;

sudo docker run --name iot-device-register-ip --env-file env_file --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

# Install the IoT Edge Security Daemon
echo "install the IoT Edge Security Daemon"
curl -L https://aka.ms/libiothsm-std-linux-armhf-latest -o libiothsm-std.deb && sudo dpkg -i ./libiothsm-std.deb
curl -L https://aka.ms/iotedged-linux-armhf-latest -o iotedge.deb && sudo dpkg -i ./iotedge.deb
sudo apt-get install -f

# Setup IoT Edge runtime
echo "setting up Azure IoT Edge runtime"
sudo sed -i -e 's@<ADD DEVICE CONNECTION STRING HERE>@'"${CONNECTION_STRING}"'@g' /etc/iotedge/config.yaml

echo "starting the IoT Edge runtime"
sudo systemctl restart iotedge