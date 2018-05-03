#!/usr/bin/env bash

SSID=$1
PASSPHRASE=$2
HUB_CONNECTION_STRING=$3
DEVICE_ID=$4
CONNECTION_STRING=$5
CR_NAME=$6
CR_USERNAME=$7
CR_PWD=$8

hostapd=$(systemctl list-units | grep hostapd)

# Check if Pi is in AP mode
if [[ -n $hostapd ]]; then
    # Switch mode from AP -> Client
    sh ./scripts/connect_pi.sh $SSID $PASSPHRASE
    while true; do sleep 5; ping -c1 www.google.com > /dev/null && break; done
fi
# additional sleep to make sure any dpkg operations triggered by connecting to the network have started
sleep 5

while sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
    echo "waiting for dpkg lock.."
    sleep 1;
done


# Pi is in client mode
sh ./scripts/sendip_and_install.sh $HUB_CONNECTION_STRING $DEVICE_ID $CONNECTION_STRING $CR_NAME $CR_USERNAME $CR_PWD
