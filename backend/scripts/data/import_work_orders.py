import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
import sys

sys.path.insert(0, '.')
import csv

from agent.graph import ingest_agent
from agent.state import AgentState
from utils.config import load_config

_cfg = load_config()
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PROJECT_ROOT, _cfg.get("data", {}).get("work_order_csv", "data/eval/work_orders_200.csv"))
MAX_ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 10
DRY_RUN = "--commit" not in sys.argv

rows = []
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

rows = rows[:MAX_ROWS]

out_path = os.path.join(os.path.dirname(__file__), "import_work_orders_output.txt")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f"input: {CSV_PATH}\n")
    f.write(f"rows: {len(rows)}, max: {MAX_ROWS}, dry_run: {DRY_RUN}\n\n")

    for i, row in enumerate(rows):
        question = row.get("问题描述", "")
        answer = row.get("处理结果/备注", "")
        work_order_type = row.get("工单类型", "")
        assign_to = row.get("流转至", "")
        plate = row.get("车牌号", "")
        order_id = row.get("工单编号", "")

        context_parts = []
        if work_order_type:
            context_parts.append(f"工单类型={work_order_type}")
        if assign_to:
            context_parts.append(f"流转至={assign_to}")
        if plate:
            context_parts.append(f"车牌号={plate}")
        work_order_context = "，".join(context_parts)

        state = AgentState(
            raw_question=question,
            raw_answer=answer,
            work_order_context=work_order_context,
        )

        try:
            result = ingest_agent.invoke(state.model_dump())
            std_q = result.get("question", question)
            std_a = result.get("answer", answer)
            ip = result.get("internal_process", "")
            fd = result.get("feedback_dept", "")
            cat = result.get("category_l1", "")
            error = result.get("error", "")
        except Exception as e:
            std_q = question
            std_a = answer
            ip = ""
            fd = ""
            cat = ""
            error = str(e)

        f.write(f"[{i+1}] {order_id}\n")
        f.write(f"  raw_q: {question[:60]}\n")
        f.write(f"  raw_a: {answer[:60]}\n")
        f.write(f"  std_q: {std_q}\n")
        f.write(f"  std_a: {std_a}\n")
        f.write(f"  internal: {ip}\n")
        f.write(f"  dept: {fd}\n")
        f.write(f"  category: {cat}\n")
        if error:
            f.write(f"  error: {error}\n")
        f.write("\n")

        if (i + 1) % 5 == 0:
            f.write(f"  --- {i+1}/{len(rows)} ---\n")
            f.flush()

    f.write(f"\nDone. {len(rows)} work orders processed.\n")

print(f"Done. Output: {out_path}")
