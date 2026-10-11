# alert-forwarder

임의의 알림(비즈니스 메트릭 알림, CloudWatch 알람 이벤트, 일반 JSON)을 AWS DevOps Agent **generic webhook** payload로 변환하고 서명해서 보냅니다. 외부 의존성은 없습니다.

```bash
export WEBHOOK_URL=... WEBHOOK_SECRET=...      # Agent Space 웹훅 .csv 값 (AUTH_MODE=bearer 이면 API key)
python3 send_test_alert.py samples/impressions-drop-during-match.json --dry-run
python3 send_test_alert.py samples/impressions-drop-during-match.json
./deploy.sh                                     # (선택) Lambda ext-alert-forwarder 로 배포
```

- 조사 컨텍스트로는 `title`/`description`/`priority` 만 전달되므로 모든 맥락을 `description` 에 넣습니다.
- HMAC 서명: `base64(HMAC-SHA256(secret, "{timestamp}:{body}"))`, 헤더 `x-amzn-event-timestamp`, `x-amzn-event-signature`.
- 가이드: https://hsr87.github.io/devops-agent-workshop-kr/part2/ext-alert/
