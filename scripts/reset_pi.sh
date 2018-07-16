#!/bin/sh

echo "uninstalling Azure IoT Edge"
sudo iotedgectl uninstall
echo "uninstalling Azure IoT Edge CTL"
sudo pip uninstall azure-iot-edge-runtime-ctl

echo "uninstalling Docker"
sudo apt-get purge docker-ce -y
sudo rm -rf /var/lib/docker

sudo cp /etc/wpa_supplicant/wpa_supplicant.conf.orig /etc/wpa_supplicant/wpa_supplicant.conf
sudo cp /etc/dhcpcd.conf.orig /etc/dhcpcd.conf

sudo systemctl start hostapd
wpa_cli -i wlan0 reconfigure
sudo systemctl restart hostapd

sudo /etc/init.d/networking restart
    