#!/usr/bin/env bash
# Synthesize a divider-sweep comparison video from a pair of input clips.
#
# Layout matches index.html:
#   - Left of divider  -> DG-Mesh
#   - Right of divider -> Ours
#
# Uses geq for dynamic alpha mask + divider line + handle, because drawbox's
# `t` variable does not re-evaluate per frame reliably inside filter_complex
# in ffmpeg 4.4. Slower than drawbox but produces correct per-frame output.
#
# Usage: make_comparison_sweep.sh <ours.mp4> <dgmesh.mp4> <out.mp4>

set -euo pipefail

OURS="$1"
DGMESH="$2"
OUT="$3"

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Divider x as a function of frame time T (seconds).
# One full sine cycle over the 6.666667s clip. Range: 0.1W..0.9W.
DIV="W*0.5+W*0.4*sin(2*PI*T/6.666667)"

# Handle: 28x28 square centered vertically at the divider.
HANDLE="gt(X,(${DIV})-14)*lt(X,(${DIV})+14)*gt(Y,H/2-14)*lt(Y,H/2+14)"
# Divider line: 3px wide white stripe.
LINE="lt(abs(X-(${DIV})),1.5)"

ffmpeg -y \
  -i "$OURS" \
  -i "$DGMESH" \
  -filter_complex "\
    [0:v]format=yuva420p,geq=\
r='r(X,Y)':\
g='g(X,Y)':\
b='b(X,Y)':\
a='if(gt(X,${DIV}),255,0)'\
[oursA];\
    [1:v][oursA]overlay=0:0,\
geq=\
r='if(${LINE},250,if(${HANDLE},250,r(X,Y)))':\
g='if(${LINE},250,if(${HANDLE},250,g(X,Y)))':\
b='if(${LINE},250,if(${HANDLE},250,b(X,Y)))',\
drawtext=fontfile=${FONT}:text='DG-Mesh':x=10:y=10:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6,\
drawtext=fontfile=${FONT}:text='Ours':x=w-tw-10:y=10:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6,\
format=yuv420p[out]" \
  -map "[out]" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -movflags +faststart \
  "$OUT"
