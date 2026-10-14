# AWS DevOps Agent 실습 워크샵 (한국어 진행 가이드 + 확장 실습)

AWS 공개 워크샵 **[Extend Your Operations with Autonomous SRE](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US)** 의 실습 환경을 그대로 쓰면서, 3시간 진행 경로와 확장 실습을 얹은 저장소입니다.

- **가이드 사이트:** https://hsr87.github.io/devops-agent-workshop-kr/
- **구성:** Part 1 기본 기능 (Lab 1) → Part 2 기존 Agent 연결 (Lab 3 + Lab 4·5 데모 + 확장 실습) → Part 3 Discovery

## 참가자: AWS 콘솔의 CloudShell(또는 VS Code IDE 터미널)에서

```bash
cd ~
git clone https://github.com/hsr87/devops-agent-workshop-kr.git ext
bash ext/scripts/bootstrap.sh
source ~/.ext-workshop.env
```

## 확장 실습

| 디렉터리 | 내용 |
|---|---|
| [`extensions/alert-forwarder`](extensions/alert-forwarder) | 비즈니스 메트릭 알림/CloudWatch 알람을 DevOps Agent generic webhook(HMAC/API key)으로 전달 |
| [`extensions/event-context-mcp`](extensions/event-context-mcp) | 외부 이벤트·계절성 baseline·서비스 owner를 제공하는 MCP 서버 (Streamable HTTP, 의존성 없음) |
| [`extensions/triage-router`](extensions/triage-router) | 메인 에이전트 예제: 결정적 판별 → DevOps Agent API로 RCA → 라우팅 → 도메인 에이전트 검증 |
| [`extensions/rca-eval`](extensions/rca-eval) | 판별·라우팅·RCA 정확도 평가 (+ Bedrock Claude 채점기) |

## 로컬에서 사이트 미리보기

```bash
pip install -r requirements-docs.txt && mkdocs serve
```

원본 워크샵 콘텐츠는 이 저장소에 포함하지 않으며 링크로만 참조합니다.
