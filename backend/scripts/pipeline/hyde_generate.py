import os

os.environ["ETC_QA_ENV"] = os.environ.get("ETC_QA_ENV", "test")
import sys

sys.path.insert(0, ".")
import json

from agent.processors.hyde_rewrite import hyde_rewrite
from agent.state import AgentState
from db.mysql_client import MySQLClient
from rag.siliconflow import get_embedding_client
from utils.config import load_config

cfg = load_config()

mysql = MySQLClient()
embed_model = get_embedding_client()
query_prefix = cfg["models"]["query_prefix"]

all_qa = mysql.get_all_questions()

cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "output", "hyde_cache.json")
if os.path.exists(cache_path):
    with open(cache_path, encoding="utf-8") as f:
        cache = json.load(f)
    print(f"Loaded existing cache: {len(cache)} entries")
else:
    cache = {}

done_ids = set(int(k) for k in cache.keys())
todo = [qa for qa in all_qa if qa["id"] not in done_ids]
print(f"Total: {len(all_qa)}, Cached: {len(done_ids)}, To generate: {len(todo)}")

MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 0
if MAX > 0:
    todo = todo[:MAX]

max_rewrite_per_batch = cfg.get("hyde", {}).get("max_rewrite_per_batch", 50)
batch_limit = max_rewrite_per_batch
skipped = 0
generated = 0

for i, qa in enumerate(todo):
    qa_id = qa["id"]
    question = qa["question"]
    answer = qa.get("answer", "")
    category_l1 = qa.get("category_l1", "")

    try:
        state = AgentState(raw_question=question, question=question, answer=answer)
        result = hyde_rewrite(state)
        hyde_questions = result.get("hyde_questions", [])
    except Exception as e:
        hyde_questions = []
        print(f"  ERROR qa_id={qa_id}: {e}")

    if not hyde_questions:
        skipped += 1
        cache[str(qa_id)] = {
            "qa_id": qa_id,
            "question": question,
            "category_l1": category_l1 or "",
            "hyde_questions": [],
            "vectors": [],
        }
    else:
        generated += 1
        if generated > batch_limit:
            print(f"  达到批量上限({batch_limit})，停止生成")
            break

        all_questions = [question] + hyde_questions
        texts = [query_prefix + q for q in all_questions]
        vectors = embed_model.encode(texts, normalize_embeddings=True).tolist()

        cache[str(qa_id)] = {
            "qa_id": qa_id,
            "question": question,
            "category_l1": category_l1 or "",
            "hyde_questions": hyde_questions,
            "vectors": vectors,
        }

    if (i + 1) % 20 == 0:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"  [{i + 1}/{len(todo)}] generated={generated}, skipped={skipped}, cache={len(cache)}")

with open(cache_path, "w", encoding="utf-8") as f:
    json.dump(cache, f, ensure_ascii=False)

print(f"Done. Cache: {len(cache)} entries -> {cache_path}")
