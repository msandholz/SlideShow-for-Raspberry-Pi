#!/bin/bash

# mDNS
apt install -y avahi-daemon
systemctl enable --now avahi-daemon
systemctl start --now avahi-daemon


# Folder for executabels
mkdir -p /opt/slideshow 
chown -R admin:admin /opt/slideshow

curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/default.jpg -o /opt/slideshow/default.jpg
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/test-default-jpg.py -o /opt/slideshow/test-default-jpg.py

curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/mount-usb.sh -o /opt/slideshow/mount-usb.sh
chmod +x /opt/slideshow/mount-usb.sh

curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/slideshow.py -o /opt/slideshow/slideshow.py
chmod +x /opt/slideshow/slideshow.py

# Folder for logfiles
mkdir -p /var/log/slideshow
chown -R admin:admin /var/log/slideshow


# Folder for pcitures
mkdir -p /data/slideshow
chown -R admin:admin /data/slideshow
chmod 755 /data/slideshow

# Download UDEV Rules
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/99-slideshow-usb.rules -o /etc/udev/rules.d/99-slideshow-usb.rules
udevadm control --reload
udevadm trigger

# Download Services
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/mount-usb.service -o /etc/systemd/system/mount-usb.service
curl -L https://raw.githubusercontent.com/msandholz/SlideShow-for-Raspberry-Pi/main/slideshow.service -o /etc/systemd/system/slideshow.service

systemctl daemon-reload
systemctl enable mount-usb.service
systemctl enable slideshow.service

systemctl start mount-usb.service
systemctl start slideshow.service
