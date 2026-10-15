# 진행자 가이드

## 운영 방식

```mermaid
flowchart TB
  P[진행자: Workshop Studio 이벤트 생성<br/>기존 공개 워크샵 그대로] --> A[참가자 계정 자동 프로비저닝<br/>IDE + cloudformation-template 스택]
  A --> B[참가자: 이 가이드 사이트를 따라 진행]
  B --> C[참가자 CloudShell 또는 IDE에서<br/>git clone + bootstrap.sh]
  D[진행자 데모 계정<br/>Lab 4·5 캡처] -.데모.-> B
```

- **워크샵을 새로 publish할 필요가 없습니다.** Workshop Studio에서 기존 공개 워크샵으로 이벤트만 만들면 됩니다.
- 참가자는 이 가이드를 보며 진행하고, 확장 실습 코드는 **CloudShell**(기본) 또는 VS Code IDE 터미널에서 `git clone` 으로 받습니다. 이 저장소가 public이라 인증이 필요 없습니다.
- 오프닝에서 **어느 환경을 쓸지 하나로 정해 안내**하세요. 기본은 콘솔 + CloudShell이고, VS Code는 Lab 3에서만 엽니다. 두 환경 모두 `bootstrap.sh` 이후 명령은 같습니다.

## 타이밍 시트

| 시각 | 진행자 행동 | 참가자 상태 | 백업 |
|---|---|---|---|
| 0:00 | 아젠다, 오늘의 네 가지 질문 → **Agent Space 생성 버튼부터 누르게** | 접속, Agent Space 생성 중 | 접속 문제: Event access code 재배포 |
| 0:10 | `git clone` + `bootstrap.sh` 안내 | 저장소 받기 | clone 실패 시 tarball 명령 |
| 0:15 | ECS 조사 시작 → **기다리는 동안 Topology 시연** | 조사 중 (약 10–15분) | 완료된 조사 화면 캡처 |
| 0:25 | Root cause → Mitigation(조치 없음 또는 임시 완화책, 실행마다 다름) → spec | 결과 확인 | |
| 0:40 | Webhook 발급 → Lambda 설정 → Method 1 트리거 | 설정 | 늦으면 Method 2 |
| 0:50 | 자동 생성된 조사 + 메타데이터, "외부 요인" 결론 → 판별 화두 | 결과 확인 | |
| 0:58 | RCA 반박 미니 실습, Q3·Q4·Q5 답변 | 채팅 재조사 | |
| 1:03 | **Lab 3 리셋 명령 실행 지시** → 휴식 | 리셋 실행 | |
| 1:10 | 패턴 설명 + 라우팅 토론 (10분) | 듣기 | |
| 1:20 | Lab 3 **Run SRE Agent** 를 **먼저** 누르게 하기 → Live Output에 `creating new task` 확인 | 대시보드 실행 | 대시보드 녹화본 |
| 1:25 | 메인 에이전트 실습: `router.py start` → -26%가 조사 없이 닫히는 것 확인 (조사 12–25분 시작) | 실습 | [사전 검증 결과](test-report.md#router) |
| 1:30 | 코드 읽기: `devops_agent_tool.py` (API 3개), `triage()`, `domain_agent.py` → Lab 3 대시보드의 Live Output 확인 | 코드 리뷰 | |
| 1:45 | `router.py finish --wait` → 도메인 에이전트의 ACCEPT/NEED_MORE_INFO 근거 읽기. 안 끝났으면 진행자 화면으로 | 실습 | 사전 검증 결과 화면 |
| 1:50 | `evaluate.py` 로 판별·라우팅 정확도 측정 → 도메인 기준 비교표로 토론 | 실습 | |
| 1:55 | Lab 4·5 핵심 화면 (Memory, trace), 확장 A·B 소개 | 시청 | trace 캡처 |
| 2:00 | Discovery 시작 | 토론 | |

## 사전 준비 체크리스트

**Workshop Studio**

- [ ] 이벤트 생성 (us-east-1). 참석자 수 + 여유 계정 확보, Event access code 준비
- [ ] 리허설로 소요 시간 확인 (사전 검증 실측: ECS 조사 약 12분, 메인 에이전트 실습의 조사 12–25분, Lab 3 전체 약 14분)
- [ ] 참가자 계정에서 MCP 등록 확인: `deploy.sh` → `register.sh` (사전 검증 Workshop Studio 계정에서는 성공) → [리스크](risks.md)
- [ ] 참가자 계정에서 `router.py start` 가 조사를 생성하는지 확인 (`create_backlog_task` 권한)
- [ ] 이벤트 계정에서 GitHub 접근(`git clone`)이 되는지 확인 (CloudShell, VS Code 각각)
- [ ] CloudShell에서 `bootstrap.sh` 가 Python 3.12 환경을 만드는지 확인 (`$EXT_PYTHON -V`)

**진행자 데모 계정 (D-1까지)**

- [ ] Lab 4 Runtime + Memory(Long-term, 과거 인시던트 시딩) + Observability 배포
- [ ] CloudWatch **Transaction Search** 활성화. span이 보이기까지 최대 10분이 걸리므로 미리 켜두기
- [ ] Lab 5 Reactive/Proactive 트리거 구성, PR이 생성된 화면 확보
- [ ] 확장 B: 진행자 계정에서 `deploy.sh` → `register.sh` 후 메인 에이전트 실습을 한 번 돌려, 조사 기록에 MCP tool(`get_metric_baseline` 등) 호출이 남은 화면 확보
- [ ] 확장 A+B: **광고 조사가 하나도 없는 Agent Space**에서 -26% 알림을 웹훅으로 보내 *"EXPECTED_EVENT — not an incident"* 결론 화면 확보. 메인 에이전트 실습 직후에 보내면 -62% 조사에 `LINKED` 되어 이 화면이 나오지 않습니다 → [확장 B의 4)](../part2/ext-mcp.md#effect)
- [ ] 백업 자료: 완료된 조사 화면, Lab 3 대시보드 녹화, trace 캡처

**참석자 사전 요청**

- [ ] 최근 인시던트 2–3건의 타임라인과 포스트모템
- [ ] 현재 에이전트 구조도, 라우팅 로직 개요

**오픈 아이템**

- [ ] 공개 사례 RCA 정확도 수치의 측정 기준 확인 후 공유
