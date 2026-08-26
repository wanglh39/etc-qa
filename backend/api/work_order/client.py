import random
from datetime import datetime


class WorkOrderClient:
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self._mock_store: dict[str, dict] = {}

    def create_work_order(self, question: str, category: str = "") -> str:
        if self.use_mock:
            wo_id = f"WO-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            self._mock_store[wo_id] = {
                "external_id": wo_id,
                "question": question,
                "category": category,
                "status": "pending",
                "answer": "",
                "created_at": datetime.now().isoformat(),
            }
            return wo_id
        return self._real_create(question, category)

    def fetch_processed_work_orders(self, since: str = "") -> list[dict]:
        if self.use_mock:
            return [v for v in self._mock_store.values() if v["status"] == "processed"]
        return self._real_fetch(since)

    def _real_create(self, question: str, category: str) -> str:
        raise NotImplementedError("真实工单API未对接，请配置后使用")

    def _real_fetch(self, since: str) -> list[dict]:
        raise NotImplementedError("真实工单API未对接，请配置后使用")
