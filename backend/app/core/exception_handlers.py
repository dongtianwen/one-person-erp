"""v1.10 异常处理器——在 detail/code 基础上追加 help 字段。

规则：
1. help 字段只追加，禁止修改 detail 和 code
2. 错误码无对应帮助内容时，响应中不包含 help 字段
3. HTTP 5xx 不附加 help
"""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.help_content import get_help


def build_error_response(detail: str, code: str) -> dict:
    """在现有 detail/code 基础上追加 help，禁止修改 detail 和 code 的内容。"""
    response: dict = {"detail": detail, "code": code}
    help_data = get_help(code)
    if help_data:
        response["help"] = help_data
    return response


class BusinessException(HTTPException):
    """业务异常——携带 detail + error_code，由 FastAPI 异常处理器统一格式化。

    继承 HTTPException 以确保被现有端点的 except HTTPException: raise 正确透传。
    """

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.code = code
        super().__init__(status_code=status_code, detail=detail)


async def business_exception_handler(request: Request, exc: BusinessException) -> JSONResponse:
    """FastAPI 异常处理器：将 BusinessException 转为含 help 的 JSON 响应。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_response(exc.detail, exc.code),
    )
