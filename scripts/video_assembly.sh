#!/usr/bin/env bash
# Video-Assembly (component 5): stills -> Ken Burns 9:16 video + edge-tts VO
# + burned "#ad · AI-generated" overlay. Runs on the VPS (disk, not RAM).
#
# Usage: ./video_assembly.sh <images_dir> <script_text_file> <voice> <out.mp4>
# Voices: rotate per run for variation (e.g. en-US-JennyNeural, en-US-GuyNeural,
#         en-US-AriaNeural, en-GB-SoniaNeural) — anti-fingerprinting.
# Deps: ffmpeg, edge-tts (pip). C2PA note: never strip metadata downstream.
set -euo pipefail

IMAGES_DIR="$1"; SCRIPT_FILE="$2"; VOICE="${3:-en-US-JennyNeural}"; OUT="${4:-out.mp4}"
WORK="$(mktemp -d /data/media/asm.XXXXXX 2>/dev/null || mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1) Voice-over (rate/pitch jitter for variation)
RATE=$(( (RANDOM % 11) - 5 ))     # -5%..+5%
PITCH=$(( (RANDOM % 7) - 3 ))     # -3Hz..+3Hz
edge-tts --voice "$VOICE" --rate="${RATE}%" --pitch="${PITCH}Hz" \
  --file "$SCRIPT_FILE" --write-media "$WORK/vo.mp3"
DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$WORK/vo.mp3")
DUR=${DUR%.*}; DUR=$(( DUR + 1 ))

# 2) Ken Burns per still (1080x1920), randomized zoom direction per image
i=0; INPUTS=(); FILTERS=""
for img in "$IMAGES_DIR"/*.{jpg,jpeg,png,webp}; do
  [ -e "$img" ] || continue
  INPUTS+=(-loop 1 -t 4 -i "$img")
  if (( RANDOM % 2 )); then Z="zoom+0.0015"; else Z="if(eq(on,1),1.15,zoom-0.0015)"; fi
  FILTERS+="[$i:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='$Z':d=100:s=1080x1920:fps=25[v$i];"
  i=$((i+1))
done
[ $i -gt 0 ] || { echo "no images found" >&2; exit 1; }

CONCAT=""; for n in $(seq 0 $((i-1))); do CONCAT+="[v$n]"; done
FILTERS+="${CONCAT}concat=n=$i:v=1:a=0[vid];"
# 3) Burn compliance overlay: top-left "#ad", bottom "AI-generated"
FILTERS+="[vid]drawtext=text='#ad':fontcolor=white:fontsize=54:box=1:boxcolor=black@0.55:boxborderw=12:x=40:y=60,"
FILTERS+="drawtext=text='AI-generated':fontcolor=white:fontsize=38:box=1:boxcolor=black@0.55:boxborderw=10:x=(w-text_w)/2:y=h-140[outv]"

ffmpeg -y "${INPUTS[@]}" -i "$WORK/vo.mp3" \
  -filter_complex "$FILTERS" \
  -map "[outv]" -map "$i:a" -t "$DUR" \
  -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -c:a aac -b:a 128k \
  -movflags +faststart "$OUT"
echo "assembled: $OUT (voice=$VOICE rate=${RATE}% pitch=${PITCH}Hz stills=$i dur=${DUR}s)"
