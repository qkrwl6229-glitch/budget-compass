# 설치 유형별 업데이트 방법

Doctor 는 안내만 한다. 다운로드·설치·파일 교체·게시·권한 변경을 실행하지 않는다.

| 설치 유형 | 업데이트 방법 | 알아둘 점 |
|---|---|---|
| **ChatGPT 개인용 ZIP** | [최신 릴리스](https://github.com/qkrwl6229-glitch/budget-compass/releases/latest)에서 `budget-compass-plugin-v<버전>.zip` 을 받는다 → ChatGPT 플러그인 화면에서 기존 플러그인의 **새 버전 업로드** 메뉴가 보이고 권한이 있으면 사용한다. 메뉴가 없거나 권한이 없으면 소유자·편집자에게 요청하거나, 배포 정책이 허용하면 자기 계정에 자기 소유 복사본을 새로 설치한다 | ZIP 업로드는 GitHub 와 동기화되지 않는다. 업로드한 시점의 내용 그대로 유지된다. 공유받은 원본을 사용자가 직접 고칠 수 있다고 안내하지 않는다 |
| **ChatGPT 데스크톱 앱 / Codex (GitHub 마켓플레이스)** | 처음 마켓플레이스를 추가한 사람이 `codex plugin marketplace upgrade budget-compass` 로 소스를 갱신한 뒤, 데스크톱 앱에서 설치 상태와 버전을 확인한다 | 소스를 갱신한 것과 현재 채팅이 쓰는 설치 버전은 다를 수 있다. 앱 재시작 후 버전을 다시 확인한다 |
| **관리형 ChatGPT 워크스페이스** | 관리자가 GitHub 마켓플레이스를 가져왔다면 일일 동기화 또는 관리자 수동 동기화 | 가져온 관리자 계정이 저장소 읽기 권한을 유지해야 한다. 개인용 ZIP 설치에는 해당하지 않는다 |

## 확인 주소
- 안정판 목록: https://github.com/qkrwl6229-glitch/budget-compass/releases
- 최신 안정판 (API): https://api.github.com/repos/qkrwl6229-glitch/budget-compass/releases/latest — 초안·시험판(prerelease)은 여기에 나오지 않는다
- 각 릴리스의 `SHA256SUMS-v<버전>.txt` 로 받은 ZIP 의 무결성을 확인할 수 있다
- OpenAI 안내: [ChatGPT 플러그인](https://help.openai.com/en/articles/20001256-plugins-in-chatgpt) · [워크스페이스 GitHub 동기화](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github) · [플러그인 패키징](https://developers.openai.com/plugins/build/plugins)

## 알려 줄 한계
- 공식 규정이 바뀌어도 **설치된 파일은 자동으로 바뀌지 않는다.** 배포자가 새 릴리스를 만들고, 사용자가 위 방법으로 갱신해야 한다.
- 새 릴리스가 없으면 Doctor 가 새 버전을 만들어 주지는 못한다. 그동안에도 업무 스킬은 웹으로 새 공식 원문을 확인해 답할 수 있다.
- 저장소나 릴리스에 접근할 수 없으면 최신판을 추정하지 않는다. 계정 토큰이나 비공개 자료를 요구하지 않는다.
