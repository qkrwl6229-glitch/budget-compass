"""lookup.py 와 수록 규정(laws/) 테스트.

실행: python3 -m unittest discover -s tests -v
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugins/budget-compass/skills/budget-compass"
LOOKUP = SKILL / "scripts/lookup.py"
LAWS = SKILL / "laws"


def run(*args):
    p = subprocess.run([sys.executable, str(LOOKUP), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class LawFiles(unittest.TestCase):
    def test_index_matches_files(self):
        index = json.loads((LAWS / "index.json").read_text(encoding="utf-8"))["laws"]
        sources = json.loads((Path(__file__).resolve().parents[1] / "tools/law_sources.json")
                             .read_text(encoding="utf-8"))["sources"]
        self.assertEqual([x["id"] for x in index], [s["id"] for s in sources])
        for meta in index:
            with self.subTest(law=meta["id"]):
                text = (LAWS / f"{meta['id']}.md").read_text(encoding="utf-8")
                heads = re.findall(r"^## (제\d+조(?:의\d+)?)", text, re.M)
                self.assertEqual(len(heads), len(meta["articles"]))
                self.assertRegex(meta["effective"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(meta["url"].startswith("https://www.law.go.kr/"))
                self.assertIn(f"- 시행일: {meta['effective']}", text)
                self.assertNotIn("부칙 <", text.split("\n## ", 1)[0])


class Lookup(unittest.TestCase):
    def check(self, args, *expected, code=0):
        c, out = run(*args)
        self.assertEqual(c, code, out)
        for e in expected:
            self.assertIn(e, out, f"{args}: '{e}' 없음\n{out[:1500]}")
        return out

    def test_list(self):
        out = self.check(["--list"], "subsidy-act", "rnd-cost-standard", "vat-act")
        self.assertGreaterEqual(out.count("\n"), 15)

    def test_article(self):
        self.check(["--law", "income-tax-act", "--article", "129"], "제129조(원천징수세율)", "100분의 3")
        self.check(["--law", "local-tax-act", "--article", "제103조의13"], "제103조의13")
        self.check(["--law", "vat-act", "--article", "29"], "직접 깎아 주는 금액", "시행 2026-01-02")

    def test_search(self):
        self.check(["회의비", "식비", "--law", "rnd-cost-standard"], "제25조(연구활동비 공통 사용기준)", "제25조의2")
        self.check(["에누리"], "부가가치세법」 제29조")
        self.check(["장비", "사전", "승인", "--law", "rnd-cost-standard"], "제73조(사전 승인 대상)")

    def test_citation_metadata(self):
        out = self.check(["--law", "rnd-cost-standard", "--article", "21"], "과학기술정보통신부고시", "수집 ")
        self.assertRegex(out, r"시행 \d{4}-\d{2}-\d{2}")

    def test_errors(self):
        self.check(["--law", "nope", "--article", "1"], "입력 오류", code=2)
        self.check(["--law", "vat-act", "--article", "abc"], "입력 오류", code=2)
        self.check(["--article", "29"], "입력 오류", code=2)
        self.check(["--law", "vat-act", "--article", "999"], "수록되어 있지 않습니다", code=2)


if __name__ == "__main__":
    unittest.main()
