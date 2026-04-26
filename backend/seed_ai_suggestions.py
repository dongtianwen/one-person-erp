import sqlite3
from datetime import datetime

conn = sqlite3.connect('shubiao.db')
cur = conn.cursor()

now = datetime.now().isoformat()

suggestions = [
    {
        "agent_run_id": 1,
        "decision_type": "resource_allocation",
        "suggestion_type": "resource_overload",
        "title": "团队接近满负荷，建议暂缓新项目接单",
        "description": "手头9个项目同时推进，团队资源占用已超过九成。当前两个核心项目正处于交付关键期，如果再接新单，很可能导致现有项目延期或质量下降。建议先稳住现有盘子，等核心交付完成后再考虑扩张。",
        "priority": "high",
        "status": "pending",
        "suggested_action": "pause_new_orders",
        'action_params': '{"duration": "30天", "reason": "资源饱和"}',
        "source_rule": "resource_utilization_rule",
        "llm_enhanced": 1,
        "risk_score": 78,
        "strategy_code": "delivery_suspension"
    },
    {
        "agent_run_id": 1,
        "decision_type": "cashflow_management",
        "suggestion_type": "cashflow_risk",
        "title": "约56万应收账款逾期，建议立即发起催收",
        "description": "目前有约56万元回款已经逾期超过一个月，账上可用资金偏紧。按当前趋势预测，未来三个月经营现金流可能持续为负，将影响日常运营周转。建议本周内主动联系欠款客户，商定分期回款计划。",
        "priority": "high",
        "status": "pending",
        "suggested_action": "create_reminder",
        'action_params': '{"type": "urgent_collection", "amount": 560000}',
        "source_rule": "cashflow_forecast_rule",
        "llm_enhanced": 1,
        "risk_score": 72,
        "strategy_code": "escalated_reminder"
    },
    {
        "agent_run_id": 1,
        "decision_type": "project_health",
        "suggestion_type": "schedule_risk",
        "title": "部分功能模块进度滞后，建议重新调配人力",
        "description": "文档识别和语音播报两个功能模块的进度明显落后于计划，目前整体完成度不到一半。如果不及时调整资源投入，很可能拖累整体项目的交付时间。建议把非紧急任务暂时搁置，集中人力保住核心功能的上线节点。",
        "priority": "medium",
        "status": "pending",
        "suggested_action": "adjust_resource",
        'action_params': '{"focus_projects": [5, 7], "deprioritize": [6]}',
        "source_rule": "project_schedule_rule",
        "llm_enhanced": 1,
        "risk_score": 55,
        "strategy_code": "light_reminder"
    },
    {
        "agent_run_id": 1,
        "decision_type": "customer_strategy",
        "suggestion_type": "customer_concentration",
        "title": "收入过度依赖少数大客户，建议加大新客户开拓力度",
        "description": "目前收入几乎全靠两三家客户支撑，其中一家占比就超过八成。这种结构很脆弱——一旦大客户有变动，整个公司都会受影响。趁现在业务稳定，应该分出精力去接触潜在新客户，逐步降低单一客户依赖。",
        "priority": "medium",
        "status": "pending",
        "suggested_action": "continue_monitoring",
        'action_params': '{"target": "新客户开发", "threshold": "单客户占比<50%"}',
        "source_rule": "customer_diversification_rule",
        "llm_enhanced": 1,
        "risk_score": 45,
        "strategy_code": "light_reminder"
    }
]

for s in suggestions:
    cur.execute("""
        INSERT INTO agent_suggestions 
        (agent_run_id, decision_type, suggestion_type, title, description, priority, status, 
         suggested_action, action_params, source_rule, llm_enhanced, created_at, updated_at, is_deleted,
         risk_score, strategy_code, score_breakdown)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (
        s["agent_run_id"], s["decision_type"], s["suggestion_type"], s["title"],
        s["description"], s["priority"], s["status"], s["suggested_action"],
        s["action_params"], s["source_rule"], s["llm_enhanced"], now, now,
        s["risk_score"], s["strategy_code"],
        f'{{"days_overdue_score": {25 if s["suggestion_type"] == "cashflow_risk" else 10}, "amount_score": {20 if s["suggestion_type"] == "cashflow_risk" else 12}, "amount_ratio_score": {18 if s["suggestion_type"] == "customer_concentration" else 8}, "customer_risk_score": {15 if s["suggestion_type"] == "customer_concentration" else 6}, "acceptance_status_score": 5, "invoice_status_score": 4}}'
    ))

conn.commit()
print(f"Inserted {len(suggestions)} suggestions")
conn.close()
