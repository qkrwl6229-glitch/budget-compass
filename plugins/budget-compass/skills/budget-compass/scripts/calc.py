#!/usr/bin/env python3
"""사업비 나침반 계산기 (표준 라이브러리만 사용).

세율·공제액 기본값은 작성 시점 기준이다. 개정되었으면 옵션으로 바꿔 넣는다.

  vat-split   합계금액 → 공급가액·부가세 분리
  vat-add     공급가액 → 부가세·합계
  other-income  기타소득 원천징수 (일시적 강연·자문·심사 등)
  business-income  사업소득 원천징수 (3.3%)
  daily-wage  일용근로소득 원천징수
  gross-up    세후 실지급액 → 세전 지급액 역산
  ratio       비목별 금액 → 비율, 상한/하한 점검
  subsidy     인정비용·보조율·상한·불인정액 → 지원액·자부담
  grant-base  보조금과 비율 → 총사업비·자부담 (두 가지 해석 모두)

예:
  python calc.py vat-split 1100000
  python calc.py other-income 500000 --expense-rate 0.6
  python calc.py business-income 1000000
  python calc.py daily-wage 200000 --days 5
  python calc.py gross-up 456000 --type other
  python calc.py subsidy 5000000 --rate 0.6 --cap 2500000 --disallowed 100000
  python calc.py grant-base 30000000 --rate 0.8
  python calc.py ratio 인건비=180000000 운영비=120000000 자부담=100000000 --cap 인건비=0.4 --min 자부담=0.2
"""
import argparse
import math
import sys
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

D = Decimal


def won(x) -> str:
    return f"{int(x):,}원"


def pct(r) -> str:
    """0.4 → '40%', 0.033 → '3.3%'"""
    return f"{(D(r) * 100).normalize():f}%"


def floor_to(x: Decimal, unit: int) -> Decimal:
    """unit 원 미만 절사 (예: unit=10 → 10원 미만 절사)."""
    return (x / unit).to_integral_value(rounding=ROUND_DOWN) * unit


# ---------- 부가세 ----------
def vat_split(total: int, rate: Decimal):
    t = D(total)
    a_supply = (t / (1 + rate)).to_integral_value(rounding=ROUND_HALF_UP)
    a_tax = t - a_supply
    b_tax = (t * rate / (1 + rate)).to_integral_value(rounding=ROUND_DOWN)
    b_supply = t - b_tax
    print(f"합계(공급대가) {won(t)}, 세율 {pct(rate)}")
    print(f"  공급가액 = 합계 ÷ {1 + rate} (원 미만 반올림) = {won(a_supply)}")
    print(f"  부가세   = 합계 − 공급가액 = {won(a_tax)}")
    if (a_supply, a_tax) != (b_supply, b_tax):
        print(f"  ※ 세액을 먼저 절사하는 방식이면: 세액 {won(b_tax)}, 공급가액 {won(b_supply)}")
        print("    → 실제 세금계산서에 기재된 금액을 우선한다.")


def vat_add(supply: int, rate: Decimal):
    s = D(supply)
    tax = (s * rate).to_integral_value(rounding=ROUND_DOWN)
    print(f"공급가액 {won(s)} × {pct(rate)} = 부가세 {won(tax)} (원 미만 절사)")
    print(f"합계 = {won(s + tax)}")


# ---------- 원천징수 ----------
def other_income_tax(amount: Decimal, expense_rate: Decimal, threshold: Decimal, rate: Decimal):
    expense = (amount * expense_rate).to_integral_value(rounding=ROUND_DOWN)
    income = amount - expense
    if income <= threshold:
        return expense, income, D(0), D(0), True
    it = floor_to(income * rate, 10)
    lt = floor_to(it * D("0.1"), 10)
    return expense, income, it, lt, False


def other_income(a):
    amt = D(a.amount)
    expense, income, it, lt, exempt = other_income_tax(amt, D(a.expense_rate), D(a.threshold), D(a.rate))
    print(f"기타소득 지급액 {won(amt)}")
    print(f"  필요경비 = 지급액 × {pct(D(a.expense_rate))} = {won(expense)}")
    print(f"  기타소득금액 = {won(income)}")
    if exempt:
        print(f"  기타소득금액이 과세최저한 {won(D(a.threshold))} 이하 → 원천징수 없음")
    else:
        print(f"  소득세 = {won(income)} × {pct(D(a.rate))} (10원 미만 절사) = {won(it)}")
        print(f"  지방소득세 = 소득세 × 10% (10원 미만 절사) = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(amt - it - lt)}")


def business_income_tax(amount: Decimal, rate: Decimal):
    it = floor_to(amount * rate, 10)
    lt = floor_to(it * D("0.1"), 10)
    return it, lt


def business_income(a):
    amt = D(a.amount)
    it, lt = business_income_tax(amt, D(a.rate))
    print(f"사업소득 지급액 {won(amt)}")
    print(f"  소득세 = 지급액 × {pct(D(a.rate))} (10원 미만 절사) = {won(it)}")
    print(f"  지방소득세 = 소득세 × 10% (10원 미만 절사) = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(amt - it - lt)}")


def daily_wage(a):
    daily, days = D(a.daily), int(a.days)
    taxable = max(D(0), daily - D(a.deduction)) * days
    calc = taxable * D(a.rate)
    credit = calc * D(a.credit)
    it = floor_to(calc - credit, 10)
    small = it < D(a.min_tax)
    if small:
        it = D(0)
    lt = floor_to(it * D("0.1"), 10)
    gross = daily * days
    print(f"일용근로 일급 {won(daily)} × {days}일 = 총지급 {won(gross)}")
    print(f"  과세표준 = (일급 − {won(D(a.deduction))}) × {days}일 = {won(taxable)}")
    print(f"  산출세액 = 과세표준 × {pct(D(a.rate))} = {won(calc)}")
    print(f"  세액공제 = 산출세액 × {pct(D(a.credit))} = {won(credit)}")
    if small:
        print(f"  결정세액이 소액부징수 기준({won(D(a.min_tax))}) 미만 → 징수하지 않음")
    else:
        print(f"  소득세 (10원 미만 절사) = {won(it)}, 지방소득세 = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(gross - it - lt)}")
    print("  ※ 소액부징수는 지급 건(지급일) 단위로 판단한다. 일별로 나눠 지급하면 결과가 달라질 수 있다.")


def gross_up(a):
    target = D(a.net)

    def net_of(g: Decimal) -> Decimal:
        if a.type == "other":
            _, _, it, lt, _ = other_income_tax(g, D(a.expense_rate), D(a.threshold), D("0.2"))
        else:
            it, lt = business_income_tax(g, D("0.03"))
        return g - it - lt

    eff = D("0.088") if a.type == "other" else D("0.033")
    g = (target / (1 - eff)).to_integral_value(rounding=ROUND_DOWN) - 50
    g = max(g, target)
    while net_of(g) < target:
        g += 1
    label = "기타소득" if a.type == "other" else "사업소득"
    print(f"세후 {won(target)}을 지급하려면 ({label})")
    print(f"  세전 지급액 = {won(g)}  → 원천징수 {won(g - net_of(g))}, 실지급 {won(net_of(g))}")
    rounded = D(math.ceil(g / 1000) * 1000)
    print(f"  (천원 단위로 올리면 {won(rounded)} → 실지급 {won(net_of(rounded))})")


# ---------- 비율 ----------
def parse_pairs(items):
    out = {}
    for s in items or []:
        if "=" not in s:
            sys.exit(f"형식 오류: {s!r} (이름=값)")
        k, v = s.split("=", 1)
        out[k.strip()] = D(v.replace(",", "").strip())
    return out


def ratio(a):
    items = parse_pairs(a.items)
    caps, mins = parse_pairs(a.cap), parse_pairs(a.min)
    total = sum(items.values())
    if total == 0:
        sys.exit("합계가 0입니다.")
    print(f"합계 {won(total)}")
    width = max(len(k) for k in items)
    for k, v in items.items():
        r = v / total
        flag = ""
        if k in caps and r > caps[k]:
            over = v - (caps[k] * total).to_integral_value(rounding=ROUND_DOWN)
            flag = f"  ⚠ 상한 {pct(caps[k])} 초과 ({won(over)} 초과)"
        if k in mins and r < mins[k]:
            short = (mins[k] * total).to_integral_value(rounding=ROUND_HALF_UP) - v
            flag += f"  ⚠ 하한 {pct(mins[k])} 미달 ({won(short)} 부족)"
        print(f"  {k:<{width}} {won(v):>18} {r * 100:7.2f}%{flag}")
    for k in list(caps) + list(mins):
        if k not in items:
            print(f"  ※ '{k}' 항목이 입력에 없습니다.")
    print("  ※ 비율의 분모(총사업비·직접비·보조금 등)는 지침 정의를 확인할 것. 여기서는 입력 합계 기준.")


# ---------- 지원액·자부담 ----------
def _rate(x: str, name: str) -> Decimal:
    r = D(x)
    if not (D(0) < r <= D(1)):
        sys.exit(f"{name} 은(는) 0 초과 1 이하여야 합니다 (예: 60% → 0.6). 입력값: {x}")
    return r


def subsidy(a):
    E = D(a.eligible)
    if E < 0:
        sys.exit("인정비용은 0 이상이어야 합니다.")
    r = _rate(a.rate, "--rate")
    raw = (E * r).to_integral_value(rounding=ROUND_DOWN)
    grant = min(raw, D(a.cap)) if a.cap is not None else raw
    own = E - grant
    dis = D(a.disallowed or 0)
    print(f"인정비용 {won(E)}, 보조율 {pct(r)}" + (f", 지원 상한 {won(D(a.cap))}" if a.cap is not None else ""))
    print(f"  인정비용 × 보조율 = {won(raw)} (원 미만 절사)")
    if a.cap is not None:
        print(f"  지원액 = min({won(raw)}, {won(D(a.cap))}) = {won(grant)}" + ("  ← 상한 적용" if grant < raw else ""))
    else:
        print(f"  지원액 = {won(grant)}")
    print(f"  인정비용 기준 자부담 = {won(E)} − {won(grant)} = {won(own)}")
    if dis:
        print(f"  불인정액 {won(dis)} 은 전액 수행기관 부담")
        print(f"  실제 수행기관 부담 = {won(own)} + {won(dis)} = {won(own + dis)}")
        print(f"  검산: 총지출 {won(E + dis)} = 지원액 {won(grant)} + 실제 부담 {won(own + dis)}")
    print("  ※ 보조율의 분모가 인정비용인지, 상한이 사업 전체에 걸리는지 항목별인지 지침에서 확인할 것.")


def grant_base(a):
    G = D(a.grant)
    r = _rate(a.rate, "--rate")
    total = (G / r).to_integral_value(rounding=ROUND_HALF_UP)
    print(f"보조금 {won(G)}, 비율 {pct(r)}")
    print(f"  [해석 A] 보조금이 총사업비의 {pct(r)}이면")
    print(f"     총사업비 = {won(G)} ÷ {r} = {won(total)}, 자부담 = {won(total - G)} (총사업비의 {pct(1 - r)})")
    if a.own_rate is not None:
        q = D(a.own_rate)
        own = (G * q).to_integral_value(rounding=ROUND_HALF_UP)
        print(f"  [해석 B] 자부담이 보조금의 {pct(q)}이면")
        print(f"     자부담 = {won(G)} × {q} = {won(own)}, 총사업비 = {won(G + own)}")
    else:
        q = 1 - r
        own = (G * q).to_integral_value(rounding=ROUND_HALF_UP)
        print(f"  [해석 B] '자부담 {pct(q)}'를 보조금 대비로 읽으면")
        print(f"     자부담 = {won(G)} × {q} = {won(own)}, 총사업비 = {won(G + own)}")
    print("  ※ 공고의 비율이 '총사업비 대비'인지 '보조금 대비'인지에 따라 결과가 다르다. 원문 표현을 확인할 것.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("vat-split"); p.add_argument("total", type=int); p.add_argument("--rate", default="0.1")
    p = sub.add_parser("vat-add"); p.add_argument("supply", type=int); p.add_argument("--rate", default="0.1")

    p = sub.add_parser("other-income")
    p.add_argument("amount", type=int)
    p.add_argument("--expense-rate", default="0.6", help="필요경비율 (60%% 의제 대상이 아니면 0)")
    p.add_argument("--threshold", default="50000", help="과세최저한 (건별 기타소득금액)")
    p.add_argument("--rate", default="0.2")

    p = sub.add_parser("business-income"); p.add_argument("amount", type=int); p.add_argument("--rate", default="0.03")

    p = sub.add_parser("daily-wage")
    p.add_argument("daily", type=int)
    p.add_argument("--days", type=int, default=1)
    p.add_argument("--deduction", default="150000", help="1일 근로소득공제")
    p.add_argument("--rate", default="0.06")
    p.add_argument("--credit", default="0.55", help="근로소득세액공제율")
    p.add_argument("--min-tax", default="1000", help="소액부징수 기준")

    p = sub.add_parser("gross-up")
    p.add_argument("net", type=int)
    p.add_argument("--type", choices=["other", "business"], default="other")
    p.add_argument("--expense-rate", default="0.6")
    p.add_argument("--threshold", default="50000")

    p = sub.add_parser("ratio")
    p.add_argument("items", nargs="+", help="이름=금액 ...")
    p.add_argument("--cap", nargs="*", help="이름=상한비율 (0.4 = 40%%)")
    p.add_argument("--min", nargs="*", help="이름=하한비율")

    p = sub.add_parser("subsidy")
    p.add_argument("eligible", type=int, help="인정비용")
    p.add_argument("--rate", required=True, help="보조율 (0.6 = 60%%)")
    p.add_argument("--cap", type=int, help="지원 상한액")
    p.add_argument("--disallowed", type=int, default=0, help="불인정액")

    p = sub.add_parser("grant-base")
    p.add_argument("grant", type=int, help="보조금")
    p.add_argument("--rate", required=True, help="보조금이 총사업비에서 차지하는 비율")
    p.add_argument("--own-rate", help="보조금 대비 자부담 비율 (해석 B에 직접 지정)")

    a = ap.parse_args()
    if a.cmd == "vat-split":
        vat_split(a.total, D(a.rate))
    elif a.cmd == "vat-add":
        vat_add(a.supply, D(a.rate))
    elif a.cmd == "other-income":
        other_income(a)
    elif a.cmd == "business-income":
        business_income(a)
    elif a.cmd == "daily-wage":
        daily_wage(a)
    elif a.cmd == "gross-up":
        gross_up(a)
    elif a.cmd == "ratio":
        ratio(a)
    elif a.cmd == "subsidy":
        subsidy(a)
    elif a.cmd == "grant-base":
        grant_base(a)


if __name__ == "__main__":
    main()
