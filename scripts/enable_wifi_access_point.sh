#!/bin/bash
set -e

ORIG_DHCP_EXISTS=1
ls /etc/dchpcd.conf.orig >> /dev/null 2>&1 || ORIG_DHCP_EXISTS=0

# If the file was copied originally, then just replace with original
if [ "${ORIG_DCHP_EXISTS}" == "1" ];
then
    echo "copying orig dhcpcd.conf file"
    sudo cp /etc/dhcpcd.conf.orig /etc/dchpcd.conf
else
        # unomment out the wlan0 section
        sudo sed -i '/^#interface wlan0.*/s/^#//' /etc/dhcpcd.conf
        sudo sed -i '/^#static ip_address=192.*/s/^#//' /etc/dhcpcd.conf
fi

# now remove the network section from the wpa_supplicant file

ORIG_WPA_EXISTS=1
ls /etc/wpa_supplicant/wpa_supplicant.conf.orig >> /dev/null 2>&1 || ORIG_WPA_EXISTS=0

if [ "${ORIG_WPA_EXISTS}" == "1" ];
then
    echo "copying orig wpa_supplicant.conf file"
    sudo cp /etc/wpa_supplicant/wpa_supplicant.conf.orig /etc/wpa_supplicant.conf
else
        # comment out the network section
        awk '/^network=/{f=1}f{next}{print}' /etc/wpa_supplicant/wpa_supplicant.conf > tmp && sudo mv tmp /etc/wpa_supplicant/wpa_supplicant.conf
fi

sudo systemctl start hostapd
wpa_cli -i wlan0 reconfigure
sudo systemctl restart hostapd

sudo /etc/init.d/networking restart
