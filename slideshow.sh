#!/bin/bash

xset s off
xset -dpms
xset s noblank

unclutter -idle 0.5 -root &

openbox-session &

exec /opt/slideshow/slideshow.py
