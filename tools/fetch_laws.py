#!/usr/bin/env python3
"""국가법령정보센터에서 공통 규정 원문을 받아 조문 단위 마크다운으로 저장한다 (표준 라이브러리만 사용).

  python3 tools/fetch_laws.py            # tools/law_sources.json 의 규정을 모두 수집 → skills/.../laws/
  python3 tools/fetch_laws.py --only vat-act subsidy-act
  python3 tools/fetch_laws.py --check    # 수록본과 현행 판본 비교 (개정이 있으면 종료 코드 1)

수록 범위: 본문 조문. 부칙·별표·서식은 제외한다.
법령·고시·훈령·예규는 저작권법 제7조에 따라 보호받지 않는 저작물이다.
"""
import argparse
import datetime as dt
import html
import json
import re
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


_CTX = None


def _ssl_context():
    """기본 인증서 저장소로 실패하는 macOS(python.org 설치본) 환경이면 시스템 루트 인증서를 쓴다."""
    global _CTX
    if _CTX is None:
        _CTX = ssl.create_default_context()
    return _CTX


def _use_macos_roots():
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
    url = urllib.parse.quote(url, safe=":/?=&%")
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


INLINE_TAG = re.compile(r"</?(?:a|span|label|font|b|i|u|strong|em|sup|sub)\b[^>]*>", re.I)


def text_of(fragment: str) -> str:
    t = INLINE_TAG.sub("", fragment)  # 조문 안의 링크·강조는 공백 없이 이어 붙인다
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


# ---------- 현행 판본 확인 ----------
def resolve(src: dict) -> dict:
    """이름 주소 → 현행 판본의 식별자·본문 주소·메타데이터."""
    seg = "법령" if src["kind"] == "law" else "행정규칙"
    page_url = f"{BASE}/{seg}/{src['name']}"
    shell = get(page_url)
    m = re.search(r"(/LSW/+(?:lsInfoP|admRulInfoP)\.do\?[^\"']+)", shell)
    if not m:
        raise RuntimeError(f"{src['id']}: 현행 판본 주소를 찾지 못함 ({page_url})")
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(m.group(1))).query)
    info = {"id": src["id"], "kind": src["kind"], "url": page_url}
    if src["kind"] == "law":
        seq, ef = q["lsiSeq"][0], q.get("efYd", [""])[0]
        info.update(seq=seq, body_url=f"{BASE}/LSW/lsInfoR.do?lsiSeq={seq}&chrClsCd=010202&efYd={ef}&ancYnChk=0")
    else:
        seq = q["admRulSeq"][0]
        info.update(seq=seq, body_url=f"{BASE}/admRulInfoR.do?admRulSeq={seq}")
    return info


def parse_header(body: str, info: dict) -> None:
    """본문 상단의 '[시행 2026. 1. 2.] [법률 제21065호, 2025. 10. 1., 타법개정]' 을 읽는다."""
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


# ---------- 조문 분리 ----------
LABEL_RE = re.compile(r"<label[^>]*>(.*?)</label>", re.S)
ART_RE = re.compile(r"^제\s*(\d+)\s*조(?:\s*의\s*(\d+))?\s*(?:\((.*)\))?\s*$")
P_RE = re.compile(r'<p class="(pty[^"]*)"[^>]*>(.*?)</p>', re.S)
INDENT = {"de2h": "  ", "de3": "    ", "de4": "      ", "de5": "        "}


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


def art_label(no: str) -> str:
    """'103의13' → '제103조의13', '29' → '제29조'"""
    base, _, sub = no.partition("의")
    return f"제{base}조" + (f"의{sub}" if sub else "")


def render(info: dict, arts: list, scope: str, collected: str) -> str:
    out = [
        f"# {info['title']}",
        "",
        f"- 구분: {'법령' if info['kind'] == 'law' else '행정규칙'} · {info['number']}"
        + (f" · {info['revision']}" if info.get("revision") else ""),
        f"- 시행일: {info['effective']}" + (f" · 공포(발령)일: {info['promulgated']}" if info.get("promulgated") else ""),
        f"- 원문: {info['url']}",
        f"- 수집일: {collected}",
        f"- 수록 범위: {scope}",
        "",
        "> 수집일 기준 사본이다. 답변에 인용하기 전에 원문 주소에서 이후 개정·시행 예정 여부를 확인한다.",
        "",
    ]
    for a in arts:
        head = art_label(a["no"]) + (f"({a['title']})" if a["title"] else "")
        out.append(f"## {head}")
        out.extend(a["lines"] or ["(본문 없음)"])
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def collect(sources, only):
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"laws": []}
    by_id = {x["id"]: x for x in index["laws"]}
    collected = dt.datetime.now(KST).date().isoformat()
    failed = []
    for src in sources:
        if only and src["id"] not in only:
            continue
        try:
            info = resolve(src)
            body = get(info["body_url"])
            parse_header(body, info)
            arts = split_articles(body)
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
                scope = f"본문 전체 {len(arts)}개 조문 (부칙·별표·서식 제외)"
            (OUT / f"{src['id']}.md").write_text(render(info, arts, scope, collected), encoding="utf-8")
            by_id[src["id"]] = {
                "id": src["id"], "title": info["title"], "kind": info["kind"], "number": info["number"],
                "effective": info["effective"], "promulgated": info.get("promulgated", ""), "seq": info["seq"],
                "url": info["url"], "collected": collected, "scope": scope,
                "articles": [{"no": a["no"], "title": a["title"]} for a in arts],
            }
            print(f"  ✓ {src['id']}: {info['title']} ({info['number']}, 시행 {info['effective']}) — {len(arts)}개 조문")
        except Exception as e:  # noqa: BLE001
            failed.append(src["id"])
            print(f"  ✗ {src['id']}: {e}", file=sys.stderr)
    order = [s["id"] for s in sources]
    index["laws"] = sorted(by_id.values(), key=lambda x: order.index(x["id"]) if x["id"] in order else 999)
    index["note"] = "수집일 기준 사본. 답변 전 원문 주소에서 개정 여부 확인."
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return failed


def check(sources):
    idx_path = OUT / "index.json"
    index = {x["id"]: x for x in json.loads(idx_path.read_text(encoding="utf-8"))["laws"]}
    changed, errors = [], []
    for src in sources:
        old = index.get(src["id"])
        try:
            info = resolve(src)
            if old is None:
                changed.append(f"{src['id']}: 수록본 없음")
            elif info["seq"] != old["seq"]:
                body = get(info["body_url"])
                parse_header(body, info)
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
