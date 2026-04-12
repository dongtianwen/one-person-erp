#!/usr/bin/env python
"""验证所有 API 返回的字段"""
import requests
import json

BASE_URL = "http://localhost:8001"

def login():
    """登录获取 token"""
    r = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    if r.status_code == 200:
        return r.json()["access_token"]
    else:
        print(f"登录失败：{r.status_code} - {r.text}")
        return None

def test_all_apis():
    token = login()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 获取项目列表
    r = requests.get(f"{BASE_URL}/api/v1/projects", headers=headers)
    projects = r.json()
    if not projects:
        print("没有项目")
        return
    project_id = projects[0]["id"]
    print(f"使用项目 ID: {project_id}")
    
    print("\n" + "="*80)
    print("1. 变更单管理 - client_confirmed_at")
    print("="*80)
    r = requests.get(f"{BASE_URL}/api/v1/projects/{project_id}/change-orders", headers=headers)
    data = r.json()
    print(f"API 返回：{json.dumps(data, indent=2, ensure_ascii=False)}")
    if data.get("data"):
        for item in data["data"]:
            print(f"[OK] ID: {item['id']}, client_confirmed_at: {item.get('client_confirmed_at')}")
    else:
        print("✗ 没有变更单数据")
    
    print("\n" + "="*80)
    print("2. 工时记录 - created_at")
    print("="*80)
    r = requests.get(f"{BASE_URL}/api/v1/projects/{project_id}/work-hours", headers=headers)
    data = r.json()
    print(f"API 返回 logs 结构：{json.dumps(data.get('logs', [])[:2], indent=2, ensure_ascii=False)}")
    if data.get("logs"):
        for log in data["logs"][:3]:
            print(f"[OK] ID: {log['id']}, created_at: {log.get('created_at')}")
    else:
        print("[FAIL] 没有工时记录")
    
    print("\n" + "="*80)
    print("3. 标注任务 - assignee, deadline, progress")
    print("="*80)
    r = requests.get(f"{BASE_URL}/api/v1/annotation-tasks", headers=headers)
    data = r.json()
    print(f"API 返回：{json.dumps(data, indent=2, ensure_ascii=False)}")
    if data.get("data"):
        for task in data["data"]:
            print(f"[OK] ID: {task['id']}, assignee: {task.get('assignee')}, deadline: {task.get('deadline')}, progress: {task.get('progress')}")
    else:
        print("[FAIL] 没有标注任务数据")
    
    print("\n" + "="*80)
    print("4. 训练实验 - metrics_summary")
    print("="*80)
    r = requests.get(f"{BASE_URL}/api/v1/training-experiments", headers=headers)
    data = r.json()
    print(f"API 返回：{json.dumps(data, indent=2, ensure_ascii=False)}")
    if data.get("data"):
        for exp in data["data"]:
            print(f"[OK] ID: {exp['id']}, metrics_summary: {exp.get('metrics_summary')}")
    else:
        print("[FAIL] 没有训练实验数据")
    
    print("\n" + "="*80)
    print("5. 模型版本 - experiment_name, model_path, metrics")
    print("="*80)
    r = requests.get(f"{BASE_URL}/api/v1/model-versions", headers=headers)
    data = r.json()
    print(f"API 返回：{json.dumps(data, indent=2, ensure_ascii=False)}")
    if data.get("data"):
        for mv in data["data"]:
            print(f"[OK] ID: {mv['id']}, experiment_name: {mv.get('experiment_name')}, model_path: {mv.get('model_path')}, metrics: {mv.get('metrics')}")
    else:
        print("[FAIL] 没有模型版本数据")
    
    print("\n" + "="*80)
    print("验证完成!")
    print("="*80)

if __name__ == "__main__":
    test_all_apis()
