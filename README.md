# 사업비 나침반 (Budget Compass)

<img src="plugins/budget-compass/assets/icon.png" width="72" align="right" alt="">

> **"질문만 하면 해당 사업의 예산·회계·세무 기준을 찾아 근거와 함께 실무 처리방법을 알려주는 AI."**

대한민국 정부지원사업 담당자를 위한 **예산·회계·세무·규정 스킬 플러그인**입니다.
사업계획서나 내부자료를 올리지 않고 질문 한 줄로 사용합니다. 공개 사업명·연도나 공고 링크를 함께 주면 더 정확해집니다.

> ⚠ v0.2.0 프로토타입입니다. 답변은 실무 참고용이며 법적·회계적 최종 판단을 대체하지 않습니다.

## 할 수 있는 일
| 기능 | 내용 |
|---|---|
| ① 예산 편성 | 비목·세목 구분, 편성 가능 여부, 편성표 구성 |
| ② 사업비 집행 | 협약·교부결정·입금·카드발급 시점을 나눈 선집행 판단, 사업비 변경, 집행 제한 |
| ③ 정산·증빙 | 실재성·관련성·이행·지급·세무 5관점 증빙 대조, 불인정 사례, 정산표 |
| ④ 세무·회계 | 부가세 공제와 사업비 인정 분리 판단, 원천징수 소득 구분, 회계처리 |
| ⑤ 법령·지침 검색 | 사건일 적용판 확인 (현행·과거·시행예정, 부칙·경과조치) |
| ⑥ 사업 유형별 판단 | R&D, 교육훈련, 인력양성, 전시회, 일반 보조 / 국고·지방·혼합 재원 |
| ⑦ 계산 지원 | 부가세 분리, 원천징수(기타·사업·일용), 세후→세전 역산, 지원액·자부담, 비율 상한 점검 |
| ⑧ 실무 사례 안내 | 처리 순서, 필요 증빙, 기관에 보낼 확인 문구 |

## 답변 형식 (고정)
1. **결론** — 가능 / 불가 / 조건부 가능 / 판단 보류 / 계산 결과
2. **관련 근거** — 법령·조항·지침, 적용 판본(시행일·공고번호), 직접 연 공식 링크
3. **상세 설명** — 사실·가정·예외 구분, 세법 / 사업비 인정 / 회계 구분
4. **실무 처리방법** — 절차, 필요 증빙, 유의사항, 기관 확인 문구, 계산
5. **추가 확인사항** — 판단을 바꾸는 한 가지 질문 또는 기관 확인 항목

## 저장소 구성
```
plugins/budget-compass/                 ← 플러그인 루트 (이 폴더를 zip)
  plugin.json                           포터블 매니페스트 (Agent Plugins 스키마 + extensions.com.openai)
  assets/icon.png, compass.svg          아이콘
  skills/budget-compass/
    SKILL.md                            절대 규칙 + 분류 → 조사 → 판단 → 계산 → 답변
    templates/answer.md                 5단계 답변 템플릿
    references/
      00-sources.md                     공식 출처·확인한 판본·적용판 확인 원칙
      01-classification.md              재원·사업 유형·쟁점 분류, 되묻기 기준
      10-budget-planning.md             예산 편성
      20-execution.md                   집행·선집행·변경
      30-settlement-evidence.md         정산·증빙
      40-tax-accounting.md              부가세·원천징수·회계·지원액 산식
      50-program-types.md               사업 유형별 판단 포인트
    scripts/calc.py                     계산기 (파이썬 표준 라이브러리만 사용)
.agents/plugins/marketplace.json        Codex 로컬 마켓플레이스 등록
evals/questions.md                      테스트 질문 37개 + 채점 기준
tools/package.sh                        배포용 zip 생성
```

## 설치

### ChatGPT
1. 배포 zip 을 만듭니다 (또는 Releases 에서 받습니다).
   ```bash
   bash tools/package.sh
   ```
2. **플러그인으로 설치**: ChatGPT의 플러그인 화면에서 `dist/budget-compass-plugin-v0.2.0.zip` 을 업로드합니다.
   **스킬만 설치**: 스킬 화면에서 `dist/budget-compass-skill-v0.2.0.zip` 을 업로드합니다.
3. **웹 검색**과 **코드 실행**(계산기용)을 켜 둡니다. 웹 검색이 꺼져 있으면 답변 맨 앞에 최신 기준을 확인하지 못했다는 경고가 붙습니다.

> 메뉴 이름·위치와 Plus 요금제에서의 업로드 지원 여부는 바뀔 수 있습니다. 설치 화면이 보이지 않으면 현재 ChatGPT 도움말을 확인하세요.
> 패키지 형식은 OpenAI [플러그인 패키징 문서](https://developers.openai.com/plugins/build/plugins)의 포터블 구조(루트 `plugin.json` + `skills/` + `assets/`)를 따릅니다.

### Codex
이 저장소의 `.agents/plugins/marketplace.json` 으로 로컬 마켓플레이스에 추가할 수 있습니다.

### 그 밖의 에이전트
`plugins/budget-compass/skills/budget-compass/` 는 Agent Skills 형식(SKILL.md + references)이라 Claude 등 다른 에이전트에서도 쓸 수 있습니다.

## 계산기 단독 사용
```bash
C=plugins/budget-compass/skills/budget-compass/scripts/calc.py
python3 $C other-income 300000                                   # 기타소득 (필요경비 60%)
python3 $C business-income 300000                                # 사업소득 3.3%
python3 $C gross-up 300000 --type other                          # 세후 30만 원 → 세전
python3 $C vat-split 1100000                                     # 공급가액·부가세
python3 $C subsidy 5000000 --rate 0.6 --cap 2500000 --disallowed 100000
python3 $C grant-base 30000000 --rate 0.8                        # 총액 대비 / 보조금 대비 두 해석
python3 $C --help
```

## 설계 원칙
- 공개된 법령·지침만 사용하며 기관 내부자료는 포함하지 않습니다.
- `references/` 는 **어디서 찾을지 알려주는 지도**입니다. 답변 근거는 매번 공식 원문을 열어 **사건일 적용판**을 확인합니다.
- 법령·조문·URL·시행일을 지어내지 않습니다. 열어 보지 못한 근거는 "미확인"으로 표시합니다.
- 개인정보를 반복하거나 검색어에 넣지 않습니다. 증빙 소급 작성·허위 기재·쪼개기 같은 부정 집행을 돕지 않습니다.

## 변경 이력
- **v0.2.0** — Codex 버전(budget-compass_codex)과 통합
  - 매니페스트를 공식 포터블 형식(루트 `plugin.json` + `extensions.com.openai`)으로 전환, 아이콘 추가
  - 2026. 1. 2. 부처 개편 반영 (기획재정부 → 기획예산처)
  - 국가법령정보센터 원문으로 확인한 판본 표기 (국고보조금 통합관리지침, 지방보조금 관리기준, 연구개발비 사용 기준, 부가가치세법, 소득세법 제129조)
  - 규범 위계 수정: 개별 지침은 상위 법령이 허용한 범위에서 적용
  - 사건일 적용판·날짜 분리(협약·교부결정·입금·카드발급), 5관점 증빙 대조, 세법/사업비/회계 3분리, 개인정보·부정집행 방지 규칙 추가
  - 계산기에 `subsidy`(지원액·자부담), `grant-base`(두 해석) 추가
  - 테스트 세트 25 → 37문항
- **v0.1.0** — 최초 버전

## 로드맵
- [x] 1단계: 기본 스킬 (질문 분류, 검색·검증 절차, 고정 답변 형식)
- [~] 2단계: 분야별 전문화 (편성·집행·정산·부가세·원천징수 완료, 부처별 지침 보강 필요)
- [ ] 3단계: 테스트·검증 (`evals/questions.md` 37문항, 일반 ChatGPT와 비교)
- [ ] 4단계: 배포 (Releases 패키지, 공개 전환)

## 라이선스
MIT
