# Lab 4·5 데모: 운영 환경에서의 연결 (1:45–1:55)

!!! info "이 파트는 진행자 데모입니다"
    원본 Lab 4는 IAM 설정 단계가 많고 실행 한 번에 10분 이상 걸립니다. Lab 5는 Lab 4가 끝나야 진행할 수 있습니다. 그래서 진행자가 **미리 배포해 둔 환경**으로 결과만 보여드립니다. 워크샵 후에 원본 [Lab 4](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab4)와 [Lab 5](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab5)를 직접 해볼 수 있습니다.

## 1. 같은 에이전트, 다른 트리거 (Lab 5)

| | Reactive | Proactive |
|---|---|---|
| 트리거 | CloudWatch Alarm (운영 장애) | CodePipeline **Test 단계 실패** |
| 시점 | 장애가 시작된 뒤 | 운영에 반영되기 전 |
| 목표 | MTTR 최소화 | 장애 자체를 예방 |
| 호출 | `invoke_agent_runtime()` | `invoke_agent_runtime()` (같은 엔드포인트) |

> 에이전트 시스템은 그대로 두고 **연결 방식만 바뀝니다.** 기존 알림 시스템이나 CI/CD에 붙일 때도 같은 원리입니다.

## 2. 사건을 넘어 기억하기: AgentCore Long-term Memory (Lab 4 Part D)

- **Short-term:** 한 사건 안에서 4개 에이전트가 같은 대화 흐름을 공유합니다.
- **Long-term (Semantic):** 대화에서 사실을 자동으로 뽑아 저장하고, 다음 사건 때 검색해서 프롬프트에 넣어줍니다. 예: *"지난달 order-api 메모리 누수는 unbounded cache 때문이었다"*

!!! note "두 가지 메모리를 구분하세요"
    - **DevOps Agent 내장 Memory:** 조사 이력과 피드백이 서비스 안에 쌓입니다(Part 1).
    - **AgentCore Memory:** 직접 만든 커스텀 에이전트에 붙이는 메모리입니다.

    피드백 루프를 커스텀 에이전트 쪽에서도 구현하고 싶을 때 AgentCore Memory를 씁니다.

## 3. 판단 경로를 감사하기: AgentCore Observability (Lab 4 Part E)

CloudWatch **GenAI Observability** 대시보드에서 볼 수 있는 것:

- 4개 에이전트의 **trace tree**, 단계별 소요 시간, 병목 (예: `run_test_suite` 80초)
- 에이전트마다 호출한 tool, 입력과 출력

!!! success "신뢰성과 연결"
    "왜 이 팀에 보냈는가"를 나중에 감사할 수 있는 **원천 데이터**입니다. 이 trace에 정답 라벨을 붙이면 [정확도 평가](ext-eval.md)의 입력이 됩니다.

## 4. 평가와 통제

AgentCore의 세 기둥 중 **Observability · Evaluations · Policy** 를 다룹니다.

- **Evaluations:** 에이전트 품질을 주기적으로 평가합니다. DevOps Agent에는 **평가 기능이 내장되어 있지 않으므로** 별도로 구성해야 합니다.
- **Policy:** tool 호출을 실행 전에 결정적으로 차단하거나 허용합니다. 예: "수정 에이전트는 `src/` 아래만 수정할 수 있다"
