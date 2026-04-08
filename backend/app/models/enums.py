"""v1.5 新增枚举定义——严格遵循 prd1_5.md，不包含未定义的值"""
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
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


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
