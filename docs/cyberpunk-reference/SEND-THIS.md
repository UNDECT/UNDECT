# 개발 세션(Opus)에 보낼 메시지

아래 상자 안을 그대로 복사해 PC의 Claude Code 개발 세션에 붙여 넣으면 된다. 파일을 따로 첨부할 필요는 없다. 개발 세션이 저장소를 받아 직접 읽는다.

```
새 작업 지시야. 먼저 아래 저장소를 받아.

git clone --depth 1 -b ccr-9e6cc8c3-bftdlm https://github.com/UNDECT/UNDECT.git <임시폴더>

받은 뒤 <임시폴더>/docs/cyberpunk-reference/send-to-claude-code-blender-assets.md 를 처음부터 끝까지 읽고 그대로 따라.
이 문서가 지금까지 보낸 지시보다 우선이야. 요점은 이래.

1. 모델, 애니메이션, 이동·전투 로직은 다른 세션이 다 만들어서 저장소에 올려 뒀어. 너는 디자인을 바꾸지 말고 게임에 반영만 해.
2. 진행 중인 C2는 끊지 말고 끝낸 다음 시작해.
3. 문서 맨 끝 "8. 작업 순서" 표대로 하고, 단계마다 멈춰서 보고해. 승인받고 다음으로 가.
4. 새 기능: NPC를 죽일 수 있게(4-2), 손 레이저(4-2), 차 훔쳐 타기와 시민·보안 반응(4-3).
5. 수위는 지금 Kids 설정을 끄고 가장 높게(Vitals.GORE = 3) 만들어. 나중에 내가 낮출 거야.
6. 쓸데없는 간판은 지워(문서 4의 거리 항목).

기존 규칙은 그대로야: 답은 한국어, cyber-3v3.rbxl 저장 금지, rojo build -o cyber-rpg.rbxl 금지, computer-use로 Studio 열기 금지,
다른 게임의 이름·에셋·툴박스 스크립트 금지, 기능 브랜치에 커밋(Co-Authored-By 포함), Lune 테스트 전부 통과.

저장소를 받지 못하거나 문서와 지금 코드가 맞지 않는 곳이 있으면 고치지 말고 먼저 나한테 알려 줘.
받은 뒤 첫 보고에는 (가) 받은 파일 목록 요약 (나) runtime 테스트 162개 통과 여부 (다) 작업 순서 표에서 지금 프로젝트와 충돌하는 곳을 적어 줘.
```

## 개발 세션이 읽게 되는 문서
| 문서 | 내용 | 상태 |
|---|---|---|
| `send-to-claude-code-blender-assets.md` | 에셋·애니메이션·로직 반영 절차 전체, 작업 순서 | **주 문서** |
| `runtime/README.md` | Luau 모듈 쓰는 법, 클립 목록, 좌표 약속 | 주 문서가 가리킴 |
| `blender/README.md` | Blender 스크립트 실행법 | 주 문서가 가리킴 |
| `send-to-claude-code-c3-onward.md` | 간판 정리, 구역 양식 4종, C3 이후 순서 | 유효 |
| `send-to-claude-code-ui-maps.md` | UI 전면 제작, 모험 맵 | 유효 |
| `spec/` (또는 합본 `send-to-claude-code-master-spec.md`) | 요소 659개의 완료 기준 | 유효 |
| `send-to-claude-code-graphics.md`, `send-to-claude-code-characters.md` | 그래픽·캐릭터 초기 지시 | 일부 폐기("모델을 직접 만든다", "간판 25개 이상") |
| `send-to-claude-code.md`, `03`, `04` | 초기 프롬프트와 갭 표 검토 | 이미 보낸 것. 다시 보낼 필요 없음 |

## 사용자가 정해 줘야 하는 것 (개발 세션이 물어볼 수 있다)
- 체포됐을 때의 벌(벌금, 차 몰수, 위치 이동)
- 죽었을 때의 벌(스펙 CMB-09)
- 퀘스트에 필요해서 죽으면 안 되는 NPC 목록
- 적·보스 디자인 방향(승인 전이라 에셋이 없다)
- 공개 등급: 수위 3으로 공개하면 Restricted 등급이 된다
- 이전부터 남은 것: UI 색, 오디오 출처, 맵 구조(MP-14), 대상 기기(MP-19), 음성 방식(SND-30)
