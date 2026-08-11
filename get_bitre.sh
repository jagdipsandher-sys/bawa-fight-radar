#!/bin/bash
# BITRE back-issue fetcher — run with:
#   curl -sL https://tsi-mos.jagdipsandher.workers.dev/get_bitre.sh | bash
# Downloads every "Road vehicle entry and recall statistics" workbook BITRE
# links from its publication pages into ~/Desktop/BITRE_backissues.
# Prints byte counts per page so a block or an empty page is visible, not silent.
set -u
mkdir -p "$HOME/Desktop/BITRE_backissues"
cd "$HOME/Desktop/BITRE_backissues" || exit 1
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

ALL=""
for p in \
  https://www.bitre.gov.au/statistics/road-vehicles \
  https://www.bitre.gov.au/publications/2026/road-vehicle-entry-and-recall-statistics \
  https://www.bitre.gov.au/publications/2025/road-vehicle-entry-and-recall-statistics \
  https://www.bitre.gov.au/publications/2024/road-vehicle-entry-and-recall-statistics \
  https://www.bitre.gov.au/publications/2023/road-vehicle-entry-and-recall-statistics \
  "https://www.bitre.gov.au/publications/publications?title=%22road+vehicles%2C+australia%22&field_publication_type_target_id=44"
do
  H=$(curl -sL --compressed -A "$UA" "$p")
  echo "fetched $(printf %s "$H" | wc -c | tr -d ' ') bytes from $p"
  ALL="$ALL$H"
done

SUBS=$(printf %s "$ALL" | grep -oE 'href="[^"]*publications/[^"]*"' | sed 's/href="//;s/"$//' | grep -iE 'road-vehicle|rvsa' | sort -u)
echo "publication sub-pages found: $(printf %s "$SUBS" | grep -c .)"
for s in $SUBS; do
  case "$s" in http*) u="$s";; *) u="https://www.bitre.gov.au$s";; esac
  ALL="$ALL$(curl -sL --compressed -A "$UA" "$u")"
done

FILES=$(printf %s "$ALL" | grep -oE 'href="[^"]*\.xlsx[^"]*"' | sed 's/href="//;s/"$//' | grep -iE 'rvsa|road|vehicle|entry|recall' | sort -u)
echo "spreadsheet links found: $(printf %s "$FILES" | grep -c .)"

for f in $FILES; do
  case "$f" in http*) u="$f";; *) u="https://www.bitre.gov.au$f";; esac
  echo "downloading  $u"
  curl -sL --compressed -A "$UA" -O "$u"
done

echo
echo "Finished. Files in ~/Desktop/BITRE_backissues:"
ls -l
open "$HOME/Desktop/BITRE_backissues" 2>/dev/null || true
