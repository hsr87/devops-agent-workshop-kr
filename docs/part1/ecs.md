# ① ECS 장애 조사 (0:15–0:40)

**시나리오:** 프로모션 중에 주문 서비스(ECS `order-api`)가 장애를 겪었습니다. 지금은 자동 복구되어 정상으로 보이지만, 다음 세일 전에 원인을 알아야 합니다.

## 실습

### 1. 지금 상태 확인 (1분)

[ECS 콘솔](https://console.aws.amazon.com/ecs/v2/clusters?region=us-east-1) → 클러스터 `cloudformation-template-cluster` → **Services** 탭 → `order-api`

Running tasks `2/2`, 배포 상태 정상 — **지금은 멀쩡해 보입니다.** 실제 장애 대응도 대개 "이미 복구된 뒤"에 원인을 찾는 일입니다.

### 2. 조사 시작 (2분)

1. [DevOps Agent 콘솔](https://console.aws.amazon.com/aidevops/home?region=us-east-1) → `api-error-incident-space` → **View details**
2. 오른쪽 위 **Operator access** → **IAM을 통해 시작** (영어 콘솔: *Launch with IAM*) → 새 탭에서 웹앱이 열립니다. Workshop Studio 계정은 IAM Identity Center가 없으므로 IAM 방식을 고릅니다.
3. 왼쪽 메뉴 **Incidents** → **Start an investigation** 입력창에 아래를 붙여 넣습니다. `<계정ID>` 는 콘솔 오른쪽 위 계정 메뉴에 보이는 12자리 숫자로 바꿉니다(터미널에서는 `aws sts get-caller-identity --query Account --output text`).

    ```text
    ECS Cluster: cloudformation-template-cluster
    AWS Account ID: <계정ID>
    AWS Region: us-east-1
    Time window: Past 24 hours
    Issue: Service unavailability - customers unable to place orders. Cluster appears healthy now but experienced failures earlier.
    ```

4. **Start Investigation** → 추가 입력 창은 비워 둔 채 **Start Investigating**

!!! note "AWS Support plan 관련 오류가 보여도 무시하세요"
    실습 계정에 Support plan이 없어서 나오는 메시지이고, 조사에는 영향이 없습니다.

### 3. 기다리는 동안 (약 10–15분) — Topology 탭 {#topology}

웹앱의 **Topology** 탭을 엽니다.

- 그래프를 둘러보고, 채팅에 `Describe my application architecture` 라고 물어보세요.
- `order-api가 장애 나면 영향받는 리소스는?` 처럼 **영향 범위(blast radius)** 를 물어보세요.

!!! question "Q. Topology에는 매니지드 서비스만 들어가나요?"
    아닙니다. 매니지드 서비스뿐 아니라 EC2, 네트워크 같은 **AWS 인프라 전반**, 그리고 연동된 **타사 서비스**도 Topology에 포함될 수 있습니다.

### 4. 결과 보기

1. 조사가 끝나면 **Go to root cause** (또는 **Root cause** 탭)
2. 위쪽 탭 **Investigation timeline** 에서 에이전트가 **어떤 API를 왜 호출했고 무엇을 근거로 삼았는지** 봅니다.
3. **Root cause** 탭 위쪽 배너의 **Generate mitigation plan** → 1–2분 뒤 **Mitigation plan** 탭에 결과가 나옵니다.
4. **Agent-ready spec** 영역에서 **Copy spec**, **View details** 를 눌러 봅니다.

## 결과를 읽는 법

**Root cause:** `POST /orders` 처리기가 요청마다 1MB 버퍼(`Buffer.alloc(1024*1024)`)를 만들어 크기 제한 없는 전역 캐시에 쌓습니다. 그래서 메모리가 계속 늘다가 결국 OOM(Exit Code 137)으로 태스크가 종료됩니다. 에이전트는 **코드와 `[MEMORY LEAK]` 로그**(RSS가 주문 수에 비례해 증가, V8 heap은 그대로)로 이를 확인하고, 태스크 정의의 모든 리비전에 같은 결함이 있다는 것까지 짚습니다.

!!! note "Exit Code 137(OOM)은 보통 나오지 않습니다 — 정상입니다"
    환경을 만들 때 파이프라인의 부하 테스트가 **한 번만** 돌기 때문에, 메모리는 약 324MB까지 찬 상태에서 멈춰 있고 1024MB 한도에 닿지 않습니다. 사전 검증에서는 환경 생성 20분 뒤와 14시간 뒤 모두 OOM이 없었습니다. 이때 에이전트는 다음처럼 보고합니다.

    - 누수: 코드, 두 태스크 정의 리비전, 파이프라인 LoadTest 실패 기록(*"unbounded cache detected (memory leak)"*)으로 **확정된 잠재 결함**
    - 신고된 5xx와 재시작: *"이 시간대 텔레메트리로는 확인되지 않는다"* 는 **investigation gap** 으로 따로 기록

    **확인한 것과 확인하지 못한 것을 구분해서 말하는 것** 자체가 볼 만한 장면입니다.

**Mitigation plan은 실행마다 다르게 나올 수 있습니다.** 조사 시점의 상태(알람 조사가 묶였는지, 재시작 흔적이 있는지 등)에 따라 둘 중 하나로 나옵니다.

- *"No immediate operational mitigation action can be identified"*: 모든 리비전에 같은 결함이 있어 롤백할 정상 버전이 없으므로 운영 조치로는 해결할 수 없다는 판단
- 재시작, 메모리 상향 같은 **임시 완화책** + "근본 해결은 코드 수정"

어느 쪽이든 핵심은 같습니다. 에이전트가 **근본 원인이 코드 결함**이라는 점과, 운영 조치는 시간을 버는 것뿐이라는 점을 구분해서 말합니다.

!!! success "신뢰성 관점에서 중요한 장면"
    에이전트가 운영 조치로 근본 해결이 되는 것처럼 말하지 않고, **코드 수정용 spec을 따로 넘깁니다.** 도입을 검토할 때 이렇게 "모른다/못 한다"를 말하는 능력은 정확도만큼 중요합니다.

**Agent-ready spec:** `THE SYSTEM SHALL ...` 형식의 변경 요구사항 3개(크기 제한 캐시, 파이프라인에서 Test를 Deploy보다 먼저, ECS circuit breaker 롤백)와 수용 기준입니다. Claude Code나 Kiro CLI, 또는 Part 2에서 볼 멀티에이전트 시스템이 이 spec을 그대로 입력으로 씁니다.

## 우리 조직에 대입해 보기

- 이 시나리오의 학습 목표는 **코드 결함과 인프라 설정 문제의 구분**입니다. 이것이 곧 라우팅 근거가 됩니다. 코드 결함이면 **서비스 도메인 owner** 에게, 인프라 설정 문제면 **플랫폼/SRE 팀** 에게 보냅니다.
- Root cause 화면의 **근거 목록**이 "왜 이 팀으로 보냈는가"를 설명하는 재료입니다. Part 3에서 라우팅할 때 반드시 첨부할 근거 항목을 정합니다.
