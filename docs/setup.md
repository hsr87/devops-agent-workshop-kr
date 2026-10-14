# 환경 준비 (0:00–0:15)

실습 환경은 **Workshop Studio가 미리 만들어 둔 것**을 그대로 씁니다. 따로 설치할 것은 없습니다.

## 1. Workshop Studio 접속

<img src="../assets/join-qr.jpeg" alt="워크샵 참가 QR 코드" width="160" align="right">

1. **[https://bit.ly/4hTUWKA](https://bit.ly/4hTUWKA)** 에 접속하거나 오른쪽 QR 코드를 스캔합니다. Event access code가 링크에 들어 있어 따로 입력하지 않아도 됩니다.
2. **Email one-time-password (OTP)** 로 로그인합니다.
3. 약관에 동의하고 **Join event** 를 누릅니다. (access code를 묻는 화면이 나오면 진행자가 화면에 띄운 코드를 입력)
4. 왼쪽 사이드바에서 **Open AWS console** 을 새 탭으로 엽니다. **VS Code IDE** 는 Part 2의 Lab 3에서만 씁니다.

임시 AWS 계정, VS Code IDE, 실습 인프라(CloudFormation 스택 `cloudformation-template`)가 모두 준비되어 있습니다.

!!! info "명령은 어디서 실행하나요? (두 가지 중 하나만 고르세요)"
    | | 콘솔 + CloudShell (기본) | VS Code IDE |
    |---|---|---|
    | 여는 법 | AWS 콘솔 위쪽 막대의 **CloudShell 아이콘** (`>_`), 리전 **us-east-1** | Workshop Studio 사이드바 → **VS Code IDE** → Terminal |
    | 쓰는 곳 | Part 1 명령, 확장 실습 전부 | 위와 같음 |
    | Lab 3 | **VS Code IDE에서만** 가능 (Lab 3 코드와 대시보드가 IDE 서버에 있음) | 그대로 |

    두 환경 모두 아래 3번의 `bootstrap.sh` 를 실행하면 이후 명령은 똑같습니다.

## 2. Agent Space 만들기 — 가장 먼저!

[AWS DevOps Agent 콘솔](https://console.aws.amazon.com/aidevops/home?region=us-east-1) → **Begin setup**

| 항목 | 값 |
|---|---|
| Name | `api-error-incident-space` |
| Description | `Investigate order API failures` |
| Role | Auto-create a new DevOps Agent role (기본값) |

!!! note "만드는 데 1–2분이 걸립니다"
    **Create** 버튼을 먼저 누르고, 기다리는 동안 다음 단계를 진행하세요. 나머지 Lab도 모두 이 이름을 기준으로 진행합니다.

## 3. 이 저장소 내려받기

=== "콘솔 + CloudShell"

    ```bash
    cd ~
    git clone https://github.com/hsr87/devops-agent-workshop-kr.git ext
    bash ext/scripts/bootstrap.sh
    source ~/.ext-workshop.env
    ```

    - CloudShell의 기본 Python은 3.9입니다. `bootstrap.sh` 가 처음 한 번 **Python 3.12 환경을 자동으로 설치**합니다(약 1분).
    - 홈 디렉터리(`~`)는 CloudShell을 닫았다 열어도 유지됩니다.
    - 20–30분 동안 입력이 없으면 세션이 끊깁니다. 다시 열고 `source ~/.ext-workshop.env` 만 실행하면 됩니다.

=== "VS Code IDE"

    ```bash
    cd /workshop
    git clone https://github.com/hsr87/devops-agent-workshop-kr.git ext
    bash ext/scripts/bootstrap.sh
    source ~/.ext-workshop.env
    ```

`bootstrap.sh` 는 아래를 점검하고 `~/.ext-workshop.env` 에 값을 저장합니다.

- AWS 계정과 워크샵 스택 상태
- Agent Space ID (메인 에이전트 실습, 확장 실습에서 사용)
- 확장 실습용 Python 환경 (`ext/.venv`, Python 3.10 이상)
- 저장소 위치 `$EXT_REPO` — 이후 모든 명령은 `cd $EXT_REPO/...` 로 시작하므로 어느 환경이든 같습니다

!!! tip "새 터미널을 열 때마다"
    `source ~/.ext-workshop.env` 를 다시 실행하세요. CloudShell 탭을 새로 열 때도 마찬가지입니다.

??? question "git clone이 막혀 있다면?"
    아래처럼 압축 파일로 내려받아도 됩니다.
    ```bash
    cd ~ && curl -sL https://github.com/hsr87/devops-agent-workshop-kr/archive/refs/heads/main.tar.gz | tar xz
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
