#!/bin/bash
# Пакетная подготовка HEVC → H.264 для Telegram.
# Запуск: bash deploy/prepare_videos.sh
# Один файл: bash deploy/prepare_videos.sh /path/to/video.MOV
set -euo pipefail
unset DEBUG || true

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MEDIA="${ROOT}/media"
OUT="${ROOT}/data/prepared_video"
STAMP_VER="v3"
mkdir -p "$OUT"

encode_one() {
  local src="$1"
  local base stem dest stamp key tmp vf
  base="$(basename "$src")"
  stem="${base%.*}"
  dest="${OUT}/${stem}.mp4"
  stamp="${dest}.src"
  key="${STAMP_VER}|$(readlink -f "$src")|$(stat -c%s "$src")|$(stat -c%Y "$src")"
  if [[ -f "$dest" && -f "$stamp" && "$(cat "$stamp")" == "$key" ]]; then
    echo "skip ${base}"
    return 0
  fi
  echo "encode ${base}"
  tmp="${dest}.part.mp4"
  rm -f "$tmp"
  vf="scale=w='min(1080,iw)':h='min(1080,ih)':force_original_aspect_ratio=decrease,scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30,format=yuv420p"
  if ! ffmpeg -y -i "$src" \
      -vf "$vf" \
      -c:v libx264 -profile:v high -level 4.1 -pix_fmt yuv420p \
      -preset medium -crf 20 \
      -c:a aac -ac 2 -ar 44100 -b:a 160k \
      -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
      -movflags +faststart -tag:v avc1 \
      "$tmp"; then
    ffmpeg -y -i "$src" \
      -vf "$vf" \
      -c:v libx264 -profile:v high -level 4.1 -pix_fmt yuv420p \
      -preset medium -crf 20 \
      -an \
      -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
      -movflags +faststart -tag:v avc1 \
      "$tmp"
  fi
  mv -f "$tmp" "$dest"
  printf '%s' "$key" > "$stamp"
  ffmpeg -y -ss 0.4 -i "$dest" -frames:v 1 -q:v 4 "${dest}.jpg" >/dev/null 2>&1 || true
}

need_encode() {
  local codec
  codec="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of csv=p=0 "$1" 2>/dev/null || true)"
  [[ "$codec" == "hevc" || "$codec" == "h265" ]]
}

if [[ $# -ge 1 ]]; then
  encode_one "$1"
  echo DONE
  exit 0
fi

shopt -s globstar nullglob
for f in "$MEDIA"/**/*.MOV "$MEDIA"/**/*.mov "$MEDIA"/**/*.MP4 "$MEDIA"/**/*.mp4; do
  if need_encode "$f"; then
    encode_one "$f"
  else
    echo "keep $(basename "$f") (already H.264)"
  fi
done

echo DONE
