# 색인 — 질문 단서 → 주제 파일 → 확인할 조문

규정·시스템 질문이면 이 색인을 한 번 읽고, **쟁점마다 주제 파일 1개**에서 시작한다. 주제 파일이 가리키는 조문 파일만 연다.
조문 원문은 `../laws/<규정 id>/<조문>.md` (예: 제25조의2 → `25-2.md`), 규정별 목록은 `../laws/<규정 id>/index.md`, 전체 목록은 [../laws/index.md](../laws/index.md).

| 질문 속 단서 | 먼저 읽는 주제 파일 | 그다음 확인할 자료 |
|---|---|---|
| 회의비·다과·식비·회의록·인당·3만 원·5만 원·10만 원 | [topics/rd-meeting.md](topics/rd-meeting.md) | 연구개발비 사용 기준 제25조(사건일에 따라 직전 판본), 제25조의2. 실제 단가는 기관·사업 기준 |
| 출장·주유·자가용·유류비·외부 전문가 교통비·강사 초청 | [topics/rd-travel-expert.md](topics/rd-travel-expert.md) | 제10조·제25조제6항, 공무원 여비 규정 제13조·제30조·별표 2, 기관 자체 규정 |
| 장비·기계·설치비·3천만 원·1억·한 번에 결제·ZEUS | [topics/rd-equipment.md](topics/rd-equipment.md) | 변경이면 제73·74조, 등록·심의면 시설·장비 표준지침 제18·28조, 결제 한도는 과제·RCMS 안내 |
| 부가세 포함 등록·RCMS 복원·여비 세액·카드 총액 | [topics/rcms-vat.md](topics/rcms-vat.md) | 제21조제4항제1호, RCMS 매뉴얼 4.2 부가세복원 |
| 자계좌·기관 계좌·원천징수계좌·이체 | [topics/rcms-transfers.md](topics/rcms-transfers.md) | 제22조제5항, RCMS 매뉴얼 3.1·3.2·3.4, 해당 전문기관 허용 근거 |
| 에누리·할인·환불·수정세금계산서·포인트 | [topics/tax-vat-adjustments.md](topics/tax-vat-adjustments.md) | 부가가치세법 제29조, 시행령 제70조. RCMS 반영까지 물으면 `rcms-vat.md` 추가 |
| 강사비·자문료·원고료·8.8%·3.3%·실수령·일용 | [topics/tax-withholding.md](topics/tax-withholding.md) | 소득세법 제21·84·86·127·129조, 시행령 제87조. 산술은 `calc.py` |
| 국고보조금·지방보조금·e나라도움·보탬e·교부 전 집행·정산 | [topics/grants-general.md](topics/grants-general.md) | 보조금법·시행령, 국고보조금 통합관리지침, 지방보조금법·관리기준 |

여러 주제에 걸치면 질문 번호마다 해당 주제 파일을 하나씩 읽는다. 같은 조문은 한 번만 열고 재사용한다.

## 기존 참고 파일 (일반 원칙)
| 파일 | 내용 |
|---|---|
| [00-sources.md](00-sources.md) | 공식 출처, 검증 이력, 적용판 확인 원칙 |
| [01-classification.md](01-classification.md) | 재원·사업 유형·쟁점 분류, 되묻기 기준 |
| [10-budget-planning.md](10-budget-planning.md) | 예산 편성 |
| [20-execution.md](20-execution.md) | 집행·선집행·변경 |
| [30-settlement-evidence.md](30-settlement-evidence.md) | 정산·증빙 |
| [40-tax-accounting.md](40-tax-accounting.md) | 부가세·원천징수·회계·지원액 산식 |
| [50-program-types.md](50-program-types.md) | 사업 유형별 판단 포인트 |
