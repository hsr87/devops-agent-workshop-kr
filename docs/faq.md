# FAQ

자주 받는 질문과 워크샵에서 답하는 시점입니다.

| # | 질문 | 짧은 답 | 자세히 |
|---|---|---|---|
| 1 | Topology에 매니지드 서비스만 들어가나요? | 아닙니다. AWS 인프라 전반과 연동된 타사 서비스까지 포함됩니다. | [Part 1 ①](part1/ecs.md#topology) |
| 2 | 자동 트리거 소스는? Grafana나 Slack도 되나요? | 대부분 됩니다. 기본 연동이 있고, 그 밖은 Generic webhook이나 MCP/A2A로 연결합니다. | [Part 1 ②](part1/proactive.md), [확장 A](part2/ext-alert.md) |
| 3 | 모델을 고를 수 있나요? 성능과 비용 최적화는? | 구체적인 모델은 고를 수 없고 Smart/Balanced Tier만 선택합니다. 모델을 고르고 싶은 단계는 커스텀 에이전트로 나눕니다. | [Part 1 ③](part1/feedback.md), [아키텍처](part2/architecture.md) |
| 4 | Self-evolving은 어떻게 동작하나요? regression 우려는? | 작업 이력과 피드백이 메모리에 저장됩니다. read-only라 운영 환경에 쓰기 영향은 없습니다. 품질 regression은 평가 루프로 감시합니다. | [Part 1 ③](part1/feedback.md), [확장 C](part2/ext-eval.md) |
| 5 | 결과가 틀렸을 때 피드백 루프는? | 채팅으로 재조사를 요청하면 Memory에 반영됩니다. 커스텀 에이전트, 스킬, 사내 MCP로 품질을 높입니다. | [Part 1 ③](part1/feedback.md), [확장 B](part2/ext-mcp.md) |
| 6 | 공개 사례의 RCA 정확도 94%는 어떤 기준인가요? 측정 기능이 내장되어 있나요? | 블로그에 세부 기준이 공개되지 않아 확인 후 공유하겠습니다. 평가 기능은 내장되어 있지 않아 따로 구성해야 합니다. | [확장 C](part2/ext-eval.md) |

## 추가 질문

??? question "Slack에서 누구나 질문할 수 있나요?"
    DevOps Agent는 **Slack 기본 연동**을 지원합니다. 조사 결과를 채널에 보낼 수 있고, Slack에서 조사를 시작할 수도 있습니다. "최근 24시간 비즈니스 메트릭 괜찮아?" 같은 질문에 답하려면 **비즈니스 메트릭을 조회할 수단이 연결되어 있어야** 합니다. 예: 메트릭 저장소 MCP, [확장 B](part2/ext-mcp.md)의 baseline. PoC 범위를 정할 때 함께 검토하세요.

??? question "웹훅 payload에 넣은 데이터가 왜 조사에 반영되지 않나요?"
    공식 문서에 따르면 `title`, `description`, `priority`, 인시던트 참조만 조사 컨텍스트로 들어갑니다. `data` 필드는 전달되지 않습니다. 필요한 정보는 `description` 에 글로 넣으세요. → [확장 A](part2/ext-alert.md#payload)

??? question "웹훅으로 200을 받았는데 조사가 시작되지 않아요."
    `incidentId` 와 `timestamp` 가 이전 요청과 같으면 중복으로 보고 무시합니다. 또는 payload 형식이 잘못되었을 수 있습니다. 200을 받았는데 조사가 바로 취소된다면 **월간 한도**에 도달했을 수 있습니다.

??? question "MCP 서버를 VPC 안에 둘 수 있나요?"
    공식 문서 기준으로 MCP 서버는 **공개 HTTPS** 로 접근할 수 있어야 하고 **Streamable HTTP** 를 지원해야 합니다. 인증은 API key, Bearer, OAuth, SigV4를 지원합니다. CLI에는 private connection 관련 옵션도 보이므로, 최신 문서에서 지원 범위를 확인하세요.
