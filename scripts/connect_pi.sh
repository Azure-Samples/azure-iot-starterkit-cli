#!/bin/sh

SSID=$1
PASSPHRASE=$2

cp /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.orig

if [ -z "$PASSPHRASE" ]
then
  network="\nnetwork={\n  ssid=\"${SSID}\"\n  key_mgmt=NONE\n}"
else
  echo "${PASSPHRASE}" >> passphrase_file
  config=$(wpa_passphrase "${SSID}" < passphrase_file)
  psk=$(echo $config | sed -n 's/.*\bpsk=\(.*\)\b.*/\1/p')
  network="\nnetwork={\n  ssid=\"${SSID}\"\n  psk=$psk\n}"
  rm passphrase_file
fi
echo $network >> /etc/wpa_supplicant/wpa_supplicant.conf

systemctl stop hostapd
sudo sed -i -e "s@^interface wlan0\b@#interface wlan0@g" /etc/dhcpcd.conf
sudo sed -i -e "s@^static ip_address=$ip\b@#static ip_address=$ip@g" /etc/dhcpcd.conf

wpa_cli -i wlan0 reconfigure
sudo /etc/init.d/networking restart
