"""Print a sample alert with its "auto" time window filled in (for `aws lambda invoke`)."""

import json
import sys

from send_test_alert import fill_window

with open(sys.argv[1], encoding="utf-8") as f:
    print(json.dumps(fill_window(json.load(f)), ensure_ascii=False))
