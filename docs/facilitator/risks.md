# 리스크 & 백업

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 조사가 예상보다 오래 걸림 (3–10분 편차) | 높음 | 대기 시간마다 할 일을 정해둠 (Topology, 코드 리뷰, 설명). 완료 화면 백업 |
| Lab 3 리셋 파이프라인이 안 끝난 상태에서 실행 | 중간 | 휴식 직전에 리셋 실행. 1:25 전에 CodePipeline 상태 확인 |
| Lab 3 대시보드 접속 실패 | 중간 | VS Code 알림 링크 대신 EC2 URL 사용. pager가 뜨면 `q`. CLI로 대체: `python3 sre-agent.py --cluster ... --issue ...` |
| 참가자 진도 차이 | 높음 | Lambda 시나리오를 빨리 끝난 사람용 버퍼로 사용. 늦은 사람은 Proactive Method 2 |
| **MCP·A2A 등록이 계정 정책으로 거부됨** | **확인 필요** | 사전 검증 때 일부 계정에서 `AccessDeniedException: Only external accounts and exempted accounts are allowed at this time`. Workshop Studio 계정도 같을 수 있으므로 **리허설 때 반드시 확인**. 막히면 확장 B는 진행자 데모로만 진행하고, 참가자는 로컬 `test_mcp.sh` 까지만 실습. A2A(`remoteagent`)도 같은 오류로 거부됨 → 메인 실습([triage-router](../part2/ext-router.md))은 DevOps Agent API만 쓰므로 영향 없음 |
| CloudShell 세션 끊김 (20–30분 무입력) | 중간 | 다시 열고 `source ~/.ext-workshop.env`. 홈 디렉터리와 venv는 유지됨. 조사 결과는 `router.py finish` 를 다시 실행하면 이어서 받음 |
| CloudShell의 AWS CLI가 `devops-agent` 명령을 모름 | 낮음 | 확장 실습 코드는 venv의 boto3를 쓰므로 영향 없음. CLI로 확인하는 단계는 콘솔 Operator access로 대신 확인 |
| Webhook Secret 분실 | 중간 | Agent Space → Capabilities → 웹훅 **Rotate** 로 재발급 (URL은 그대로) |
| 웹훅 200인데 조사가 안 생김 | 낮음 | 같은 `incidentId`/`timestamp` 는 중복으로 무시됨. forwarder는 매번 고유 ID 생성. 그래도 안 되면 payload 형식 확인 |
| "워크샵 수치가 우리 환경에서도 나오나?" | 높음 | 시뮬레이션 수치임을 먼저 밝히고, Part 3 신뢰성 정의로 연결 |
| 확장 C `--judge` 에서 Bedrock 모델 접근 오류 | 중간 | `--model` 로 계정에서 쓸 수 있는 Claude 모델 ID 지정. 또는 결정적 지표만 시연 |
