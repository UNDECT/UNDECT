# 사이버펑크 레퍼런스 패키지

| 파일 | 내용 |
|---|---|
| [01-ingame-research.md](01-ingame-research.md) | 레퍼런스 인게임 정밀 조사 + 항목별 로블록스 구현안(난이도 A~D) |
| [02-progress-score.md](02-progress-score.md) | 현재 진행 상황 채점(38/100)과 점수를 올리는 순서 |
| [03-claude-code-prompt.md](03-claude-code-prompt.md) | Claude Code에 그대로 붙여 넣을 구현 프롬프트(v2: 갭 표 검토 반영) |
| [04-gap-table-review.md](04-gap-table-review.md) | 로컬 갭 표 비판적 검토 + 수정된 Phase 계획(47/100) |
| [send-to-claude-code.md](send-to-claude-code.md) | Claude Code에 그대로 보낼 메시지(지시 + 프롬프트 v2 + 검토본 v2 합본) |
| [send-to-claude-code-graphics.md](send-to-claude-code-graphics.md) | 그래픽 패스용 메시지(현재 화면 진단 + 조명 수치 + 레이어·밀도 기준 + 에셋 규칙 + 검증 표) |
| [05-engine-limit-workarounds.md](05-engine-limit-workarounds.md) | 엔진 한계 돌파 기법(거울 지오메트리 반사, 도시 큐브맵, 베이크 GI, CC0 PBR·발광 마스크, 렌즈 플레어 등) |
| [send-to-claude-code-characters.md](send-to-claude-code-characters.md) | 캐릭터·1인칭 팔·총·로봇·차량 Blender 사실화 패스(MPFB2 CC0 인간, 자동화 파이프라인, 규격 검사, LOD, 애니메이션) |
| [send-to-claude-code-c3-onward.md](send-to-claude-code-c3-onward.md) | C3부터 바뀐 절차: 분위기·배경 우선, 간판 정리(계층·면적 규칙), 구역 스타일 4종, 이후 팔·총·캐릭터 |
| [send-to-claude-code-ui-maps.md](send-to-claude-code-ui-maps.md) | UI 전면 제작(디자인 시스템, HUD, 메뉴 전체, Blender 아이콘·3D 미리보기·홀로그램 지도) + 모험 맵 기획·제작, 최종 순서표 |
| [spec/](spec/00-index.md) | **마스터 스펙**: 레퍼런스 전 요소 명세 659개(전투 이펙트, 시술소·시술의, 사이버웨어, 넷러닝, 이동, 적·AI, NPC, 세계, UI, 성장, 차량, 사운드, 보안 NPC, 제외 목록) |
| [send-to-claude-code-master-spec.md](send-to-claude-code-master-spec.md) | 마스터 스펙 합본(지시 + spec 8개 파일). Claude Code에 보내는 파일 |
| [send-to-claude-code-blender-assets.md](send-to-claude-code-blender-assets.md) | **지금 보낼 파일**: 여기서 만든 에셋·애니메이션·이동 코드를 개발 세션이 변환·연결하는 절차(에셋 표, 에셋별 연결 방법, 단계 영향, 남은 목록) |
| [blender/](blender/README.md) | Blender 스크립트와 결과물(`out/`): 보안 로봇, 드론, 포탑, 감시 카메라, 차, 비행 차량, 무기 17종, 사람 10명, 가면 NPC 5종, 1인칭 팔, 사이버웨어 팔 4종(손 레이저 포함), 시술소, 거리 소품, 구역 4종 그림, 클립 158개(죽는 동작, 차 타기 포함) |
| [runtime/](runtime/README.md) | Luau 모듈: 애니메이션 재생, 뼈대 계산, 군중·순찰·교통 이동, NPC 피해·사망, 손 레이저, 차 훔쳐 타기·운전·수배, 보안 로봇 두뇌, 서버 전송, 테스트 189개 |
| [samples/cyber-arm/](samples/cyber-arm/README.md) | 블레이드 사이버웨어 팔 |
