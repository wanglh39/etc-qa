import json
from datetime import datetime
from difflib import SequenceMatcher

from agent.graph import ingest_agent
from agent.state import AgentState
from alert.notifier import record_task_result
from api.work_order.client import WorkOrderClient
from db.mysql_client import MySQLClient
from utils.config import get_config
from utils.logger import get_logger

logger = get_logger("scheduler.tasks")


def _question_similarity(q1: str, q2: str) -> float:
    if not q1 or not q2:
        return 0.0
    return SequenceMatcher(None, q1, q2).ratio()


def _check_dedup(question: str, existing_questions: list[str], threshold: float) -> tuple[bool, float]:
    best_score = 0.0
    for eq in existing_questions:
        score = _question_similarity(question, eq)
        if score > best_score:
            best_score = score
            if best_score >= threshold:
                return True, best_score
    return False, best_score


def sync_and_ingest_task():
    logger.info("定时任务开始: sync_and_ingest")
    cfg = get_config()
    mysql = MySQLClient()
    wo_client = WorkOrderClient(use_mock=cfg.get("work_order", {}).get("use_mock", True))
    job_cfg = cfg.get("scheduler", {}).get("jobs", {}).get("sync_and_ingest", {})
    dedup_threshold = job_cfg.get("dedup_threshold", 0.85)

    stats = {"fetched": 0, "preprocessed": 0, "deduped": 0, "rejected_dup": 0, "errors": 0}

    try:
        processed = wo_client.fetch_processed_work_orders()
        stats["fetched"] = len(processed)
        logger.info(f"拉取到 {len(processed)} 条已处理工单")

        for wo in processed:
            if mysql.work_order_exists(wo["external_id"]):
                mysql.update_work_order(wo["external_id"], json.dumps(wo, ensure_ascii=False), "answered")
            else:
                mysql.insert_work_order(wo["external_id"], json.dumps(wo, ensure_ascii=False))
                mysql.update_work_order(wo["external_id"], json.dumps(wo, ensure_ascii=False), "answered")
    except Exception as e:
        logger.error(f"拉取工单失败: {e}")
        stats["errors"] += 1

    try:
        answered = mysql.get_work_orders_by_status("answered")
        for wo in answered:
            try:
                raw = json.loads(wo["raw_data"]) if wo["raw_data"] else {}
                state = AgentState(
                    raw_question=raw.get("detail_desc", "") or raw.get("question", ""),
                    raw_answer=raw.get("handle_remark", "") or raw.get("answer", ""),
                    work_order_context=(f"工单类型={raw.get('problem_type', '')}，流转至={raw.get('next_dept', '')}"),
                )
                result = ingest_agent.invoke(state.model_dump())
                raw.update(result)
                mysql.update_work_order(wo["external_id"], json.dumps(raw, ensure_ascii=False), "processed")
                stats["preprocessed"] += 1
            except Exception as e:
                logger.error(f"工单 {wo['external_id']} 预处理失败: {e}")
                stats["errors"] += 1
    except Exception as e:
        logger.error(f"获取answered工单失败: {e}")
        stats["errors"] += 1

    try:
        all_qa = mysql.get_all_questions(only_active=False)
        existing_questions = [item["question"] for item in all_qa if item.get("question")]

        processed_wos = mysql.get_work_orders_by_status("processed")
        for wo in processed_wos:
            try:
                raw = json.loads(wo["raw_data"]) if wo["raw_data"] else {}
                question = raw.get("question", "")
                answer = raw.get("answer", "")
                if not question:
                    logger.warning(f"工单 {wo['external_id']} 无有效question，跳过")
                    continue

                is_dup, sim_score = _check_dedup(question, existing_questions, dedup_threshold)
                if is_dup:
                    logger.info(f"工单 {wo['external_id']} 疑似重复(相似度={sim_score:.2f})，标记rejected")
                    mysql.update_work_order(wo["external_id"], wo["raw_data"], "rejected")
                    stats["rejected_dup"] += 1
                    continue

                qa_id = mysql.insert_qa_with_status(
                    question=question,
                    answer=answer,
                    category_l1=raw.get("category_l1", ""),
                    category_l2=raw.get("category_l2", ""),
                    internal_process=raw.get("internal_process", ""),
                    feedback_dept=raw.get("feedback_dept", ""),
                    status="deprecated",
                )
                existing_questions.append(question)
                mysql.update_work_order(wo["external_id"], wo["raw_data"], "deduped")
                logger.info(f"工单 {wo['external_id']} 已写入qa_pairs(qa_id={qa_id}, status=deprecated)待人工审核")
                stats["deduped"] += 1
            except Exception as e:
                logger.error(f"工单 {wo['external_id']} 去重/入库失败: {e}")
                stats["errors"] += 1
    except Exception as e:
        logger.error(f"去重入库阶段失败: {e}")
        stats["errors"] += 1

    logger.info(f"定时任务完成: sync_and_ingest, 统计={stats}")
    _log_task_execution("sync_and_ingest", stats)
    record_task_result("sync_and_ingest", stats["errors"] == 0)
    return stats


def cleanup_task():
    logger.info("定时任务开始: cleanup")
    mysql = MySQLClient()
    stats = {"cleaned": 0}
    success = True
    try:
        mysql.delete_work_orders_by_status(["imported", "rejected"])
        stats["cleaned"] = 1
        logger.info("已清理 imported/rejected 状态的工单记录")
    except Exception as e:
        logger.error(f"清理任务失败: {e}")
        stats["cleaned"] = 0
        success = False
    _log_task_execution("cleanup", stats)
    record_task_result("cleanup", success)
    return stats


def alert_check_task():
    logger.info("定时任务开始: alert_check")
    try:
        from alert.checker import check_alerts

        triggered = check_alerts()
        logger.info(f"告警检查完成, 触发{triggered}条告警")
        return {"triggered": triggered}
    except Exception as e:
        logger.error(f"告警检查失败: {e}")
        return {"triggered": 0, "error": str(e)}


def _log_task_execution(task_name: str, stats: dict):
    try:
        mysql = MySQLClient()
        mysql.insert_scheduler_log(task_name, json.dumps(stats, ensure_ascii=False), "success")
    except Exception as e:
        logger.warning(f"写入调度日志失败(不影响任务): {e}")
