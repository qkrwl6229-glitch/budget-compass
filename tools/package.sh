#!/usr/bin/env bash
# 검사·테스트를 통과하면 릴리스용 zip 두 개와 SHA-256 체크섬을 dist/ 에 만든다.
# 플러그인 zip 안의 Doctor 설치 정보(installed-release.md)에는 이 커밋과 build=release-zip 을 기록한다.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 -c "import json;print(json.load(open('plugins/budget-compass/plugin.json'))['version'])")
COMMIT=$(git rev-parse --short=12 HEAD 2>/dev/null || echo unknown)
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "⚠ 커밋되지 않은 변경이 있습니다. 릴리스용이면 커밋한 뒤 다시 실행하세요." >&2
  COMMIT="${COMMIT}-dirty"
fi

python3 tools/validate.py
python3 -m unittest discover -s tests -q

mkdir -p dist
rm -rf dist/.stage
rm -f dist/budget-compass-*-v"${VERSION}".zip dist/SHA256SUMS-v"${VERSION}".txt
EXCLUDES=('*/__pycache__/*' '*.DS_Store' '*.pyc')

# 스테이징 사본에 커밋 기록
STAGE=dist/.stage/budget-compass
mkdir -p dist/.stage
cp -R plugins/budget-compass "$STAGE"
REL="$STAGE/skills/budget-compass-doctor/references/installed-release.md"
python3 - "$REL" "$COMMIT" <<'EOF'
import re, sys
p, commit = sys.argv[1], sys.argv[2]
s = open(p, encoding="utf-8").read()
s = re.sub(r'^source_commit: .*$', f'source_commit: "{commit}"', s, flags=re.M)
s = re.sub(r'^build: .*$', 'build: "release-zip"', s, flags=re.M)
open(p, "w", encoding="utf-8").write(s)
EOF

# 1) 스킬 zip (업무 스킬만): 최상위에 budget-compass/SKILL.md
( cd "$STAGE/skills" && zip -qr -X "../../../budget-compass-skill-v${VERSION}.zip" budget-compass -x "${EXCLUDES[@]}" )

# 2) 플러그인 zip: zip 루트에 plugin.json, skills/(업무 스킬 + Doctor), assets/
( cd "$STAGE" && zip -qr -X "../../budget-compass-plugin-v${VERSION}.zip" plugin.json skills assets -x "${EXCLUDES[@]}" )

ENTRIES=$(unzip -Z1 "dist/budget-compass-plugin-v${VERSION}.zip")
for need in plugin.json skills/budget-compass/SKILL.md skills/budget-compass/references/index.md \
            skills/budget-compass/scripts/calc.py skills/budget-compass/laws/index.md \
            skills/budget-compass-doctor/SKILL.md skills/budget-compass-doctor/references/installed-release.md \
            skills/budget-compass-doctor/references/source-catalog.md assets/icon.png; do
  grep -qx "$need" <<<"$ENTRIES" || { echo "플러그인 zip 에 $need 없음" >&2; exit 1; }
done
if grep -qE '__pycache__|\.DS_Store|\.pyc$' <<<"$ENTRIES"; then echo "불필요한 파일 포함" >&2; exit 1; fi
unzip -p "dist/budget-compass-plugin-v${VERSION}.zip" skills/budget-compass-doctor/references/installed-release.md \
  | grep -q "package_version: \"${VERSION}\"" || { echo "Doctor 버전 정보 불일치" >&2; exit 1; }

rm -rf dist/.stage
for z in dist/*-v"${VERSION}".zip; do unzip -tq "$z" >/dev/null; done
( cd dist && shasum -a 256 budget-compass-*-v"${VERSION}".zip > "SHA256SUMS-v${VERSION}.txt" && cat "SHA256SUMS-v${VERSION}.txt" )
echo "커밋: ${COMMIT}"
