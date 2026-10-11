# Discovery 템플릿

복사해서 화이트보드나 공유 문서에 붙여 쓰세요.

## A. 인시던트 타임라인

| 시각 | 단계 | 무슨 일이 있었나 | 누가 | 걸린 시간 | 자동화 후보 |
|---|---|---|---|---|---|
| | 감지 | (어떤 알림이 울렸나) | | | Webhook 트리거 |
| | 판별 | (진짜 장애라고 확신한 근거) | | | 이벤트 컨텍스트 MCP |
| | 원인 탐색 | (어떤 대시보드와 로그를 봤나) | | | Investigation |
| | 라우팅 | (어느 팀에 몇 번 넘겼나) | | | owner 매핑 + 근거 패키지 |
| | 복구 | (무엇을 했나) | | | Mitigation plan / spec |

## B. 연동 매트릭스

| 데이터/시스템 | 현재 위치 | 분류 (기본/Webhook/MCP/A2A/미보유) | 담당 | 비고 |
|---|---|---|---|---|
| 비즈니스 메트릭 알림 | | | | |
| 인프라 메트릭·로그 | | | | |
| 트레이스 | | | | |
| 배포 이력 / CI/CD | | | | |
| 이벤트 캘린더 (경기·프로모션·공휴일) | | | | |
| 서비스 카탈로그 / owner | | | | |
| 기존 에이전트 (메인/서브) | | | | |
| 커뮤니케이션 채널 (Slack 등) | | | | |

## C. 평가 기준 (초안)

| 항목 | 정의 | 목표치 | 측정 주기 |
|---|---|---|---|
| 판별 정확도 | INCIDENT vs EXPECTED_EVENT 일치율 | | |
| 놓친 장애율 | 실제 장애를 EXPECTED_EVENT로 판정한 비율 | | |
| 라우팅 정확도 | owner 팀 일치율 (실제 장애 기준) | | |
| RCA 일치도 | MATCH (+PARTIAL?) 비율 | | |
| 근거 첨부율 | 필수 근거 항목을 모두 갖춘 비율 | | |
| MTTD / MTTR | 알림 → 판별 / 알림 → 원인 확정 시간 | | |

## D. 라우팅 근거 패키지 (필수 항목 후보)

```yaml
incident_id:
verdict: INCIDENT | EXPECTED_EVENT | INCONCLUSIVE
owner_team:
confidence: high | medium | low
evidence:            # 이 팀이라고 판단한 근거 (메트릭, 로그, trace 링크)
  - 
ruled_out:           # 배제한 가설과 그 근거
  - hypothesis:
    reason:
topology_path:       # 증상 → 원인 컴포넌트 경로
change_history:      # 관련 배포와 설정 변경
external_context:    # 동시간대 이벤트 (explain_deviation 결과)
next_action:
```

## E. Use case 2x2

|  | **실현 쉬움** | **실현 어려움** |
|---|---|---|
| **Impact 큼** | (먼저 PoC) | (단계적 접근) |
| **Impact 작음** | (빠른 성과) | (보류) |
