#!/usr/bin/env bash
# 검사·테스트를 통과하면 릴리스용 zip 두 개와 SHA-256 체크섬을 dist/ 에 만든다.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 -c "import json;print(json.load(open('plugins/budget-compass/plugin.json'))['version'])")

python3 tools/validate.py
python3 -m unittest discover -s tests -q

mkdir -p dist
rm -f dist/budget-compass-*-v"${VERSION}".zip dist/SHA256SUMS-v"${VERSION}".txt
EXCLUDES=('*/__pycache__/*' '*.DS_Store' '*.pyc')

# 1) 스킬 zip: 최상위에 budget-compass/SKILL.md
( cd plugins/budget-compass/skills && zip -qr -X "../../../dist/budget-compass-skill-v${VERSION}.zip" budget-compass -x "${EXCLUDES[@]}" )

# 2) 플러그인 zip: zip 루트에 plugin.json, skills/, assets/ (ChatGPT 개인용 업로드에서 설치 확인된 형식)
( cd plugins/budget-compass && zip -qr -X "../../dist/budget-compass-plugin-v${VERSION}.zip" plugin.json skills assets -x "${EXCLUDES[@]}" )

ENTRIES=$(unzip -Z1 "dist/budget-compass-plugin-v${VERSION}.zip")
for need in plugin.json skills/budget-compass/SKILL.md skills/budget-compass/scripts/calc.py skills/budget-compass/scripts/lookup.py skills/budget-compass/laws/index.json assets/icon.png; do
  grep -qx "$need" <<<"$ENTRIES" || { echo "플러그인 zip 에 $need 없음" >&2; exit 1; }
done
if grep -qE '__pycache__|\.DS_Store|\.pyc$' <<<"$ENTRIES"; then echo "불필요한 파일 포함" >&2; exit 1; fi

for z in dist/*-v"${VERSION}".zip; do unzip -tq "$z" >/dev/null; done
( cd dist && shasum -a 256 budget-compass-*-v"${VERSION}".zip > "SHA256SUMS-v${VERSION}.txt" && cat "SHA256SUMS-v${VERSION}.txt" )
