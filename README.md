# 사업비 나침반 (Budget Compass)

> **"질문만 하면 해당 사업의 예산·회계·세무 기준을 찾아 근거와 함께 실무 처리방법을 알려주는 AI."**

정부지원사업 담당자를 위한 **예산·회계·세무·규정 전문 스킬 플러그인**입니다.
사업계획서나 내부자료를 올리지 않고 질문 한 줄로 사용합니다.

> ⚠ 초기 버전(v0.1.0)입니다. 답변은 실무 참고용이며 법적·회계적 최종 판단을 대체하지 않습니다.

## 할 수 있는 일
| 기능 | 내용 |
|---|---|
| ① 예산 편성 | 비목·세목 구분, 편성 가능 여부, 편성 기준 |
| ② 사업비 집행 | 집행 가능 여부, 선집행, 사업비 변경, 집행 제한사항 |
| ③ 정산·증빙 | 적격 증빙, 불인정 사례, 정산 기준·필요 서류 |
| ④ 세무·회계 | 부가세 매입세액 공제·불공제, 원천징수, 회계처리 |
| ⑤ 법령·지침 검색 | 법령·고시·운영지침 검색 및 비교 |
| ⑥ 사업 유형별 판단 | R&D, 교육훈련, 인력양성, 전시회, 일반 보조사업 |
| ⑦ 계산 지원 | 부가세 분리, 공급가액, 원천징수, 세후→세전 역산, 예산 비율 |
| ⑧ 실무 사례 안내 | 처리방법·주의사항 |

## 답변 형식 (고정)
1. **결론** — 가능 / 불가 / 조건부 가능 / 판단 보류
2. **관련 근거** — 법령·조항·지침·시행일·공식 링크
3. **상세 설명** — 판단 사유, 적용 조건
4. **실무 처리방법** — 절차, 필요 증빙, 유의사항
5. **추가 확인사항** — 사업별 특례, 담당 기관 확인 사항

## 저장소 구성
```
.agents/plugins/marketplace.json        플러그인 마켓플레이스 등록 정보
plugins/budget-compass/
  .codex-plugin/plugin.json             플러그인 매니페스트
  skills/budget-compass/
    SKILL.md                            핵심 스킬 (분류 → 조사 → 판단 → 계산 → 답변)
    templates/answer.md                 5단계 답변 템플릿
    references/
      00-sources.md                     공식 출처·검색 패턴·검증 원칙
      01-classification.md              재원·사업 유형·쟁점 분류, 되묻기 기준
      10-budget-planning.md             예산 편성
      20-execution.md                   사업비 집행
      30-settlement-evidence.md         정산·증빙
      40-tax-accounting.md              부가세·원천징수·회계
      50-program-types.md               사업 유형별 판단 포인트
    scripts/calc.py                     계산기 (표준 라이브러리만 사용)
evals/questions.md                      테스트 질문 25개 + 채점 기준
tools/package.sh                        배포용 zip 생성
```

## 설치

### ChatGPT (스킬 업로드)
1. 아래 명령으로 zip 을 만들거나 Releases 에서 받습니다.
   ```bash
   bash tools/package.sh
   ```
2. ChatGPT의 스킬 설정 화면에서 `dist/budget-compass-skill-v0.1.0.zip` 을 업로드합니다.
3. **웹 검색**과 **코드 실행**(계산기용)을 켜 둡니다. 웹 검색이 꺼져 있으면 최신 법령을 확인하지 못했다고 답변에 표시됩니다.

> ChatGPT 메뉴 이름과 위치는 바뀔 수 있습니다. 현재 화면 기준으로 "Skills" 항목을 찾으세요.

### Codex (플러그인)
이 저장소에는 `.agents/plugins/marketplace.json` 이 있어서 Codex 플러그인 마켓플레이스로 추가할 수 있습니다.

### 그 밖의 에이전트
`plugins/budget-compass/skills/budget-compass/` 폴더는 Agent Skills 형식(SKILL.md + references)이라 Claude 등 다른 에이전트에서도 스킬로 쓸 수 있습니다.

## 계산기 단독 사용
```bash
python plugins/budget-compass/skills/budget-compass/scripts/calc.py other-income 500000
python plugins/budget-compass/skills/budget-compass/scripts/calc.py vat-split 3300000
python plugins/budget-compass/skills/budget-compass/scripts/calc.py --help
```

## 설계 원칙
- 공개된 법령·지침만 사용하며 기관 내부자료는 포함하지 않습니다.
- `references/` 는 **어디서 찾을지 알려주는 지도**입니다. 답변 근거는 매번 공식 원문을 검색해 확인합니다. (스킬에 법령을 저장해 두는 것만으로는 최신성이 보장되지 않기 때문입니다.)
- 법령·조문·판례·출처를 지어내지 않습니다. 확인하지 못한 것은 "확인 필요"로 표시합니다.
- 개별 사업지침·협약을 확인하지 못하면 최종 집행 적격성은 "조건부 가능" 또는 "판단 보류"로 답합니다.

## 로드맵
- [x] 1단계: 기본 스킬 (질문 분류, 검색·검증 절차, 고정 답변 형식)
- [~] 2단계: 분야별 전문화 (편성·집행·정산·부가세·원천징수 초안 완료, 부처별 지침 보강 필요)
- [ ] 3단계: 테스트·검증 (`evals/questions.md` 25문항, 일반 ChatGPT와 비교)
- [ ] 4단계: 배포 (Releases 패키지, 사용 가이드)

## 라이선스
MIT
