import os

os.environ['ETC_QA_ENV'] = os.environ.get('ETC_QA_ENV', 'test')
import sys

sys.path.insert(0, '.')
import json
import time

from db.milvus_client import MilvusQA
from utils.config import load_config

cfg = load_config()

cache_path = os.path.join(os.path.dirname(__file__), "..", "..", "output", "hyde_cache.json")
if not os.path.exists(cache_path):
    print(f"ERROR: {cache_path} not found. Run hyde_generate.py first.")
    sys.exit(1)

with open(cache_path, encoding='utf-8') as f:
    cache = json.load(f)
print(f"Cache: {len(cache)} entries")

milvus = MilvusQA()
milvus.init_collection()
milvus.client.load_collection(milvus.collection_name)
existing = milvus.client.query(
    collection_name=milvus.collection_name,
    filter="is_hyde == true",
    output_fields=["qa_id"],
)
existing_hyde_ids = set(r["qa_id"] for r in existing)
milvus.close()
print(f"Existing HyDE in Milvus: {len(existing_hyde_ids)}")

todo = [v for k, v in cache.items() if v["qa_id"] not in existing_hyde_ids]
print(f"To insert: {len(todo)} entries")

total_inserted = 0
batch_data = []
BATCH_SIZE = 30

out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "hyde_insert_report.txt")
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f"Cache: {len(cache)}, Existing: {len(existing_hyde_ids)}, To insert: {len(todo)}\n")

    for i, entry in enumerate(todo):
        qa_id = entry["qa_id"]
        category_l1 = entry["category_l1"]
        vectors = entry["vectors"]

        for j, vec in enumerate(vectors):
            vec_id = qa_id * 1000 + j if j > 0 else qa_id
            is_hyde = j > 0
            batch_data.append({
                "id": vec_id, "qa_id": qa_id,
                "vector": vec, "category_l1": category_l1,
                "is_hyde": is_hyde,
            })

        if len(batch_data) >= BATCH_SIZE:
            milvus = MilvusQA()
            milvus.client.insert(collection_name=milvus.collection_name, data=batch_data)
            milvus.client.load_collection(milvus.collection_name)
            milvus.close()
            total_inserted += len(batch_data)
            f.write(f"  Inserted {total_inserted} (processed {i+1}/{len(todo)})\n")
            f.flush()
            batch_data = []
            time.sleep(3)

    if batch_data:
        milvus = MilvusQA()
        milvus.client.insert(collection_name=milvus.collection_name, data=batch_data)
        milvus.client.load_collection(milvus.collection_name)
        milvus.close()
        total_inserted += len(batch_data)

    f.write(f"\nDone. Total inserted: {total_inserted}\n")

print(f"Done. Inserted: {total_inserted} -> {out_path}")
