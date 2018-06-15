#!/bin/sh

CONNECTION_STRING=$1

sudo apt-get upgrade --fix-missing -y
sudo apt-add-repository universe -y
sudo apt-get update -y

# Install Docker and send IP to device twin
sudo apt-get install curl -y
sudo curl -fsSL get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo docker run --name iot-device-register-ip --env-file env_file --rm microsoft/azure-iot-starterkit-setuputil:1.0-arm32v7

# Install pip and Azure IoT Edge runtime CTL
sudo apt-get install python2.7-dev libffi-dev libssl-dev -y
sudo apt-get install python-pip -y
sudo pip install --upgrade pip
sudo pip install setuptools
sudo pip install -U cryptography idna 
sudo pip install -U azure-iot-edge-runtime-ctl

# Setup IoT Edge runtime
sudo iotedgectl setup --connection-string $CONNECTION_STRING --nopass --image microsoft/azureiotedge-agent:1.0.0-preview022-linux-arm32v7
sudo iotedgectl start
