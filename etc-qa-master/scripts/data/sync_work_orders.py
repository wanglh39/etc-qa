import json

from agent.graph import ingest_agent
from agent.state import AgentState
from api.work_order.client import WorkOrderClient
from db.mysql_client import MySQLClient
from utils.config import get_config


def sync_work_orders():
    cfg = get_config()
    mysql = MySQLClient()
    wo_client = WorkOrderClient(use_mock=cfg.get("work_order", {}).get("use_mock", True))

    processed = wo_client.fetch_processed_work_orders()

    for wo in processed:
        existing = mysql.get_work_orders_by_status("submitted")
        matched = [e for e in existing if e["external_id"] == wo["external_id"]]

        if matched:
            mysql.update_work_order(
                wo["external_id"],
                json.dumps(wo, ensure_ascii=False),
                "answered",
            )
        else:
            mysql.insert_work_order(
                wo["external_id"],
                json.dumps(wo, ensure_ascii=False),
            )
            mysql.update_work_order(wo["external_id"], json.dumps(wo, ensure_ascii=False), "answered")

    answered = mysql.get_work_orders_by_status("answered")
    for wo in answered:
        try:
            raw = json.loads(wo["raw_data"]) if wo["raw_data"] else {}
            state = AgentState(
                raw_question=raw.get("question", ""),
                raw_answer=raw.get("answer", ""),
            )
            result = ingest_agent.invoke(state.model_dump())
            mysql.update_work_order(wo["external_id"], json.dumps(result, ensure_ascii=False), "processed")
        except Exception as e:
            print(f"工单 {wo['external_id']} 预处理失败: {e}")


def cleanup_finished_orders():
    mysql = MySQLClient()
    mysql.delete_work_orders_by_status(["imported", "rejected"])
    print("已清理 imported/rejected 状态的工单记录")


if __name__ == "__main__":
    sync_work_orders()
    cleanup_finished_orders()
