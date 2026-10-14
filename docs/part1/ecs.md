# ① ECS 장애 조사 (0:15–0:40)

원본: [Lab 1 · ECS Application Investigation](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab1/ecs-investigation) → *Trigger & Investigate* → *Review Mitigation*

**시나리오:** 프로모션 중에 주문 서비스(ECS `order-api`)가 장애를 겪었습니다. 지금은 자동 복구되어 정상으로 보이지만, 다음 세일 전에 원인을 알아야 합니다.

## 진행 순서와 관찰 포인트

| 단계 | 할 일 (원본 지침대로) | 눈여겨볼 것 |
|---|---|---|
| 1 | ECS 콘솔에서 `order-api` 상태 확인 | "지금은 괜찮아 보이는" 상태에서 조사를 시작하는 것이 실제 장애 대응과 같습니다 |
| 2 | Operator access → **Incidents** → 클러스터, 계정 ID, 시간 범위, 증상을 입력하고 **Start Investigation** | AWS Support plan 관련 오류는 무시해도 됩니다 (원본 안내) |
| 3 | **기다리는 동안(약 10–15분) Topology 탭 탐색** | 아래 "Topology에서 해볼 것" 참고 |
| 4 | Investigation timeline → **Root cause** | 에이전트가 **어떤 API를 왜 호출했고 무엇을 근거로 삼았는지** 보입니다 |
| 5 | **Generate mitigation plan** | 결과가 *"No immediate operational mitigation action can be identified"* 로 나옵니다 |
| 6 | **Agent-ready spec** → Copy spec / View details | 사람이 읽는 산출물과 에이전트가 쓰는 산출물이 따로 나옵니다 |

### Topology에서 해볼 것 {#topology}

- 그래프를 둘러보고, 채팅에 `Describe my application architecture` 라고 물어보세요.
- `order-api가 장애 나면 영향받는 리소스는?` 처럼 **영향 범위(blast radius)** 를 물어보세요.

!!! question "Q. Topology에는 매니지드 서비스만 들어가나요?"
    아닙니다. 매니지드 서비스뿐 아니라 EC2, 네트워크 같은 **AWS 인프라 전반**, 그리고 연동된 **타사 서비스**도 Topology에 포함될 수 있습니다.

## 결과를 읽는 법

**Root cause:** `POST /orders` 처리기가 요청마다 1MB 버퍼(`Buffer.alloc(1024*1024)`)를 만들어 크기 제한 없는 전역 캐시에 쌓습니다. 그래서 메모리가 계속 늘다가 결국 OOM(Exit Code 137)으로 태스크가 종료됩니다. 에이전트는 **코드와 `[MEMORY LEAK]` 로그**(RSS가 주문 수에 비례해 증가, V8 heap은 그대로)로 이를 확인하고, 태스크 정의의 모든 리비전에 같은 결함이 있다는 것까지 짚습니다.

!!! note "Exit Code 137(OOM)은 보통 나오지 않습니다 — 정상입니다"
    환경을 만들 때 파이프라인의 부하 테스트가 **한 번만** 돌기 때문에, 메모리는 약 324MB까지 찬 상태에서 멈춰 있고 1024MB 한도에 닿지 않습니다. 사전 검증에서는 환경 생성 20분 뒤와 14시간 뒤 모두 OOM이 없었습니다. 이때 에이전트는 다음처럼 보고합니다.

    - 누수: 코드, 두 태스크 정의 리비전, 파이프라인 LoadTest 실패 기록(*"unbounded cache detected (memory leak)"*)으로 **확정된 잠재 결함**
    - 신고된 5xx와 재시작: *"이 시간대 텔레메트리로는 확인되지 않는다"* 는 **investigation gap** 으로 따로 기록

    **확인한 것과 확인하지 못한 것을 구분해서 말하는 것** 자체가 볼 만한 장면입니다.

**Mitigation plan이 "조치 없음"인 이유:** 모든 태스크 정의 리비전에 같은 결함이 들어 있어서 롤백할 정상 버전이 없습니다. 운영 조치(재시작, 스케일링, 롤백)로는 해결되지 않는 **코드 결함**이라고 판단한 것입니다.

!!! success "신뢰성 관점에서 중요한 장면"
    에이전트가 해결책을 억지로 만들지 않고 **"운영 조치로는 해결할 방법이 없다"고 말합니다.** 대신 코드 수정용 spec을 넘깁니다. 도입을 검토할 때 이렇게 "모른다/못 한다"를 말하는 능력은 정확도만큼 중요합니다.

**Agent-ready spec:** `THE SYSTEM SHALL ...` 형식의 변경 요구사항 3개(크기 제한 캐시, 파이프라인에서 Test를 Deploy보다 먼저, ECS circuit breaker 롤백)와 수용 기준입니다. Claude Code나 Kiro CLI, 또는 Part 2에서 볼 멀티에이전트 시스템이 이 spec을 그대로 입력으로 씁니다.

## 우리 조직에 대입해 보기

- 이 시나리오의 학습 목표는 **코드 결함과 인프라 설정 문제의 구분**입니다. 이것이 곧 라우팅 근거가 됩니다. 코드 결함이면 **서비스 도메인 owner** 에게, 인프라 설정 문제면 **플랫폼/SRE 팀** 에게 보냅니다.
- Root cause 화면의 **근거 목록**이 "왜 이 팀으로 보냈는가"를 설명하는 재료입니다. Part 3에서 라우팅할 때 반드시 첨부할 근거 항목을 정합니다.
