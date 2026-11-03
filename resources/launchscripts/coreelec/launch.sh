#!/usr/bin/sh

# Kodi is frozen (SIGSTOP) while streaming, so its last frame (e.g. a busy spinner)
# stays on the OSD layer, which sits above the video layer. prescript.sh blanks
# the OSD only once. On some Amlogic setups this is not enough: the stream keeps
# running (decoder is fine, sound works) but the TV stays black, or shows only a
# corner of the picture because /sys/class/video/axis is left at another
# resolution after a display mode change. Re-applying the OSD blank, the video
# axis and screen_mode every 2 seconds while moonlight runs fixed this reliably
# (upstream script: 2 of 3 starts black, this one: 0 of ~8).

fix_video() {
    case "$(cat /sys/class/display/mode)" in
        2160*|4k*) A="0 0 3839 2159" ;;
        1080*)     A="0 0 1919 1079" ;;
        720*)      A="0 0 1279 719" ;;
        *)         A="" ;;
    esac
    if [ -n "$A" ] && [ "$(cat /sys/class/video/axis)" != "$A" ]; then
        echo "$A" > /sys/class/video/axis
    fi
    echo 0 > /sys/class/video/screen_mode            # 0 = normal (keep aspect ratio)
    echo 1 > /sys/class/graphics/fb0/blank
}

OLD_AXIS=$(cat /sys/class/video/axis)
OLD_SMODE=$(cut -d: -f1 /sys/class/video/screen_mode)

killall -STOP kodi.bin
echo 1 > /sys/class/graphics/fb1/blank

( while :; do fix_video; sleep 2; done ) &
FIXPID=$!

mv logfile logfile.old
moonlight stream -app "$@" >> logfile 2>&1

kill $FIXPID 2>/dev/null
echo "$OLD_AXIS" > /sys/class/video/axis
echo "$OLD_SMODE" > /sys/class/video/screen_mode

killall -CONT kodi.bin
