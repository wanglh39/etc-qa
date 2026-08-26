import json

import numpy as np

from db.milvus_client import MilvusQA
from db.mysql_client import MySQLClient
from rag.siliconflow import get_embedding_client
from utils.config import get_config


def weekly_dedup():
    cfg = get_config()
    mysql = MySQLClient()
    milvus = MilvusQA()
    embed_model = get_embedding_client()

    dedup_cfg = cfg.get("dedup", {})
    q_threshold = dedup_cfg.get("question_threshold", 0.92)
    a_threshold = dedup_cfg.get("answer_threshold", 0.85)

    processed = mysql.get_work_orders_by_status("processed")

    if not processed:
        print("本周无待去重工单")
        return

    questions = []
    for wo in processed:
        raw = json.loads(wo["raw_data"]) if wo["raw_data"] else {}
        questions.append(
            {
                "id": wo["id"],
                "external_id": wo["external_id"],
                "question": raw.get("question", ""),
                "answer": raw.get("answer", ""),
            }
        )

    deduped_ids = set()

    print(f"第一轮：{len(questions)}条新问题 vs 已有知识库")
    active_qa_ids = mysql.get_active_ids()
    for q in questions:
        if q["id"] in deduped_ids:
            continue
        query_vector = embed_model.encode([q["question"]])[0]
        results = milvus.search(query_vector.tolist(), top_k=1, active_qa_ids=active_qa_ids)
        if results:
            top_qa_id = results[0][0]
            top_score = results[0][1]
            if top_score >= q_threshold:
                print(f"  重复: {q['question']} → 已有qa_id={top_qa_id} (score={top_score:.4f})")
                mysql.update_work_order(q["external_id"], json.dumps({"duplicate_of": top_qa_id}), "rejected")
                deduped_ids.add(q["id"])

    remaining = [q for q in questions if q["id"] not in deduped_ids]

    print(f"第二轮：{len(remaining)}条新问题之间互相比对")
    if len(remaining) > 1:
        q_vectors = embed_model.encode([q["question"] for q in remaining])
        norms = np.linalg.norm(q_vectors, axis=1, keepdims=True)
        normed = q_vectors / norms
        sim_matrix = normed @ normed.T

        for i in range(len(remaining)):
            if remaining[i]["id"] in deduped_ids:
                continue
            for j in range(i + 1, len(remaining)):
                if remaining[j]["id"] in deduped_ids:
                    continue
                q_sim = sim_matrix[i][j]
                if q_sim >= q_threshold:
                    a_vectors = embed_model.encode([remaining[i]["answer"], remaining[j]["answer"]])
                    a_norms = np.linalg.norm(a_vectors, axis=1, keepdims=True)
                    a_normed = a_vectors / a_norms
                    a_sim = float(a_normed[0] @ a_normed[1].T)
                    if a_sim >= a_threshold:
                        if len(remaining[i]["answer"]) >= len(remaining[j]["answer"]):
                            keep, reject = remaining[i], remaining[j]
                        else:
                            keep, reject = remaining[j], remaining[i]
                        print(f"  内部重复: {reject['question']} → 保留 {keep['question']}")
                        mysql.update_work_order(
                            reject["external_id"], json.dumps({"duplicate_of": keep["id"]}), "rejected"
                        )
                        deduped_ids.add(reject["id"])

    for q in questions:
        if q["id"] not in deduped_ids:
            mysql.update_work_order(q["external_id"], "", "deduped")

    total = len(questions)
    kb_dup = sum(1 for q in questions if q["id"] in deduped_ids)
    print(f"\n去重报告: 本周{total}条, 重复{kb_dup}条, 保留{total - kb_dup}条")


if __name__ == "__main__":
    weekly_dedup()
