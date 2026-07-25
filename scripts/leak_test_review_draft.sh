#!/usr/bin/env bash
# B-013 leak test — the draft must be reachable at its obscure URL and appear
# in NONE of the public surfaces.
SLUG="${1:?usage: leak_test_review_draft.sh <review-slug-with-token>}"
HOST="https://www.viney.ca"
URL="$HOST/review/$SLUG/"
pass=0; fail=0
chk() { # name, condition-result
  if [ "$2" = "0" ]; then echo "  PASS  $1"; pass=$((pass+1)); else echo "  FAIL  $1"; fail=$((fail+1)); fi
}
echo "Draft: $URL"
echo
PAGE=$(curl -s "$URL")
echo "== reachability & render =="
[ -n "$PAGE" ] && echo "$PAGE" | grep -q "Red Ledger"; chk "draft reachable at obscure URL" $?
echo "$PAGE" | grep -qi '<head' ; chk "renders through the theme (has <head>)" $?
echo "$PAGE" | grep -qiE 'name="robots"[^>]*noindex'; chk "carries noindex robots meta   <-- the 7th criterion" $?
echo "$PAGE" | grep -qE '<img[^>]*(src|srcset)='; chk "no src-less <img> (BUG-055 regression)" $?
echo
echo "== must NOT be listed anywhere public =="
for path in "/" "/blog/" "/feed.xml" "/sitemap.xml" "/search.json"; do
  body=$(curl -s "$HOST$path")
  if echo "$body" | grep -q "$SLUG"; then echo "  FAIL  absent from $path"; fail=$((fail+1));
  else echo "  PASS  absent from $path"; pass=$((pass+1)); fi
done
R=$(curl -s "$HOST/robots.txt"); echo "$R" | grep -qi "Disallow:[[:space:]]*/review/"; chk "robots.txt disallows /review/" $?
echo
echo "RESULT: $pass passed, $fail failed"
