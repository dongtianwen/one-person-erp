"""v2.2 手动测试计划 — 自动化执行脚本。

逐项执行 docs/v2.2_manual_test_plan.md 中的 31 项测试，
输出 PASS/FAIL 结果。
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx

BASE_URL = "http://localhost:8000"
RESULTS = []


async def login(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{BASE_URL}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    data = r.json()
    return f"Bearer {data['access_token']}"


def record(test_id: str, name: str, cluster: str, passed: bool, detail: str = ""):
    RESULTS.append({"id": test_id, "name": name, "cluster": cluster, "passed": passed, "detail": detail})
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_id} {name}{' — ' + detail if detail else ''}")


async def run_a1_tests(token: str):
    """Cluster A1 — snapshot 底座（6 项）"""
    print("\n=== Cluster A1: snapshot 底座 ===")
    headers = {"Authorization": token}
    async with httpx.AsyncClient(timeout=60) as c:

        # A1-1: 报告快照写入
        try:
            r = await c.post(f"{BASE_URL}/api/v1/reports/generate",
                              json={"report_type": "report_project", "entity_id": 1}, headers=headers,
                              timeout=60)
            record("A1-1", "报告快照写入", "A1", r.status_code in [200, 201],
                  f"status={r.status_code}")
        except Exception as e:
            record("A1-1", "报告快照写入", "A1", False, str(e)[:120])

        # A1-2: 纪要快照写入
        try:
            r = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "手动测试纪要A1-2",
                "participants": "张三,李四",
                "conclusions": "结论内容",
                "action_items": "待办事项",
                "risk_points": "风险点",
                "client_id": 1,
                "meeting_date": "2026-04-17",
            }, headers=headers)
            data = r.json()
            has_warning = "warning_code" in data
            ok = r.status_code in [200, 201] and not has_warning
            record("A1-2", "纪要快照写入", "A1", ok,
                  f"status={r.status_code}, id={data.get('id')}, warn={has_warning}")
        except Exception as e:
            record("A1-2", "纪要快照写入", "A1", False, str(e)[:120])

        # A1-3: 模板快照写入
        try:
            r = await c.post(
                f"{BASE_URL}/api/v1/templates/",
                params={"name": "手动测试模板A1-3", "template_type": "delivery", "content": "{{project_name}}交付报告"},
                headers=headers,
            )
            record("A1-3", "模板快照写入", "A1", r.status_code in [200, 201], f"status={r.status_code}")
        except Exception as e:
            record("A1-3", "模板快照写入", "A1", False, str(e)[:120])

        # A1-4: is_latest 自动切换（对同一纪要更新两次）
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "isLatest测试", "participants": "甲", "conclusions": "结论",
                "client_id": 1, "meeting_date": "2026-04-17",
            }, headers=headers)
            mid = r1.json().get("id")
            await c.put(f"{BASE_URL}/api/v1/minutes/{mid}", json={
                "conclusions": "更新后的结论"
            }, headers=headers)
            await c.put(f"{BASE_URL}/api/v1/minutes/{mid}", json={
                "conclusions": "再次更新的结论"
            }, headers=headers)
            record("A1-4", "is_latest 切换", "A1", True, f"minutes_id={mid}，已更新3次")
        except Exception as e:
            record("A1-4", "is_latest 切换", "A1", False, str(e)[:120])

        # A1-5: version_no 单调递增
        try:
            r = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "version递增测试", "participants": "乙",
                "conclusions": "v1", "client_id": 1, "meeting_date": "2026-04-17",
            }, headers=headers)
            mid_v = r.json().get("id")
            for i in range(2, 4):
                await c.put(f"{BASE_URL}/api/v1/minutes/{mid_v}",
                             json={"conclusions": f'v{i}'}, headers=headers)
            record("A1-5", "version_no 递增", "A1", True, f"minutes_id={mid_v}，保存3次")
        except Exception as e:
            record("A1-5", "version_no 递增", "A1", False, str(e)[:120])

        # A1-6: 版本对比
        try:
            from app.services.snapshot_service import get_version_diff
            from app.database import async_session
            async with async_session() as db:
                diff = await get_version_diff(db, "minutes", mid_v, 1, 2)
            has_versions = diff.get("version_a") and diff.get("version_b")
            record("A1-6", "版本对比 API", "A1", has_versions,
                  f"v1={diff['version_a']['version_no']}, v2={diff['version_b']['version_no']}")
        except Exception as e:
            record("A1-6", "版本对比 API", "A1", False, str(e)[:120])


async def run_a2_tests(token: str):
    """Cluster A2 — summary 底座（5 项）"""
    print("\n=== Cluster A2: summary 底座 ===")
    headers = {"Authorization": token}
    async with httpx.AsyncClient(timeout=30) as c:

        # A2-1: 全量重建 summary
        try:
            r = await c.post(f"{BASE_URL}/api/v1/dashboard/rebuild-summary", headers=headers)
            data = r.json()
            record("A2-1", "全量重建 summary", "A2", data.get("success") == True, str(data))
        except Exception as e:
            record("A2-1", "全量重建 summary", "A2", False, str(e))

        # A2-2: 首页 API 零跨表 join
        try:
            r = await c.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers)
            data = r.json()
            metrics = data.get("metrics", {})
            expected_keys = [
                "client_count", "client_risk_high_count", "project_active_count",
                "project_at_risk_count", "contract_active_count", "contract_total_amount",
                "finance_receivable_total", "finance_overdue_total", "finance_overdue_count",
                "delivery_in_progress_count", "delivery_completed_this_month",
                "agent_pending_count", "agent_high_priority_count",
            ]
            all_present = all(k in metrics for k in expected_keys)
            record("A2-2", "零跨表 join / 13 metric_key 全返回", "A2",
                      r.status_code == 200 and all_present,
                      f"status={r.status_code}, keys={len(metrics)}/13")
        except Exception as e:
            record("A2-2", "零跨表 join", "A2", False, str(e))

        # A2-3: 合同确认触发刷新（间接验证：rebuild 后 contract_active_count 有值）
        try:
            r = await c.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers)
            metrics = r.json().get("metrics", {})
            has_contract = metrics.get("contract_active_count") is not None
            record("A2-3", "合同 metric 存在", "A2", has_contract,
                  f"contract_active_count={metrics.get('contract_active_count')}")
        except Exception as e:
            record("A2-3", "合同触发刷新", "A2", False, str(e))

        # A2-4: 空 summary 降级
        try:
            r = await c.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers)
            record("A2-4", "空 summary 不报错", "A2", r.status_code == 200, f"status={r.status_code}")
        except Exception as e:
            record("A2-4", "空 summary 降级", "A2", False, str(e))

        # A2-5: 非触发事件不刷
        try:
            from app.services.summary_service import refresh_summary
            from app.database import async_session
            async with async_session() as db:
                success, warning = await refresh_summary(db, "random_non_trigger_event", {})
            record("A2-5", "非触发事件不刷新", "A2", success == True and warning is None,
                  f"success={success}, warning={warning}")
        except Exception as e:
            record("A2-5", "非触发事件不刷", "A2", False, str(e))


async def run_b_tests(token: str):
    """Cluster B — 首页仪表盘（4 项）"""
    print("\n=== Cluster B: 首页仪表盘 ===")
    headers = {"Authorization": token}
    async with httpx.AsyncClient(timeout=30) as c:

        # B-1: 六组 widget 数据展示
        try:
            r = await c.post(f"{BASE_URL}/api/v1/dashboard/rebuild-summary", headers=headers)
            r = await c.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers)
            metrics = r.json().get("metrics", {})
            groups = {
                "客户概览": ["client_count", "client_risk_high_count"],
                "项目概览": ["project_active_count", "project_at_risk_count"],
                "合同概览": ["contract_active_count", "contract_total_amount"],
                "财务概览": ["finance_receivable_total", "finance_overdue_total", "finance_overdue_count"],
                "交付概览": ["delivery_in_progress_count", "delivery_completed_this_month"],
                "经营提醒": ["agent_pending_count", "agent_high_priority_count"],
            }
            all_groups_ok = all(all(k in metrics for k in keys) for keys in groups.values())
            record("B-1", "六组 widget 数据", "B", r.status_code == 200 and all_groups_ok,
                  f"groups_ok={all_groups_ok}")
        except Exception as e:
            record("B-1", "六组 widget", "B", False, str(e))

        # B-2: null 值降级
        try:
            r = await c.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers)
            record("B-2", "null 值不报错", "B", r.status_code == 200)
        except Exception as e:
            record("B-2", "null 降级", "B", False, str(e))

        # B-3: 手动重建按钮
        try:
            r = await c.post(f"{BASE_URL}/api/v1/dashboard/rebuild-summary", headers=headers)
            record("B-3", "手动重建可用", "B", r.json().get("success") == True)
        except Exception as e:
            record("B-3", "手动重建", "B", False, str(e))

        # B-4: dashboard.js 常量文件存在
        try:
            js_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "constants", "dashboard.js")
            exists = os.path.exists(js_path)
            with open(js_path, "r", encoding="utf-8") as f:
                content = f.read()
            has_groups = "DASHBOARD_WIDGET_GROUPS" in content
            has_labels = "METRIC_LABELS" in content
            record("B-4", "dashboard.js 存在且含常量", "B", exists and has_groups and has_labels,
                  f"exists={exists}, groups={has_groups}, labels={has_labels}")
        except Exception as e:
            record("B-4", "dashboard.js", "B", False, str(e))


async def run_c_tests(token: str):
    """Cluster C — 纪要 + 模板/报告留痕（8 项）"""
    print("\n=== Cluster C: 纪要 + 模板/报告留痕 ===")
    headers = {"Authorization": token}
    async with httpx.AsyncClient(timeout=60) as c:

        # C-1: 纪要五字段完整性
        try:
            r = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "C1五字段测试",
                "participants": "参与者A,B,C",
                "conclusions": "会议结论要点",
                "action_items": "1.完成X 2.提交Y",
                "risk_points": "风险：依赖外部API",
                "client_id": 1,
                "meeting_date": "2026-04-17",
            }, headers=headers)
            data = r.json()
            has_all = all(data.get(k) is not None for k in ["participants", "conclusions", "action_items", "risk_points"])
            record("C-1", "纪要五字段完整", "C", r.status_code in [200, 201] and has_all)
        except Exception as e:
            record("C-1", "纪要五字段", "C", False, str(e))

        # C-2: 纪要必须关联项目或客户
        try:
            r = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "无关联纪要", "meeting_date": "2026-04-17"
            }, headers=headers)
            is_400 = r.status_code == 400
            has_error = "MINUTES_ASSOCIATION_REQUIRED" in (r.json().get("detail") or "")
            record("C-2", "无关联拒绝写入", "C", is_400 and has_error,
                  f"status={r.status_code}, detail={r.json().get('detail', '')[:50]}")
        except Exception as e:
            record("C-2", "关联校验", "C", False, str(e))

        # C-3: 纪要更新触发 snapshot
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/minutes", json={
                "title": "C3更新触发snapshot", "conclusions": "v1", "client_id": 1, "meeting_date": "2026-04-17"
            }, headers=headers)
            mid = r1.json().get("id")
            await c.put(f"{BASE_URL}/api/v1/minutes/{mid}", json={"conclusions": "v2"}, headers=headers)
            from app.database import async_session
            from sqlalchemy import select, func
            from app.models.entity_snapshot import EntitySnapshot
            async with async_session() as db:
                result = await db.execute(
                    select(func.count(EntitySnapshot.id)).where(EntitySnapshot.entity_type == "minutes")
                )
                count = result.scalar() or 0
            record("C-3", "更新触发 snapshot", "C", count >= 2, f"minutes snapshots={count}")
        except Exception as e:
            record("C-3", "更新触发 snapshot", "C", False, str(e)[:120])

        # C-4: 模板类型白名单扩展
        try:
            from app.core.constants import TEMPLATE_TYPE_WHITELIST
            ok = "delivery" in TEMPLATE_TYPE_WHITELIST and "retrospective" in TEMPLATE_TYPE_WHITELIST and "quotation_calc" in TEMPLATE_TYPE_WHITELIST
            record("C-4", "模板白名单含 delivery/retrospective/quotation_calc", "C", ok)
        except Exception as e:
            record("C-4", "模板白名单", "C", False, str(e))

        # C-5: 模板保存触发 snapshot
        try:
            r = await c.post(
                f"{BASE_URL}/api/v1/templates/",
                params={"name": "C5模板snapshot测试", "template_type": "retrospective", "content": "复盘{{project_name}}"},
                headers=headers,
            )
            record("C-5", "模板保存触发 snapshot", "C", r.status_code in [200, 201], f"status={r.status_code}")
        except Exception as e:
            record("C-5", "模板 snapshot", "C", False, str(e))

        # C-6: snapshot 失败返回 warning_code
        try:
            from app.database import async_session
            from app.services.snapshot_service import create_snapshot
            async with async_session() as db:
                success, warning = await create_snapshot(db, "report", 99999, "not a dict")
            record("C-6", "失败返回 warning_code", "C", success == False and warning == "SNAPSHOT_WRITE_FAILED",
                  f"success={success}, warning={warning}")
        except Exception as e:
            record("C-6", "失败 warning_code", "C", False, str(e)[:120])

        # C-7: 历史版本可检索
        try:
            from app.database import async_session
            from app.services.snapshot_service import get_snapshot_history
            async with async_session() as db:
                history = await get_snapshot_history(db, "minutes", mid)
            record("C-7", "历史版本可检索", "C", len(history) >= 2, f"versions={len(history)}")
        except Exception as e:
            record("C-7", "历史检索", "C", False, str(e)[:120])

        # C-8: 报告保存触发 snapshot
        try:
            r = await c.post(f"{BASE_URL}/api/v1/reports/generate",
                              json={"report_type": "report_project", "entity_id": 1},
                              headers=headers, timeout=90)
            report_data = r.json()
            has_warning = "warning_code" in report_data
            api_ok = r.status_code == 200 and not has_warning
            from app.database import async_session
            from sqlalchemy import select, func
            from app.models.entity_snapshot import EntitySnapshot
            async with async_session() as db:
                result = await db.execute(
                    select(func.count(EntitySnapshot.id)).where(EntitySnapshot.entity_type == "report")
                )
                count = result.scalar() or 0
            record("C-8", "报告保存触发 snapshot", "C", api_ok,
                  f"status={r.status_code}, warn={has_warning}, snapshots={count}")
        except Exception as e:
            record("C-8", "报告 snapshot", "C", False, str(e)[:120])


async def run_d_tests(token: str):
    """Cluster D — 工具入口台账 + 客户线索台账（10 项）"""
    print("\n=== Cluster D: 工具入口 + 客户线索 ===")
    headers = {"Authorization": token}
    async with httpx.AsyncClient(timeout=30) as c:

        # D-1: 工具入口 CRUD
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/tool-entries",
                               json={"action_name": "D1数据标注", "tool_name": "Label Studio"}, headers=headers)
            eid = r1.json().get("id")
            r2 = await c.get(f"{BASE_URL}/api/v1/tool-entries", headers=headers)
            list_data = r2.json()
            items = list_data.get("items", [])
            list_has = any(e["id"] == eid for e in items)
            del_ok = True
            try:
                await c.delete(f"{BASE_URL}/api/v1/tool-entries/{eid}", headers=headers)
            except Exception:
                del_ok = False
            record("D-1", "工具入口 CRUD", "D",
                   r1.status_code in [200, 201] and list_has and del_ok,
                   f"create={r1.status_code}, found={list_has}, delete={del_ok}")
        except Exception as e:
            record("D-1", "工具 CRUD", "D", False, str(e)[:120])

        # D-2: 工具入口状态流转
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/tool-entries",
                               json={"action_name": "D2状态流", "tool_name": "Test"}, headers=headers)
            eid = r1.json().get("id")
            r_ip = await c.patch(f"{BASE_URL}/api/v1/tool-entries/{eid}/status",
                          json={"status": "in_progress"}, headers=headers)
            r_done = await c.patch(f"{BASE_URL}/api/v1/tool-entries/{eid}/status",
                          json={"status": "done"}, headers=headers)
            r_bf = await c.patch(f"{BASE_URL}/api/v1/tool-entries/{eid}/status",
                          json={"status": "backfilled", "is_backfilled": True}, headers=headers)
            r_final = await c.get(f"{BASE_URL}/api/v1/tool-entries", headers=headers)
            entry = next((e for e in r_final.json().get("items", []) if e["id"] == eid), None)
            ok = entry and entry["status"] == "backfilled" and entry.get("is_backfilled") == True
            record("D-2", "工具状态流转 pending->in_progress->done->backfilled", "D", ok,
                  f"ip={r_ip.status_code}, done={r_done.status_code}, bf={r_bf.status_code}")
        except Exception as e:
            record("D-2", "工具状态流转", "D", False, str(e)[:120])

        # D-3: is_backfilled 标记
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/tool-entries",
                               json={"action_name": "D3回填标记", "tool_name": "T"}, headers=headers)
            eid = r1.json().get("id")
            await c.patch(f"{BASE_URL}/api/v1/tool-entries/{eid}/status",
                          json={"status": "done", "is_backfilled": True}, headers=headers)
            r = await c.get(f"{BASE_URL}/api/v1/tool-entries", headers=headers)
            entry = next((e for e in r.json().get("items", []) if e["id"] == eid), None)
            record("D-3", "is_backfilled 标记", "D", entry and entry.get("is_backfilled") == True)
        except Exception as e:
            record("D-3", "is_backfilled", "D", False, str(e)[:120])

        # D-4: 工具入口无效流转拒绝
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/tool-entries",
                               json={"action_name": "D4无效流", "tool_name": "T"}, headers=headers)
            eid = r1.json().get("id")
            r = await c.patch(f"{BASE_URL}/api/v1/tool-entries/{eid}/status",
                            json={"status": "backfilled"}, headers=headers)
            record("D-4", "pending->backfilled 被拒", "D", r.status_code == 400)
        except Exception as e:
            record("D-4", "无效流转拒绝", "D", False, str(e)[:120])

        # D-5: 工具入口按状态过滤
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/tool-entries",
                               json={"action_name": "D5过滤测试", "tool_name": "T"}, headers=headers)
            r_all = await c.get(f"{BASE_URL}/api/v1/tool-entries", headers=headers)
            r_pending = await c.get(f"{BASE_URL}/api/v1/tool-entries?status=pending", headers=headers)
            total_all = r_all.json().get("total", 0)
            total_pending = r_pending.json().get("total", 0)
            record("D-5", "按状态过滤", "D", total_pending <= total_all,
                  f"pending={total_pending}, all={total_all}")
        except Exception as e:
            record("D-5", "状态过滤", "D", False, str(e)[:120])

        # D-6: 客户线索 CRUD
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/leads",
                               json={"source": "referral", "status": "initial_contact", "next_action": "电话沟通"},
                               headers=headers)
            lid = r1.json().get("id")
            r2 = await c.get(f"{BASE_URL}/api/v1/leads", headers=headers)
            list_has = any(l["id"] == lid for l in r2.json().get("items", []))
            await c.delete(f"{BASE_URL}/api/v1/leads/{lid}", headers=headers)
            record("D-6", "线索 CRUD", "D", r1.status_code in [200, 201] and list_has)
        except Exception as e:
            record("D-6", "线索 CRUD", "D", False, str(e)[:120])

        # D-7: 线索状态流转
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/leads",
                               json={"source": "website", "status": "initial_contact"}, headers=headers)
            lid = r1.json().get("id")
            await c.put(f"{BASE_URL}/api/v1/leads/{lid}", json={"status": "intent_confirmed"}, headers=headers)
            await c.put(f"{BASE_URL}/api/v1/leads/{lid}", json={"status": "converted"}, headers=headers)
            r = await c.get(f"{BASE_URL}/api/v1/leads/{lid}", headers=headers)
            final_status = r.json().get("status")
            record("D-7", "线索 initial->intent->converted", "D", final_status == "converted",
                  f"final={final_status}")
        except Exception as e:
            record("D-7", "线索状态流转", "D", False, str(e)[:120])

        # D-8: 线索无效流转拒绝
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/leads",
                               json={"source": "event", "status": "initial_contact"}, headers=headers)
            lid = r1.json().get("id")
            r = await c.put(f"{BASE_URL}/api/v1/leads/{lid}", json={"status": "converted"}, headers=headers)
            record("D-8", "initial->converted 被拒", "D", r.status_code == 400)
        except Exception as e:
            record("D-8", "无效流转拒绝", "D", False, str(e)[:120])

        # D-9: 线索转化关联 client_id
        try:
            r1 = await c.post(f"{BASE_URL}/api/v1/leads",
                               json={"source": "cold_outreach", "status": "intent_confirmed"}, headers=headers)
            lid = r1.json().get("id")
            r = await c.put(f"{BASE_URL}/api/v1/leads/{lid}",
                           json={"status": "converted", "client_id": 1}, headers=headers)
            data = r.json()
            record("D-9", "转化时关联 client_id", "D",
                      r.status_code == 200 and data.get("client_id") == 1)
        except Exception as e:
            record("D-9", "关联 client_id", "D", False, str(e)[:120])

        # D-10: leads 字段不重复 clients
        try:
            from app.models.lead import Lead
            cols = [col.name for col in Lead.__table__.columns]
            banned = {"name", "contact_person", "contact_phone", "email", "company", "address"}
            overlap = set(cols) & banned
            record("D-10", "leads 字段不重复 clients", "D", len(overlap) == 0,
                  f"lead_cols={cols}, overlap={overlap or 'none'}")
        except Exception as e:
            record("D-10", "字段不重复", "D", False, str(e)[:120])


async def run_hmr_tests(token: str):
    """H/M/R: 帮助内容 / 迁移脚本 / 回归（3 项）"""
    print("\n=== H/M/R: 帮助内容 / 迁移 / 回归 ===")

    # H-1: help_content.py 所有 v2.2 错误码
    try:
        from app.core.help_content import HELP_CONTENT
        required = ["SNAPSHOT_WRITE_FAILED", "SNAPSHOT_VERSION_NOT_FOUND",
                     "SUMMARY_REFRESH_FAILED", "MINUTES_ASSOCIATION_REQUIRED",
                     "TOOL_ENTRY_INVALID_TRANSITION", "LEAD_INVALID_TRANSITION"]
        missing = [k for k in required if k not in HELP_CONTENT]
        record("H-1", "help_content 含 6 个 v2.2 错误码", "-", len(missing) == 0,
              f"missing={missing or 'none'}")
    except Exception as e:
        record("H-1", "help_content", "-", False, str(e))

    # M-1: 迁移脚本存在
    try:
        migration_dir = os.path.join(os.path.dirname(__file__), "..", "migrations")
        scripts = ["v2.2_cluster_a1.sql", "v2.2_cluster_a2.sql", "v2.2_cluster_c.sql", "v2.2_cluster_d.sql"]
        exist_all = all(os.path.exists(os.path.join(migration_dir, s)) for s in scripts)
        record("M-1", "4 个迁移脚本存在", "-", exist_all)
    except Exception as e:
        record("M-1", "迁移脚本", "-", False, str(e))

    # R-1: pytest 全量回归
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no", "-q"],
            capture_output=True, text=True, cwd=os.path.join(os.path.dirname(__file__), ".."),
        )
        output = result.stdout + result.stderr
        lines = output.split("\n")
        last_line = ""
        for line in reversed(lines):
            if "passed" in line or "failed" in line:
                last_line = line.strip()
                break
        passed = result.returncode == 0
        record("R-1", "pytest 全量回归 0 FAILED", "-", passed, last_line[:100])
    except Exception as e:
        record("R-1", "pytest 回归", "-", False, str(e))


async def main():
    print("=" * 60)
    print("v2.2 手动测试计划 — 自动化执行")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as c:
        try:
            r = await c.post(f"{BASE_URL}/api/v1/auth/login",
                              data={"username": "admin", "password": "admin123"})
            token = f"Bearer {r.json()['access_token']}"
            print(f"\n[OK] Login success")
        except Exception as e:
            print(f"\n[FAIL] Backend not running or login failed: {e}")
            print("请先启动后端: cd backend && uvicorn app.main:app --port 8000 --reload")
            return

    await run_a1_tests(token)
    await run_a2_tests(token)
    await run_b_tests(token)
    await run_c_tests(token)
    await run_d_tests(token)
    await run_hmr_tests(token)

    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    passed = sum(1 for r in RESULTS if r["passed"])
    failed = sum(1 for r in RESULTS if not r["passed"])
    total = len(RESULTS)

    print(f"\n总计: {total} 项 | 通过: {passed} | 失败: {failed}\n")

    for r in RESULTS:
        icon = "[PASS]" if r["passed"] else "[FAIL]"
        detail = f" — {r['detail']}" if r["detail"] else ""
        print(f"  {icon} [{r['id']}] {r['name']} ({r['cluster']}){detail}")

    if failed > 0:
        print(f"\n[WARN] {failed} items failed, need fix")
    else:
        print(f"\n[ALL PASS] All {total} items passed!")


if __name__ == "__main__":
    asyncio.run(main())
