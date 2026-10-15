# ② 자동 트리거 · Proactive Investigation (0:40–0:58)

```mermaid
flowchart LR
  A[CloudWatch Alarm<br/>API Gateway 5xx] --> B[EventBridge Rule] --> C[Lambda<br/>webhook forwarder] -->|HMAC 서명| D[DevOps Agent<br/>Webhook] --> E[Investigation<br/>자동 시작]
```

CloudWatch 알람, EventBridge 규칙, forwarder Lambda는 **이미 배포되어 있습니다.** 할 일은 웹훅을 발급해 Lambda에 넣고 알람을 울리는 것뿐입니다.

## 실습

### 1. 웹훅 발급 (콘솔, 2분)

1. [DevOps Agent 콘솔](https://console.aws.amazon.com/aidevops/home?region=us-east-1) → `api-error-incident-space` → **기능** 탭 (영어 콘솔: *Capabilities*)
2. **Webhooks** → **Add Webhook** → **Next** → **Next** → **Generate URL and secret key**
3. **.csv 파일을 다운로드**하고 *"I've saved and stored my URL and secret key"* 를 체크합니다.

!!! important "Secret은 이때 한 번만 보입니다"
    .csv 파일을 꼭 받아 두세요. Part 2의 [확장 A](../part2/ext-alert.md)에서도 같은 웹훅을 씁니다.

### 2. 웹훅 값을 환경 파일에 저장 (CloudShell 또는 VS Code 터미널)

.csv 의 값으로 `<URL>`, `<SECRET>` 을 바꿔 실행합니다.

```bash
sed -i "s#^export WEBHOOK_URL=.*#export WEBHOOK_URL=<URL>#; s#^export WEBHOOK_SECRET=.*#export WEBHOOK_SECRET=<SECRET>#" ~/.ext-workshop.env
source ~/.ext-workshop.env
echo "$WEBHOOK_URL"        # https://event-ai.us-east-1.api.aws/webhook/generic/... 가 나오면 OK
```

### 3. forwarder Lambda에 웹훅 설정

```bash
FUNCTION_NAME=$(aws cloudformation describe-stacks --stack-name cloudformation-template \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookForwarderFunctionName`].OutputValue' --output text)
aws lambda update-function-configuration --function-name "$FUNCTION_NAME" \
  --environment "Variables={WEBHOOK_URL=${WEBHOOK_URL},WEBHOOK_SECRET=${WEBHOOK_SECRET}}" \
  --query LastUpdateStatus --output text
aws lambda wait function-updated --function-name "$FUNCTION_NAME" && echo "Lambda 설정 완료"
```

### 4. 알람 울리기

```bash
ALARM_NAME=$(aws cloudformation describe-stacks --stack-name cloudformation-template \
  --query 'Stacks[0].Outputs[?OutputKey==`ProactiveInvestigationAlarmName`].OutputValue' --output text)
aws cloudwatch set-alarm-state --alarm-name "$ALARM_NAME" --state-value ALARM \
  --state-reason "Manual test trigger - simulating production alarm"
sleep 15
aws logs tail /aws/lambda/$FUNCTION_NAME --since 5m --format short | grep -iE "webhook|incident"
```

로그에 `Incident ID: ...` 와 `Webhook request sent successfully`(또는 `Webhook request sent, response not verified`)가 보이면 성공입니다. `WEBHOOK_URL not configured` 가 보이면 3번을 다시 실행하세요.

??? note "실제 5xx 오류로 울리고 싶다면 (선택, 2–3분)"
    알람 상태를 직접 바꾸는 대신, mock API Gateway를 만들어 진짜 5xx를 발생시키는 방법도 있습니다. 시간이 남는 분만 [원본 Method 1](https://catalog.us-east-1.prod.workshops.aws/workshops/a03aac5c-40f1-44c3-87ef-495507743b8b/en-US/exercises/lab1/proactive-investigation/trigger-observe)을 참고하세요. 이 가이드의 사전 검증은 위의 방법으로 했습니다.

### 5. 자동으로 생긴 조사 확인

Operator access 웹앱(①에서 연 탭)을 새로고침하면 **아무도 버튼을 누르지 않았는데** *"Proactive Investigation: cloudformation-template-api-5xx-errors"* 가 생겨 있습니다. (선택) 터미널에서도 볼 수 있습니다.

```bash
aws devops-agent list-backlog-tasks --agent-space-id "$AGENT_SPACE_ID" \
  --query 'tasks[].[title,status]' --output table
```

!!! info "새 조사가 `LINKED` 로 보이면: 정상입니다 (사전 검증에서 확인)"
    ①의 ECS 조사와 같은 클러스터, 같은 시간대의 알람이라서 DevOps Agent가 **같은 장애로 묶습니다.** 알람 조사는 `LINKED` 상태가 되고, ①의 ECS 조사가 알람 정보를 반영해 **다시 조사**에 들어갑니다.

    - 확인할 곳: 알람 조사를 열어 **연결 사유**와 메타데이터(`Source: webhook`)를 봅니다. 그다음 ①의 ECS 조사로 가서 재조사 결과를 확인합니다.
    - 사전 검증 때 남은 연결 사유: *"Same underlying infrastructure (cloudformation-template-cluster), same incident window … The 5xx errors are the likely root cause of the order-api service unavailability reported in the primary incident."*
    - 이 장면은 **알림이 쏟아질 때 중복 조사를 막는 기능**입니다. "알림 노이즈" 질문에 답할 때 쓰세요.

## 관찰 포인트

| 무엇을 보나 | 왜 중요한가 |
|---|---|
| 메타데이터: `Source: webhook`, `Triggered By: lambda-automation` | 누가, 언제, 왜 조사를 시작했는지 **감사 추적**이 남습니다 |
| 조사 흐름: Context gathering → Data collection → Analysis → Root cause | 배포 이력과 설정 변경을 **먼저 배제**하고 결론을 냅니다 |
| 결론: *"No recent deployments, no config changes → external trigger or simulated condition"* | 아래 "인시던트 판별" 참고 |

!!! question "Q. 자동 트리거 소스는 무엇이 되나요? Grafana나 Slack도 되나요?"
    대부분 됩니다. 원리는 **웹훅으로 HTTP POST를 보낼 수 있으면 무엇이든 트리거가 된다**는 것입니다.

    - **기본 연동:** CloudWatch, Datadog, Dynatrace, New Relic, Splunk, Grafana(알림 contact point), ServiceNow, PagerDuty, Slack
    - **Generic webhook:** 그 밖의 모든 시스템. 사내 비즈니스 메트릭 알림 시스템도 여기에 해당합니다 → [확장 A](../part2/ext-alert.md)에서 직접 해봅니다.
    - **MCP / A2A:** 기본 지원 목록에 없는 도구나 에이전트도 연결할 수 있습니다 → [Part 2](../part2/index.md)

## 인시던트 판별로 연결하기

이 시나리오의 결론은 *"최근 배포도 설정 변경도 없으니 외부 요인이거나 시뮬레이션된 상황"* 입니다. 에이전트가 **배포와 설정 변경 가설을 배제한 뒤에** 판단을 내린 것입니다.

이 추론 구조가 바로 "진짜 장애인가, 예상된 변동인가"를 가리는 데 필요한 것입니다. 하지만 축구 경기 일정, 프로모션, 공휴일 같은 **비즈니스 맥락은 텔레메트리에 없습니다.** 그래서 에이전트에게 따로 알려줘야 합니다 → [확장 B · 이벤트 컨텍스트 MCP](../part2/ext-mcp.md)

!!! note "MTTR 수치에 대해"
    원본의 "19분 → 3분 (84% 감소)"는 **워크샵 시뮬레이션 기준 예시**입니다. 우리 환경에서 어떤 수치가 나올지는 Part 3에서 정의하는 평가 방법으로 측정해야 합니다.
