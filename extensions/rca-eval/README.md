# rca-eval

과거 인시던트 정답셋과 에이전트 결과를 비교해 **판별 정확도, 라우팅 정확도와 오라우팅률, 근거 첨부율, RCA 일치도**를 계산합니다. RCA 일치도는 선택 기능이며 Amazon Bedrock의 Claude가 채점합니다.

```bash
python3 evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl
pip install -r requirements.txt
python3 evaluate.py samples/ground_truth.jsonl samples/agent_results.jsonl --judge --out report.md
# 채점기 모델 변경: --model <bedrock model id> 또는 JUDGE_MODEL (기본 anthropic.claude-opus-5-5)
```

가이드: https://hsr87.github.io/devops-agent-workshop-kr/part2/ext-eval/
