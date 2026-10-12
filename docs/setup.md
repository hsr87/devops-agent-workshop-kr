# 환경 준비 (0:00–0:15)

실습 환경은 **Workshop Studio가 미리 만들어 둔 것**을 그대로 씁니다. 따로 설치할 것은 없습니다.

## 1. Workshop Studio 접속

원본: [Setup your workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/getting-started)

1. 진행자가 안내한 Workshop Studio 링크에 접속합니다.
2. **Email one-time-password (OTP)** 로 로그인합니다.
3. 12자리 **Event access code** 를 입력하고 약관에 동의한 뒤 **Join event** 를 누릅니다.
4. 왼쪽 사이드바에서 **Open AWS console** 과 **VS Code IDE** 를 각각 새 탭으로 엽니다.

임시 AWS 계정, VS Code IDE, CLI 도구(AWS CLI, Git, Python, Claude Code, Kiro CLI), 실습 인프라(`devops-mttr-workshop` 스택)가 모두 준비되어 있습니다.

## 2. Agent Space 만들기 — 가장 먼저!

원본: [Setup your AWS environment → Step 1](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/getting-started/3-setup-aws)

[AWS DevOps Agent 콘솔](https://console.aws.amazon.com/aidevops/home?region=us-east-1) → **Begin setup**

| 항목 | 값 |
|---|---|
| Name | `api-error-incident-space` |
| Description | `Investigate order API failures` |
| Role | Auto-create a new DevOps Agent role (기본값) |

!!! note "만드는 데 1–2분이 걸립니다"
    **Create** 버튼을 먼저 누르고, 기다리는 동안 다음 단계를 진행하세요. 나머지 Lab도 모두 이 이름을 기준으로 진행합니다.

## 3. 이 저장소 내려받기 (VS Code IDE 터미널)

```bash
cd /workshop
git clone https://github.com/hsr87/devops-agent-workshop-kr.git ext
bash ext/scripts/bootstrap.sh
source ~/.ext-workshop.env
```

`bootstrap.sh` 는 아래를 점검하고 `~/.ext-workshop.env` 에 값을 저장합니다.

- AWS 계정과 워크샵 스택 상태
- Agent Space ID (Part 2 Lab 3, 메인 에이전트 실습, 확장 실습에서 사용)
- 확장 실습용 Python 패키지 (`ext/.venv`)

!!! tip "새 터미널을 열 때마다"
    `source ~/.ext-workshop.env` 를 다시 실행하세요.

??? question "git clone이 막혀 있다면?"
    아래처럼 압축 파일로 내려받아도 됩니다.
    ```bash
    cd /workshop && curl -sL https://github.com/hsr87/devops-agent-workshop-kr/archive/refs/heads/main.tar.gz | tar xz
    mv devops-agent-workshop-kr-main ext && bash ext/scripts/bootstrap.sh
    ```

## 저장소 구성

```
ext/
├── docs/                      # 이 가이드 사이트 원본
├── extensions/
│   ├── alert-forwarder/       # 확장 A: 비즈니스 메트릭 알림 → DevOps Agent 웹훅
│   ├── event-context-mcp/     # 확장 B: 외부 이벤트·baseline·서비스 owner MCP 서버
│   ├── triage-router/         # Part 2 메인 실습: 기존 메인 에이전트에 DevOps Agent 붙이기
│   └── rca-eval/              # 확장 C: 판별·라우팅·RCA 정확도 평가
└── scripts/
    ├── bootstrap.sh
    └── cleanup-extensions.sh  # 확장 실습 리소스 정리 (원본 스택·Agent Space는 그대로)
```
