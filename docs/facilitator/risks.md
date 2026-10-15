# 리스크 & 백업

| 리스크 | 가능성 | 대응 |
|---|---|---|
| 조사가 예상보다 오래 걸림 (3–10분 편차) | 높음 | 대기 시간마다 할 일을 정해둠 (Topology, 코드 리뷰, 설명). 완료 화면 백업 |
| Lab 3 리셋 파이프라인이 안 끝난 상태에서 실행 | 중간 | 휴식 직전에 리셋 실행. 1:25 전에 CodePipeline 상태 확인 |
| Lab 3 대시보드 접속 실패 | 중간 | VS Code 알림 링크 대신 EC2 URL 사용. pager가 뜨면 `q`. CLI로 대체: `python3 sre-agent.py --cluster ... --issue ...` |
| Lab 3이 엉뚱한 조사를 분석함 | 중간 | Lab 3은 진행 중인 조사를 재사용함. **Lab 3을 먼저 시작**하고 Live Output에 `creating new task` 가 보인 뒤 메인 에이전트 실습 시작 |
| Lab 3을 다시 실행했더니 PR이 안 만들어짐 | 낮음 | 브랜치 이름이 날짜 기준이라 같은 날 재실행하면 충돌. 첫 실행의 PR을 보여주면 됨 |
| 메인 에이전트 실습의 조사가 1:50까지 안 끝남 | 중간 | 조사 12–25분. `Ctrl+C` 후 나중에 `router.py finish` 재실행. 토론은 진행자 화면(사전 검증 결과)으로 |
| 참가자 진도 차이 | 높음 | 빨리 끝난 사람은 확장 실습으로. 늦은 사람은 Proactive Method 2 |
| MCP·A2A 등록이 계정 정책으로 거부됨 | 낮음 (Workshop Studio) | 일부 일반 계정에서는 *"Only external accounts and exempted accounts are allowed"* 로 거부됨. **Workshop Studio 계정에서는 MCP 등록·연결 성공 확인**(사전 검증). A2A는 정책상 허용되지만 실제 A2A 엔드포인트가 필요 |
| CloudShell 세션 끊김 (20–30분 무입력) | 중간 | 다시 열고 `source ~/.ext-workshop.env`. 홈 디렉터리와 venv는 유지됨. 조사 결과는 `router.py finish` 를 다시 실행하면 이어서 받음 |
| CloudShell의 AWS CLI가 `devops-agent` 명령을 모름 | 낮음 | 확장 실습 코드는 venv의 boto3를 쓰므로 영향 없음. CLI로 확인하는 단계는 콘솔 Operator access로 대신 확인 |
| Proactive 알람 조사가 `LINKED` 이거나, 독립 조사로 "Not a real incident" 결론 | 둘 다 정상 | 알람 시점에 ECS 조사가 진행 중이면(약 20분 창) LINKED → ECS 조사 타임라인에서 확인. 이미 끝났으면 독립 조사 → "강제로 울린 테스트 알람" 판별 장면으로 활용 |
| 확장 A의 -26% 알림이 `LINKED` 되어 "EXPECTED_EVENT" 결론이 안 보임 | 높음 (메인 에이전트 실습 직후) | 정상. 실습의 -62% 조사에 묶이고, 그 조사가 *"recovering (−62% → −26%)"* 로 재조사됨. 결론 화면은 진행자 데모 계정(광고 조사 없는 상태)에서 미리 확보 |
| CLI로 Agent Space를 만들면 계정 연결이 `Unauthorized` | 낮음 | 콘솔의 Begin setup을 쓰면 해당 없음. CLI로 만들 때는 역할 생성 후 1–10분(IAM 전파) 기다렸다가 `associate-service` 재시도. 같은 이름의 역할을 지웠다 다시 만들면 더 오래 걸리므로 새 이름 사용 |
| ECS 조사에서 Exit Code 137(OOM)이 안 보임 | 중간 | 환경 생성 직후에는 아직 OOM 전일 수 있음. 에이전트가 코드와 `[MEMORY LEAK]` 로그로 누수를 확정하고, 확인 못 한 부분은 investigation gap으로 따로 적는 것이 정상 동작 |
| Webhook Secret 분실 | 중간 | Agent Space → 기능(Capabilities) → 웹훅 **Rotate** 로 재발급 (URL은 그대로) |
| 웹훅 200인데 조사가 안 생김 | 낮음 | 같은 `incidentId`/`timestamp` 는 중복으로 무시됨. forwarder는 매번 고유 ID 생성. 그래도 안 되면 payload 형식 확인 |
| "워크샵 수치가 우리 환경에서도 나오나?" | 높음 | 시뮬레이션 수치임을 먼저 밝히고, Part 3 신뢰성 정의로 연결 |
| 확장 C `--judge` 에서 Bedrock 모델 접근 오류 | 중간 | `--model` 로 계정에서 쓸 수 있는 Claude 모델 ID 지정. 또는 결정적 지표만 시연 |
