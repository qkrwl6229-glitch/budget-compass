"""스크립트 없이 색인만으로 질문 단서 → 주제 파일 → 조문 파일에 도달하는지 확인한다.

실행: python3 -m unittest discover -s tests -v
"""
import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugins/budget-compass/skills/budget-compass"
INDEX = SKILL / "references/index.md"

# (질문 단서, 도착해야 할 주제 파일, 그 주제 파일이 링크해야 할 조문 파일들)
ROUTES = [
    ("회의비", "topics/rd-meeting.md", ["rnd-cost-standard/25.md", "rnd-cost-standard/25.prev-2026-03-11.md",
                                      "rnd-cost-standard/25-2.md", "rnd-cost-standard/addenda.md"]),
    ("주유", "topics/rd-travel-expert.md", ["rnd-cost-standard/10.md", "travel-regulation/13.md"]),
    ("장비", "topics/rd-equipment.md", ["rnd-cost-standard/73.md", "rnd-cost-standard/74.md",
                                     "rnd-facility-standard/18.md", "rnd-facility-standard/28.md"]),
    ("RCMS 복원", "topics/rcms-vat.md", ["rnd-cost-standard/21.md", "vat-act/39.md"]),
    ("에누리", "topics/tax-vat-adjustments.md", ["vat-act/29.md", "vat-decree/70.md"]),
    ("자계좌", "topics/rcms-transfers.md", ["rnd-cost-standard/22.md"]),
    ("강사비", "topics/tax-withholding.md", ["income-tax-act/129.md", "income-tax-decree/87.md",
                                         "local-tax-act/103-13.md"]),
    ("e나라도움", "topics/grants-general.md", ["subsidy-act/index.md", "local-subsidy-standard/index.md"]),
]


def links(path: Path):
    return [(path.parent / t).resolve() for t in re.findall(r"\]\(([^)#\s]+)\)", path.read_text(encoding="utf-8"))
            if not t.startswith("http")]


class IndexRouting(unittest.TestCase):
    def test_routes(self):
        rows = [ln for ln in INDEX.read_text(encoding="utf-8").splitlines() if ln.startswith("| ")]
        for cue, topic, targets in ROUTES:
            with self.subTest(cue=cue):
                row = next((r for r in rows if all(w in r for w in cue.split())), None)
                self.assertIsNotNone(row, f"색인에 '{cue}' 단서 없음")
                self.assertIn(f"({topic})", row)
                topic_path = SKILL / "references" / topic
                got = set(links(topic_path))
                for t in targets:
                    want = (SKILL / "laws" / t).resolve()
                    self.assertTrue(want.exists(), f"{t} 파일 없음")
                    self.assertIn(want, got, f"{topic} 가 {t} 를 링크하지 않음")

    def test_article_headers_have_version_fields(self):
        for f in [SKILL / "laws/rnd-cost-standard/25.md", SKILL / "laws/rnd-cost-standard/25.prev-2026-03-11.md"]:
            head = f.read_text(encoding="utf-8").split("\n---\n")[0]
            for k in ("effective_from", "effective_to", "retrieved_on", "official_url", "fixed_url"):
                self.assertIn(f"\n{k}: ", head)
        prev = (SKILL / "laws/rnd-cost-standard/25.prev-2026-03-11.md").read_text(encoding="utf-8")
        self.assertIn('effective_to: "2026-05-05"', prev)
        self.assertIn("사전에 내부결재가 완료된 회의", prev)
        cur = (SKILL / "laws/rnd-cost-standard/25-2.md").read_text(encoding="utf-8")
        self.assertIn("2026-06-11", cur)


if __name__ == "__main__":
    unittest.main()
