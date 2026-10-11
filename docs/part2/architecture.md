# 멀티에이전트 패턴과 우리 구조 (1:10–1:25)

원본: [Lab 3 · Multi-Agent Architecture](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab3/multi-agent-architecture)

!!! warning "시작 전에 확인"
    휴식 직전에 [Lab 3 리셋](lab3.md#reset)을 실행했나요? 아직이라면 지금 실행하세요. CodePipeline이 약 7분 걸리므로, 이 설명을 듣는 동안 끝납니다.

## 왜 에이전트 하나로는 부족한가

| 문제 | 증상 |
|---|---|
| 컨텍스트 한계 | 조사 결과, 코드, 테스트 결과, Git 이력을 한 에이전트가 모두 들고 있어야 함 |
| 전문성 부족 | 인프라 분석, 코드 분석, 수정, 테스트, Git을 한 에이전트가 모두 처리 |
| 디버깅 어려움 | 어느 단계에서 틀렸는지, 어느 부분만 개선해야 하는지 알기 어려움 |

## 네 가지 패턴 (Strands Agents SDK)

| 패턴 | 경로를 누가 정하나 | 적합한 경우 | 우리 구조에 대입하면 |
|---|---|---|---|
| **Agents as Tools** | 오케스트레이터 LLM | 계층형 위임, 가장 빨리 만들 수 있음 | **메인+서브 에이전트 구조**가 여기에 해당. 메인이 도메인 서브에이전트를 tool처럼 호출 |
| **Graph** | 코드로 정의한 엣지와 조건 | 결정적인 분기, 반복, 명시적 통제 | "판별 → (장애면) RCA → 도메인 라우팅"처럼 **분기를 결정적으로** 만들고 싶을 때 |
| **Swarm** | 에이전트끼리 자율적으로 handoff | 원인이 여러 도메인에 얽힌 탐색 | 강력하지만 **판단 경로를 추적하고 검증하기 어려움** |
| **Workflow** | 정해진 의존성 순서 | 고정된 파이프라인 | 원본 SRE 파이프라인: 조사 → 분석 → 수정 → PR |

!!! question "토론: 지금 라우팅 결정은 누가 내리나요?"
    메인 에이전트의 LLM이 "어느 팀 문제인지"를 정한다면, 그 결정은 **재현하기도 측정하기도 어렵습니다.** 정확도를 측정하기 어려웠던 이유가 여기에 있을 수 있습니다.

    **제안하는 하이브리드 구조**

    1. **판별과 라우팅은 Graph로 결정적으로** 만듭니다. 판별 결과와 owner 매핑을 규칙으로 정하고, 각 분기의 입력과 출력을 기록합니다.
    2. **조사(RCA)는 DevOps Agent에 맡깁니다.** 텔레메트리, 배포, Topology를 상관 분석하는 일입니다.
    3. **도메인 검증은 서브에이전트가 합니다.** "정말 우리 문제인가"를 도메인 데이터로 확인하고 근거를 덧붙입니다.

    이렇게 나누면 단계마다 정답과 비교할 수 있어서 [정확도 평가](ext-eval.md)가 가능해집니다.

## 연결 방향 두 가지 {#a2a}

| | 기존 에이전트 → DevOps Agent | DevOps Agent → 기존 에이전트 |
|---|---|---|
| 방식 | DevOps Agent **API** 를 tool로 호출 (원본 Lab 3의 `aidevops_client.py`) | 기존 에이전트를 **원격 A2A 에이전트** 로 등록 (`register-service --service remoteagent`) |
| 주도권 | 기존 오케스트레이터가 흐름을 통제 | DevOps Agent가 조사하다가 필요할 때 도메인 에이전트에게 질의 |
| 적합한 경우 | 이미 오케스트레이션과 라우팅 로직이 있을 때 | 도메인 지식이 에이전트 형태로 이미 있을 때 |
| 인증 | IAM (SigV4) | API key / Bearer / OAuth client credentials |

```bash
# DevOps Agent CLI에서 지원하는 연동 유형 확인
aws devops-agent register-service help | grep -A16 "Possible values"
#   mcpserver, mcpserversigv4, remoteagent, remoteagentsigv4, eventChannel(webhook), ...
```

!!! question "Q. 모델을 고를 수 있나요? (다시)"
    DevOps Agent는 Tier만 고를 수 있습니다. 반면 Lab 3의 커스텀 에이전트는 모델을 직접 지정합니다(원본은 Claude Sonnet 계열). 비용과 성능을 세밀하게 조정해야 하는 단계는 커스텀 에이전트 쪽에서 모델을 고르면 됩니다.
