import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ETC_QA_ENV", "test")

from main import app

schema = app.openapi()

output_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend",
    "tests",
    "contract",
    "openapi.json",
)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(schema, f, ensure_ascii=False, indent=2)

print(f"OpenAPI schema exported to {output_path}")
print(f"Total endpoints: {len(schema.get('paths', {}))}")