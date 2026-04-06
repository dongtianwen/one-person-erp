"""v1.4 数据导出核心函数——可独立于 FastAPI 应用直接调用和测试。"""
import io
import logging
from datetime import date, datetime
from typing import Optional

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.core.constants import EXPORT_DATE_FORMAT, EXPORT_MAX_ROWS_PER_SHEET

logger = logging.getLogger(__name__)

# ── 导出类型枚举 ──
EXPORT_TYPES = ("finance_report", "customers", "projects", "contracts", "tax_ledger")
EXPORT_FORMATS = ("xlsx", "pdf")

# ── 中文标题映射 ──
EXPORT_TITLES = {
    "finance_report": "月度财务报表",
    "customers": "客户列表",
    "projects": "项目列表",
    "contracts": "合同列表",
    "tax_ledger": "增值税发票台账",
}

# ── 列定义（严格按照 PRD，不得自行增减列）──
COLUMNS = {
    "finance_report": {
        "收支明细": ["日期", "类型(收入/支出)", "分类", "金额", "资金来源", "关联合同", "发票号码", "状态", "备注"],
        "分类汇总": ["分类", "收入合计", "支出合计", "净额"],
        "资金来源汇总": ["资金来源", "支出合计", "未结清笔数", "未结清金额"],
    },
    "customers": ["客户名称", "联系人", "电话", "公司名称", "状态", "来源渠道", "合作项目数",
                  "历史合同总额", "历史实收金额", "首次合作日期", "最近合作日期", "创建日期"],
    "projects": ["项目名称", "关联客户", "项目状态", "预算金额", "项目收入", "项目成本",
                 "项目利润", "利润率(%)", "开始日期", "结束日期", "进度(%)"],
    "contracts": ["合同编号", "合同标题", "关联客户", "关联项目", "合同金额", "已收金额",
                  "应收账款", "合同状态", "签署日期", "生效日期", "到期日期"],
    "tax_ledger": ["日期", "发票号码", "发票方向(销项/进项)", "发票类型", "金额", "税率", "税额", "关联合同", "备注"],
}

# ── Excel 样式 ──
_header_font = Font(name="Microsoft YaHei", bold=True, size=11)
_header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
_header_font_white = Font(name="Microsoft YaHei", bold=True, size=11, color="FFFFFF")
_cell_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
_thin_border = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)


def _register_chinese_fonts() -> None:
    """注册中文字体（SimHei / Microsoft YaHei），PDF 生成时使用。"""
    import platform
    system = platform.system()
    font_registered = False

    if system == "Windows":
        import os
        windir = os.environ.get("WINDIR", r"C:\Windows")
        font_paths = [
            os.path.join(windir, "Fonts", "msyh.ttc"),
            os.path.join(windir, "Fonts", "simhei.ttf"),
            os.path.join(windir, "Fonts", "simsun.ttc"),
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                    font_registered = True
                    break
                except Exception:
                    continue
    elif system == "Darwin":
        import os
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/STHeiti Light.ttc",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                    font_registered = True
                    break
                except Exception:
                    continue
    else:
        import os
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    pdfmetrics.registerFont(TTFont("ChineseFont", fp))
                    font_registered = True
                    break
                except Exception:
                    continue

    if not font_registered:
        logger.warning("未找到中文字体，PDF 中文可能显示为方块")


def get_export_filename(
    export_type: str, format: str, year: int,
    month: Optional[int] = None, quarter: Optional[int] = None,
) -> str:
    """
    生成文件名，格式：{模块名}_{年份}_{月份或季度}.{扩展名}

    示例：finance_report_2026_04.xlsx / tax_ledger_2026_Q1.pdf
    """
    ext = "xlsx" if format == "xlsx" else "pdf"
    if export_type == "tax_ledger" and quarter is not None:
        return f"{export_type}_{year}_Q{quarter}.{ext}"
    elif month is not None:
        return f"{export_type}_{year}_{month:02d}.{ext}"
    else:
        # 对于不需要年份月份的全局列表，使用当前年月
        today = date.today()
        return f"{export_type}_{today.year}_{today.month:02d}.{ext}"


def generate_excel(
    export_type: str, data: dict, year: int,
    month: Optional[int] = None, quarter: Optional[int] = None,
) -> bytes:
    """
    生成 Excel 文件，返回 bytes。数据为空时生成含表头的空文件。

    data 结构：
      finance_report: {"details": [...], "category_summary": [...], "funding_summary": [...]}
      customers: {"items": [...]}
      projects: {"items": [...]}
      contracts: {"items": [...]}
      tax_ledger: {"items": [...], "summary": {...}}
    """
    wb = Workbook()

    if export_type == "finance_report":
        _write_finance_report_xlsx(wb, data)
    elif export_type == "customers":
        _write_single_sheet_xlsx(wb, "客户列表", COLUMNS["customers"], data.get("items", []), "customers")
    elif export_type == "projects":
        _write_single_sheet_xlsx(wb, "项目列表", COLUMNS["projects"], data.get("items", []), "projects")
    elif export_type == "contracts":
        _write_single_sheet_xlsx(wb, "合同列表", COLUMNS["contracts"], data.get("items", []), "contracts")
    elif export_type == "tax_ledger":
        _write_tax_ledger_xlsx(wb, data)

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def generate_pdf(
    export_type: str, data: dict, year: int,
    month: Optional[int] = None, quarter: Optional[int] = None,
) -> bytes:
    """
    生成 PDF 文件，返回 bytes。必须正确渲染中文字体。
    数据为空时生成含标题的空文件。
    """
    _register_chinese_fonts()

    output = io.BytesIO()
    title = EXPORT_TITLES.get(export_type, export_type)

    if export_type == "tax_ledger" and quarter is not None:
        period_label = f"{year}年 Q{quarter}"
    elif month is not None:
        period_label = f"{year}年{month:02d}月"
    else:
        period_label = f"当前快照 (导出时间: {date.today().strftime('%Y-%m-%d')})"

    doc = SimpleDocTemplate(
        output, pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    elements: list = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChineseTitle", parent=styles["Title"],
        fontName="ChineseFont", fontSize=16,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ChineseSubtitle", parent=styles["Normal"],
        fontName="ChineseFont", fontSize=10,
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        "ChineseCell", parent=styles["Normal"],
        fontName="ChineseFont", fontSize=8,
        leading=10,
    )

    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"报表期间：{period_label}", subtitle_style))
    elements.append(Spacer(1, 5 * mm))

    if export_type == "finance_report":
        _write_finance_report_pdf(elements, data, cell_style)
    elif export_type == "tax_ledger":
        _write_tax_ledger_pdf(elements, data, cell_style)
    else:
        cols = COLUMNS[export_type]
        items = data.get("items", [])
        _write_table_pdf(elements, cols, items, export_type, cell_style)

    doc.build(elements)
    return output.getvalue()


# ── Excel 内部函数 ──


def _apply_header_style(ws, col_count: int) -> None:
    """应用表头样式。"""
    for col_idx in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = _header_font_white
        cell.fill = _header_fill
        cell.alignment = _cell_alignment
        cell.border = _thin_border


def _auto_width(ws, col_count: int) -> None:
    """自动调整列宽，并为所有行添加边框、居中、字体等基础样式。"""
    for col_idx in range(1, col_count + 1):
        max_len = 0
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx, values_only=False):
            for cell in row:
                if cell.value is not None:
                    # 动态计算字符视觉宽度：中文字符算作约 2.2，英文字符算作约 1.2
                    val_str = str(cell.value)
                    # 按照换行符分割，取最长的那一行计算
                    lines = val_str.split('\n')
                    for line in lines:
                        length = sum(2.2 if ord(c) > 255 else 1.2 for c in line)
                        if length > max_len:
                            max_len = length
        # 设置列宽，最多不超过 60
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 60)

    # 给从第2行开始的数据行统一加上边框和居中（第1行表头已经在 _apply_header_style 处理）
    for row in ws.iter_rows(min_row=2, max_col=col_count):
        for cell in row:
            cell.alignment = _cell_alignment
            cell.border = _thin_border


def _write_finance_report_xlsx(wb: Workbook, data: dict) -> None:
    """写入月度财务报表（3 个 Sheet）。"""
    sheets_config = [
        ("收支明细", COLUMNS["finance_report"]["收支明细"], data.get("details", [])),
        ("分类汇总", COLUMNS["finance_report"]["分类汇总"], data.get("category_summary", [])),
        ("资金来源汇总", COLUMNS["finance_report"]["资金来源汇总"], data.get("funding_summary", [])),
    ]

    for idx, (sheet_name, columns, rows) in enumerate(sheets_config):
        ws = wb.active if idx == 0 else wb.create_sheet(sheet_name)
        ws.title = sheet_name
        ws.append(columns)
        _apply_header_style(ws, len(columns))
        for row in rows[:EXPORT_MAX_ROWS_PER_SHEET]:
            ws.append(row)
        _auto_width(ws, len(columns))


def _write_single_sheet_xlsx(wb: Workbook, sheet_name: str, columns: list, items: list, export_type: str) -> None:
    """写入单 Sheet 导出。"""
    ws = wb.active
    ws.title = sheet_name
    ws.append(columns)
    _apply_header_style(ws, len(columns))
    for row in items[:EXPORT_MAX_ROWS_PER_SHEET]:
        ws.append(row)
    _auto_width(ws, len(columns))


def _write_tax_ledger_xlsx(wb: Workbook, data: dict) -> None:
    """写入增值税发票台账（含底部汇总行）。"""
    cols = COLUMNS["tax_ledger"]
    ws = wb.active
    ws.title = "增值税发票台账"
    ws.append(cols)
    _apply_header_style(ws, len(cols))

    items = data.get("items", [])
    for row in items[:EXPORT_MAX_ROWS_PER_SHEET]:
        ws.append(row)

    summary = data.get("summary", {})
    if summary:
        output_tax = summary.get("output_tax", 0)
        input_tax = summary.get("input_tax", 0)
        payable = summary.get("payable_tax", 0)
        summary_row = ["汇总", "", "", "", "", "", output_tax, "", f"销项:{output_tax} 进项:{input_tax} 应纳:{payable}"]
        ws.append(summary_row)

    _auto_width(ws, len(cols))


# ── PDF 内部函数 ──


def _write_table_pdf(
    elements: list, columns: list, items: list,
    export_type: str, cell_style: ParagraphStyle,
) -> None:
    """写入通用 PDF 表格。"""
    table_data = [[Paragraph(str(c), cell_style) for c in columns]]
    for row in items:
        table_data.append([Paragraph(str(v) if v is not None else "", cell_style) for v in row])

    # A4 landscape width is 297mm. Margins are 15mm each. Available = 267mm.
    # We use 265mm to be safe and avoid overflow.
    col_widths = [265 * mm / max(len(columns), 1)] * len(columns)
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "ChineseFont"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))
    elements.append(table)


def _write_finance_report_pdf(
    elements: list, data: dict, cell_style: ParagraphStyle,
) -> None:
    """写入月度财务报表 PDF。"""
    sections = [
        ("收支明细", COLUMNS["finance_report"]["收支明细"], data.get("details", [])),
        ("分类汇总", COLUMNS["finance_report"]["分类汇总"], data.get("category_summary", [])),
        ("资金来源汇总", COLUMNS["finance_report"]["资金来源汇总"], data.get("funding_summary", [])),
    ]

    section_style = ParagraphStyle(
        "SectionTitle", parent=cell_style,
        fontSize=12, spaceAfter=4, spaceBefore=8,
    )

    for section_name, columns, rows in sections:
        elements.append(Paragraph(section_name, section_style))
        _write_table_pdf(elements, columns, rows, "finance_report", cell_style)
        elements.append(Spacer(1, 5 * mm))


def _write_tax_ledger_pdf(
    elements: list, data: dict, cell_style: ParagraphStyle,
) -> None:
    """写入增值税发票台账 PDF（含汇总）。"""
    cols = COLUMNS["tax_ledger"]
    items = data.get("items", [])

    _write_table_pdf(elements, cols, items, "tax_ledger", cell_style)

    summary = data.get("summary", {})
    if summary:
        elements.append(Spacer(1, 3 * mm))
        summary_text = (
            f"销项税合计：{summary.get('output_tax', 0)}  |  "
            f"进项税合计（仅专用发票）：{summary.get('input_tax', 0)}  |  "
            f"应纳税额：{summary.get('payable_tax', 0)}"
        )
        elements.append(Paragraph(summary_text, cell_style))
