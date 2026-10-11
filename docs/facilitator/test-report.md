# 사전 검증 결과

워크샵 전에 실제 AWS 계정(us-east-1)에서 확장 실습을 끝까지 실행해 본 결과입니다. 실행일은 2026-10-11입니다. 계정 정보와 리소스 이름은 일반화했습니다.

## 요약

| # | 검증 항목 | 결과 | 비고 |
|---|---|---|---|
| 1 | Agent Space 생성, AWS 계정 연결 (CLI) | ✅ | `create-agent-space`, `associate-service --service-id aws` |
| 2 | Generic webhook 발급 (CLI) | ✅ | `register-service --service eventChannel` → `associate-service` 응답에 URL과 HMAC secret 포함 |
| 3 | **확장 A** `send_test_alert.py` → 웹훅 | ✅ | HTTP 200 `Webhook received` → 약 3초 뒤 `INVESTIGATION` 태스크 생성 |
| 4 | **확장 A** Lambda 배포(`deploy.sh`) → `aws lambda invoke` → 웹훅 | ✅ | 태스크 생성됨. 11분 전의 -26% 조사와 같은 장애로 판단되어 **`LINKED`** 처리 (아래 참고) |
| 5 | HMAC 서명이 공식 문서의 openssl 방식과 일치 | ✅ | `base64(HMAC-SHA256(secret, "{ts}:{body}"))` |
| 6 | **확장 B** MCP 서버 로컬 실행 + 스모크 테스트 | ✅ | initialize, notifications(202), tools/list, tools/call, 401 |
| 7 | **확장 B** Lambda + HTTP API 배포 + 원격 스모크 테스트 | ✅ | 6개 항목 모두 통과 |
| 8 | **확장 B** DevOps Agent에 MCP 등록 (`register.sh`) | ⚠️ **계정 정책으로 거부** | `AccessDeniedException: Only external accounts and exempted accounts are allowed at this time` |
| 9 | **확장 C** 결정적 지표 | ✅ | 판별 83.3%, 라우팅 75.0%, 오라우팅 25.0% (샘플 기준) |
| 10 | **확장 C** `--judge` (Bedrock Claude Opus 5.5) | ✅ | MATCH 2 / PARTIAL 1 / MISS 1, 근거 포함 |
| 11 | 참가자 흐름: 새로 clone → `bootstrap.sh` → 확장 B·C | ✅ | venv 생성과 패키지 설치 포함 |
| 12 | 가이드 사이트 `mkdocs build --strict` | ✅ | 경고 없음 |

## 실제 조사 결과에서 확인한 것 (MCP 미연결 상태)

`impressions-drop-during-match.json` (-26%) 알림으로 조사를 실행했습니다. 약 10분 뒤 완료되었고, 저널 레코드는 66건이었습니다.

- 에이전트가 `description` 의 **판별 가이드를 그대로 따랐습니다.** 그래서 경기 같은 외부 이벤트를 먼저 확인하려 했습니다.
- **가설 4개를 배제**했습니다(모두 근거 포함).
    - 배포·설정 변경: CloudTrail에 변경 없음
    - ECS 성능 저하: 해당 리소스 없음
    - API Gateway 장애: 5xx 없음
    - 그 밖의 서빙 경로: 해당 시간대에 트래픽 없음
- MCP가 연결되지 않은 것을 **`investigation_gap` 으로 명시적으로 기록**했습니다:
  > *"The event-context MCP tools (explain_deviation / list_external_events / get_service_owner) are not wired into this space … external-event context cannot be queried."*
- 결론적으로 장애를 단정하지 않았습니다. "야간 수요 감소일 가능성"을 언급하는 데 그쳤고, 사실상 **INCONCLUSIVE** 였습니다.

!!! success "워크샵 메시지로 쓰기 좋은 장면"
    비즈니스 맥락이 없으면 에이전트는 **인프라 가설을 성실하게 배제한 뒤 "판단할 정보가 부족하다"고 말합니다.** 억지로 결론을 내지 않습니다.
    판별 정확도를 높이는 것은 모델 성능이 아니라 **어떤 컨텍스트를 연결하느냐**의 문제라는 점을 보여줍니다. 그래서 확장 B와 Part 3의 연동 인벤토리가 필요합니다.

## 알림 자동 묶기 (LINKED)

-26% 알림을 보낸 지 11분 뒤에 Lambda 경로로 -62% 알림을 보냈습니다. 그 결과는 다음과 같습니다.

- 새 조사가 시작되지 않고 `status: LINKED` 가 되었습니다. `primaryTaskId` 는 첫 조사를 가리킵니다.
- 판단 근거(`statusReason`):
  > *"Same service (ads-serving), same metric (ad_impressions), same market (KR), same AWS account/region, and occurs within 11 minutes of the primary's start time, indicating a worsening of the same ongoing incident (drop deepened from -26% to -62%)."*
- 첫 조사는 새 정보를 반영해 다시 조사 대기(`PENDING_START`)로 돌아갔습니다.

→ 알림 폭주 상황에서 **중복 조사를 막고 악화 신호를 기존 조사에 합치는** 동작입니다. 워크샵에서 "알림 노이즈" 질문이 나오면 이 장면을 보여주세요. 반대로, 두 샘플의 판별 결과를 각각 비교하는 시연이라면 간격을 두고 보내야 합니다.

## 진행자 조치 사항

1. **MCP 등록 제한(8번):** Workshop Studio 이벤트 계정에서 `register.sh` 를 리허설로 실행해 보세요.
    - 막히면 확장 B는 **등록이 허용되는 별도 계정에서 진행자 데모**로 대체합니다.
    - 참가자는 로컬 서버와 `test_mcp.sh` 까지만 실습합니다.
2. **조사 소요 시간:** 웹훅 수신 후 시작까지 약 1분, 완료까지 약 10분이 걸렸습니다. 데모 일정에 반영하세요.
3. **조사 대상 계정의 기존 리소스:** 에이전트는 계정에 있는 **모든 리소스**를 후보로 탐색합니다. 데모 계정에는 데모와 관계없는 리소스가 없도록 정리해 두는 것이 좋습니다.
