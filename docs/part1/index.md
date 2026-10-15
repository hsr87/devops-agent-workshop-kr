# Part 1 · DevOps Agent 기본 기능 (0:15–1:05)

원본 워크샵 **Lab 1** 의 실습 환경으로 직접 실행합니다. 단계는 각 페이지에 모두 들어 있습니다.

| 시간 | 실습 | 원본 Lab | 필수 여부 |
|---|---|---|---|
| 0:15–0:40 | [① ECS 장애 조사](ecs.md): Topology, RCA, Mitigation, Agent-ready spec | Lab 1 · ECS Application Investigation | 필수 |
| 0:40–0:58 | [② 자동 트리거](proactive.md): Alarm → EventBridge → Lambda → Webhook | Lab 1 · Proactive Investigation | 필수 |
| 0:58–1:05 | [③ 피드백 루프](feedback.md): RCA 반박해 재조사 요청 | — | 필수 |

!!! info "이번 워크샵에서 건너뛰는 것"
    원본 **Lab 2(Claude Code로 코드 수정)** 는 건너뜁니다. Lab 1의 *Agent-ready spec* 화면으로 "조사 결과가 코드 수정 도구로 넘어가는 지점"만 확인합니다. 원본에도 Lab 3는 Lab 1·2를 건너뛰어도 진행할 수 있다고 되어 있습니다.

## Part 1을 마치면 답할 수 있는 것

- DevOps Agent는 **무엇을 보고**(메트릭, 로그, 배포, Topology) **어떻게 결론을 내리는가**
- **코드 결함**과 **인프라 설정 문제**를 어떻게 구분하고, 각각 어떤 산출물을 내는가
- 사람이 버튼을 누르지 않아도 **기존 알람에서 조사가 시작되게** 하려면 무엇이 필요한가
- 결과가 틀렸을 때 **어떻게 바로잡고, 그것이 다음 조사에 어떻게 반영되는가**

!!! warning "휴식(1:05) 직전에 꼭 하세요"
    Part 2의 Lab 3를 하려면 환경을 원래의 버그 상태로 되돌려야 합니다. 이때 CodePipeline이 **약 7분** 동안 돕니다.
    Part 1이 끝나면 [Lab 3 리셋 명령](../part2/lab3.md#reset)을 먼저 실행하고 쉬세요.
