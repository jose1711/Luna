#!/usr/bin/sh

killall -STOP kodi.bin

mv logfile logfile.old
moonlight stream -app "$1" >> logfile 2>&1

killall -CONT kodi.bin