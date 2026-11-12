#!/usr/bin/env python3
"""사업비 나침반 계산기 (Python 표준 라이브러리만 사용).

세율·공제액 기본값은 계산 편의를 위한 값이다. 지급일과 소득 유형에 맞는 기준을 확인한 뒤,
다르면 옵션으로 바꿔 넣는다. 이 계산기는 세무 판정(소득 구분·과세 여부)을 하지 않는다.

  vat-split        합계금액(부가세 포함) → 공급가액·부가세
  vat-add          공급가액 → 부가세·합계
  other-income     기타소득 원천징수 (예: 필요경비 60% 적용 대상인 일시적 강연료)
  business-income  거주자 인적용역 사업소득 원천징수 (3% + 지방소득세)
  daily-wage       일용근로소득 원천징수
  gross-up         세후 실수령액 → 세전 지급액 (기타소득·사업소득)
  subsidy          인정비용·보조율·상한·불인정액 → 지원액·자부담
  grant-base       보조금과 비율 → 총사업비·자부담 (두 가지 해석)
  ratio            비목별 금액 → 비율, 상한/하한 점검

예:
  python calc.py vat-split 1100000
  python calc.py other-income 500000
  python calc.py business-income 1000000
  python calc.py daily-wage 200000 --days 5
  python calc.py gross-up 456000 --type other
  python calc.py subsidy 5000000 --rate 0.6 --cap 2500000 --disallowed 100000
  python calc.py grant-base 30000000 --rate 0.8
  python calc.py ratio 인건비=180000000 운영비=120000000 자부담=100000000 --cap 인건비=0.4 --min 자부담=0.2

입력이 잘못되면 '입력 오류'를 출력하고 종료 코드 2로 끝난다.
"""
import argparse
import sys
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

D = Decimal


class InputError(ValueError):
    """사용자 입력 오류 (계산기 버그와 구분)."""


# ---------- 공통 ----------
def won(x) -> str:
    return f"{int(x):,}원"


def pct(r) -> str:
    """0.4 → '40%', 0.033 → '3.3%'"""
    return f"{(D(r) * 100).normalize():f}%"


def floor_to(x: Decimal, unit: int) -> Decimal:
    """unit 원 미만 절사 (예: unit=10 → 10원 미만 절사)."""
    return (x / unit).to_integral_value(rounding=ROUND_DOWN) * unit


def to_dec(raw, name: str) -> Decimal:
    try:
        v = D(str(raw).replace(",", "").strip())
    except InvalidOperation:
        raise InputError(f"{name}: 숫자가 아닙니다 ({raw!r})")
    if not v.is_finite():
        raise InputError(f"{name}: 유한한 숫자여야 합니다 ({raw!r})")
    return v


def money(raw, name: str, *, positive=False) -> Decimal:
    v = to_dec(raw, name)
    if v != v.to_integral_value():
        raise InputError(f"{name}: 원 단위 정수여야 합니다 ({raw!r})")
    if v < 0 or (positive and v == 0):
        raise InputError(f"{name}: {'0보다 커야' if positive else '0 이상이어야'} 합니다 ({raw!r})")
    return v


def rate(raw, name: str, lo=D(0), hi=D(1), *, lo_open=False) -> Decimal:
    v = to_dec(raw, name)
    if v < lo or v > hi or (lo_open and v == lo):
        rng = f"{'(' if lo_open else '['}{lo}, {hi}]"
        raise InputError(f"{name}: 범위 {rng} 밖입니다 ({raw!r}). 60%는 0.6으로 입력")
    return v


# ---------- 부가세 ----------
def vat_split(a):
    t = money(a.total, "합계금액")
    r = rate(a.rate, "--rate")
    a_supply = (t / (1 + r)).to_integral_value(rounding=ROUND_HALF_UP)
    a_tax = t - a_supply
    b_tax = (t * r / (1 + r)).to_integral_value(rounding=ROUND_DOWN)
    b_supply = t - b_tax
    print(f"합계(공급대가) {won(t)}, 세율 {pct(r)}")
    print(f"  공급가액 = 합계 ÷ {1 + r} (원 미만 반올림) = {won(a_supply)}")
    print(f"  부가세   = 합계 − 공급가액 = {won(a_tax)}")
    if (a_supply, a_tax) != (b_supply, b_tax):
        print(f"  ※ 세액을 먼저 절사하는 방식이면: 세액 {won(b_tax)}, 공급가액 {won(b_supply)}")
        print("    → 실제 세금계산서에 기재된 금액을 우선한다.")


def vat_add(a):
    s = money(a.supply, "공급가액")
    r = rate(a.rate, "--rate")
    tax = (s * r).to_integral_value(rounding=ROUND_DOWN)
    print(f"공급가액 {won(s)} × {pct(r)} = 부가세 {won(tax)} (원 미만 절사)")
    print(f"합계 = {won(s + tax)}")


# ---------- 원천징수 ----------
OTHER_TAX_RATE = "0.2"
BUSINESS_TAX_RATE = "0.03"


def other_income_tax(amount: Decimal, expense_rate: Decimal, threshold: Decimal, tax_rate: Decimal):
    """기타소득 원천징수. (필요경비, 기타소득금액, 소득세, 지방소득세, 과세최저한 해당 여부)"""
    expense = (amount * expense_rate).to_integral_value(rounding=ROUND_DOWN)
    income = amount - expense
    if income <= threshold:
        return expense, income, D(0), D(0), True
    it = floor_to(income * tax_rate, 10)
    lt = floor_to(it * D("0.1"), 10)
    return expense, income, it, lt, False


def business_income_tax(amount: Decimal, tax_rate: Decimal):
    """거주자 인적용역 사업소득: 2024. 7. 1. 이후 지급분은 1,000원 미만도 징수 (소액부징수 미적용)."""
    it = floor_to(amount * tax_rate, 10)
    lt = floor_to(it * D("0.1"), 10)
    return it, lt


def other_params(a):
    return (rate(a.expense_rate, "--expense-rate"), money(a.threshold, "--threshold"),
            rate(a.rate or OTHER_TAX_RATE, "--rate"))


def other_income(a):
    amt = money(a.amount, "지급액")
    er, th, tr = other_params(a)
    expense, income, it, lt, exempt = other_income_tax(amt, er, th, tr)
    print(f"기타소득 지급액 {won(amt)}  (가정: 거주자 개인, 세전 약정, 필요경비율 {pct(er)} 적용 대상)")
    print(f"  필요경비 = 지급액 × {pct(er)} = {won(expense)}")
    print(f"  기타소득금액 = {won(income)}")
    if exempt:
        print(f"  기타소득금액이 과세최저한 {won(th)} 이하 → 원천징수 없음")
    else:
        print(f"  소득세 = 기타소득금액 × {pct(tr)} (10원 미만 절사) = {won(it)}")
        print(f"  지방소득세 = 소득세 × 10% (10원 미만 절사) = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(amt - it - lt)}")
    print("  ※ 필요경비율·과세최저한은 소득 유형과 지급일 기준으로 확인할 것.")


def business_income(a):
    amt = money(a.amount, "지급액")
    tr = rate(a.rate, "--rate")
    it, lt = business_income_tax(amt, tr)
    print(f"사업소득 지급액 {won(amt)}  (가정: 거주자 개인의 인적용역, 세전 약정)")
    print(f"  소득세 = 지급액 × {pct(tr)} (10원 미만 절사) = {won(it)}")
    print(f"  지방소득세 = 소득세 × 10% (10원 미만 절사) = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(amt - it - lt)}")
    print("  ※ 2024. 7. 1. 이후 지급분은 원천징수세액이 1,000원 미만이어도 징수한다(국세청 안내).")


def daily_wage(a):
    daily = money(a.daily, "일급")
    if a.days < 1:
        raise InputError(f"--days: 1 이상이어야 합니다 ({a.days})")
    days = a.days
    ded = money(a.deduction, "--deduction")
    tr = rate(a.rate, "--rate")
    cr = rate(a.credit, "--credit")
    min_tax = money(a.min_tax, "--min-tax")
    taxable = max(D(0), daily - ded) * days
    calc = taxable * tr
    credit = calc * cr
    it = floor_to(calc - credit, 10)
    small = it < min_tax
    if small:
        it = D(0)
    lt = floor_to(it * D("0.1"), 10)
    gross = daily * days
    print(f"일용근로 일급 {won(daily)} × {days}일 = 총지급 {won(gross)}  (한 사람에게 한 번에 지급 가정)")
    print(f"  과세표준 = (일급 − {won(ded)}) × {days}일 = {won(taxable)}")
    print(f"  산출세액 = 과세표준 × {pct(tr)} = {won(calc)}")
    print(f"  세액공제 = 산출세액 × {pct(cr)} = {won(credit)}")
    if small:
        print(f"  결정세액이 소액부징수 기준({won(min_tax)}) 미만 → 징수하지 않음")
    else:
        print(f"  소득세 (10원 미만 절사) = {won(it)}, 지방소득세 = {won(lt)}")
    print(f"  원천징수 합계 {won(it + lt)} / 실지급액 {won(gross - it - lt)}")
    print("  ※ 일당을 한꺼번에 지급하면 소득자별 지급액의 세액 합계로 소액부징수를 판단한다(국세청 안내).")


def solve_gross_up(target: Decimal, tax_of, eff: Decimal):
    """세후 target 을 만드는 세전액 후보를 정방향 재검산으로 찾는다.

    세액은 10원 절사·과세최저한 때문에 세전액에 대해 단조증가하지 않는다. 그래서
    (1) 세금이 없는 해 g = target, (2) 선형 근사해 주변 창을 모두 재검산한다.
    세액은 선형식과 수십 원 이내로 차이 나므로 창 안에 모든 해가 들어온다.
    반환: (정확히 일치하는 세전액 목록, 목표보다 많은 최소안, 목표보다 적은 최대안)
    """
    approx = (target / (1 - eff)).to_integral_value(rounding=ROUND_DOWN)
    window = 200
    lo, hi = max(target, approx - window), approx + window
    cands = sorted({target} | {D(g) for g in range(int(lo), int(hi) + 1)})
    net = {g: g - tax_of(g) for g in cands}
    exact = [g for g in cands if net[g] == target]
    above = [g for g in cands if net[g] > target]
    below = [g for g in cands if net[g] < target]
    return exact, (above[0] if above else None), (below[-1] if below else None)


def gross_up(a):
    target = money(a.net, "세후 금액")
    if a.type == "other":
        er, th, tr = other_params(a)
        eff = (1 - er) * tr * D("1.1")

        def tax_of(g):
            _, _, it, lt, _ = other_income_tax(g, er, th, tr)
            return it + lt
        label = f"기타소득, 필요경비 {pct(er)}, 과세최저한 {won(th)}"
    else:
        tr = rate(a.rate or BUSINESS_TAX_RATE, "--rate")
        eff = tr * D("1.1")

        def tax_of(g):
            it, lt = business_income_tax(g, tr)
            return it + lt
        label = f"사업소득 {pct(tr)} + 지방소득세"
    if eff >= 1:
        raise InputError("실효세율이 100% 이상이라 역산할 수 없습니다.")

    exact, above, below = solve_gross_up(target, tax_of, eff)
    print(f"세후 {won(target)} 지급 → 세전 역산  [{label}, 가정: 거주자 개인]")
    if exact:
        g = exact[0]
        print(f"  최소 세전 지급액 = {won(g)}  → 원천징수 {won(tax_of(g))}, 실수령 {won(g - tax_of(g))} (재검산 일치)")
        if len(exact) > 1:
            print(f"  ※ 같은 실수령액이 되는 세전액이 여러 개: {won(exact[0])} ~ {won(exact[-1])} 중 {len(exact)}개")
    else:
        print("  정확히 일치하는 세전액이 없습니다 (10원 절사 때문).")
        if above is not None:
            print(f"  실수령이 목표보다 조금 많은 최소안: 세전 {won(above)} → 실수령 {won(above - tax_of(above))}")
        if below is not None:
            print(f"  실수령이 목표보다 조금 적은 최대안: 세전 {won(below)} → 실수령 {won(below - tax_of(below))}")
    print("  ※ 세후 약정은 지급 전에 소득 구분을 확인하고, 계약서에는 세전 금액을 적을 것.")


# ---------- 지원액·자부담 ----------
def subsidy(a):
    E = money(a.eligible, "인정비용")
    r = rate(a.rate, "--rate", lo_open=True)
    cap = money(a.cap, "--cap") if a.cap is not None else None
    dis = money(a.disallowed, "--disallowed")
    raw = (E * r).to_integral_value(rounding=ROUND_DOWN)
    grant = min(raw, cap) if cap is not None else raw
    own = E - grant
    print(f"인정비용 {won(E)}, 보조율 {pct(r)}" + (f", 지원 상한 {won(cap)}" if cap is not None else ""))
    print(f"  인정비용 × 보조율 = {won(raw)} (원 미만 절사)")
    if cap is not None:
        print(f"  지원액 = min({won(raw)}, {won(cap)}) = {won(grant)}" + ("  ← 상한 적용" if grant < raw else ""))
    else:
        print(f"  지원액 = {won(grant)}")
    print(f"  인정비용 기준 자부담 = {won(E)} − {won(grant)} = {won(own)}")
    if dis:
        print(f"  불인정액 {won(dis)} 은 전액 수행기관 부담")
        print(f"  실제 수행기관 부담 = {won(own)} + {won(dis)} = {won(own + dis)}")
    print(f"  검산: 총지출 {won(E + dis)} = 지원액 {won(grant)} + 수행기관 부담 {won(own + dis)}")
    print("  ※ 보조율의 분모가 인정비용인지, 상한이 사업 전체에 걸리는지 항목별인지 지침에서 확인할 것.")


def grant_base(a):
    G = money(a.grant, "보조금", positive=True)
    r = rate(a.rate, "--rate", lo_open=True)
    total = (G / r).to_integral_value(rounding=ROUND_HALF_UP)
    print(f"보조금 {won(G)}, 비율 {pct(r)}")
    print(f"  [해석 A] 보조금이 총사업비의 {pct(r)}이면")
    print(f"     총사업비 = {won(G)} ÷ {r} = {won(total)}, 자부담 = {won(total - G)} (총사업비의 {pct(1 - r)})")
    if a.own_rate is not None:
        q = rate(a.own_rate, "--own-rate", hi=D(10))
        label = f"자부담이 보조금의 {pct(q)}이면"
    else:
        q = 1 - r
        label = f"'자부담 {pct(q)}'를 보조금 대비로 읽으면"
    own = (G * q).to_integral_value(rounding=ROUND_HALF_UP)
    print(f"  [해석 B] {label}")
    print(f"     자부담 = {won(G)} × {q} = {won(own)}, 총사업비 = {won(G + own)}")
    print("  ※ 공고의 비율이 '총사업비 대비'인지 '보조금 대비'인지에 따라 결과가 다르다. 원문 표현을 확인할 것.")


# ---------- 비율 ----------
def parse_pairs(items, what, *, as_rate=False, sum_dupes=False):
    out = {}
    for s in items or []:
        if "=" not in s:
            raise InputError(f"{what}: 형식은 이름=값 입니다 ({s!r})")
        k, v = (x.strip() for x in s.split("=", 1))
        if not k:
            raise InputError(f"{what}: 이름이 비었습니다 ({s!r})")
        val = rate(v, f"{what} {k}") if as_rate else money(v, f"{what} {k}")
        if k in out:
            if not sum_dupes:
                raise InputError(f"{what}: '{k}' 가 중복 입력되었습니다. 합산하려면 --sum-duplicates")
            out[k] += val
        else:
            out[k] = val
    return out


def ratio(a):
    items = parse_pairs(a.items, "항목", sum_dupes=a.sum_duplicates)
    caps = parse_pairs(a.cap, "--cap", as_rate=True)
    mins = parse_pairs(a.min, "--min", as_rate=True)
    unknown = [k for k in list(caps) + list(mins) if k not in items]
    if unknown:
        raise InputError(f"상한/하한에 지정한 항목이 입력에 없습니다: {', '.join(unknown)}")
    total = sum(items.values())
    if total == 0:
        raise InputError("합계가 0입니다.")
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
    print("  ※ 비율의 분모(총사업비·직접비·보조금 등)는 지침 정의를 확인할 것. 여기서는 입력 합계 기준.")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("vat-split"); p.add_argument("total"); p.add_argument("--rate", default="0.1")
    p.set_defaults(fn=vat_split)
    p = sub.add_parser("vat-add"); p.add_argument("supply"); p.add_argument("--rate", default="0.1")
    p.set_defaults(fn=vat_add)

    def other_opts(p, rate_default):
        p.add_argument("--expense-rate", default="0.6", help="필요경비율 (해당 유형이 아니면 0)")
        p.add_argument("--threshold", default="50000", help="과세최저한 (건별 기타소득금액)")
        p.add_argument("--rate", default=rate_default, help="소득세율 (기타소득 0.2 / 사업소득 0.03)")

    p = sub.add_parser("other-income"); p.add_argument("amount"); other_opts(p, OTHER_TAX_RATE)
    p.set_defaults(fn=other_income)
    p = sub.add_parser("business-income"); p.add_argument("amount"); p.add_argument("--rate", default=BUSINESS_TAX_RATE)
    p.set_defaults(fn=business_income)

    p = sub.add_parser("daily-wage")
    p.add_argument("daily")
    p.add_argument("--days", type=int, default=1)
    p.add_argument("--deduction", default="150000", help="1일 근로소득공제")
    p.add_argument("--rate", default="0.06")
    p.add_argument("--credit", default="0.55", help="근로소득세액공제율")
    p.add_argument("--min-tax", default="1000", help="소액부징수 기준")
    p.set_defaults(fn=daily_wage)

    p = sub.add_parser("gross-up")
    p.add_argument("net")
    p.add_argument("--type", choices=["other", "business"], default="other")
    other_opts(p, None)
    p.set_defaults(fn=gross_up)

    p = sub.add_parser("subsidy")
    p.add_argument("eligible", help="인정비용")
    p.add_argument("--rate", required=True, help="보조율 (0.6 = 60%%)")
    p.add_argument("--cap", help="지원 상한액")
    p.add_argument("--disallowed", default="0", help="불인정액")
    p.set_defaults(fn=subsidy)

    p = sub.add_parser("grant-base")
    p.add_argument("grant", help="보조금")
    p.add_argument("--rate", required=True, help="보조금이 총사업비에서 차지하는 비율")
    p.add_argument("--own-rate", help="보조금 대비 자부담 비율 (해석 B에 직접 지정)")
    p.set_defaults(fn=grant_base)

    p = sub.add_parser("ratio")
    p.add_argument("items", nargs="+", help="이름=금액 ...")
    p.add_argument("--cap", nargs="*", help="이름=상한비율 (0.4 = 40%%)")
    p.add_argument("--min", nargs="*", help="이름=하한비율")
    p.add_argument("--sum-duplicates", action="store_true", help="같은 이름을 합산")
    p.set_defaults(fn=ratio)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.fn(a)
    except InputError as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
