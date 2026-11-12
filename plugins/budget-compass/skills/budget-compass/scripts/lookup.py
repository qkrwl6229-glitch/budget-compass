#!/usr/bin/env python3
"""수록된 공통 규정(laws/)에서 조문을 찾는다 (Python 표준 라이브러리만 사용).
코드를 실행할 수 없으면 references/index.md → laws/<id>/index.md → 조문 파일 순서로 직접 읽어도 된다.

  python lookup.py --list                                   # 수록 규정·판본·수집일
  python lookup.py 회의비 식비                                # 모든 낱말이 들어간 조문 (전체 규정)
  python lookup.py 회의비 식비 --law rnd-cost-standard        # 특정 규정 안에서
  python lookup.py --law vat-act --article 29                # 조문 번호로 (29의2, 103조의13 도 가능)
  python lookup.py 원천징수 --law income-tax-act --full      # 긴 조문도 전체 출력
  python lookup.py --law rnd-cost-standard --article 25 --prev  # 직전 판본과 함께

결과마다 문서명·조문·번호·시행일·수집일·원문 주소를 함께 출력한다.
수록본은 수집일 기준 사본이므로, 답변에 인용하기 전에 원문 주소에서 이후 개정 여부를 확인한다.
"""
import argparse
import json
import re
import sys
from pathlib import Path

LAWS = Path(__file__).resolve().parent.parent / "laws"
LONG = 2500  # 이보다 긴 조문은 낱말이 든 줄만 발췌

# 실무 용어 → 조문에 실제로 쓰이는 표현 (낱말마다 원래 낱말 또는 대체어 중 하나만 있으면 일치)
ALIASES = {
    "부가세": ["부가가치세"],
    "에누리": ["직접 깎아 주는", "에누리"],
    "할인": ["직접 깎아 주는", "할인"],
    "원천세": ["원천징수"],
    "강사료": ["강연", "강사"],
    "자문료": ["자문"],
    "영수증": ["영수증서", "증명자료", "영수증"],
    "카드": ["연구비카드", "신용카드", "카드"],
    "장비": ["연구시설ㆍ장비", "시설ㆍ장비", "장비"],
    "주유": ["유류", "자가용", "주유"],
    "식대": ["식비", "식대"],
    "다과": ["다과", "식비"],
    "이체": ["계좌이체", "이체"],
    "환수": ["환수", "반환"],
}


def variants(word):
    return [word] + [v for v in ALIASES.get(word, []) if v != word]


class LookupError_(ValueError):
    pass


def load_index():
    p = LAWS / "index.json"
    if not p.exists():
        raise LookupError_(f"수록 규정 목록이 없습니다: {p}")
    return {x["id"]: x for x in json.loads(p.read_text(encoding="utf-8"))["laws"]}


def load_articles(law_id, include_prev=False):
    """laws/<id>/<조문>.md 를 읽는다. 직전 판본(*.prev-*.md)은 include_prev 일 때만."""
    arts = []
    for f in sorted((LAWS / law_id).glob("*.md")):
        if f.name in ("index.md", "addenda.md") or (".prev-" in f.name and not include_prev):
            continue
        text = f.read_text(encoding="utf-8")
        meta, body = {}, text
        if text.startswith("---\n"):
            head, _, body = text[4:].partition("\n---\n")
            for ln in head.splitlines():
                k, _, v = ln.partition(": ")
                meta[k] = json.loads(v) if v and v[0] in '"n' else v
        body = re.sub(r"^# .*\n+", "", body.strip())
        prov = meta.get("provisions", f.stem)
        m = re.match(r"제(\d+)조(?:의(\d+))?", prov)
        key = (m.group(1) + (f"의{m.group(2)}" if m.group(2) else "")) if m else f.stem
        label = prov + (f" [직전 판본, {meta.get('effective_from')}~{meta.get('effective_to')}]" if ".prev-" in f.name else "")
        if meta.get("addenda_note"):
            label += f" [{meta['addenda_note']}]"
        arts.append({"no": key, "head": label, "body": body.strip(), "file": f"laws/{law_id}/{f.name}",
                     "prev": ".prev-" in f.name})
    arts.sort(key=lambda x: [int(n) for n in re.findall(r"\d+", x["no"])] + [x["prev"]])
    return arts


def norm_article(s: str) -> str:
    """'제103조의13', '103조의13', '103의13', '29' → '103의13' / '29'"""
    m = re.fullmatch(r"\s*제?\s*(\d+)\s*조?\s*(?:의\s*(\d+))?\s*", s)
    if not m:
        raise LookupError_(f"조문 번호 형식이 아닙니다: {s!r} (예: 29, 29의2, 제103조의13)")
    return m.group(1) + (f"의{m.group(2)}" if m.group(2) else "")


def cite(meta, art):
    return (f"━━ 「{meta['title']}」 {art['head']}\n"
            f"   {meta['number']} · 시행 {meta['effective']} · 수집 {meta['collected']} · {meta['url']} · 파일 {art['file']}")


def excerpt(body: str, words, full: bool) -> str:
    if full or len(body) <= LONG or not words:
        return body
    lines = body.split("\n")
    keep = set()
    terms = [v for w in words for v in variants(w)]
    for i, ln in enumerate(lines):
        if any(t in ln for t in terms):
            keep.update({i - 1, i, i + 1} if i > 0 else {i, i + 1})
    if not keep:
        return body[:LONG] + "\n   … (이하 생략, --full 로 전체 보기)"
    out, prev = [], -2
    for i in sorted(k for k in keep if 0 <= k < len(lines)):
        if i != prev + 1:
            out.append("   …")
        out.append(lines[i])
        prev = i
    out.append("   … (낱말이 든 부분만 발췌, --full 로 전체 보기)")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*", help="찾을 낱말 (모두 포함한 조문)")
    ap.add_argument("--law", help="규정 id (--list 로 확인)")
    ap.add_argument("--article", help="조문 번호 (예: 29, 29의2)")
    ap.add_argument("--list", action="store_true", help="수록 규정 목록")
    ap.add_argument("--max", type=int, default=6, help="최대 결과 수 (기본 6)")
    ap.add_argument("--full", action="store_true", help="긴 조문도 전체 출력")
    ap.add_argument("--prev", action="store_true", help="직전 판본 조문도 함께 (수록된 경우)")
    a = ap.parse_args(argv)
    try:
        index = load_index()
        if a.list:
            print("id | 규정 | 번호 | 시행일 | 수집일 | 수록 범위")
            for m in index.values():
                print(f"{m['id']} | {m['title']} | {m['number']} | {m['effective']} | {m['collected']} | {m['scope']}")
            return
        if a.law and a.law not in index:
            raise LookupError_(f"없는 규정 id: {a.law} (--list 로 확인)")
        if a.article:
            if not a.law:
                raise LookupError_("--article 은 --law 와 함께 씁니다")
            key = norm_article(a.article)
            hits = [x for x in load_articles(a.law, a.prev) if x["no"] == key]
            if not hits:
                raise LookupError_(f"{index[a.law]['title']}에 제{a.article}조가 수록되어 있지 않습니다")
            for art in hits:
                print(cite(index[a.law], art))
                print(art["body"])
            return
        if not a.words:
            raise LookupError_("찾을 낱말, --article 또는 --list 중 하나가 필요합니다")
        laws = [a.law] if a.law else list(index)
        results = []
        for lid in laws:
            for art in load_articles(lid, a.prev):
                hay = art["head"] + "\n" + art["body"]
                if all(any(v in hay for v in variants(w)) for w in a.words):
                    score = sum(hay.count(v) for w in a.words for v in variants(w))
                    score += 20 * sum(any(v in art["head"] for v in variants(w)) for w in a.words)
                    results.append((score, lid, art))
        if not results:
            print(f"'{' '.join(a.words)}' 가 모두 들어간 조문이 없습니다. 낱말을 줄이거나 바꿔 보세요.")
            return
        results.sort(key=lambda r: -r[0])
        for _, lid, art in results[:a.max]:
            print(cite(index[lid], art))
            print(excerpt(art["body"], a.words, a.full))
            print()
        if len(results) > a.max:
            rest = ", ".join(f"{index[l]['title']} {x['head'].split('(')[0]}" for _, l, x in results[a.max:a.max + 8])
            print(f"(그 밖에 {len(results) - a.max}건: {rest}{' …' if len(results) > a.max + 8 else ''})")
    except LookupError_ as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
