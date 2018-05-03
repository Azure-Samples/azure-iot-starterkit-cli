#!/bin/sh

SSID=$1
PASSPHRASE=$2

sudo su -c "echo 0 > /sys/module/bcmdhd/parameters/op_mode"

nmcli device disconnect wlan0

sleep 5

if [ -z "$PASSPHRASE" ]
then
  nmcli device wifi connect $SSID ifname wlan0
else
  nmcli device wifi connect $SSID ifname wlan0 password $PASSPHRASE
fi
