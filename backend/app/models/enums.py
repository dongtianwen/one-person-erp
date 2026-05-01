"""枚举定义——包含 v1.0 ~ v2.3 所有枚举"""
from enum import Enum


class RequirementStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"


class ChangeType(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"
    DESIGN = "design"


class ConfirmMethod(str, Enum):
    OFFLINE = "offline"
    WECHAT = "wechat"
    EMAIL = "email"
    SYSTEM = "system"


class AcceptanceResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"


class DeliverableType(str, Enum):
    SOURCE_CODE = "source_code"
    INSTALLER = "installer"
    DEPLOYMENT_DOC = "deployment_doc"
    API_DOC = "api_doc"
    USER_MANUAL = "user_manual"
    ACCOUNT_HANDOVER = "account_handover"
    DESIGN_FILE = "design_file"
    TEST_REPORT = "test_report"
    OTHER = "other"


class DeliveryMethod(str, Enum):
    OFFLINE = "offline"
    REMOTE = "remote"
    CLOUD = "cloud"
    REPOSITORY = "repository"


class ReleaseType(str, Enum):
    RELEASE = "release"
    HOTFIX = "hotfix"
    BETA = "beta"
    ROLLBACK = "rollback"


class DeployEnv(str, Enum):
    PRODUCTION = "production"
    TESTING = "testing"
    INTRANET = "intranet"


class ChangeOrderStatus(str, Enum):
    """v1.7 变更单状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class MaintenanceType(str, Enum):
    WARRANTY = "warranty"
    MAINTENANCE = "maintenance"
    ANNUAL_FEE = "annual_fee"
    HOSTING = "hosting"
    SUPPORT = "support"


class MaintenanceStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class QuoteItemType(str, Enum):
    LABOR = "labor"
    DESIGN = "design"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    OUTSOURCE = "outsource"
    OTHER = "other"


class QuoteChangeType(str, Enum):
    FIELD_UPDATE = "field_update"
    STATUS_CHANGE = "status_change"
    CONVERTED = "converted"


# v1.1 提醒管理枚举
class ReminderType(str, Enum):
    """提醒类型枚举"""
    ANNUAL_AUDIT = "annual_audit"      # 年报/审计提醒
    TAX_FILING = "tax_filing"          # 税期申报提醒
    CONTRACT_EXPIRY = "contract_expiry"  # 合同到期提醒
    TASK_DEADLINE = "task_deadline"    # 任务截止提醒
    FILE_EXPIRY = "file_expiry"        # 文件到期提醒
    ASSET_EXPIRY = "asset_expiry"      # 客户资产到期提醒（v1.2新增）
    CUSTOM = "custom"                  # 自定义提醒


class ReminderStatus(str, Enum):
    """提醒状态枚举"""
    PENDING = "pending"    # 待处理
    OVERDUE = "overdue"    # 已逾期
    COMPLETED = "completed"  # 已完成


# v1.1 文件索引枚举
class FileType(str, Enum):
    """文件类型枚举"""
    BUSINESS_LICENSE = "business_license"    # 营业执照
    COMPANY_CHARTER = "company_charter"      # 公司章程
    LEASE_AGREEMENT = "lease_agreement"      # 租赁/入驻协议
    AUDIT_REPORT = "audit_report"            # 审计报告
    TAX_REGISTRATION = "tax_registration"    # 税务备案回执
    INVOICE = "invoice"                      # 发票
    ANNUAL_REPORT = "annual_report"          # 年度报告
    CONTRACT = "contract"                    # 合同文件（纸质存档）
    OTHER = "other"                          # 其他


# v1.2 客户资产枚举
class AssetType(str, Enum):
    """客户资产类型枚举"""
    SERVER = "server"            # 服务器
    DOMAIN = "domain"            # 域名
    SSL = "ssl"                  # SSL证书
    MINIPROGRAM = "miniprogram"  # 小程序
    APP = "app"                  # APP
    OTHER = "other"              # 其他


# v1.8 财务对接模块枚举
class InvoiceType(str, Enum):
    """发票类型枚举"""
    STANDARD = "standard"        # 增值税专用发票
    ORDINARY = "ordinary"        # 增值税普通发票
    ELECTRONIC = "electronic"    # 电子发票
    SMALL_SCALE = "small_scale"  # 小规模纳税人


class InvoiceStatus(str, Enum):
    """发票状态枚举"""
    DRAFT = "draft"            # 草稿
    ISSUED = "issued"          # 已开具
    RECEIVED = "received"      # 已收票
    VERIFIED = "verified"      # 已核销（终态）
    CANCELLED = "cancelled"    # 已作废（终态）


class ReconciliationStatus(str, Enum):
    """对账状态枚举"""
    PENDING = "pending"        # 待对账
    MATCHED = "matched"        # 已匹配
    VERIFIED = "verified"      # 已确认（终态）


# v1.9 固定成本枚举
class FixedCostPeriod(str, Enum):
    """固定成本周期枚举"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONETIME = "onetime"


class FixedCostCategory(str, Enum):
    """固定成本分类枚举"""
    OFFICE = "office"
    CLOUD = "cloud"
    SOFTWARE = "software"
    EQUIPMENT = "equipment"
    OTHER = "other"


# v2.3 研发费用台账枚举
class RdCategory(str, Enum):
    """研发费用大类——对应税法六大类"""
    PERSONNEL = "personnel"              # 人员人工费用
    DIRECT_INPUT = "direct_input"        # 直接投入费用
    DEPRECIATION = "depreciation"        # 折旧费用
    AMORTIZATION = "amortization"        # 无形资产摊销
    DESIGN_OTHER = "design_other"        # 设计/试验/其他费用
    OUTSOURCED_RD = "outsourced_rd"      # 委托外部研发


class RdSubCategory(str, Enum):
    """研发费用子分类"""
    # 人员人工
    SALARY = "salary"
    SOCIAL_INSURANCE = "social_insurance"
    WELFARE = "welfare"
    EXPERT_FEE = "expert_fee"

    # 直接输入
    MATERIAL = "material"
    FUEL_POWER = "fuel_power"
    TEST_EQUIPMENT = "test_equipment"
    SOFTWARE_PURCHASE = "software_purchase"
    SAMPLE_PROTOTYPE = "sample_prototype"

    # 折旧
    EQUIPMENT_DEPRE = "equipment_depre"
    BUILDING_DEPRE = "building_depre"

    # 无形资产摊销
    SOFT_AMORT = "soft_amort"
    PATENT_AMORT = "patent_amort"

    # 设计/试验/其他
    DESIGN_FEE = "design_fee"
    PROCESS_FEE = "process_fee"
    TEST_FEE = "test_fee"
    TRAVEL = "travel"
    DATA_BOOK = "data_book"
    OTHER_RD = "other_rd"

    # 委托外部研发
    DOMESTIC_OUTSOURCE = "domestic_outsource"
    FOREIGN_OUTSOURCE = "foreign_outsource"


class RdStatus(str, Enum):
    """研发费用审核状态"""
    DRAFT = "draft"
    VERIFIED = "verified"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
