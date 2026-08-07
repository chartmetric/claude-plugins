#!/usr/bin/env bash
# Org-wide PR sweep for the DE monthly update.
#
#   ./collect-prs.sh 2026-07-01 2026-08-04 [outdir]
#
# Writes merged.tsv, open.tsv and by-person.md to outdir (default: ./de-update-<end>).
#
# Why the date range is split: `gh search prs` caps at ~200 results and returns the
# MOST RECENT first, so a single month-wide query silently truncates the early weeks.
# We chunk into ~10-day windows and concatenate.

set -euo pipefail

START="${1:?usage: collect-prs.sh YYYY-MM-DD YYYY-MM-DD [outdir]}"
END="${2:?usage: collect-prs.sh YYYY-MM-DD YYYY-MM-DD [outdir]}"
OUT="${3:-./de-update-$END}"
ORG=chartmetric
ROSTER="$(dirname "$0")/roster.json"

mkdir -p "$OUT"
: > "$OUT/merged.tsv"
: > "$OUT/open.tsv"

# --- chunk the range so gh's 200-result cap can't truncate us ---------------
d="$START"
while [[ "$d" < "$END" ]]; do
  nxt=$(date -j -v+10d -f "%Y-%m-%d" "$d" "+%Y-%m-%d" 2>/dev/null || date -d "$d +10 days" "+%Y-%m-%d")
  [[ "$nxt" > "$END" ]] && nxt="$END"
  echo "  merged $d..$nxt" >&2
  gh search prs --owner "$ORG" --merged --merged-at "$d..$nxt" --limit 200 \
    --json author,repository,title,number,closedAt \
    --jq '.[] | [.author.login, .repository.name, "#\(.number)", .closedAt[:10], .title] | @tsv' \
    >> "$OUT/merged.tsv" 2>/dev/null || true
  d="$nxt"
done

# --- open PRs = work in flight. NEVER report these as shipped. --------------
echo "  open PRs created >= $START" >&2
gh search prs --owner "$ORG" --state open --created ">=$START" --limit 200 \
  --json author,repository,title,number,createdAt \
  --jq '.[] | [.author.login, .repository.name, "#\(.number)", .createdAt[:10], .title] | @tsv' \
  >> "$OUT/open.tsv" 2>/dev/null || true

sort -u -o "$OUT/merged.tsv" "$OUT/merged.tsv"
sort -u -o "$OUT/open.tsv"   "$OUT/open.tsv"

# --- group by roster person -------------------------------------------------
{
  echo "# PR sweep $START .. $END"
  echo
  jq -r '(.team + .adjacent)[] | select(.gh != null) | "\(.gh)\t\(.name)\t\(.focus)"' "$ROSTER" |
  while IFS=$'\t' read -r gh name focus; do
    m=$(grep -c "^$gh	" "$OUT/merged.tsv" || true)
    o=$(grep -c "^$gh	" "$OUT/open.tsv"   || true)
    echo "## $name  ($gh) — $focus"
    echo "_${m} merged · ${o} open_"
    echo
    echo "### Merged"
    grep "^$gh	" "$OUT/merged.tsv" | sort -k4 | awk -F'\t' '{print "- `"$2" "$3"` "$5"  <sub>"$4"</sub>"}' || echo "- none"
    echo
    echo "### Open — IN FLIGHT, do not claim as shipped"
    grep "^$gh	" "$OUT/open.tsv" | sort -k4 | awk -F'\t' '{print "- `"$2" "$3"` "$5"  <sub>"$4"</sub>"}' || echo "- none"
    echo
  done

  echo "## Bot-authored (someone drove these — check Slack for who)"
  jq -r '.bot_authors[]' "$ROSTER" | while read -r b; do
    grep "^$b	" "$OUT/merged.tsv" | awk -F'\t' '{print "- "$1": `"$2" "$3"` "$5}' || true
  done

  echo
  echo "## Authors seen but not in roster (new joiners?)"
  cut -f1 "$OUT/merged.tsv" | sort -u | while read -r a; do
    jq -e --arg a "$a" '(.team + .adjacent) | any(.gh == $a)' "$ROSTER" >/dev/null 2>&1 || \
    jq -e --arg a "$a" '.bot_authors | index($a)' "$ROSTER" >/dev/null 2>&1 || echo "- $a"
  done
} > "$OUT/by-person.md"

echo
echo "Wrote:"
echo "  $OUT/merged.tsv   ($(wc -l < "$OUT/merged.tsv" | tr -d ' ') PRs)"
echo "  $OUT/open.tsv     ($(wc -l < "$OUT/open.tsv"   | tr -d ' ') PRs)"
echo "  $OUT/by-person.md  <- start here"
