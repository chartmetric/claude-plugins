#!/usr/bin/env bash
# Refresh team profile photos into ~/Desktop/de-allhands-photos.
#
#   ./fetch-photos.sh urls.tsv          # tsv of: filename <TAB> avatar_url
#   ./fetch-photos.sh --resize          # just resize whatever is already there
#
# Get current avatar URLs by asking Claude to run slack_search_users for each
# roster member (the "Profile Pic" field). They change when people update their
# photo, so re-pull rather than caching URLs in the repo.

set -euo pipefail
DIR="$HOME/Desktop/de-allhands-photos"
mkdir -p "$DIR"

resize() {
  command -v sips >/dev/null || { echo "sips not found; skipping resize"; return; }
  for f in "$DIR"/*.png "$DIR"/*.jpg; do
    [[ -e "$f" ]] || continue
    sips -Z 128 "$f" >/dev/null 2>&1 && echo "  resized $(basename "$f")"
  done
}

if [[ "${1:-}" == "--resize" ]]; then resize; exit 0; fi

TSV="${1:?usage: fetch-photos.sh urls.tsv | --resize}"
while IFS=$'\t' read -r fn url; do
  [[ -z "${fn:-}" || "${fn:0:1}" == "#" ]] && continue
  if curl -sS -L --max-time 30 -o "$DIR/$fn" "$url"; then
    echo "OK   $fn ($(du -h "$DIR/$fn" | cut -f1))"
  else
    echo "FAIL $fn"
  fi
done < "$TSV"

resize
echo
echo "Photos in $DIR:"
ls -1 "$DIR"
