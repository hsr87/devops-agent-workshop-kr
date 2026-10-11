# Lab 3 실습: DevOps Agent를 tool로 쓰는 멀티에이전트 (1:25–1:45)

원본: [Lab 3 · Build Autonomous Agents](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab3/build-autonomous-agents) → [Run & Observe the Workflow](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab3/run-and-observe)

## 0. 환경 리셋 (휴식 직전) {#reset}

원본 [Lab 3 첫 페이지](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab3)의 **"First: Reset the Environment"** 명령을 그대로 실행합니다. 원래의 버그 코드를 CodeCommit에 다시 push하면 파이프라인이 약 7분 동안 돕니다.

!!! note "Lab 1·2를 건너뛴 경우"
    "nothing to commit, working tree clean" 이 나와도 정상입니다. 이 단계에서 설치되는 `git-remote-codecommit` 이 이후에 필요하므로 명령은 그대로 실행하세요.

## 1. 실행

```bash
# 1) Agent Space ID 설정 (bootstrap이 찾아 둔 값 사용)
source ~/.ext-workshop.env
sed -i "s/<YOUR_AGENT_SPACE_ID>/${AGENT_SPACE_ID}/" /workshop/lab-3/.env
grep AGENT_SPACE_ID /workshop/lab-3/.env

# 2) 리셋된 코드 clone
rm -rf /workshop/lab-3/order-processing
git clone codecommit::us-east-1://order-api /workshop/lab-3/order-processing

# 3) 대시보드 실행
cd /workshop/lab-3
bash open-dashboard.sh     # 출력되는 EC2 URL을 복사 (pager가 뜨면 q)
python3 server.py
```

출력된 **EC2 URL**을 새 탭에서 열고 **Run SRE Agent** 를 누릅니다(기본값 그대로).

!!! warning "대시보드 링크 주의"
    VS Code가 띄우는 "Open in Browser" 알림 링크는 쓰지 마세요. CloudFront 프록시를 거쳐서 스트리밍이 동작하지 않습니다. 스크립트가 출력한 **EC2 URL** 을 쓰세요.

## 2. 기다리는 동안 (10–15분): 코드 읽기

| 파일 | 볼 것 |
|---|---|
| `agents/devops_agent.py` | `construct_investigation_prompt`, `investigate` tool → **DevOps Agent API를 boto3로 호출**하고 10초마다 결과를 폴링 |
| `aidevops_client.py` | API 호출부. 우리 메인 에이전트에 **tool 하나로 추가**할 때 그대로 참고할 코드 |
| `sre-agent.py` | `handle_incident()`: 앞 에이전트의 결과가 다음 에이전트의 프롬프트로 들어가는 Workflow 패턴 |
| `agents/analysis_agent.py` | `search_codebase`: 키워드를 하드코딩하지 않고 LLM이 RCA를 읽고 직접 고름 |

!!! tip "핵심 관찰 포인트: Live Output"
    DevOps Agent 단계에서 `CLOUDWATCH describe alarms`, `ECS describe services`, `CODEPIPELINE list pipeline executions` 처럼 **에이전트가 실제로 호출하는 API가 실시간으로 보입니다.** 판단 근거가 이렇게 투명하게 보여야 결과를 믿을 수 있습니다.

## 3. 결과

| 단계 | 결과 |
|---|---|
| DevOps Agent | 메모리 누수와 OOM 원인 조사 |
| Analysis | 원인 2곳 식별: 크기 제한 없는 `validationCache`, 요청당 1MB 버퍼 |
| Remediation | 수정 → 부하 테스트 1,000/1,000 통과 (실패하면 최대 3회 재시도) |
| PR | CodeCommit에 PR 생성. 본문에 **조사 근거, 변경 사항, 테스트 결과** 포함 |

## 우리 구조에 대입하기

- 이 PR 본문이 **"왜 이 팀에 보냈는가"를 담는 근거 패키지의 원형**입니다. 도메인 팀에 라우팅할 때 다음을 함께 넘기는 형식을 Part 3에서 정합니다.
    - 증거 메트릭과 로그
    - 배제한 가설
    - Topology상의 경로
    - 변경 이력
- 우리 메인 에이전트에 `investigate` tool을 하나 추가하면 같은 구조가 됩니다. 판별과 라우팅은 기존 로직을 유지하면서 **조사만 DevOps Agent에 위임**할 수 있습니다.
