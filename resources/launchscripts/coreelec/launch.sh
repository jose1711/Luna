#!/usr/bin/sh

# Kodi is frozen (SIGSTOP) while streaming, so its last frame stays on the OSD
# layer, which sits above the video layer, and hides the stream (black screen,
# or just a spinner). prescript.sh blanks the OSD once, but the kernel re-enables
# it when the display mode changes right after moonlight starts (the log shows
# "fb: outputmode changed ... reset osd0"). The same mode change can leave
# /sys/class/video/axis at the old resolution, so only a corner of the picture is
# shown. Keep re-applying both while moonlight runs, and keep the aspect ratio.

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
    echo 1 > /sys/class/graphics/fb1/blank
}

OLD_AXIS=$(cat /sys/class/video/axis)
OLD_SMODE=$(cut -d: -f1 /sys/class/video/screen_mode)

killall -STOP kodi.bin

( while :; do fix_video; sleep 2; done ) &
FIXPID=$!

mv logfile logfile.old
moonlight stream -app "$@" >> logfile 2>&1

kill $FIXPID 2>/dev/null
echo "$OLD_AXIS" > /sys/class/video/axis
echo "$OLD_SMODE" > /sys/class/video/screen_mode

killall -CONT kodi.bin
