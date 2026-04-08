"""枚举定义——包含 v1.0 ~ v1.7 所有枚举"""
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
