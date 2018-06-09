#!/bin/sh

echo "uninstalling Azure IoT Edge"
sudo iotedgectl uninstall

echo "uninstalling Azure IoT Edge CTL"
sudo pip uninstall azure-iot-edge-runtime-ctl

echo "uninstalling Docker"
sudo apt-get purge docker-ce -y
sudo rm -rf /var/lib/docker

/bin/bash -c ./enable_wifi_access_point.sh
