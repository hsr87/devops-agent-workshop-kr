# 리스크 & 백업

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 조사가 예상보다 오래 걸림 (3–10분 편차) | 높음 | 대기 시간마다 할 일을 정해둠 (Topology, 코드 리뷰, 설명). 완료 화면 백업 |
| Lab 3 리셋 파이프라인이 안 끝난 상태에서 실행 | 중간 | 휴식 직전에 리셋 실행. 1:25 전에 CodePipeline 상태 확인 |
| Lab 3 대시보드 접속 실패 | 중간 | VS Code 알림 링크 대신 EC2 URL 사용. pager가 뜨면 `q`. CLI로 대체: `python3 sre-agent.py --cluster ... --issue ...` |
| 참가자 진도 차이 | 높음 | Lambda 시나리오를 빨리 끝난 사람용 버퍼로 사용. 늦은 사람은 Proactive Method 2 |
| MCP·A2A 등록이 계정 정책으로 거부됨 | 낮음 (Workshop Studio) | 일부 일반 계정에서는 *"Only external accounts and exempted accounts are allowed"* 로 거부됨. **Workshop Studio 계정에서는 MCP 등록·연결 성공 확인**(사전 검증). A2A는 정책상 허용되지만 실제 A2A 엔드포인트가 필요 |
| CloudShell 세션 끊김 (20–30분 무입력) | 중간 | 다시 열고 `source ~/.ext-workshop.env`. 홈 디렉터리와 venv는 유지됨. 조사 결과는 `router.py finish` 를 다시 실행하면 이어서 받음 |
| CloudShell의 AWS CLI가 `devops-agent` 명령을 모름 | 낮음 | 확장 실습 코드는 venv의 boto3를 쓰므로 영향 없음. CLI로 확인하는 단계는 콘솔 Operator access로 대신 확인 |
| Proactive 알람 조사가 `LINKED` 로 보임 | 높음 | 정상. ①의 ECS 조사와 같은 클러스터·시간대라 같은 장애로 묶임. 알람 조사의 연결 사유와 메타데이터를 보고, ①의 ECS 조사에서 재조사 결과를 확인. "알림 노이즈" 답변 소재로 활용 |
| CLI로 Agent Space를 만들면 계정 연결이 `Unauthorized` | 낮음 | 콘솔의 Begin setup을 쓰면 해당 없음. CLI로 만들 때는 역할 생성 후 1–3분(IAM 전파) 기다렸다가 `associate-service` 재시도 |
| ECS 조사에서 Exit Code 137(OOM)이 안 보임 | 중간 | 환경 생성 직후에는 아직 OOM 전일 수 있음. 에이전트가 코드와 `[MEMORY LEAK]` 로그로 누수를 확정하고, 확인 못 한 부분은 investigation gap으로 따로 적는 것이 정상 동작 |
| Webhook Secret 분실 | 중간 | Agent Space → Capabilities → 웹훅 **Rotate** 로 재발급 (URL은 그대로) |
| 웹훅 200인데 조사가 안 생김 | 낮음 | 같은 `incidentId`/`timestamp` 는 중복으로 무시됨. forwarder는 매번 고유 ID 생성. 그래도 안 되면 payload 형식 확인 |
| "워크샵 수치가 우리 환경에서도 나오나?" | 높음 | 시뮬레이션 수치임을 먼저 밝히고, Part 3 신뢰성 정의로 연결 |
| 확장 C `--judge` 에서 Bedrock 모델 접근 오류 | 중간 | `--model` 로 계정에서 쓸 수 있는 Claude 모델 ID 지정. 또는 결정적 지표만 시연 |
