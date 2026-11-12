"""calc.py 회귀 테스트 (표준 라이브러리 unittest).

실행: python3 -m unittest discover -s tests -v
"""
import importlib.util
import subprocess
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

CALC = Path(__file__).resolve().parents[1] / "plugins/budget-compass/skills/budget-compass/scripts/calc.py"
spec = importlib.util.spec_from_file_location("calc", CALC)
calc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calc)


def run(*args):
    p = subprocess.run([sys.executable, str(CALC), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class Outputs(unittest.TestCase):
    def check(self, args, *expected):
        code, out = run(*args)
        self.assertEqual(code, 0, out)
        for e in expected:
            self.assertIn(e, out, f"{args}: '{e}' 없음\n{out}")

    def test_vat(self):
        self.check(["vat-split", "1100000"], "1,000,000원", "100,000원")
        self.check(["vat-split", "3300000"], "3,000,000원", "300,000원")
        self.check(["vat-add", "1000000"], "부가세 100,000원", "합계 = 1,100,000원")

    def test_withholding(self):
        self.check(["other-income", "500000"], "원천징수 합계 44,000원", "실지급액 456,000원")
        self.check(["other-income", "3000000"], "원천징수 합계 264,000원")
        self.check(["business-income", "3000000"], "원천징수 합계 99,000원")
        self.check(["other-income", "125000"], "원천징수 없음", "원천징수 합계 0원")
        self.check(["other-income", "125001"], "원천징수 합계 11,000원")
        # 인적용역 사업소득은 소액부징수 미적용 (2024. 7. 1. 이후)
        self.check(["business-income", "30000"], "원천징수 합계 990원")

    def test_daily_wage(self):
        self.check(["daily-wage", "180000"], "징수하지 않음", "원천징수 합계 0원")
        self.check(["daily-wage", "200000", "--days", "5"], "원천징수 합계 7,420원")

    def test_gross_up_review_cases(self):
        self.check(["gross-up", "125000", "--type", "other"], "최소 세전 지급액 = 125,000원")
        self.check(["gross-up", "1000000", "--type", "other", "--expense-rate", "1"], "최소 세전 지급액 = 1,000,000원")
        self.check(["gross-up", "967000", "--type", "business"], "실수령 967,000원")

    def test_subsidy_and_grant_base(self):
        self.check(["subsidy", "5000000", "--rate", "0.6", "--cap", "2500000", "--disallowed", "100000"],
                   "= 2,500,000원  ← 상한 적용", "실제 수행기관 부담 = 2,500,000원 + 100,000원 = 2,600,000원")
        self.check(["grant-base", "30000000", "--rate", "0.8"], "37,500,000원", "총사업비 = 36,000,000원")

    def test_ratio(self):
        self.check(["ratio", "인건비=180,000,000", "운영비=120000000", "--cap", "인건비=0.4"], "상한 40% 초과")
        self.check(["ratio", "인건비=100", "인건비=200", "운영비=100", "--sum-duplicates"], "합계 400원")


class InputErrors(unittest.TestCase):
    CASES = [
        ["subsidy", "1000", "--rate", "0.5", "--cap", "-1"],
        ["subsidy", "1000", "--rate", "0.5", "--disallowed", "-300"],
        ["subsidy", "1000", "--rate", "60"],
        ["vat-split", "110", "--rate", "-1"],
        ["vat-split", "abc"],
        ["vat-split", "100.5"],
        ["ratio", "인건비=100", "--cap", "인건비=NaN"],
        ["ratio", "인건비=100", "--cap", "인건비=Infinity"],
        ["ratio", "인건비=100", "인건비=200", "운영비=100"],
        ["ratio", "인건비=100", "--cap", "운영비=0.4"],
        ["ratio", "인건비=0"],
        ["grant-base", "1000", "--rate", "0.8", "--own-rate", "-0.2"],
        ["grant-base", "0", "--rate", "0.8"],
        ["daily-wage", "200000", "--days", "-1"],
        ["daily-wage", "-200000"],
        ["other-income", "500000", "--expense-rate", "1.5"],
        ["gross-up", "-1"],
    ]

    def test_rejected(self):
        for args in self.CASES:
            with self.subTest(args=args):
                code, out = run(*args)
                self.assertEqual(code, 2, f"{args} 는 입력 오류여야 함\n{out}")
                self.assertIn("입력 오류", out)
                self.assertNotIn("Traceback", out)


class GrossUpExhaustive(unittest.TestCase):
    """역산 결과를 전수 탐색(브루트포스)과 비교한다."""

    def brute(self, target, tax_of, upper):
        for g in range(target, upper + 1):
            if g - tax_of(D(g)) == target:
                return g
        return None

    def test_matches_brute_force(self):
        targets = [1, 9990, 50000, 114001, 125000, 125010, 125020, 300000, 456000, 999990, 1234567, 2999999]
        configs = []
        for er in ("0.6", "0.8", "0"):
            er_d, th, tr = D(er), D(50000), D("0.2")
            configs.append((f"other er={er}", (1 - er_d) * tr * D("1.1"),
                            lambda g, er_d=er_d, th=th, tr=tr: sum(calc.other_income_tax(g, er_d, th, tr)[2:4])))
        configs.append(("business", D("0.033"), lambda g: sum(calc.business_income_tax(g, D("0.03")))))
        for name, eff, tax_of in configs:
            for t in targets:
                with self.subTest(cfg=name, target=t):
                    upper = int(t / (1 - float(eff))) + 500
                    expect = self.brute(t, tax_of, upper)
                    exact, _, _ = calc.solve_gross_up(D(t), tax_of, eff)
                    got = int(exact[0]) if exact else None
                    self.assertEqual(got, expect)


if __name__ == "__main__":
    unittest.main()
