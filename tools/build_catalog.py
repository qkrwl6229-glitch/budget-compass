#!/usr/bin/env python3
"""Doctor 스킬의 출처 카탈로그(source-catalog.md)를 laws/index.json 과 tools/manual_sources.json 에서 만든다.

  python3 tools/build_catalog.py          # 파일 생성
  python3 tools/build_catalog.py --check  # 현재 파일이 원본과 같은지만 확인 (다르면 종료 코드 1)

카탈로그에는 조문 본문을 복제하지 않고 문서 ID·조문·수록 판본·고정 판본 주소·현행 확인 주소만 적는다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAWS = ROOT / "plugins/budget-compass/skills/budget-compass/laws/index.json"
MANUALS = ROOT / "tools/manual_sources.json"
OUT = ROOT / "plugins/budget-compass/skills/budget-compass-doctor/references/source-catalog.md"

# 기본 점검 범위: 자주 쓰는 R&D·세무 조문 (주제 파일이 가리키는 조문)
FREQUENT = {
    "rnd-cost-standard": ["10", "21", "22", "23", "25", "25의2", "73", "74"],
    "rnd-facility-standard": ["18", "28"],
    "travel-regulation": ["13", "30"],
    "vat-act": ["29", "38", "39"],
    "vat-decree": ["70"],
    "income-tax-act": ["21", "84", "86", "129", "164"],
    "income-tax-decree": ["87"],
    "local-tax-act": ["103의13"],
}


def label(no):
    base, _, sub = no.partition("의")
    return f"제{base}조" + (f"의{sub}" if sub else "")


def build() -> str:
    laws = json.loads(LAWS.read_text(encoding="utf-8"))["laws"]
    manuals = json.loads(MANUALS.read_text(encoding="utf-8"))["manuals"]
    lines = [
        "# 출처 카탈로그",
        "",
        "> 자동 생성 파일 (`tools/build_catalog.py`). 직접 고치지 않는다.",
        "> 수록 판본과 공식 현행 판본을 비교할 때 쓴다. 조문 본문은 `budget-compass/laws/` 에 있다.",
        "",
        "## 법령·행정규칙",
        "| id | 문서 | 수록 판본 | 시행일 | 수집일 | 수록 범위 | 이 판본 고정 주소 | 현행·연혁 확인 주소 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for x in laws:
        lines.append(f"| {x['id']} | {x['title']} | {x['number']} | {x['effective']} | {x['collected']} "
                     f"| {x['scope']} | {x['fixed_url']} | {x['url']} |")
    lines += ["", "## 조문별 특이사항"]
    notes = []
    for x in laws:
        for p in x.get("previous", []):
            notes.append(f"- {x['id']} {label(p['no'])}: 직전 판본 수록 (`{p['file']}`)")
        for no, d in sorted(x.get("staged_effective", {}).items()):
            if any(a["no"] == no for a in x["articles"]):
                notes.append(f"- {x['id']} {label(no)}: 부칙상 개정규정 시행일 {d}")
    lines += notes or ["- 없음"]
    lines += ["", "## 기본 점검 범위 (자주 쓰는 조문)", "| id | 조문 |", "|---|---|"]
    ids = {x["id"] for x in laws}
    for lid, arts in FREQUENT.items():
        if lid in ids:
            lines.append(f"| {lid} | {', '.join(label(a) for a in arts)} |")
    lines += ["", "## 시스템 매뉴얼 (요약·쪽 번호만 수록)",
              "| id | 문서 | 작성 기관 | 판본 | 게시일 | 적용 범위 | 주소 |", "|---|---|---|---|---|---|---|"]
    for mnl in manuals:
        lines.append(f"| {mnl['id']} | {mnl['title']} | {mnl['issuer']} | {mnl['version']} | {mnl['posted']} "
                     f"| {mnl['scope']} | {mnl['url']} |")
    return "\n".join(lines) + "\n"


def main():
    text = build()
    if "--check" in sys.argv:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print("카탈로그 일치" if ok else "카탈로그가 원본과 다름 — python3 tools/build_catalog.py 실행")
        sys.exit(0 if ok else 1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"생성: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
