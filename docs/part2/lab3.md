# Lab 3: DevOps Agent를 tool로 쓰는 멀티에이전트 (1:20–1:25 실행, 결과는 1:45 전후)

## 0. 환경 리셋 (휴식 직전, VS Code IDE 터미널) {#reset}

주문 서비스 코드를 원래의 버그 상태로 CodeCommit에 다시 올립니다. 그러면 CodePipeline이 **약 7분** 동안 돕니다. 실행해 두고 쉬세요.

!!! warning "브라우저의 **VS Code IDE** 탭 터미널에서 실행하세요"
    내 PC(Mac/Windows) 터미널이나 CloudShell에서 실행하면 `cp: lab-1/...: No such file or directory` 가 납니다. Lab 1 원본 코드(`/workshop/lab-1`)가 IDE 서버에만 있기 때문입니다.

```bash
pip install git-remote-codecommit
cd /workshop/lab-1/order-processing &&
R=/tmp/order-api-reset && rm -rf $R &&
git clone codecommit::us-east-1://order-api $R &&
cp src/app.js $R/src/app.js &&
cp src/validators/orderValidator.js $R/src/validators/orderValidator.js &&
cp package.json $R/package.json &&
cd $R && git add -A &&
git commit -m "Reset to original code for Lab 3 investigation" && git push origin main
```

명령이 `&&` 로 이어져 있어 중간에 실패하면 거기서 멈춥니다.

!!! note "\"nothing to commit, working tree clean\" 이 나와도 정상입니다"
    이 워크샵은 원본의 Lab 2(코드 수정)를 건너뛰므로 코드가 이미 버그 상태입니다. 그래도 위 명령은 그대로 실행하세요. 첫 줄의 `git-remote-codecommit` 이 아래 1번에서 필요합니다.

## 1. 실행

!!! info "Lab 3은 VS Code IDE 터미널에서 실행합니다"
    Lab 3 코드(`/workshop/lab-3`)와 대시보드가 IDE 서버에 있어서 CloudShell에서는 실행할 수 없습니다.

**새 터미널을 열었다면 먼저** (터미널마다 한 번):

```bash
# ① Workshop Studio 사이드바 → Get AWS CLI credentials → Mac/Linux 의 export 줄을 먼저 붙여 넣고 Enter
# ② 실습 값 불러오기 + 자격 증명 확인
source ~/.ext-workshop.env
aws sts get-caller-identity --query Arn --output text
```

```bash
cd /workshop/lab-3                # 이후 경로는 모두 이 폴더 기준

# 1) Agent Space ID 설정 (IDE에서 bootstrap을 실행하지 않았어도 동작)
AGENT_SPACE_ID=$(aws devops-agent list-agent-spaces --region us-east-1 \
  --query "agentSpaces[?name=='api-error-incident-space'].agentSpaceId | [0]" --output text)
# 위 명령이 안 되면: DevOps Agent 콘솔 → api-error-incident-space 에서 ID를 복사해 AGENT_SPACE_ID=<ID>
sed -i "s/<YOUR_AGENT_SPACE_ID>/${AGENT_SPACE_ID}/" .env
grep AGENT_SPACE_ID .env

# 2) 리셋된 코드 clone
rm -rf order-processing
git clone codecommit::us-east-1://order-api order-processing

# 3) 대시보드 실행
bash open-dashboard.sh     # 출력되는 EC2 URL을 복사 (pager가 뜨면 q)
python3 server.py
```

출력된 **EC2 URL**을 새 탭에서 열고 **Run SRE Agent** 를 누릅니다(기본값 그대로).

!!! warning "Lab 3을 먼저 시작하세요 (사전 검증에서 발견)"
    Lab 3 코드(`aidevops_client.py`)는 Agent Space에 **진행 중인 조사가 있으면 새로 만들지 않고 그 조사를 재사용**합니다. 메인 에이전트 실습이나 확장 A의 광고 알림 조사가 돌고 있을 때 Lab 3을 시작하면, Lab 3이 **엉뚱한 조사**(예: ad_impressions)를 분석하게 됩니다.

    - **순서:** Lab 3 **Run SRE Agent** → Live Output에 `No existing investigation found, creating new task...` 가 보이면 → 그다음 [메인 에이전트 실습](ext-router.md)의 `start`
    - Live Output에 `Reusing existing investigation` 이 보이면 무엇을 재사용했는지 확인하세요. Part 1의 ECS 조사(order-api)라면 괜찮습니다. 광고 조사라면 그 조사가 끝난 뒤 다시 실행합니다.

!!! tip "실행을 걸어 두고 바로 다음 실습으로"
    끝까지 10–15분 걸립니다. 실행 중에는 [메인 에이전트 실습](ext-router.md)을 진행하고, 그 실습의 조사를 기다리는 동안 이 탭으로 돌아와 아래 2·3번을 확인하세요. `server.py` 는 터미널 하나를 차지하므로 **새 터미널**을 열어 다음 실습을 하세요.

!!! warning "대시보드 링크 주의"
    VS Code가 띄우는 "Open in Browser" 알림 링크는 쓰지 마세요. CloudFront 프록시를 거쳐서 스트리밍이 동작하지 않습니다. 스크립트가 출력한 **EC2 URL** 을 쓰세요.

## 2. 코드 읽기 (메인 에이전트 실습의 조사를 기다리는 동안)

브라우저 IDE 왼쪽 탐색기에서 `/workshop/lab-3/` 를 엽니다. 위에서 아래로 호출 순서입니다.

| 단계 | 파일 | 볼 것 |
|---|---|---|
| 전체 흐름 | `sre-agent.py` | `handle_incident()`: [1/4]→[4/4] 에이전트를 차례로 부르고, 앞 결과를 다음 프롬프트에 넣는 Workflow 패턴. Remediation은 테스트가 실패하면 재시도 (`config.py` 의 `MAX_RETRIES`, 기본 10) |
| ① DevOps Agent | `agents/devops_agent.py` | `construct_investigation_prompt`, `investigate` tool (Strands `@tool`) |
| | `tools/investigation.py` | `investigate_incident()`: 조사 시작 → 폴링 → 결과 요약 |
| | `aidevops_client.py` | **DevOps Agent API를 boto3로 호출**하는 부분. `start_investigation()` 은 진행 중인 조사가 있으면 재사용하고 없으면 `create_task()` 로 새로 만듭니다. 우리 메인 에이전트에 tool로 붙일 때 참고할 코드 |
| ② Analysis | `agents/analysis_agent.py` | `analyze_code`, `search_codebase`: 키워드를 하드코딩하지 않고 LLM이 RCA를 읽고 직접 고름 (`tools/code_analysis.py`) |
| ③ Remediation | `agents/remediation_agent.py` | `apply_fix`, `run_test_suite`, `rollback_changes` (`tools/code_fixer.py`) |
| ④ PR | `agents/pr_agent.py` | `create_fix_branch`, `commit_fix`, `create_pull_request` (`tools/git_operations.py`) |
| 설정 | `config.py`, `.env` | 모델 ID, Agent Space ID, 재시도 횟수 |

!!! tip "핵심 관찰 포인트: Live Output"
    DevOps Agent 단계에서 `CLOUDWATCH describe alarms`, `ECS describe services`, `CODEPIPELINE list pipeline executions` 처럼 **에이전트가 실제로 호출하는 API가 실시간으로 보입니다.** 판단 근거가 이렇게 투명하게 보여야 결과를 믿을 수 있습니다.

## 3. 결과

| 단계 | 결과 |
|---|---|
| DevOps Agent | 메모리 누수와 OOM 원인 조사 |
| Analysis | 원인 2곳 식별: 크기 제한 없는 `validationCache`, 요청당 1MB 버퍼 |
| Remediation | 수정 → 부하 테스트 1,000/1,000 통과 (실패하면 재시도) |
| PR | CodeCommit에 PR 생성. 본문에 **조사 근거, 변경 사항, 테스트 결과** 포함 |

## 우리 구조에 대입하기

- 이 PR 본문이 **"왜 이 팀에 보냈는가"를 담는 근거 패키지의 원형**입니다. 도메인 팀에 라우팅할 때 다음을 함께 넘기는 형식을 Part 3에서 정합니다.
    - 증거 메트릭과 로그
    - 배제한 가설
    - Topology상의 경로
    - 변경 이력
- 우리 메인 에이전트에 `investigate` tool을 하나 추가하면 같은 구조가 됩니다. 판별과 라우팅은 기존 로직을 유지하면서 **조사만 DevOps Agent에 위임**할 수 있습니다.
