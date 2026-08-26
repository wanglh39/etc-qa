"""
工单流转链路自动化测试脚本

用法：
    python scripts/test_workorder_flow.py              # 默认连 localhost:8000
    python scripts/test_workorder_flow.py --host 192.168.1.100 --port 8000

前提：后端已启动（python main.py），MySQL 已运行

模拟链路：
    service 登录 → 提交工单
    → dept 登录 → 查看本部门工单 → 办结
    → admin 登录 → 看统计 → 看待审核列表（证明审的是知识库不是工单）
"""

import argparse
import random
import sys
import time

try:
    import requests
except ImportError:
    print("[ERROR] 缺少 requests 库，请先安装：pip install requests")
    sys.exit(1)


GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def fail(msg):
    global failed
    failed += 1
    print(f"  {RED}[FAIL]{RESET} {msg}")


def info(msg):
    print(f"  {CYAN}[INFO]{RESET} {msg}")


def step(n, title):
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}Step {n}: {title}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")


def login(base, username, password="123456"):
    resp = requests.post(f"{base}/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"登录失败({resp.status_code}): {resp.text}"
    data = resp.json()
    return data["access_token"], data["role"], data.get("dept", "")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    parser = argparse.ArgumentParser(description="工单流转链路自动化测试")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    base = f"http://{args.host}:{args.port}"

    print(f"\n{BOLD}工单流转链路自动化测试{RESET}")
    print(f"目标后端: {base}")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        requests.get(f"{base}/health", timeout=3)
    except Exception:
        print(f"\n{RED}[ERROR] 无法连接后端 {base}{RESET}")
        print(f"请先启动后端：cd backend && python main.py")
        sys.exit(1)

    wo_id = None
    external_id = None

    step(1, "客服(service)登录")
    try:
        token, role, dept = login(base, "service")
        ok(f"登录成功 — 角色: {role}, 部门: '{dept}'")
    except Exception as e:
        fail(f"登录失败: {e}")
        return

    step(2, "客服提交工单(转交售后部门)")
    try:
        customer = f"测试客户{random.randint(1000, 9999)}"
        payload = {
            "service_id": "S001",
            "customer_name": customer,
            "phone": "13800001111",
            "problem_type": "ETC重复扣费",
            "next_dept": "aftersale",
            "priority": "high",
            "detail_desc": f"自动化测试创建的工单 — {customer}反映ETC被重复扣费，要求退款",
        }
        resp = requests.post(f"{base}/api/work_orders", json=payload, headers=auth_header(token))
        assert resp.status_code == 200, f"创建工单失败({resp.status_code}): {resp.text}"
        data = resp.json()
        wo_id = data["id"]
        external_id = data.get("external_id", "")
        ok(f"工单创建成功 — ID: {wo_id}, 外部编号: {external_id}")
        info(f"初始状态: {data.get('status')}, 分配部门: {data.get('dept')}")
        if data.get("status") != "submitted":
            fail(f"状态应为 submitted，实际为 {data.get('status')}")
        if data.get("dept") != "aftersale":
            fail(f"部门应为 aftersale，实际为 {data.get('dept')}")
    except Exception as e:
        fail(f"创建工单失败: {e}")
        return

    step(3, "部门处理员(dept)登录")
    try:
        token_dept, role_d, dept_d = login(base, "dept")
        ok(f"登录成功 — 角色: {role_d}, 部门: '{dept_d}'")
        if dept_d != "aftersale":
            fail(f"dept 用户部门应为 aftersale，实际为 '{dept_d}'")
    except Exception as e:
        fail(f"登录失败: {e}")
        return

    step(4, "部门处理员查看本部门工单列表")
    try:
        resp = requests.get(
            f"{base}/api/work_orders",
            params={"status": "submitted", "dept": "aftersale"},
            headers=auth_header(token_dept),
        )
        assert resp.status_code == 200, f"查询失败({resp.status_code}): {resp.text}"
        data = resp.json()
        items = data.get("items", [])
        ok(f"查询成功 — 共 {data.get('total', 0)} 条待处理工单")
        found = any(item["id"] == wo_id for item in items)
        if found:
            ok(f"刚提交的工单(ID:{wo_id})在部门列表中找到")
        else:
            fail(f"刚提交的工单(ID:{wo_id})未在部门列表中找到")
            info(f"列表中的工单ID: {[item['id'] for item in items[:5]]}")
    except Exception as e:
        fail(f"查询工单列表失败: {e}")

    step(5, "部门处理员办结工单")
    try:
        resp = requests.put(
            f"{base}/api/work_orders/{wo_id}/reply",
            json={"handle_remark": "自动化测试办结 — 已核实扣费记录，3个工作日内退款"},
            headers=auth_header(token_dept),
        )
        assert resp.status_code == 200, f"办结失败({resp.status_code}): {resp.text}"
        data = resp.json()
        ok(f"工单办结成功 — ID: {wo_id}")
        info(f"办结后状态: {data.get('status')}")
        if data.get("status") == "processed":
            ok("状态正确变为 processed")
        else:
            fail(f"状态应为 processed，实际为 {data.get('status')}")
    except Exception as e:
        fail(f"办结工单失败: {e}")

    step(6, "业务管理员(admin)登录")
    try:
        token_admin, role_a, dept_a = login(base, "admin")
        ok(f"登录成功 — 角色: {role_a}, 部门: '{dept_a}'")
    except Exception as e:
        fail(f"登录失败: {e}")
        return

    step(7, "管理员查看数据看板统计")
    try:
        resp = requests.get(f"{base}/api/stats", headers=auth_header(token_admin))
        assert resp.status_code == 200, f"查询失败({resp.status_code}): {resp.text}"
        data = resp.json()
        ok(
            f"查询成功 — 工单总数: {data.get('work_order_total', '?')}, "
            f"已提交: {data.get('work_order_submitted', '?')}, "
            f"已办结: {data.get('work_order_processed', '?')}"
        )
    except Exception as e:
        fail(f"查询统计失败: {e}")

    step(8, "管理员查看待审核列表(验证:审的是知识库不是工单)")
    try:
        resp = requests.get(
            f"{base}/api/qa/list",
            params={"status": "deprecated", "page": 1, "page_size": 5},
            headers=auth_header(token_admin),
        )
        assert resp.status_code == 200, f"查询失败({resp.status_code}): {resp.text}"
        data = resp.json()
        items = data.get("items", [])
        ok(f"待审核列表查询成功 — 共 {data.get('total', 0)} 条待审核知识")
        info("此列表查的是 qa_pairs 表(status=deprecated)，即 Agent 入库的新知识问题")
        info("不是 work_orders 表(工单)，工单不经过 admin 审核")
        if items:
            info(f"示例: ID={items[0].get('id')}, 问题='{items[0].get('question', '')[:30]}...'")
    except Exception as e:
        fail(f"查询待审核列表失败: {e}")

    step(9, "验证工单不出现在待审核列表中")
    try:
        resp = requests.get(
            f"{base}/api/qa/list",
            params={"status": "deprecated"},
            headers=auth_header(token_admin),
        )
        data = resp.json()
        items = data.get("items", [])
        has_wo = any("work_order" in str(item).lower() or "工单" in str(item) for item in items)
        if not has_wo:
            ok("确认: 待审核列表中无工单数据，工单与知识审核是两条独立链路")
        else:
            info("待审核列表中可能包含含'工单'字样的知识问题(正常，这是知识内容不是工单记录)")
    except Exception as e:
        fail(f"验证失败: {e}")

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}测试总结{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")
    print(f"  {GREEN}通过: {passed}{RESET}  {RED}失败: {failed}{RESET}")
    if failed == 0:
        print(f"\n  {GREEN}{BOLD}全部通过! 工单流转链路正常。{RESET}")
    else:
        print(f"\n  {RED}{BOLD}有 {failed} 项失败，请检查。{RESET}")
    print(f"\n链路回顾:")
    print(f"  service 提交工单 → work_orders 表(status=submitted, dept=aftersale)")
    print(f"  → dept 按部门过滤看到 → 办结 → status=processed")
    print(f"  → admin 只在数据看板看统计数字，不参与工单审核")
    print(f"  → admin 待审核列表审的是 qa_pairs(知识库)，与工单无关")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
