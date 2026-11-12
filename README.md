# 사업비 나침반 (Budget Compass)

<img src="plugins/budget-compass/assets/icon.png" width="72" align="right" alt="">

대한민국 정부지원사업 담당자를 위한 **예산·회계·세무·규정 스킬 플러그인**입니다.
사업계획서나 내부자료 없이 질문만으로 사용하며, 공식 법령·지침을 근거로 실무 처리방법을 안내합니다.
자주 쓰는 공통 규정 15종의 조문 원문을 함께 담고 있어, 해당 조문을 바로 찾아 근거로 제시합니다.
공개 사업명·연도나 공고 링크를 함께 주면 더 정확해집니다.

> 답변은 실무 참고자료이며 법적·회계적 최종 판단을 대체하지 않습니다.

## 기능
| 기능 | 내용 |
|---|---|
| 예산 편성 | 비목·세목 구분, 편성 가능 여부, 편성표 구성 |
| 사업비 집행 | 협약·교부결정·입금·카드발급 시점을 나눈 선집행 판단, 사업비 변경, 집행 제한 |
| 정산·증빙 | 실재성·관련성·이행·지급·세무 5관점 증빙 대조, 불인정 사례, 정산표 |
| 세무·회계 | 부가세 공제와 사업비 인정 분리 판단, 원천징수 소득 구분, 회계처리 |
| 수록 규정 검색 | 공통 규정 15종의 조문 원문을 낱말·조문 번호로 찾아 판본·시행일·원문 주소와 함께 인용 |
| 법령·지침 확인 | 수록본 이후 개정 여부, 사건일 적용판, 개별 사업 공고·지침은 웹에서 확인 |
| 국가R&D·RCMS | 회의비·식비, 장비 구입 사전승인, 부가세 포함 등록, 출장·유류비, 이체 경로 — 고시 기준과 과제별 허용을 구분 |
| 사업 유형별 판단 | R&D, 교육훈련, 인력양성, 전시회, 일반 보조 / 국고·지방·혼합 재원 |
| 계산 | 부가세 분리, 원천징수(기타·사업·일용), 세후→세전 역산(재검산), 지원액·자부담, 비율 상한 점검 |

## 답변 형식
1. **결론** — 가능 / 불가 / 조건부 가능 / 판단 보류 / 계산 결과
2. **근거** — 법령·조항·지침, 적용 판본(시행일·공고번호), 공식 링크
3. **설명** — 사실·가정·예외 구분, 세법 / 사업비 인정 / 회계 구분, 계산
4. **실무처리** — 지금 할 일, 필요 증빙, 기관 문의 문구
5. **확인사항** — 판단을 바꾸는 한 가지 질문

여러 질문을 한 번에 하면 질문마다 결론을 한 줄씩 먼저 보여줍니다.

## 설치

| 사용 환경 | 설치 방법 |
|---|---|
| ChatGPT 웹 (개인) | 릴리스 zip 업로드 |
| ChatGPT 데스크톱 앱 / Codex | GitHub 저장소를 마켓플레이스로 추가 |
| ChatGPT 워크스페이스 | 관리자 콘솔에서 GitHub 마켓플레이스 가져오기 |

### ChatGPT 웹
1. [최신 릴리스](https://github.com/qkrwl6229-glitch/budget-compass/releases/latest)에서 `budget-compass-plugin-v*.zip` 을 내려받습니다.
2. [ChatGPT 플러그인](https://chatgpt.com/plugins) → **개인용** → **추가** → **플러그인 압축 파일 업로드** 에서 zip 을 선택합니다.
3. 등록된 플러그인의 상세 화면에서 **설치**합니다.
4. 새 채팅에서 플러그인을 선택하고 질문합니다. 웹 검색과 코드 실행이 켜져 있어야 근거 확인과 계산이 동작합니다.

업로드한 zip 은 그 버전 그대로 유지됩니다. 새 버전은 새 zip 을 다시 업로드해서 사용합니다.

### ChatGPT 데스크톱 앱 / Codex
```bash
codex plugin marketplace add qkrwl6229-glitch/budget-compass
codex plugin add budget-compass@budget-compass
```
설치 후 ChatGPT 데스크톱 앱을 다시 시작하면 플러그인 디렉터리에 표시됩니다.

### ChatGPT 워크스페이스
관리자 콘솔 → 플러그인 → 추가 → 마켓플레이스 가져오기에서 이 저장소를 연결합니다. ([OpenAI 안내](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github))

## 계산기 단독 사용
```bash
C=plugins/budget-compass/skills/budget-compass/scripts/calc.py
python3 $C vat-split 1100000                                     # 공급가액·부가세
python3 $C other-income 300000                                   # 기타소득
python3 $C business-income 300000                                # 사업소득 3.3%
python3 $C gross-up 300000 --type other                          # 세후 → 최소 세전액
python3 $C subsidy 5000000 --rate 0.6 --cap 2500000 --disallowed 100000
python3 $C grant-base 30000000 --rate 0.8                        # 총액 대비 / 보조금 대비
python3 $C --help
```
세율·공제액 기본값은 계산 편의를 위한 값입니다. 지급일과 소득 유형에 맞는 기준을 확인한 뒤 사용하세요.
잘못된 입력(음수, 범위를 벗어난 비율, 중복 항목 등)은 계산하지 않고 `입력 오류`로 알려줍니다.

## 수록 규정
| 분야 | 규정 |
|---|---|
| 국고보조금 | 보조금 관리에 관한 법률·시행령, 국고보조금 통합관리지침 |
| 지방보조금 | 지방자치단체 보조금 관리에 관한 법률·시행령, 지방보조금 관리기준 |
| 국가R&D | 국가연구개발혁신법·시행령, 국가연구개발사업 연구개발비 사용 기준, 국가연구개발 시설ㆍ장비의 관리 등에 관한 표준지침 |
| 세무 | 부가가치세법, 소득세법(사업·근로·기타소득, 원천징수, 지출증명, 지급명세서 조문), 소득세법 시행령 제87조, 법인세법 제116조, 지방세법 제103조의13 |

국가법령정보센터의 현행 판본을 조문 단위로 담았습니다(부칙·별표·서식 제외). 각 파일에 번호·시행일·수집일·원문 주소가 적혀 있으며, 매주 현행 판본과 비교해 개정 여부를 확인합니다.

```bash
L=plugins/budget-compass/skills/budget-compass/scripts/lookup.py
python3 $L --list                                   # 수록 규정·판본·수집일
python3 $L 회의비 식비 --law rnd-cost-standard        # 낱말로 찾기
python3 $L --law vat-act --article 29                # 조문 번호로 찾기
```

## 저장소 구성
```
plugins/budget-compass/
  plugin.json                     플러그인 매니페스트
  assets/                         아이콘
  skills/budget-compass/
    SKILL.md                      스킬 본문
    templates/answer.md           답변 템플릿
    references/                   공식 출처, 분류 기준, 분야별 참고 자료
    laws/                         공통 규정 조문 원문과 목록(index.json)
    scripts/calc.py               계산기 (Python 표준 라이브러리)
    scripts/lookup.py             수록 규정 조문 검색
.agents/plugins/marketplace.json  마켓플레이스 정보
evals/questions.md                평가 질문과 채점 기준
tests/                            계산기·조문 검색 테스트
tools/fetch_laws.py               국가법령정보센터에서 수록 규정 수집·개정 확인
tools/law_sources.json            수록 규정 목록
tools/validate.py                 플러그인 구조 검사
tools/package.sh                  검사·테스트 후 릴리스 zip 과 체크섬 생성
```

## 원칙
- 공개된 법령·지침만 사용하며 기관 내부자료는 포함하지 않습니다.
- 답변 근거는 수록 원문 또는 직접 확인한 공식 원문만 사용하며, 수록본을 인용할 때는 수집일 기준임을 밝힙니다.
- 확인하지 못한 법령·조문·URL·시행일은 만들어내지 않고 "미확인"으로 표시합니다.
- 개인정보를 반복하거나 검색어에 넣지 않으며, 증빙 소급 작성·허위 기재 등 부정 집행을 돕지 않습니다.

## 라이선스
MIT
