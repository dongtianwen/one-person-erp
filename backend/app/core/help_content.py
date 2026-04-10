"""v1.10 帮助内容映射——纯 Python 字典，不入数据库，不建查询接口。

前端帮助内容在 frontend/src/constants/help.js，后端帮助内容在此文件。
"""

from __future__ import annotations

from app.core.constants import HELP_MAX_NEXT_STEPS

HELP_CONTENT: dict[str, dict] = {
    "REQUIREMENT_FROZEN": {
        "reason": "该项目已关联报价单且报价状态为已接受，需求进入冻结状态，不允许直接修改。",
        "next_steps": [
            "前往项目详情页 → 变更单 Tab",
            "点击「新建变更单」，填写变更描述和额外费用",
            "等待变更单状态流转为 confirmed",
            "confirmed 后需求变更才正式生效",
        ],
        "doc_anchor": "change-order-flow",
    },
    "CHANGE_ORDER_INVALID_TRANSITION": {
        "reason": "变更单当前状态不允许执行此操作。confirmed/rejected/cancelled 为终态。",
        "next_steps": [
            "pending 状态可执行：确认、拒绝、撤回",
            "confirmed/rejected/cancelled 为终态，不可再操作",
            "如需重新提交，请新建一条变更单",
        ],
        "doc_anchor": "change-order-status",
    },
    "MILESTONE_NOT_COMPLETED": {
        "reason": "收款状态流转需要里程碑先标记为已完成。",
        "next_steps": [
            "前往项目详情页 → 里程碑列表",
            "找到对应里程碑，将状态更新为「已完成」",
            "完成后即可触发开票/收款流转",
        ],
        "doc_anchor": "milestone-payment",
    },
    "PROJECT_CLOSE_CONDITIONS_NOT_MET": {
        "reason": "项目关闭需要满足所有前置条件，当前有条件未满足。",
        "next_steps": [
            "点击「关闭条件检查」查看具体未满足项",
            "确保所有里程碑状态为已完成",
            "确保存在 acceptance_type=final 且 status=passed 的验收记录",
            "确保所有里程碑收款状态为已到账（或收款金额为0）",
            "确保至少有一条交付物记录",
        ],
        "doc_anchor": "project-close",
    },
    "PROJECT_ALREADY_CLOSED": {
        "reason": "项目已完成关闭，不可重复关闭，核心字段不可修改。",
        "next_steps": [
            "已关闭项目数据仅供查阅",
            "如需查看关闭条件快照，前往项目详情页查看 close_checklist",
        ],
        "doc_anchor": "project-close",
    },
    "INVOICE_AMOUNT_EXCEEDS_CONTRACT": {
        "reason": "同一合同下所有未作废发票的金额合计不得超过合同总金额。",
        "next_steps": [
            "前往合同详情页 → 发票 Tab 查看已开票金额进度条",
            "检查是否有重复开票",
            "如需开票金额超出合同，请先修改合同金额",
        ],
        "doc_anchor": "invoice-amount-limit",
    },
    "INVOICE_STATUS_INVALID_TRANSITION": {
        "reason": "发票状态只能按固定顺序流转：草稿→已开票→客户已收→已核销。",
        "next_steps": [
            "草稿可流转到：已开票、已作废",
            "已开票可流转到：客户已收、已作废",
            "客户已收可流转到：已核销",
            "已核销和已作废为终态，不可再操作",
        ],
        "doc_anchor": "invoice-status",
    },
    "INVOICE_CANNOT_DELETE": {
        "reason": "已核销（verified）和已作废（cancelled）的发票不允许删除，以保证财务记录完整性。",
        "next_steps": [
            "已核销发票如有问题请联系代理记账处理",
            "如需作废已开票发票，可将状态流转为「已作废」",
        ],
        "doc_anchor": "invoice-delete",
    },
    "QUOTE_ALREADY_CONVERTED": {
        "reason": "一张报价单只能转换为一份合同，该报价单已完成转换。",
        "next_steps": [
            "前往报价单详情页查看已关联的合同编号",
            "如需新合同，请重新创建报价单",
        ],
        "doc_anchor": "quote-convert",
    },
    "QUOTE_NOT_ACCEPTED": {
        "reason": "只有状态为「已接受」的报价单才能转换为合同。",
        "next_steps": [
            "先执行「接受」操作，将报价单状态变更为 accepted",
            "再执行「转换合同」",
        ],
        "doc_anchor": "quote-convert",
    },
    # 以下错误码 detail 已足够说明，不需要 help 映射：
    # PAYMENT_STATUS_INVALID_TRANSITION — 通用提示已够用
    # QUOTE_STATUS_INVALID_TRANSITION — 通用提示已够用
    # NOT_FOUND — detail 已说明
    # VALIDATION_ERROR — detail 已说明
}


def get_help(error_code: str) -> dict | None:
    """返回错误码对应帮助内容，不存在时返回 None。"""
    content = HELP_CONTENT.get(error_code)
    if not content:
        return None
    return {
        "reason": content["reason"],
        "next_steps": content["next_steps"][:HELP_MAX_NEXT_STEPS],
        **({"doc_anchor": content["doc_anchor"]} if "doc_anchor" in content else {}),
    }
