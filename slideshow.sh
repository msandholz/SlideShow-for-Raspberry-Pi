#!/bin/bash

xset s off
xset -dpms
xset s noblank

unclutter -idle 0.5 -root &

openbox-session &

exec python3 /opt/slideshow/slideshow.py
