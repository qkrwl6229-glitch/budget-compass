#!/usr/bin/env python3
"""플러그인 구조 검사 (표준 라이브러리만 사용).

검사 항목
  - plugin.json: JSON, name·version·description, extensions.com.openai.interface, 아이콘 경로 존재
  - marketplace.json: 플러그인 이름·경로 일치, policy·category 존재
  - SKILL.md: frontmatter name·description, 본문에서 가리키는 references/·templates/·scripts/ 파일 존재
  - references/ 의 모든 파일이 SKILL.md 에서 연결됨
실행: python3 tools/validate.py   (문제가 있으면 종료 코드 1)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/budget-compass"
SKILL = PLUGIN / "skills/budget-compass"
errors = []


def err(msg):
    errors.append(msg)


def load_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(f"{p.relative_to(ROOT)}: JSON 오류 {e}")
        return {}


m = load_json(PLUGIN / "plugin.json")
for k in ("name", "version", "description"):
    if not m.get(k):
        err(f"plugin.json: '{k}' 없음")
if m.get("version") and not re.fullmatch(r"\d+\.\d+\.\d+", m["version"]):
    err(f"plugin.json: version 형식 오류 {m['version']}")
ui = m.get("extensions", {}).get("com.openai", {}).get("interface", {})
if not ui.get("displayName"):
    err("plugin.json: extensions.com.openai.interface.displayName 없음")
for k in ("composerIcon", "logo"):
    if ui.get(k) and not (PLUGIN / ui[k]).is_file():
        err(f"plugin.json: {k} 파일 없음 ({ui[k]})")
if len(ui.get("defaultPrompt", [])) > 3:
    err("plugin.json: defaultPrompt 는 3개까지")
for i, s in enumerate(ui.get("defaultPrompt", [])):
    if len(s) > 128:
        err(f"plugin.json: defaultPrompt[{i}] 128자 초과")

mk = load_json(ROOT / ".agents/plugins/marketplace.json")
entries = [e for e in mk.get("plugins", []) if e.get("name") == m.get("name")]
if not entries:
    err("marketplace.json: 플러그인 항목 없음")
for e in entries:
    path = e.get("source", {}).get("path", "")
    if not (ROOT / path).resolve() == PLUGIN.resolve():
        err(f"marketplace.json: source.path 가 플러그인 폴더와 다름 ({path})")
    for k in ("policy", "category"):
        if k not in e:
            err(f"marketplace.json: '{k}' 없음")
    cat = ui.get("category")
    if cat and e.get("category") and cat != e["category"]:
        err(f"category 불일치: plugin.json {cat} / marketplace.json {e['category']}")

text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
if not fm:
    err("SKILL.md: frontmatter 없음")
else:
    meta = dict(re.findall(r"^(\w+):\s*(.+)$", fm.group(1), re.M))
    if meta.get("name") != "budget-compass":
        err(f"SKILL.md: name 이 budget-compass 가 아님 ({meta.get('name')})")
    if not meta.get("description"):
        err("SKILL.md: description 없음")
refs = set(re.findall(r"`((?:references|templates|scripts)/[\w./-]+)`", text))
refs |= set(re.findall(r"python (scripts/[\w.]+)", text))
for r in sorted(refs):
    if not (SKILL / r).is_file():
        err(f"SKILL.md: 가리키는 파일 없음 {r}")
for f in sorted((SKILL / "references").glob("*.md")):
    if f"references/{f.name}" not in refs:
        err(f"references/{f.name} 이 SKILL.md 에서 연결되지 않음")

laws_dir = SKILL / "laws"
idx_path = laws_dir / "index.json"
if not idx_path.is_file():
    err("laws/index.json 없음")
else:
    idx = load_json(idx_path).get("laws", [])
    ids = [x.get("id") for x in idx]
    src_ids = [x["id"] for x in load_json(ROOT / "tools/law_sources.json").get("sources", [])]
    if ids != src_ids:
        err(f"laws/index.json 과 tools/law_sources.json 의 규정 목록이 다름")
    for x in idx:
        f = laws_dir / f"{x.get('id')}.md"
        if not f.is_file():
            err(f"laws/{x.get('id')}.md 없음")
        for k in ("title", "number", "effective", "collected", "url", "articles"):
            if not x.get(k):
                err(f"laws/index.json {x.get('id')}: '{k}' 없음")
    extra = {f.stem for f in laws_dir.glob("*.md")} - set(ids)
    if extra:
        err(f"index.json 에 없는 수록 파일: {sorted(extra)}")
    if "scripts/lookup.py" not in refs:
        err("SKILL.md 가 scripts/lookup.py 를 안내하지 않음")

if errors:
    print("검사 실패:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"검사 통과: {m.get('name')} v{m.get('version')} (참조 파일 {len(refs)}개, 수록 규정 {len(idx) if idx_path.is_file() else 0}개)")
