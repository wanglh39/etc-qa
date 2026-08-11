from api.work_order.client import WorkOrderClient


class TestWorkOrderClient:
    def test_create_work_order_returns_id(self):
        client = WorkOrderClient(use_mock=True)
        wo_id = client.create_work_order("ETC扣费异常", "售后业务")
        assert wo_id.startswith("WO-")

    def test_fetch_processed_returns_empty_initially(self):
        client = WorkOrderClient(use_mock=True)
        results = client.fetch_processed_work_orders()
        assert results == []

    def test_create_and_fetch_flow(self):
        client = WorkOrderClient(use_mock=True)
        wo_id = client.create_work_order("ETC扣费异常", "售后业务")

        client._mock_store[wo_id]["status"] = "processed"
        client._mock_store[wo_id]["answer"] = "核实后退款"

        results = client.fetch_processed_work_orders()
        assert len(results) == 1
        assert results[0]["external_id"] == wo_id
