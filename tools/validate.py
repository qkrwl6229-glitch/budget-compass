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
refs |= set(re.findall(r"\]\(((?:references|templates|scripts)/[\w./-]+)\)", text))
for r in sorted(refs):
    if not (SKILL / r).exists():
        err(f"SKILL.md: 가리키는 파일 없음 {r}")
for f in sorted((SKILL / "references").glob("*.md")):
    if f"references/{f.name}" not in refs:
        err(f"references/{f.name} 이 SKILL.md 에서 연결되지 않음")

laws_dir = SKILL / "laws"
idx_path = laws_dir / "index.json"
idx = []
if not idx_path.is_file():
    err("laws/index.json 없음")
else:
    idx = load_json(idx_path).get("laws", [])
    ids = [x.get("id") for x in idx]
    src_ids = [x["id"] for x in load_json(ROOT / "tools/law_sources.json").get("sources", [])]
    if ids != src_ids:
        err("laws/index.json 과 tools/law_sources.json 의 규정 목록이 다름")
    for x in idx:
        d = laws_dir / str(x.get("id"))
        if not (d / "index.md").is_file():
            err(f"laws/{x.get('id')}/index.md 없음")
            continue
        files = [f for f in d.glob("*.md") if f.name not in ("index.md", "addenda.md") and ".prev-" not in f.name]
        if len(files) != len(x.get("articles", [])):
            err(f"laws/{x.get('id')}: 조문 파일 수({len(files)})가 목록({len(x.get('articles', []))})과 다름")
        for k in ("title", "number", "effective", "collected", "url", "fixed_url", "articles"):
            if not x.get(k):
                err(f"laws/index.json {x.get('id')}: '{k}' 없음")
    extra = {p.name for p in laws_dir.iterdir() if p.is_dir()} - set(ids)
    if extra:
        err(f"index.json 에 없는 규정 폴더: {sorted(extra)}")

# 마크다운 상대 링크가 모두 실제 파일을 가리키는지
link_files = [SKILL / "SKILL.md", SKILL / "references/index.md", *(SKILL / "references/topics").glob("*.md"),
              laws_dir / "index.md", *laws_dir.glob("*/index.md")]
DOCTOR = PLUGIN / "skills/budget-compass-doctor"
link_files += [DOCTOR / "SKILL.md", *(DOCTOR / "references").glob("*.md")]
n_links = 0
for f in link_files:
    if not f.is_file():
        err(f"파일 없음: {f.relative_to(ROOT)}")
        continue
    for t in re.findall(r"\]\(([^)#\s]+)\)", f.read_text(encoding="utf-8")):
        if t.startswith(("http://", "https://")):
            continue
        n_links += 1
        if not (f.parent / t).resolve().exists():
            err(f"{f.relative_to(ROOT)}: 깨진 링크 {t}")
for t in ("references/index.md",):
    if f"]({t})" not in text:
        err(f"SKILL.md 가 {t} 를 연결하지 않음")
if not list((SKILL / "references/topics").glob("*.md")):
    err("references/topics/ 비어 있음")

# Doctor
dtext = (DOCTOR / "SKILL.md").read_text(encoding="utf-8") if (DOCTOR / "SKILL.md").is_file() else ""
dm = re.match(r"^---\n(.*?)\n---\n", dtext, re.S)
if not dm or "name: budget-compass-doctor" not in dm.group(1):
    err("budget-compass-doctor/SKILL.md frontmatter name 오류")
rel = (DOCTOR / "references/installed-release.md")
if rel.is_file():
    pv = re.search(r'^package_version:\s*"?([\d.]+)"?', rel.read_text(encoding="utf-8"), re.M)
    if not pv or pv.group(1) != m.get("version"):
        err(f"installed-release.md package_version({pv.group(1) if pv else None}) ≠ plugin.json version({m.get('version')})")
import subprocess
if subprocess.run([sys.executable, str(ROOT / "tools/build_catalog.py"), "--check"], capture_output=True).returncode:
    err("source-catalog.md 가 laws/index.json 과 다름 — python3 tools/build_catalog.py")

if errors:
    print("검사 실패:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"검사 통과: {m.get('name')} v{m.get('version')} (참조 {len(refs)}개, 수록 규정 {len(idx)}개, 상대 링크 {n_links}개)")
