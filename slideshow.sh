#!/bin/bash

# Bildschirmschoner deaktivieren
xset s off
xset -dpms
xset s noblank

exec /usr/bin/python3 /opt/slideshow/slideshow.py
