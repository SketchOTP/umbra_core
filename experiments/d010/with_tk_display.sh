#!/usr/bin/env bash
# Environment for D-010 Task 14 Tkinter + Xvfb when system python3-tk is absent.
set -euo pipefail
TKROOT="${UMBRA_TK_ROOT:-$HOME/.local/umbratk/extract}"
if [[ -d "$TKROOT/usr/lib/x86_64-linux-gnu" ]]; then
  export LD_LIBRARY_PATH="$TKROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
if [[ -d "$TKROOT/usr/share/tcltk/tcl8.6" ]]; then
  export TCL_LIBRARY="$TKROOT/usr/share/tcltk/tcl8.6"
  export TK_LIBRARY="$TKROOT/usr/share/tcltk/tk8.6"
fi
if [[ -z "${DISPLAY:-}" ]]; then
  if ! xdpyinfo -display :99 >/dev/null 2>&1; then
    Xvfb :99 -screen 0 1280x720x24 >/tmp/umbra-d010-xvfb99.log 2>&1 &
    echo $! >/tmp/umbra-d010-xvfb99.pid
    sleep 1
  fi
  export DISPLAY=:99
fi
exec "$@"
