"""FR-302 外包协作记录测试。"""


async def _auth(client) -> dict:
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- FR-302: 外包协作 ---


async def test_outsource_create_all_fields_success(client):
    """外包费用——完整字段创建成功"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "outsource_name": "张三",
        "has_invoice": True,
        "tax_treatment": "invoiced",
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["outsource_name"] == "张三"
    assert data["has_invoice"] is True
    assert data["tax_treatment"] == "invoiced"


async def test_outsource_create_missing_name_returns_422(client):
    """外包费用缺少外包方姓名 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "has_invoice": True,
        "tax_treatment": "invoiced",
    }, headers=h)
    assert r.status_code == 422
    assert "外包费用必须填写外包方姓名" in r.json()["detail"]


async def test_outsource_create_missing_has_invoice_returns_422(client):
    """外包费用缺少是否取得发票 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "outsource_name": "李四",
        "tax_treatment": "none",
    }, headers=h)
    assert r.status_code == 422
    assert "外包费用必须填写是否取得发票" in r.json()["detail"]


async def test_outsource_create_missing_tax_treatment_returns_422(client):
    """外包费用缺少税务处理方式 → 422"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "outsource_name": "王五",
        "has_invoice": False,
    }, headers=h)
    assert r.status_code == 422
    assert "外包费用必须填写税务处理方式" in r.json()["detail"]


async def test_outsource_error_message_contains_field_name(client):
    """422 错误消息包含字段名称"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
    }, headers=h)
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "外包方姓名" in detail


async def test_non_outsource_create_ignores_outsource_fields(client):
    """非外包分类——传入外包字段应被忽略"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-04-01",
        "category": "office",
        "funding_source": "company_account",
        "outsource_name": "不应保留",
        "has_invoice": True,
        "tax_treatment": "invoiced",
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["outsource_name"] is None
    assert data["has_invoice"] is None
    assert data["tax_treatment"] is None


async def test_non_outsource_create_stores_null(client):
    """非外包分类——外包字段存储为 NULL"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 3000, "date": "2026-04-01",
        "category": "office",
        "funding_source": "company_account",
    }, headers=h)
    assert r.status_code == 201
    data = r.json()
    assert data["outsource_name"] is None
    assert data["has_invoice"] is None
    assert data["tax_treatment"] is None


async def test_outsource_update_also_validates_fields(client):
    """更新接口——外包分类同样校验必填字段"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "outsource_name": "张三",
        "has_invoice": True,
        "tax_treatment": "invoiced",
    }, headers=h)
    rid = r.json()["id"]

    # 更新时清空外包方姓名 → 应返回 422
    r2 = await client.put(f"/api/v1/finances/{rid}", json={
        "outsource_name": None,
    }, headers=h)
    assert r2.status_code == 422
    assert "外包费用必须填写外包方姓名" in r2.json()["detail"]


async def test_non_outsource_update_clears_outsource_fields(client):
    """更新接口——切换到非外包分类时，外包字段被清空"""
    h = await _auth(client)
    r = await client.post("/api/v1/finances", json={
        "type": "expense", "amount": 5000, "date": "2026-04-01",
        "category": "outsourcing",
        "funding_source": "company_account",
        "outsource_name": "李四",
        "has_invoice": True,
        "tax_treatment": "withholding",
    }, headers=h)
    rid = r.json()["id"]

    # 切换分类为 office
    r2 = await client.put(f"/api/v1/finances/{rid}", json={
        "category": "office",
    }, headers=h)
    assert r2.status_code == 200
    data = r2.json()
    assert data["category"] == "office"
    assert data["outsource_name"] is None
    assert data["has_invoice"] is None
    assert data["tax_treatment"] is None
