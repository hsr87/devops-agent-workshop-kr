# 사전 검증 결과

워크샵 전에 **Workshop Studio 이벤트 계정**(원본 워크샵으로 provision, us-east-1, 참가자 역할 `WSParticipantRole`)에서 가이드 순서대로 처음부터 끝까지 실행한 결과입니다. 계정 정보는 일반화했습니다.

- **1회차 (2026-10-14):** 문제를 찾아 고친 실행
- **2회차 (2026-10-15):** 고친 코드로 계정을 **프로비저닝 직후 상태로 되돌린 뒤** 처음부터 다시 실행. 모든 단계 통과 → [2회차 요약](#run2)

- 콘솔 클릭 단계는 같은 일을 하는 API로 대신 실행했습니다(Agent Space 생성, 조사 시작, 웹훅 발급).
- **VS Code 경로**는 IDE 서버에서 `participant` 사용자로 실제 실행했습니다.
- **CloudShell 경로**는 같은 조건(Python 3.9, 빈 홈 디렉터리)을 재현한 환경에서 실행했습니다.

## 1회차 요약

| # | 단계 | 결과 | 비고 |
|---|---|---|---|
| 1 | Agent Space 생성 + AWS 계정 연결 | ✅ | CLI로 만들 때는 역할 생성 후 IAM 전파에 1–10분 필요(콘솔 Begin setup은 해당 없음) |
| 2 | `bootstrap.sh` (VS Code IDE, Python 3.12) | ✅ | 스택·Agent Space 탐지, venv 생성 |
| 3 | `bootstrap.sh` (CloudShell 조건, Python 3.9) | ✅ | uv로 Python 3.12 venv 자동 생성(약 20초), 재실행 시 웹훅 값 유지 |
| 4 | Part 1 ① ECS 조사 | ✅ | 약 10–15분. 원인 = `POST /orders` 무제한 캐시(요청당 1MB). [아래](#ecs) |
| 5 | Part 1 ② 웹훅 발급 → forwarder Lambda 설정 → 알람(Method 2) | ✅ | 조사 자동 생성, 단 ①과 **`LINKED`** 됨. [아래](#linked) |
| 6 | Bedrock 점검 (`evaluate.py --judge`) | ✅ | 참가자 역할로 호출 가능 |
| 7 | 확장 B MCP 배포 → 원격 스모크 테스트 → **DevOps Agent 등록·연결** | ✅ | Workshop Studio 계정에서는 등록 허용. `register.sh` 버그 수정 후 성공, 재실행 안전 |
| 8 | 확장 B 로컬 서버 테스트 (VS Code IDE) | ✅ | **포트 8080은 Code Editor가 사용 중** → 8765로 변경 |
| 9 | **메인 에이전트 실습** (MCP 연결 상태, 2회) | ✅ | 판별 100%, 라우팅 100%, RCA MATCH. [아래](#router) |
| 10 | **메인 에이전트 실습** (MCP 없이 — 참가자 기본 경로) | ✅ | 판별 100%, 라우팅 100%, RCA MATCH |
| 11 | `finish --reverify` 반복 (조사 2세트 × 3회) | ✅ | 6회 모두 같은 결과 |
| 12 | 확장 A `send_test_alert.py` → 웹훅 | ✅ | HTTP 200, 조사 생성 |
| 13 | 확장 A Lambda 배포 → `aws lambda invoke` → 웹훅 | ✅ | HTTP 200 (3초 전 알림과 `LINKED`) |
| 14 | **확장 A + B**: -26% 알림을 웹훅으로, MCP 연결 상태 | ✅ | DevOps Agent가 스스로 **"Verdict: EXPECTED_EVENT — not an incident"** (앞선 광고 조사와 묶이지 않았을 때. [2회차](#run2) 참고) |
| 15 | Lab 3 (VS Code, CLI `sre-agent.py`) | ✅ | 조사 → 분석 → 수정·테스트 → **CodeCommit PR 생성**. 단 [진행 중 조사 재사용 주의](#lab3) |
| 16 | A2A 등록 (`remoteagent`) | – | 계정 정책상 허용. 실제 A2A 엔드포인트가 있어야 등록됨(가짜 주소로는 조회 실패) |
| 17 | 가이드 사이트 `mkdocs build --strict` | ✅ | 경고 없음 |

## 2회차: 초기화 후 처음부터 재실행 {#run2}

1회차에서 만든 리소스(Agent Space, 웹훅·MCP 등록, 확장 Lambda, CodeCommit PR, IDE 파일, forwarder Lambda 설정)를 모두 지워 **프로비저닝 직후 상태**로 되돌린 뒤, 가이드 순서대로 다시 실행했습니다.

| 순서 | 단계 | 결과 | 실측 |
|---|---|---|---|
| 1 | Agent Space 생성 + 계정 연결 | ✅ | (CLI 경로) IAM 전파 약 10분 — 콘솔 Begin setup은 해당 없음 |
| 2 | `bootstrap.sh` (VS Code IDE) → Bedrock 점검 → 로컬 MCP 테스트 | ✅ | 약 1분 |
| 3 | Part 1 ① ECS 조사 | ✅ 메모리 누수 확정, OOM 없음(아래) | **약 12분** |
| 4 | Part 1 ② 웹훅 → forwarder Lambda → 알람 | ✅ 조사 생성, ①에 `LINKED` | 1분 이내 |
| 5 | Lab 3 리셋 → **Run SRE Agent 먼저** | ✅ `creating new task` → 조사 → 분석 → 수정·테스트 통과 → **PR 생성** | **약 14분** |
| 6 | 메인 에이전트 실습 `start` (Lab 3 시작 직후) | ✅ -26%는 조사 없이 종료, 나머지 2건 조사 생성 | 즉시 |
| 7 | `finish --wait` → `evaluate.py` (`--judge` 포함) | ✅ 판별 3/3, 라우팅 100%, RCA **MATCH** | 조사 약 15분 |
| 8 | 확장 B `deploy.sh` → `test_mcp.sh` → `register.sh` | ✅ | 약 1분 |
| 9 | 확장 A `send_test_alert.py` (MCP 연결 상태) | ✅ HTTP 200. 단 -62% 조사에 **`LINKED`** (아래) | |
| 10 | 확장 A Lambda `deploy.sh` → `aws lambda invoke` | ✅ HTTP 200 | |

**2회차에서 새로 확인한 것**

- **OOM은 환경이 오래돼도 나오지 않습니다.** 부하 테스트가 프로비저닝 때 한 번만 돌아서 메모리가 약 324MB에서 멈춰 있습니다(한도 1024MB). 환경 생성 14시간 뒤에도 Exit Code 137은 없었고, 에이전트는 파이프라인 LoadTest 실패 기록(*"unbounded cache detected (memory leak)"*)까지 근거로 들어 누수를 확정했습니다.
- **메인 에이전트 실습 직후의 확장 A 알림은 `LINKED` 됩니다.** -62% 조사가 이미 완료된 뒤였는데도 *"a continuation of the same ongoing ad_impressions degradation"* 으로 묶였습니다. -62% 조사가 MCP tool을 호출하며 재조사했고, 결론은 *"recovering (−62% → −26%)"* 였습니다. 1회차의 *"EXPECTED_EVENT — not an incident"* 결론은 앞선 광고 조사와 묶이지 않았을 때 나온 것입니다. 가이드와 [리스크](risks.md)에 반영했습니다.
- Lab 3을 먼저 시작하는 순서를 지키면 `Reusing existing investigation` 없이 새 조사로 진행됩니다.

## 1회차에서 발견해서 고친 것

| 문제 | 영향 | 수정 |
|---|---|---|
| `register.sh` 의 tool 연결 단계 따옴표 오류 | MCP 등록 후 Agent Space 연결 실패 | 설정 JSON을 Python으로 생성, 이미 등록된 서버는 재사용 |
| 로컬 MCP 테스트 포트 8080 충돌 | VS Code IDE에서 `test_mcp.sh` 실패 | 기본 포트 8765 |
| 도메인 에이전트가 "알림 메트릭 하락까지 증명"을 요구 | 주문 건도 NEED_MORE_INFO → 판별 33% | "RCA가 확정한 원인이 우리 서비스에 있는가"로 기준 변경 |
| 도메인 에이전트가 라우팅 규칙·다른 서비스 메트릭을 근거로 인정 | -62%가 가끔 ads-bidding으로 오라우팅 | "그 서비스 자체의 관측만 근거"로 명시 |
| `finish --wait` 가 20분 대기 한도에 걸리면 미완료 조사를 완료로 처리 | 조사가 길면 부분 결과로 판정 | 미완료로 두고 `finish` 재실행 안내, 대기 한도 40분 |
| CloudShell 기본 Python 3.9 | `anthropic` 설치 불가, 타입 표기 오류 | bootstrap이 Python 3.12 venv 생성, 모듈은 3.9 호환 |

## Part 1 ① ECS 조사 {#ecs}

- **원인:** `POST /orders` 가 요청마다 `Buffer.alloc(1024*1024)` 를 만들어 비우지 않는 전역 `cache[]` 에 쌓음. 코드와 `[MEMORY LEAK]` 로그(RSS 190MB→324MB, V8 heap은 약 8MB로 고정)로 확정. 태스크 정의 두 리비전 모두 같은 결함이라 **롤백으로 해결 불가**.
- **Exit Code 137(OOM)은 없었습니다.** 1회차는 환경 생성 약 20분 뒤, 2회차는 14시간 뒤였는데 둘 다 같았습니다(부하 테스트가 한 번만 돌기 때문). 에이전트는 이를 *"신고된 장애는 이 시간대 텔레메트리로 확인되지 않는다"* 는 **investigation gap** 으로 따로 적었습니다.

## Part 1 ② 알람 조사가 `LINKED` 됨 {#linked}

알람 조사를 두 번 실행했습니다(①과 30초 차이, ① 완료 후 12분 뒤). 두 번 모두 ①의 ECS 조사에 `LINKED` 되었습니다.

> *"Same underlying infrastructure (cloudformation-template-cluster), same incident window … The 5xx errors from the cloudformation-template-api are the likely root cause of the order-api service unavailability reported in the primary incident."*

→ 워크샵에서도 그렇게 될 가능성이 높습니다. 가이드에 "정상 동작"으로 안내했고, 알림 노이즈 질문에 답하는 장면으로 씁니다.

## 메인 에이전트 실습 (triage-router) {#router}

| 알림 | 판별 (코드) | DevOps Agent | 도메인 에이전트 | 최종 | 정답 |
|---|---|---|---|---|---|
| 노출 -26% (경기 중) | EXPECTED_EVENT (잔차 -1.3%) | **호출 안 함** | – | EXPECTED_EVENT | ✅ |
| 노출 -62% (경기 중) | INCIDENT (잔차 -49.3%) | 계정 리소스 배제, 원인 후보는 가설뿐 | NEED_MORE_INFO | INCONCLUSIVE | ✅ |
| 주문 성공률 -28% | INCIDENT | 무제한 캐시 + 배포 후 부하 테스트 + 롤백 꺼짐 | **ACCEPT** | INCIDENT → commerce-order-team | ✅ (RCA MATCH) |

- **MCP 연결 여부와 관계없이 같은 결과**였습니다. MCP가 연결되면 DevOps Agent가 `get_metric_baseline`, `explain_deviation`, `get_service_owner` 를 호출하고, RCA에 잔차(-49.3%)와 라우팅 규칙을 인용합니다.
- **소요 시간:** 조사 생성 약 1초, **DevOps Agent 조사 12–25분**, 결과 수집 2–3초, 도메인 에이전트 10–20초.
- **도메인 에이전트 기준에 따른 차이:** [실습 페이지](../part2/ext-router.md)의 "해보기" 표 참고(33% → 67–100% → 100%).

## Lab 3 {#lab3}

IDE 서버에서 `participant` 사용자로 원본 리셋 명령과 [가이드의 실행 단계](../part2/lab3.md)를 그대로 실행하고, 대시보드 대신 같은 동작을 하는 CLI(`sre-agent.py`, 대시보드 기본 입력값)로 돌렸습니다.

| 실행 | 결과 |
|---|---|
| 리셋 | Lab 1·2를 건너뛰었으므로 *"nothing to commit"* (원본 안내대로 정상) |
| Agent Space ID 설정 (가이드의 한 줄 명령) | ✅ |
| 1차 실행 (다른 조사가 진행 중일 때) | ⚠️ `Reusing existing investigation` → 진행 중이던 **ad_impressions 조사를 재사용**. 그래도 분석 에이전트가 코드에서 원인을 찾아 **PR #1 생성** |
| 2차 실행 (진행 중 조사 없음) | ✅ `creating new task` → 조사 → 분석 → 수정(테스트 통과) → PR 단계까지 **약 14분**. 단 같은 날 두 번째 실행이라 브랜치 이름이 1차와 겹쳐 PR은 생성되지 않음 |

→ Lab 3은 **다른 조사가 진행 중이지 않을 때 먼저 시작**해야 합니다. 가이드의 Lab 3 페이지와 메인 에이전트 실습 페이지에 순서를 명시했습니다.

## 진행자 조치 사항

1. **Lab 3 → 메인 에이전트 실습 순서를 지키게 하세요.** Lab 3은 진행 중인 조사를 재사용합니다.
2. **조사 시간이 12–25분입니다.** 메인 에이전트 실습의 `start` 는 1:25에 바로 하게 하고, 1:50까지 안 끝난 참가자는 진행자 화면의 결과로 토론을 진행합니다. 참가자는 나중에 `finish` 를 다시 실행하면 결과를 받습니다.
3. **확장 B(MCP)를 라이브로 보여줄 수 있습니다.** 진행자 계정에서 미리 `deploy.sh` → `register.sh` 를 해 두고, **광고 조사가 없는 상태에서** -26% 알림을 웹훅으로 보내 *"EXPECTED_EVENT — not an incident"* 결론 화면을 확보하세요. 참가자 계정에서는 메인 에이전트 실습 직후라 `LINKED` 됩니다.
4. **조사 대상 계정의 기존 리소스:** 에이전트는 계정에 있는 모든 리소스를 후보로 탐색합니다. 진행자 데모 계정에는 데모와 관계없는 리소스를 두지 마세요.

## 이전 검증 (일반 계정, 2026-10-11)

워크샵 스택이 없는 일반 계정에서 먼저 검증했습니다. 그 계정에서는 MCP·A2A 등록이 *"Only external accounts and exempted accounts are allowed at this time"* 로 거부되었습니다. Workshop Studio 계정에서는 이 제한이 없었습니다. 웹훅 HMAC 서명이 공식 문서의 openssl 방식(`base64(HMAC-SHA256(secret, "{ts}:{body}"))`)과 일치하는 것도 이때 확인했습니다.
