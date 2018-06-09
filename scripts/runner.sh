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
    echo -n "Checking internet connection"
    while true
    do
        ping -c1 www.microsoft.com > /dev/null 2>&1 && break
        echo -n "."
        sleep 1
    done
    echo "."
fi
# additional sleep to make sure any dpkg operations triggered by connecting to the network have started

echo -n "Checking for dpkg lock.."

while sudo fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
    echo -n "."
    sleep 1;
done
echo "."

# Pi is in client mode
echo "Starting Raspberry Pi configuration"
sh ./scripts/sendip_and_install.sh $HUB_CONNECTION_STRING $DEVICE_ID $CONNECTION_STRING $CR_NAME $CR_USERNAME $CR_PWD
