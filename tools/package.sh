#!/usr/bin/env bash
# ChatGPT 스킬 업로드용 zip 과 플러그인 패키지 zip 을 dist/ 에 만든다.
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION=$(python3 -c "import json;print(json.load(open('plugins/budget-compass/plugin.json'))['version'])")
mkdir -p dist
rm -f dist/budget-compass-*-v"${VERSION}".zip

# 1) 스킬 단독 zip (ChatGPT 스킬 업로드용: 최상위에 budget-compass/SKILL.md)
( cd plugins/budget-compass/skills && zip -qr -X "../../../dist/budget-compass-skill-v${VERSION}.zip" budget-compass -x '*/__pycache__/*' '*.DS_Store' )

# 2) 플러그인 전체 zip (plugin.json + skills/ + assets/, 폴더 한 겹)
( cd plugins && zip -qr -X "../dist/budget-compass-plugin-v${VERSION}.zip" budget-compass -x '*/__pycache__/*' '*.DS_Store' )

for z in dist/*-v"${VERSION}".zip; do unzip -tq "$z"; done
ls -l dist
