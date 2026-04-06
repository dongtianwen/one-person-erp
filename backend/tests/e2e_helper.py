"""
数标云管 - 端到端功能测试
测试所有核心业务逻辑和 API 端点
"""

import httpx
import json
import sys

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"

passed = 0
failed = 0
token = ""


def log(msg, ok=True):
    global passed, failed
    if ok:
        passed += 1
        print(f"  [PASS] {msg}")
    else:
        failed += 1
        print(f"  [FAIL] {msg}")


def test(name, actual, expected=None, check_fn=None):
    global passed, failed
    try:
        if check_fn:
            result = check_fn(actual)
            if result:
                passed += 1
                print(f"  [PASS] {name}")
            else:
                failed += 1
                print(f"  [FAIL] {name} - got: {actual}")
        elif expected is not None:
            if actual == expected:
                passed += 1
                print(f"  [PASS] {name}")
            else:
                failed += 1
                print(f"  [FAIL] {name} - expected: {expected}, got: {actual}")
        else:
            if actual:
                passed += 1
                print(f"  [PASS] {name}")
            else:
                failed += 1
                print(f"  [FAIL] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name} - error: {e}")


def auth_headers():
    return {"Authorization": f"Bearer {token}"}


def main():
    global token
    client = httpx.Client(base_url=BASE_URL, timeout=10)

    print("\n" + "=" * 60)
    print("  数标云管 - 端到端功能测试")
    print("=" * 60)

    # ========== 1. 认证模块 ==========
    print("\n[1] 认证模块测试")

    # 1.1 健康检查
    r = client.get("/health")
    test("健康检查", r.status_code, 200)

    # 1.2 登录成功
    r = client.post(f"{API}/auth/login", data={"username": "admin", "password": "admin123"})
    test("登录成功", r.status_code, 200)
    if r.status_code == 200:
        data = r.json()
        token = data["access_token"]
        test("返回 access_token", len(token) > 0)
        test("token_type 为 bearer", data["token_type"], "bearer")
        test("返回 refresh_token", len(data["refresh_token"]) > 0)

    # 1.3 登录失败 - 错误密码
    r = client.post(f"{API}/auth/login", data={"username": "admin", "password": "wrong"})
    test("错误密码返回401", r.status_code, 401)

    # 1.4 获取当前用户
    r = client.get(f"{API}/auth/me", headers=auth_headers())
    test("获取当前用户", r.status_code, 200)
    if r.status_code == 200:
        test("用户名为admin", r.json()["username"], "admin")

    # 1.5 无Token访问受保护接口
    r = client.get(f"{API}/auth/me")
    test("无Token返回401", r.status_code, 401)

    # 1.6 Token刷新
    login_resp = client.post(f"{API}/auth/login", data={"username": "admin", "password": "admin123"})
    refresh_token = login_resp.json()["refresh_token"]
    r = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token})
    test("Token刷新成功", r.status_code, 200)

    # 1.7 登出
    r = client.post(f"{API}/auth/logout", headers=auth_headers())
    test("登出成功", r.status_code, 200)

    # 重新登录继续测试
    login_resp = client.post(f"{API}/auth/login", data={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]

    # ========== 2. 客户管理模块 ==========
    print("\n[2] 客户管理模块测试")

    # 2.1 创建客户
    customer_data = {
        "name": "测试科技公司",
        "contact_person": "张三",
        "phone": "13800138000",
        "email": "test@example.com",
        "company": "测试科技有限公司",
        "source": "referral",
        "status": "potential",
        "notes": "测试客户",
    }
    r = client.post(f"{API}/customers", json=customer_data, headers=auth_headers())
    test("创建客户成功", r.status_code, 201)
    customer_id = None
    if r.status_code == 201:
        customer_id = r.json()["id"]
        test("客户ID正确", customer_id > 0)
        test("客户名称正确", r.json()["name"], "测试科技公司")
        test("客户状态正确", r.json()["status"], "potential")

    # 2.2 重复客户检测
    r = client.post(f"{API}/customers", json=customer_data, headers=auth_headers())
    test("重复客户被拒绝", r.status_code, 400)

    # 2.3 获取客户列表
    r = client.get(f"{API}/customers", headers=auth_headers())
    test("获取客户列表", r.status_code, 200)
    if r.status_code == 200:
        test("客户总数正确", r.json()["total"], 1)

    # 2.4 获取客户详情
    r = client.get(f"{API}/customers/{customer_id}", headers=auth_headers())
    test("获取客户详情", r.status_code, 200)

    # 2.5 更新客户
    r = client.put(f"{API}/customers/{customer_id}", json={"status": "follow_up"}, headers=auth_headers())
    test("更新客户状态", r.status_code, 200)
    if r.status_code == 200:
        test("状态更新为follow_up", r.json()["status"], "follow_up")

    # 2.6 流失客户必须填写原因
    r = client.put(f"{API}/customers/{customer_id}", json={"status": "lost"}, headers=auth_headers())
    test("流失无原因被拒绝", r.status_code, 400)

    r = client.put(
        f"{API}/customers/{customer_id}", json={"status": "lost", "lost_reason": "价格太高"}, headers=auth_headers()
    )
    test("流失有原因成功", r.status_code, 200)

    # 2.7 客户统计
    r = client.get(f"{API}/customers/stats/status", headers=auth_headers())
    test("客户统计API", r.status_code, 200)

    # 创建第二个客户用于测试删除
    customer2 = {
        "name": "另一家公司",
        "contact_person": "李四",
        "phone": "13900139000",
        "company": "另一家公司",
        "source": "network",
        "status": "potential",
    }
    r = client.post(f"{API}/customers", json=customer2, headers=auth_headers())
    customer2_id = r.json()["id"]

    # 2.8 删除无关联客户
    r = client.delete(f"{API}/customers/{customer2_id}", headers=auth_headers())
    test("删除无关联客户", r.status_code, 200)

    # 2.9 删除有关联客户（第一个客户有关联项目）
    # 先创建项目关联
    project_data = {
        "name": "ERP系统",
        "customer_id": customer_id,
        "description": "企业ERP",
        "budget": 50000,
        "start_date": "2026-04-01",
        "end_date": "2026-06-30",
    }
    r = client.post(f"{API}/projects", json=project_data, headers=auth_headers())
    project_id = r.json()["id"]

    r = client.delete(f"{API}/customers/{customer_id}", headers=auth_headers())
    test("删除有关联客户被拒绝", r.status_code, 400)

    # ========== 3. 项目管理模块 ==========
    print("\n[3] 项目管理模块测试")

    # 3.1 创建项目
    test("创建项目成功", r.status_code if hasattr(r, "status_code") else 0, 0)  # placeholder
    r = client.post(
        f"{API}/projects",
        json={
            "name": "小程序开发",
            "customer_id": customer_id,
            "description": "微信小程序",
            "budget": 30000,
            "start_date": "2026-05-01",
            "end_date": "2026-07-31",
        },
        headers=auth_headers(),
    )
    test("创建项目成功", r.status_code, 201)
    project2_id = None
    if r.status_code == 201:
        project2_id = r.json()["id"]
        test("项目名称正确", r.json()["name"], "小程序开发")
        test("预算正确", r.json()["budget"], 30000)
        test("初始进度为0", r.json()["progress"], 0)

    # 3.2 项目列表
    r = client.get(f"{API}/projects", headers=auth_headers())
    test("项目列表", r.status_code, 200)
    if r.status_code == 200:
        test("项目数量>=2", len(r.json()) >= 2)

    # 3.3 项目详情
    r = client.get(f"{API}/projects/{project2_id}", headers=auth_headers())
    test("项目详情", r.status_code, 200)

    # 3.4 创建任务
    r = client.post(
        f"{API}/projects/{project2_id}/tasks",
        json={"title": "需求分析", "description": "完成需求文档", "priority": "high", "due_date": "2026-05-15"},
        headers=auth_headers(),
    )
    test("创建任务成功", r.status_code, 201)
    task_id = None
    if r.status_code == 201:
        task_id = r.json()["id"]
        test("任务标题正确", r.json()["title"], "需求分析")
        test("任务优先级正确", r.json()["priority"], "high")

    # 3.5 更新任务状态
    r = client.put(f"{API}/projects/tasks/{task_id}", json={"status": "in_progress"}, headers=auth_headers())
    test("更新任务状态", r.status_code, 200)

    # 3.6 创建里程碑
    r = client.post(
        f"{API}/projects/{project2_id}/milestones",
        json={"title": "需求确认", "due_date": "2026-05-15"},
        headers=auth_headers(),
    )
    test("创建里程碑成功", r.status_code, 201)
    milestone_id = None
    if r.status_code == 201:
        milestone_id = r.json()["id"]
        test("里程碑标题正确", r.json()["title"], "需求确认")
        test("初始未完成", r.json()["is_completed"], False)

    # 3.7 完成里程碑
    r = client.put(f"{API}/projects/milestones/{milestone_id}", json={"is_completed": True}, headers=auth_headers())
    test("完成里程碑", r.status_code, 200)
    if r.status_code == 200:
        test("里程碑已标记完成", r.json()["is_completed"], True)
        test("记录了完成日期", r.json()["completed_date"] is not None)

    # 3.8 检查项目进度更新
    r = client.get(f"{API}/projects/{project2_id}", headers=auth_headers())
    if r.status_code == 200:
        test("项目进度自动更新为100%", r.json()["project"]["progress"], 100)

    # 3.9 删除项目（级联删除）
    r = client.delete(f"{API}/projects/{project2_id}", headers=auth_headers())
    test("删除项目成功", r.status_code, 200)

    # ========== 4. 合同管理模块 ==========
    print("\n[4] 合同管理模块测试")

    # 4.1 创建合同
    r = client.post(
        f"{API}/contracts",
        json={
            "title": "ERP开发合同",
            "customer_id": customer_id,
            "project_id": project_id,
            "amount": 50000,
            "signed_date": "2026-04-01",
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
        },
        headers=auth_headers(),
    )
    test("创建合同成功", r.status_code, 201)
    contract_id = None
    if r.status_code == 201:
        contract_id = r.json()["id"]
        test("合同编号自动生成", r.json()["contract_no"].startswith("HT-"))
        test("合同金额正确", r.json()["amount"], 50000)
        test("初始状态为草稿", r.json()["status"], "draft")

    # 4.2 合同列表
    r = client.get(f"{API}/contracts", headers=auth_headers())
    test("合同列表", r.status_code, 200)

    # 4.3 合同状态流转 - 草稿->生效
    r = client.put(f"{API}/contracts/{contract_id}", json={"status": "active"}, headers=auth_headers())
    test("合同状态: 草稿->生效", r.status_code, 200)

    # 4.4 合同状态流转 - 生效->执行中
    r = client.put(f"{API}/contracts/{contract_id}", json={"status": "executing"}, headers=auth_headers())
    test("合同状态: 生效->执行中", r.status_code, 200)

    # 4.5 非法状态流转 - 执行中->草稿（应拒绝）
    r = client.put(f"{API}/contracts/{contract_id}", json={"status": "draft"}, headers=auth_headers())
    test("非法状态流转被拒绝", r.status_code, 400)

    # 4.6 合同终止必须填写原因
    r = client.put(f"{API}/contracts/{contract_id}", json={"status": "terminated"}, headers=auth_headers())
    test("终止无原因被拒绝", r.status_code, 400)

    r = client.put(
        f"{API}/contracts/{contract_id}",
        json={"status": "terminated", "termination_reason": "客户取消"},
        headers=auth_headers(),
    )
    test("终止有原因成功", r.status_code, 200)

    # 4.7 生效中的合同不可删除
    # 先创建一个新合同
    r = client.post(
        f"{API}/contracts",
        json={
            "title": "测试合同",
            "customer_id": customer_id,
            "amount": 10000,
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
        },
        headers=auth_headers(),
    )
    contract2_id = r.json()["id"]
    client.put(f"{API}/contracts/{contract2_id}", json={"status": "active"}, headers=auth_headers())
    r = client.delete(f"{API}/contracts/{contract2_id}", headers=auth_headers())
    test("生效中合同不可删除", r.status_code, 400)

    # ========== 5. 财务管理模块 ==========
    print("\n[5] 财务管理模块测试")

    # 5.1 创建收入记录
    r = client.post(
        f"{API}/finances",
        json={
            "type": "income",
            "amount": 20000,
            "category": "development",
            "description": "首付款",
            "date": "2026-04-04",
            "contract_id": contract_id,
            "status": "confirmed",
        },
        headers=auth_headers(),
    )
    test("创建收入记录", r.status_code, 201)
    if r.status_code == 201:
        test("收入金额正确", r.json()["amount"], 20000)
        test("收入类型正确", r.json()["type"], "income")

    # 5.2 创建支出记录
    r = client.post(
        f"{API}/finances",
        json={
            "type": "expense",
            "amount": 5000,
            "category": "server",
            "description": "服务器费用",
            "date": "2026-04-04",
            "status": "confirmed",
        },
        headers=auth_headers(),
    )
    test("创建支出记录", r.status_code, 201)

    # 5.3 发票号码唯一性
    r = client.post(
        f"{API}/finances",
        json={"type": "income", "amount": 10000, "date": "2026-04-04", "invoice_no": "INV-001", "status": "pending"},
        headers=auth_headers(),
    )
    test("首次使用发票号", r.status_code, 201)

    r = client.post(
        f"{API}/finances",
        json={"type": "income", "amount": 10000, "date": "2026-04-04", "invoice_no": "INV-001", "status": "pending"},
        headers=auth_headers(),
    )
    test("重复发票号被拒绝", r.status_code, 400)

    # 5.4 财务记录列表
    r = client.get(f"{API}/finances", headers=auth_headers())
    test("财务记录列表", r.status_code, 200)

    # 5.5 月度统计
    r = client.get(f"{API}/finances/stats/monthly?year=2026&month=4", headers=auth_headers())
    test("月度统计API", r.status_code, 200)
    if r.status_code == 200:
        test("月收入=20000", r.json()["income"], 20000)
        test("月支出=5000", r.json()["expense"], 5000)
        test("月利润=15000", r.json()["profit"], 15000)

    # 5.6 分类统计
    r = client.get(f"{API}/finances/stats/categories?year=2026&month=4", headers=auth_headers())
    test("分类统计API", r.status_code, 200)

    # 5.7 应收账款
    r = client.get(f"{API}/finances/stats/accounts-receivable", headers=auth_headers())
    test("应收账款API", r.status_code, 200)

    # 5.8 更新财务记录
    r = client.put(f"{API}/finances/1", json={"description": "更新后的描述"}, headers=auth_headers())
    test("更新财务记录", r.status_code, 200)

    # ========== 6. 数据看板模块 ==========
    print("\n[6] 数据看板模块测试")

    # 6.1 仪表盘数据
    r = client.get(f"{API}/dashboard", headers=auth_headers())
    test("仪表盘API", r.status_code, 200)
    if r.status_code == 200:
        data = r.json()
        test("包含月收入", "monthly_income" in data)
        test("包含月支出", "monthly_expense" in data)
        test("包含月利润", "monthly_profit" in data)
        test("活跃项目数>=1", data["active_projects"] >= 1)
        test("客户转化率>=0", data["customer_conversion_rate"] >= 0)

    # 6.2 营收趋势
    r = client.get(f"{API}/dashboard/revenue-trend", headers=auth_headers())
    test("营收趋势API", r.status_code, 200)
    if r.status_code == 200:
        test("返回12个月数据", len(r.json()), 12)

    # 6.3 客户转化漏斗
    r = client.get(f"{API}/dashboard/customer-funnel", headers=auth_headers())
    test("客户漏斗API", r.status_code, 200)

    # 6.4 项目状态分布
    r = client.get(f"{API}/dashboard/project-status", headers=auth_headers())
    test("项目状态分布API", r.status_code, 200)

    # 6.5 待办事项
    r = client.get(f"{API}/dashboard/todos", headers=auth_headers())
    test("待办事项API", r.status_code, 200)
    if r.status_code == 200:
        test("包含tasks字段", "tasks" in r.json())
        test("包含expiring_contracts字段", "expiring_contracts" in r.json())

    # 6.6 数据库备份
    r = client.post(f"{API}/dashboard/backup?backup_dir=./backups", headers=auth_headers())
    test("数据库备份API", r.status_code, 200)
    if r.status_code == 200:
        test("返回备份路径", "backup_path" in r.json())
        test("返回时间戳", "timestamp" in r.json())

    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print(f"  测试结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 项")
    print("=" * 60)

    if failed > 0:
        print(f"\n  有 {failed} 项测试失败，需要修复！")
        sys.exit(1)
    else:
        print(f"\n  所有测试通过！系统功能正常。")
        sys.exit(0)


if __name__ == "__main__":
    main()
