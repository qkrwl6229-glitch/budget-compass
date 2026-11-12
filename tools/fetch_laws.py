#!/usr/bin/env python3
"""국가법령정보센터에서 공통 규정 원문을 받아 조문별 마크다운 파일로 저장한다 (표준 라이브러리만 사용).

  python3 tools/fetch_laws.py            # tools/law_sources.json 의 규정을 모두 수집 → skills/budget-compass/laws/
  python3 tools/fetch_laws.py --only vat-act subsidy-act
  python3 tools/fetch_laws.py --check    # 수록본과 현행 판본 비교 (개정이 있으면 종료 코드 1)

출력 (규정마다 폴더 하나):
  laws/index.md, laws/index.json        수록 규정 목록
  laws/<id>/index.md                    판본 정보, 조문 목록, 부칙·별표 링크
  laws/<id>/<조문>.md                   조문 하나 (YAML 헤더 + 본문). 제25조의2 → 25-2.md
  laws/<id>/<조문>.prev-<시행일>.md       직전 판본 조문 (law_sources.json 의 previous 에 지정한 것만)
  laws/<id>/addenda.md                  현재 판본의 부칙

법령·고시·훈령·예규는 저작권법 제7조에 따라 보호받지 않는 저작물이다.
"""
import argparse
import datetime as dt
import html
import json
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "tools/law_sources.json"
OUT = ROOT / "plugins/budget-compass/skills/budget-compass/laws"
BASE = "https://www.law.go.kr"
UA = "Mozilla/5.0 (compatible; budget-compass-law-fetcher)"
KST = dt.timezone(dt.timedelta(hours=9))

# ---------- HTTP ----------
_CTX = None


def _ssl_context():
    global _CTX
    if _CTX is None:
        _CTX = ssl.create_default_context()
    return _CTX


def _use_macos_roots():
    """python.org 설치본처럼 기본 인증서 저장소가 비어 있는 macOS 환경용."""
    global _CTX
    pem = subprocess.run(
        ["security", "find-certificate", "-a", "-p",
         "/System/Library/Keychains/SystemRootCertificates.keychain", "/Library/Keychains/System.keychain"],
        capture_output=True, text=True, check=True).stdout
    f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    f.write(pem)
    f.close()
    _CTX = ssl.create_default_context(cafile=f.name)


def get(url: str) -> str:
    url = urllib.parse.quote(url, safe=":/?=&%(),")
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40, context=_ssl_context()) as r:
                body = r.read().decode("utf-8", "replace")
            time.sleep(0.8)  # 서버 부담을 줄이기 위한 간격
            return body
        except Exception as e:  # noqa: BLE001
            last = e
            if isinstance(getattr(e, "reason", e), ssl.SSLCertVerificationError) and sys.platform == "darwin":
                _use_macos_roots()
                continue
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} ({last})")


# ---------- 텍스트 ----------
INLINE_TAG = re.compile(r"</?(?:a|span|label|font|b|i|u|strong|em|sup|sub)\b[^>]*>", re.I)


ATTR = re.compile(r"""\s[\w:-]+\s*=\s*(?:"[^"]*"|'[^']*')""")


def text_of(fragment: str) -> str:
    t = ATTR.sub("", fragment)  # onclick="...'<제2026-38호>'..." 같은 속성값 안의 꺾쇠가 태그 제거를 깨뜨리지 않게
    t = INLINE_TAG.sub("", t)  # 조문 안의 링크·강조는 공백 없이 이어 붙인다
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def ymd(s: str) -> str:
    """'20260102' 또는 '2026. 1. 2.' → '2026-01-02'"""
    nums = re.findall(r"\d+", s)
    if len(nums) == 1 and len(nums[0]) == 8:
        n = nums[0]
        return f"{n[:4]}-{n[4:6]}-{n[6:]}"
    if len(nums) >= 3:
        return f"{int(nums[0]):04d}-{int(nums[1]):02d}-{int(nums[2]):02d}"
    return ""


def art_label(no: str) -> str:
    """'103의13' → '제103조의13'"""
    base, _, sub = no.partition("의")
    return f"제{base}조" + (f"의{sub}" if sub else "")


def art_file(no: str) -> str:
    """'25의2' → '25-2'"""
    return no.replace("의", "-")


def q(v) -> str:
    """YAML 값 (JSON 문자열은 유효한 YAML)."""
    return "null" if v is None else json.dumps(v, ensure_ascii=False)


# ---------- 판본 확인 ----------
def resolve(src: dict, page_url: str = None) -> dict:
    """이름 주소(또는 지정 주소) → 그 판본의 식별자·본문 주소."""
    seg = "법령" if src["kind"] == "law" else "행정규칙"
    page_url = page_url or f"{BASE}/{seg}/{src['name']}"
    shell = get(page_url)
    m = re.search(r"(/LSW/+(?:lsInfoP|admRulInfoP)\.do\?[^\"']+)", shell)
    if not m:
        raise RuntimeError(f"{src['id']}: 판본 주소를 찾지 못함 ({page_url})")
    qs = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(m.group(1))).query)
    info = {"id": src["id"], "kind": src["kind"], "url": f"{BASE}/{seg}/{src['name']}"}
    if src["kind"] == "law":
        seq, ef = qs["lsiSeq"][0], qs.get("efYd", [""])[0]
        info.update(seq=seq,
                    body_url=f"{BASE}/LSW/lsInfoR.do?lsiSeq={seq}&chrClsCd=010202&efYd={ef}&ancYnChk=0",
                    fixed_url=f"{BASE}/LSW/lsInfoP.do?lsiSeq={seq}&efYd={ef}")
    else:
        seq = qs["admRulSeq"][0]
        info.update(seq=seq, body_url=f"{BASE}/admRulInfoR.do?admRulSeq={seq}",
                    fixed_url=f"{BASE}/LSW/admRulInfoP.do?admRulSeq={seq}")
    return info


def parse_header(body: str, info: dict) -> None:
    """'[시행 2026. 1. 2.] [법률 제21065호, 2025. 10. 1., 타법개정]'"""
    t = text_of(body[:60000])
    m = re.search(r"\[시행\s*([\d.\s]+?)\]\s*\[([^\]]+?)\]", t)
    if not m:
        raise RuntimeError(f"{info['id']}: 시행일·번호를 찾지 못함")
    info["effective"] = ymd(m.group(1))
    parts = [p.strip() for p in m.group(2).split(",")]
    info["number"] = parts[0]
    info["promulgated"] = ymd(", ".join(parts[1:4])) if len(parts) > 1 else ""
    info["revision"] = parts[-1] if len(parts) > 2 else ""
    tm = re.search(r'<input type="hidden" id="(?:lsNm|admRulNm)"[^>]*value="([^"]+)"', body)
    if tm:
        info["title"] = html.unescape(tm.group(1)).strip()
    else:
        tt = re.search(r"([^\[\]]{2,80}?)\s*\[시행", t)
        info["title"] = tt.group(1).strip() if tt else info["id"]


# ---------- 조문·부칙·별표 ----------
LABEL_RE = re.compile(r"<label[^>]*>(.*?)</label>", re.S)
ART_RE = re.compile(r"^제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*(?:\((.*)\))?\s*$")
P_RE = re.compile(r'<p class="(pty[^"]*)"[^>]*>(.*?)</p>', re.S)
INDENT = {"de2h": "  ", "de3": "    ", "de4": "      ", "de5": "        "}


def split_body(body: str):
    """(본문, 부칙 영역) — 부칙 영역은 arDivArea 이후."""
    i = body.find('id="arDivArea"')
    return (body[:i], body[i:]) if i >= 0 else (body, "")


def split_articles(body: str):
    arts, cur, max_no = [], None, 0
    for cls, inner in P_RE.findall(body):
        lm = LABEL_RE.search(inner)
        am = ART_RE.match(text_of(lm.group(1))) if lm else None
        if am:
            no = int(am.group(1))
            if max_no >= 3 and no == 1 and arts:
                break  # 부칙 시작 (조문 번호가 1로 돌아감)
            max_no = max(max_no, no)
            key = f"{no}" + (f"의{am.group(2)}" if am.group(2) else "")
            cur = {"no": key, "title": (am.group(3) or "").strip(), "lines": []}
            arts.append(cur)
            inner = inner[lm.end():]
        if cur is None:
            continue
        line = text_of(inner)
        if not line:
            continue
        indent = next((v for k, v in INDENT.items() if k in cls), "")
        cur["lines"].append(indent + line)
    return arts


def split_addenda(area: str):
    """부칙 영역 → [(제목, [줄...])] (오래된 것부터)."""
    blocks, cur = [], None
    for cls, inner in P_RE.findall(area):
        line = text_of(inner)
        if not line:
            continue
        if cls == "pty3" or re.match(r"^부\s*칙\s*<", line):
            cur = (re.sub(r"^부\s*칙", "부칙", line).strip(), [])
            blocks.append(cur)
        elif cur is not None:
            indent = next((v for k, v in INDENT.items() if k in cls), "")
            cur[1].append(indent + line)
    return blocks


def find_appendices(body: str, fixed_url: str = None):
    """[(별표 제목, 보기 주소)] — 별표는 대부분 이미지·첨부파일이라 본문은 수록하지 않는다.
    행정규칙은 별표 보기 주소가 따로 없어 판본 고정 주소를 쓴다."""
    out, seen = [], set()
    for m in re.finditer(r"bylInfoDiv\('(\d+)'\)", body):
        seq = m.group(1)
        if seq in seen:
            continue
        tail = body[m.end():m.end() + 800]
        tail = tail[tail.find(">") + 1:]  # 여는 태그 밖으로
        tm = re.search(r"\[별표\s*\d+(?:의\d+)?\][^\[<]{0,90}", text_of(tail))
        if not tm:
            continue
        title = re.sub(r"\s+(\.?hwpx?|\.pdf)\b.*$", "", tm.group(0)).strip()
        if "삭제" in title[:14]:
            continue
        seen.add(seq)
        out.append((title, fixed_url or f"{BASE}/LSW/lsBylContentsInfoR.do?bylSeq={seq}&chrClsCd=010202"))
    return out


def staged_effective(lines, revision: str):
    """부칙의 '제5조, 제10조의2 및 제25조의2의 개정규정은 2026년 6월 11일부터 시행' → {'5': '2026-06-11', ...}.
    타법개정 부칙은 다른 법률의 조문을 가리키므로 쓰지 않는다."""
    if "타법" in (revision or ""):
        return {}
    out = {}
    text = " ".join(lines)
    for m in re.finditer(r"((?:제\d+조(?:의\d+)?(?:제\d+항)?(?:제\d+호)?(?:\s*[,ㆍ]\s*|\s*및\s*)?)+)의?\s*개정규정은\s*"
                         r"(\d{4})년\s*(\d+)월\s*(\d+)일부터\s*시행", text):
        date = f"{int(m.group(2)):04d}-{int(m.group(3)):02d}-{int(m.group(4)):02d}"
        for a in re.finditer(r"제(\d+)조(?:의(\d+))?", m.group(1)):
            out[a.group(1) + (f"의{a.group(2)}" if a.group(2) else "")] = date
    return out


# ---------- 쓰기 ----------
def article_md(info, art, collected, *, effective_to=None, previous=None, superseded_by=None, scope_note="",
               staged=None):
    head = art_label(art["no"]) + (f"({art['title']})" if art["title"] else "")
    meta = [
        "---",
        f"source_id: {q(info['id'] + '-art' + art_file(art['no']))}",
        f"document: {q(info['title'])}",
        f"revision: {q(info['number'] + (' (' + info['revision'] + ')' if info.get('revision') else ''))}",
        f"provisions: {q(head)}",
        f"effective_from: {q(info['effective'])}",
        f"effective_to: {q(effective_to)}",
        f"retrieved_on: {q(collected)}",
        f"official_url: {q(info['url'])}",
        f"fixed_url: {q(info['fixed_url'])}",
    ]
    if staged:
        meta.append(f"addenda_note: {q('부칙: 이 조의 개정규정(전부 또는 일부)은 ' + staged + ' 부터 시행. 그 전 사건은 직전 판본 확인')}")
    if previous:
        meta.append(f"previous_snapshot: {q(previous)}")
    if superseded_by:
        meta.append(f"superseded_by: {q(superseded_by)}")
    meta.append(f"scope: {q(scope_note or '본문 조문. 시행일·적용례·경과조치는 addenda.md 와 원문 부칙 확인')}")
    meta.append("---")
    body = [f"# {info['title']} {head}", ""] + (art["lines"] or ["(본문 없음)"])
    return "\n".join(meta + body) + "\n"


def doc_index_md(info, arts, scope, collected, addenda, appendices, prev):
    lines = [
        f"# {info['title']}",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 구분 | {'법령' if info['kind'] == 'law' else '행정규칙'} |",
        f"| 번호 | {info['number']}" + (f" ({info['revision']})" if info.get("revision") else "") + " |",
        f"| 시행일 | {info['effective']} |",
    ]
    if info.get("promulgated"):
        lines.append(f"| 공포(발령)일 | {info['promulgated']} |")
    lines += [
        f"| 수집일 | {collected} |",
        f"| 현행 원문 | {info['url']} |",
        f"| 이 판본 고정 주소 | {info['fixed_url']} |",
        f"| 수록 범위 | {scope} |",
        "",
        "> 수집일 기준 사본. `effective_to: null` 은 종료일이 확인되지 않았다는 뜻이지 최신이라는 뜻이 아니다.",
        "> 사건일이 시행일보다 이전이면 직전 판본 또는 원문 연혁을 확인한다.",
        "",
        "## 조문",
        "| 조문 | 파일 |",
        "|---|---|",
    ]
    for a in arts:
        head = art_label(a["no"]) + (f"({a['title']})" if a["title"] else "")
        extra = ""
        if a["no"] in prev:
            extra = f" · 직전 판본 [{prev[a['no']]}]({prev[a['no']]})"
        lines.append(f"| {head} | [{art_file(a['no'])}.md]({art_file(a['no'])}.md){extra} |")
    if addenda:
        lines += ["", "## 부칙", f"- [addenda.md](addenda.md) — {addenda}"]
    if appendices:
        lines += ["", "## 별표 (이미지 원문 — 수록하지 않음, 링크로 확인)"]
        lines += [f"- [{t}]({u})" for t, u in appendices]
    return "\n".join(lines) + "\n"


def collect(sources, only):
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"laws": []}
    by_id = {x["id"]: x for x in index.get("laws", [])}
    collected = dt.datetime.now(KST).date().isoformat()
    failed = []
    for src in sources:
        if only and src["id"] not in only:
            continue
        try:
            info = resolve(src)
            body = get(info["body_url"])
            parse_header(body, info)
            main, ar_area = split_body(body)
            arts = split_articles(main)
            if not arts:
                raise RuntimeError("조문을 하나도 찾지 못함")
            if src.get("articles"):
                want = list(src["articles"])
                arts = [a for a in arts if a["no"] in want]
                missing = [w for w in want if w not in {a["no"] for a in arts}]
                if missing:
                    print(f"  ! {src['id']}: 찾지 못한 조문 {missing}", file=sys.stderr)
                scope = "일부 조문 (" + ", ".join(art_label(a["no"]) for a in arts) + ")"
            else:
                scope = f"본문 전체 {len(arts)}개 조문 (별표·서식 제외)"

            d = OUT / src["id"]
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)

            # 직전 판본 (지정한 조문만)
            prev_files = {}
            pv = src.get("previous")
            if pv:
                pinfo = resolve(src, f"{BASE}/행정규칙/{src['name']}/({pv['number']},{pv['date'].replace('-', '')})")
                pbody = get(pinfo["body_url"])
                parse_header(pbody, pinfo)
                pinfo["title"] = info["title"]
                end = (dt.date.fromisoformat(info["effective"]) - dt.timedelta(days=1)).isoformat()
                for pa in split_articles(split_body(pbody)[0]):
                    if pa["no"] in pv["articles"]:
                        fname = f"{art_file(pa['no'])}.prev-{pinfo['effective']}.md"
                        prev_files[pa["no"]] = fname
                        (d / fname).write_text(article_md(
                            pinfo, pa, collected, effective_to=end, superseded_by=f"{art_file(pa['no'])}.md",
                            scope_note=f"직전 판본. {end} 까지 시행된 사건에 적용 여부 확인 (부칙의 적용례·경과조치 우선)"),
                            encoding="utf-8")
                gone = [n for n in pv["articles"] if n not in prev_files]
                if gone:
                    print(f"  · {src['id']}: 직전 판본에 없는 조문 {gone} (새로 생긴 조문)")

            # 부칙: 현재 판본 번호와 같은 블록
            addenda_note = ""
            digits = re.sub(r"[^\d-]", "", info["number"].split("제")[-1])
            blocks = split_addenda(ar_area)
            cur_blocks = [b for b in blocks if digits and digits in re.sub(r"[^\d-]", "", b[0])]
            staged = staged_effective(cur_blocks[-1][1], info.get("revision")) if cur_blocks else {}

            for a in arts:
                (d / f"{art_file(a['no'])}.md").write_text(
                    article_md(info, a, collected, previous=prev_files.get(a["no"]), staged=staged.get(a["no"])),
                    encoding="utf-8")

            if cur_blocks:
                title, lines = cur_blocks[-1]
                (d / "addenda.md").write_text(
                    f"# {info['title']} {title}\n\n"
                    f"- 이 판본({info['number']}, 시행 {info['effective']})의 부칙만 수록. 이전 부칙은 원문에서 확인.\n"
                    f"- 원문: {info['fixed_url']}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
                addenda_note = title

            appendices = find_appendices(body, None if info["kind"] == "law" else info["fixed_url"])
            (d / "index.md").write_text(
                doc_index_md(info, arts, scope, collected, addenda_note, appendices, prev_files), encoding="utf-8")

            by_id[src["id"]] = {
                "id": src["id"], "title": info["title"], "kind": info["kind"], "number": info["number"],
                "effective": info["effective"], "promulgated": info.get("promulgated", ""), "seq": info["seq"],
                "url": info["url"], "fixed_url": info["fixed_url"], "collected": collected, "scope": scope,
                "articles": [{"no": a["no"], "title": a["title"]} for a in arts],
                "previous": [{"no": k, "file": v} for k, v in prev_files.items()],
                "addenda": bool(addenda_note), "staged_effective": staged, "appendices": [{"title": t, "url": u} for t, u in appendices],
            }
            print(f"  ✓ {src['id']}: {info['title']} ({info['number']}, 시행 {info['effective']}) — "
                  f"{len(arts)}개 조문, 직전판 {len(prev_files)}, 부칙 {'있음' if addenda_note else '없음'}, 별표 {len(appendices)}")
        except Exception as e:  # noqa: BLE001
            failed.append(src["id"])
            print(f"  ✗ {src['id']}: {e}", file=sys.stderr)

    order = [s["id"] for s in sources]
    for stale in [k for k in by_id if k not in order]:
        del by_id[stale]
    index["laws"] = sorted(by_id.values(), key=lambda x: order.index(x["id"]))
    index["note"] = "수집일 기준 사본. 답변 전 원문 주소에서 개정 여부 확인."
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_top_index(index["laws"])
    subprocess.run([sys.executable, str(ROOT / "tools/build_catalog.py")], check=False)
    for old in OUT.glob("*.md"):  # v0.4.0 의 단일 파일 형식 정리
        if old.name != "index.md":
            old.unlink()
    return failed


def write_top_index(laws):
    lines = [
        "# 수록 규정 목록",
        "",
        "국가법령정보센터 현행 판본을 조문별 파일로 담았다. 각 규정 폴더의 `index.md` 에서 조문 파일을 고른다.",
        "수집일 기준 사본이므로 인용할 때 판본과 수집일을 밝히고, 웹을 쓸 수 있으면 이후 개정 여부를 확인한다.",
        "",
        "| id | 규정 | 번호 | 시행일 | 수집일 | 수록 범위 |",
        "|---|---|---|---|---|---|",
    ]
    for x in laws:
        lines.append(f"| [{x['id']}]({x['id']}/index.md) | {x['title']} | {x['number']} | {x['effective']} "
                     f"| {x['collected']} | {x['scope']} |")
    (OUT / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def check(sources):
    index = {x["id"]: x for x in json.loads((OUT / "index.json").read_text(encoding="utf-8"))["laws"]}
    changed, errors = [], []
    for src in sources:
        old = index.get(src["id"])
        try:
            info = resolve(src)
            if old is None:
                changed.append(f"{src['id']}: 수록본 없음")
            elif info["seq"] != old["seq"]:
                parse_header(get(info["body_url"]), info)
                changed.append(f"{old['title']}: {old['number']} (시행 {old['effective']}) → "
                               f"{info['number']} (시행 {info['effective']})")
        except Exception as e:  # noqa: BLE001
            errors.append(f"{src['id']}: {e}")
    for c in changed:
        print(f"개정 감지 — {c}")
    for e in errors:
        print(f"확인 실패 — {e}", file=sys.stderr)
    if not changed and not errors:
        print(f"변경 없음 ({len(sources)}개 규정)")
    return 1 if changed else (2 if errors else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", help="이 id 만 수집")
    ap.add_argument("--check", action="store_true", help="현행 판본과 비교만 한다")
    a = ap.parse_args()
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    if a.check:
        sys.exit(check(sources))
    failed = collect(sources, set(a.only or []))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
