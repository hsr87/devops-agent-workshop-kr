# 확장 C · 판별·라우팅·RCA 정확도 평가

**목표:** "에이전트를 얼마나 믿을 수 있나?"를 **숫자로** 답합니다. DevOps Agent에는 평가 기능이 내장되어 있지 않으므로, 과거 인시던트 정답셋과 에이전트 결과를 주기적으로 비교하는 평가 루프를 따로 둡니다.

코드: [`extensions/rca-eval`](https://github.com/hsr87/devops-agent-workshop-kr/tree/main/extensions/rca-eval)

## 무엇을 측정하나

| 지표 | 정의 | 대응하는 질문 |
|---|---|---|
| **판별 정확도** | 장애(INCIDENT)와 예상된 변동(EXPECTED_EVENT)을 맞게 구분한 비율 + confusion matrix | 인시던트 판별 |
| **라우팅 정확도 / 오라우팅률** | 실제 장애 중 owner 팀을 맞게 지목한 비율 | 도메인 라우팅 |
| **근거 첨부율** | 맞게 라우팅한 건 중 근거가 N개 이상 첨부된 비율 | 라우팅 신뢰성 |
| **RCA 일치도** (선택) | LLM 채점기가 포스트모템 원인과 비교해 매긴 MATCH / PARTIAL / MISS | RCA 정확도 |

!!! question "Q. 공개 사례의 'RCA 정확도 94%'는 어떤 기준인가요?"
    공개 블로그에는 측정 방식이 자세히 나와 있지 않습니다(확인 후 공유 예정). 핵심은 **"무엇을 맞았다고 볼지"를 우리가 먼저 정의해야 한다**는 것입니다. 이 도구는 그 정의를 코드로 옮긴 출발점입니다. 판정 기준은 Part 3에서 함께 정합니다.

## 실습

```bash
cd $EXT_REPO/extensions/rca-eval

# 결정적 지표만 계산 (LLM 호출 없음)
python3 evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl

# LLM 채점기 포함 (Amazon Bedrock의 Claude 사용, bootstrap이 만든 venv에서 실행)
source ~/.ext-workshop.env
$EXT_PYTHON evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl --judge --out report.md
```

샘플로 실행한 결과입니다.

```text
- Verdict accuracy (incident vs. expected event): 83.3% (5/6)
- Routing accuracy on true incidents: 75.0% (3/4)
- Misrouting rate: 25.0% (1/4)
- Routed with evidence (>= 2 items): 75.0% (3/4)

| INC-004 | INCIDENT | INCIDENT | MISROUTED -> ads-serving-team | MISS: The agent blames degraded ad serving. The postmortem says ad serving was healthy and the real cause was the impression collector lagging ... |
| INC-005 | INCIDENT | INCIDENT | OK | PARTIAL: The agent ties the 5xx errors to the deployment ... gives an alternative hypothesis equal weight. |
```

!!! tip "INC-004가 보여주는 것"
    노출이 줄면 직관적으로 "서빙 팀 문제"라고 생각하기 쉽습니다. 하지만 실제로는 서빙은 정상이었고 **집계 파이프라인**이 원인이었습니다. 이런 오라우팅을 줄이려면 [확장 B](ext-mcp.md)의 `get_service_owner` 에 **라우팅 규칙**(예: "서빙 정상인데 집계 메트릭만 감소 → 데이터 팀")을 넣고, 판별 단계에서 서빙 에러율을 반드시 확인하게 해야 합니다.

## 입력 형식 (JSONL, `incident_id` 로 조인)

```json
// ground_truth.jsonl : 포스트모템에서 확정된 정답
{"incident_id": "INC-004", "true_verdict": "INCIDENT", "true_owner_team": "ads-data-team",
 "true_root_cause": "The impression event collector lagged after a Kinesis shard limit ..."}

// agent_results.jsonl : 에이전트 결과 (조사 결과에서 추출)
{"incident_id": "INC-004", "verdict": "INCIDENT", "owner_team": "ads-serving-team",
 "root_cause": "Ad serving degradation reduced impressions.", "evidence": ["impressions -40%"]}
```

## 운영에 적용할 때

- **정답셋:** 최근 포스트모템 20–50건으로 시작합니다. 예상된 변동(EXPECTED_EVENT) 사례도 반드시 포함해야 판별 능력을 측정할 수 있습니다.
- **재현:** 과거 인시던트의 알림을 [확장 A](ext-alert.md)로 다시 보내 결과를 모읍니다. 주기적으로 반복하면 **regression을 감지**할 수 있습니다.
- **채점기 모델:** `--model` 또는 `JUDGE_MODEL` 로 지정합니다. 기본값은 `anthropic.claude-opus-5-5` 입니다. 채점기가 정답 원인과 비교만 하므로 결과가 비교적 안정적입니다. 그래도 일부 샘플은 사람이 직접 검수해 채점 기준이 맞는지 확인하세요.
