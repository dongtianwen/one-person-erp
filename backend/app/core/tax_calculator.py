"""可配置税务计算引擎——支持小规模纳税人 / 一般纳税人两种模式。

使用方式：
    from app.core.tax_calculator import TaxCalculator, TaxConfig

    config = await TaxConfig.load_from_db(db)
    calc = TaxCalculator(config)
    result = await calc.calculate_quarterly(db, year, quarter)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceRecord
from app.models.setting import SystemSetting
from app.core.constants import (
    INVOICE_DIRECTION_OUTPUT,
    INVOICE_DIRECTION_INPUT,
    INVOICE_TYPE_SPECIAL,
)
from app.core.finance_utils import get_quarter_date_range


@dataclass
class TaxConfig:
    """税务配置，从 settings 表加载。"""

    payer_type: str = "small_scale"
    small_scale_rate: float = 0.01
    small_scale_exempt_threshold: float = 300_000.0
    general_standard_rate: float = 0.13
    general_include_ordinary_input: bool = False

    @classmethod
    async def load_from_db(cls, db: AsyncSession) -> "TaxConfig":
        async def _get(key: str, default: str = "") -> str:
            r = await db.execute(
                select(SystemSetting).where(
                    SystemSetting.key == key,
                    SystemSetting.is_deleted == False,
                )
            )
            s = r.scalar_one_or_none()
            return s.value if s and s.value else default

        return cls(
            payer_type=await _get("tax_payer_type", "small_scale"),
            small_scale_rate=float(await _get("tax_small_scale_rate", "0.01")),
            small_scale_exempt_threshold=float(await _get("tax_small_scale_exempt_threshold", "300000")),
            general_standard_rate=float(await _get("tax_general_standard_rate", "0.13")),
            general_include_ordinary_input=await _get("tax_general_include_ordinary_input", "false") == "true",
        )

    def as_dict(self) -> dict:
        return {
            "payer_type": self.payer_type,
            "small_scale_rate": self.small_scale_rate,
            "small_scale_exempt_threshold": self.small_scale_exempt_threshold,
            "general_standard_rate": self.general_standard_rate,
            "general_include_ordinary_input": self.general_include_ordinary_input,
        }


@dataclass
class TaxResult:
    """季度增值税汇总结果。"""

    year: int
    quarter: int
    payer_type: str

    output_tax_total: float = 0.0
    input_tax_total: float = 0.0
    tax_payable: float = 0.0

    quarterly_sales: float = 0.0
    is_exempt: bool = False
    effective_rate: Optional[float] = None
    note: str = ""

    record_count: dict = field(default_factory=lambda: {"output": 0, "input": 0})


class TaxCalculator:
    def __init__(self, config: TaxConfig):
        self.config = config

    async def calculate_quarterly(self, db: AsyncSession, year: int, quarter: int) -> TaxResult:
        start_date, end_date = get_quarter_date_range(year, quarter)

        result = TaxResult(year=year, quarter=quarter, payer_type=self.config.payer_type)

        output_rows = await self._query_output(db, start_date, end_date)
        input_rows = await self._query_input(db, start_date, end_date)

        output_tax = sum((r[0] or 0) for r in output_rows)
        input_tax = sum((r[0] or 0) for r in input_rows)

        result.output_tax_total = round(output_tax, 2)
        result.input_tax_total = round(input_tax, 2)
        result.record_count["output"] = len(output_rows)
        result.record_count["input"] = len(input_rows)

        if self.config.payer_type == "small_scale":
            await self._calc_small_scale(db, result, start_date, end_date)
        else:
            self._calc_general(result)

        return result

    async def _query_output(self, db: AsyncSession, start: date, end: date):
        r = await db.execute(
            select(FinanceRecord.tax_amount).where(
                FinanceRecord.invoice_direction == INVOICE_DIRECTION_OUTPUT,
                FinanceRecord.date >= start,
                FinanceRecord.date <= end,
                FinanceRecord.is_deleted == False,
            )
        )
        return r.all()

    async def _query_input(self, db: AsyncSession, start: date, end: date):
        cond = [
            FinanceRecord.invoice_direction == INVOICE_DIRECTION_INPUT,
            FinanceRecord.date >= start,
            FinanceRecord.date <= end,
            FinanceRecord.is_deleted == False,
        ]
        if not self.config.general_include_ordinary_input:
            cond.append(FinanceRecord.invoice_type == INVOICE_TYPE_SPECIAL)
        r = await db.execute(select(FinanceRecord.tax_amount).where(*cond))
        return r.all()

    async def _calc_small_scale(self, db: AsyncSession, result: TaxResult, start: date, end: date):
        """小规模纳税人算法：按销售额判断免税/减征。"""
        sales_r = await db.execute(
            select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                FinanceRecord.type == "income",
                FinanceRecord.status.in_(["paid", "confirmed"]),
                FinanceRecord.date >= start,
                FinanceRecord.date <= end,
                FinanceRecord.is_deleted == False,
            )
        )
        quarterly_sales = float(sales_r.scalar() or 0)
        result.quarterly_sales = round(quarterly_sales, 2)

        threshold = self.config.small_scale_exempt_threshold
        rate = Decimal(str(self.config.small_scale_rate))

        if quarterly_sales <= threshold:
            result.tax_payable = 0.0
            result.is_exempt = True
            result.effective_rate = 0.0
            result.note = f"季度销售额 ¥{quarterly_sales:,.2f} ≤ 免税额 ¥{threshold:,.2f}，免征增值税"
        else:
            taxable = Decimal(str(quarterly_sales)) * rate
            result.tax_payable = float(taxable.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            result.effective_rate = self.config.small_scale_rate
            result.note = (
                f"季度销售额 ¥{quarterly_sales:,.2f} > 免税额 ¥{threshold:,.2f}，"
                f"减按 {self.config.small_scale_rate*100:.0f}% 征收"
            )

        result.output_tax_total = 0.0
        result.input_tax_total = 0.0

    def _calc_general(self, result: TaxResult):
        """一般纳税人算法：销项 - 进项（差额法）。"""
        result.tax_payable = round(result.output_tax_total - result.input_tax_total, 2)
        result.effective_rate = self.config.general_standard_rate
        label = "含普票" if self.config.general_include_ordinary_input else "仅专票"
        result.note = f"一般纳税人差额法（进项：{label}）"
