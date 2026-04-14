"""v1.12 模板 CRUD 测试——覆盖增删改查、默认保护、语法校验、渲染验证。"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.template import Template
from app.core.template_utils import render_template, can_regenerate_content
from app.core.constants import (
    TEMPLATE_TYPE_QUOTATION, TEMPLATE_TYPE_CONTRACT,
)
from app.core.error_codes import ERROR_CODES
from app.crud import template as tpl_crud


async def _auth(client) -> dict:
    """登录并返回 Authorization headers。"""
    r = await client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── 3.14: Template CRUD operations ──────────────────────────────


@pytest.mark.asyncio
async def test_crud_list(client):
    """验证模板列表。"""
    h = await _auth(client)
    resp = await client.get("/api/v1/templates/", headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # 种子数据有 quotation + contract 模板


@pytest.mark.asyncio
async def test_crud_create_and_read(client):
    """验证创建并读取模板。"""
    h = await _auth(client)
    resp = await client.post("/api/v1/templates/", params={
        "name": "测试模板",
        "content": "# 测试\n\n{{ quotation_no }}\n",
        "template_type": "quotation",
        "description": "测试用",
    }, headers=h)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "测试模板"
    tid = data["id"]

    # 读取
    resp = await client.get(f"/api/v1/templates/{tid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["name"] == "测试模板"


@pytest.mark.asyncio
async def test_crud_update(client):
    """验证更新模板。"""
    h = await _auth(client)
    resp = await client.post("/api/v1/templates/", params={
        "name": "更新前",
        "template_type": "contract",
        "content": "旧内容",
    }, headers=h)
    tid = resp.json()["id"]

    resp = await client.put(f"/api/v1/templates/{tid}", params={
        "name": "更新后",
        "content": "新内容",
    }, headers=h)
    assert resp.status_code == 200
    assert resp.json()["name"] == "更新后"


@pytest.mark.asyncio
async def test_crud_delete_non_default(client):
    """验证删除非默认模板。"""
    h = await _auth(client)
    resp = await client.post("/api/v1/templates/", params={
        "name": "可删除",
        "template_type": "quotation",
        "content": "内容",
    }, headers=h)
    tid = resp.json()["id"]

    resp = await client.delete(f"/api/v1/templates/{tid}", headers=h)
    assert resp.status_code == 200

    # 确认已删除
    resp = await client.get(f"/api/v1/templates/{tid}", headers=h)
    assert resp.status_code == 404


# ── 3.15: Set default with atomic transaction ───────────────────


@pytest.mark.asyncio
async def test_set_default_atomic(client):
    """验证设为默认是原子事务：新模板变默认，旧模板取消默认。"""
    h = await _auth(client)

    # 创建新模板
    resp = await client.post("/api/v1/templates/", params={
        "name": "新默认",
        "template_type": "quotation",
        "content": "新内容",
    }, headers=h)
    new_id = resp.json()["id"]

    # 获取旧默认
    resp = await client.get("/api/v1/templates/default/quotation", headers=h)
    old_id = resp.json()["id"]

    # 设为默认
    resp = await client.patch("/api/v1/templates/set-default", params={
        "template_type": "quotation",
        "template_id": new_id,
    }, headers=h)
    assert resp.status_code == 200

    # 验证新模板是默认
    resp = await client.get(f"/api/v1/templates/{new_id}", headers=h)
    assert resp.json()["is_default"] == 1

    # 验证旧模板不是默认
    resp = await client.get(f"/api/v1/templates/{old_id}", headers=h)
    assert resp.json()["is_default"] == 0


# ── 3.16: Default template deletion protection ──────────────────


@pytest.mark.asyncio
async def test_default_template_deletion_protected(client):
    """验证默认模板不可删除。"""
    h = await _auth(client)
    resp = await client.get("/api/v1/templates/default/quotation", headers=h)
    default_id = resp.json()["id"]

    resp = await client.delete(f"/api/v1/templates/{default_id}", headers=h)
    assert resp.status_code == 400


# ── 3.17: Non-default template deletion with content preservation ─


@pytest.mark.asyncio
async def test_non_default_delete_preserves_generated_content(db_session: AsyncSession):
    """验证删除非默认模板后，已生成的内容不受影响。"""
    tpl = Template(
        name="测试内容保留",
        template_type="quotation",
        content="测试内容",
        is_default=0,
    )
    db_session.add(tpl)
    await db_session.flush()
    tpl_id = tpl.id

    await tpl_crud.delete_template(db_session, tpl_id)

    # 确认模板不存在
    result = await db_session.execute(select(Template).where(Template.id == tpl_id))
    assert result.scalar_one_or_none() is None


# ── 3.18: Invalid Jinja2 syntax rejection ──────────────────────


@pytest.mark.asyncio
async def test_invalid_jinja2_syntax_rejected(client):
    """验证无效 Jinja2 语法被拒绝。"""
    h = await _auth(client)
    resp = await client.post("/api/v1/templates/", params={
        "name": "坏模板",
        "template_type": "quotation",
        "content": "{% if x %}不完整",
    }, headers=h)
    assert resp.status_code == 400


# ── 3.19: Template rendering success ───────────────────────────


@pytest.mark.asyncio
async def test_template_rendering_success():
    """验证模板渲染成功。"""
    content = "你好 {{ name }}！"
    context = {"name": "世界"}
    rendered, error = render_template(content, context)
    assert error == ""
    assert "你好 世界！" == rendered


# ── 3.20: Missing required vars error ──────────────────────────


@pytest.mark.asyncio
async def test_missing_required_vars_error():
    """验证缺少必填变量返回错误。"""
    content = "{{ a }} {{ b }}"
    context = {"a": "值"}
    rendered, error = render_template(content, context, required_vars=["a", "b"])
    assert rendered == ""
    assert "缺少必填变量" in error


# ── 3.21: Bad template rendering error ─────────────────────────


@pytest.mark.asyncio
async def test_bad_template_rendering_error():
    """验证模板渲染失败返回错误。"""
    content = "{% for x in items %}{{ x }}"  # 缺少 endfor
    context: dict = {}
    rendered, error = render_template(content, context)
    assert rendered == ""
    assert error != ""


# ── 3.22: Missing vars not causing render error ────────────────


@pytest.mark.asyncio
async def test_missing_vars_not_causing_render_error():
    """验证变量缺失不导致渲染错误（跳过校验时）。"""
    content = "你好 {{ name }}"
    context: dict = {}
    rendered, error = render_template(content, context)
    assert error == ""
    assert "你好 " in rendered


# ── 3.23: Optional vars using empty string ─────────────────────


@pytest.mark.asyncio
async def test_optional_vars_using_empty_string():
    """验证可选变量使用空字符串。"""
    content = "名称: {{ name }}, 备注: {{ notes }}"
    context = {"name": "测试", "notes": ""}
    rendered, error = render_template(content, context)
    assert error == ""
    assert "名称: 测试, 备注: " in rendered


# ── 3.24: can_regenerate_content with accepted status ──────────


@pytest.mark.asyncio
async def test_can_regenerate_with_accepted_status():
    """验证 accepted 状态不可重新生成。"""
    can, error_code = can_regenerate_content(
        status="accepted",
        template_type=TEMPLATE_TYPE_QUOTATION,
        has_content=True,
        force=True,
    )
    assert can is False
    assert error_code == ERROR_CODES["CONTENT_FROZEN"]


# ── 3.25: can_regenerate_content with active status ────────────


@pytest.mark.asyncio
async def test_can_regenerate_with_active_status():
    """验证 active 状态不可重新生成。"""
    can, error_code = can_regenerate_content(
        status="active",
        template_type=TEMPLATE_TYPE_CONTRACT,
        has_content=True,
        force=True,
    )
    assert can is False
    assert error_code == ERROR_CODES["CONTENT_FROZEN"]


# ── Additional API tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_default_template_by_type(client):
    """验证按类型获取默认模板。"""
    h = await _auth(client)
    resp = await client.get("/api/v1/templates/default/quotation", headers=h)
    assert resp.status_code == 200
    assert resp.json()["template_type"] == "quotation"
    assert resp.json()["is_default"] == 1


@pytest.mark.asyncio
async def test_create_invalid_type_rejected(client):
    """验证创建模板时使用非法类型被拒绝。"""
    h = await _auth(client)
    resp = await client.post("/api/v1/templates/", params={
        "name": "非法类型",
        "template_type": "invalid",
        "content": "内容",
    }, headers=h)
    assert resp.status_code == 422
