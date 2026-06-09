from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime


@dataclass
class Building:
    id: Optional[int]
    name: str
    code: str
    location: str = ""
    description: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Component:
    id: Optional[int]
    building_id: int
    code: str
    name: str = ""
    component_type: str = ""
    design_length: float = 0.0
    design_width: float = 0.0
    design_angle: float = 0.0
    deviation_threshold: float = 5.0
    description: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class MortiseTenon:
    id: Optional[int]
    building_id: int
    mortise_component_id: int
    tenon_component_id: int
    joint_type: str = ""
    description: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class MeasurementRecord:
    id: Optional[int]
    component_id: int
    component_code: str
    length: float
    width: float
    angle: float
    measure_time: str
    version: int = 1
    is_recheck: bool = False
    remark: str = ""
    batch_id: Optional[int] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


RECHECK_STATUS_PENDING = "pending"
RECHECK_STATUS_IN_PROGRESS = "in_progress"
RECHECK_STATUS_COMPLETED = "completed"
RECHECK_STATUS_CANCELLED = "cancelled"


@dataclass
class RecheckTask:
    id: Optional[int]
    building_id: int
    component_id: int
    component_code: str
    record_id: int
    status: str = RECHECK_STATUS_PENDING
    assigned_to: str = ""
    priority: str = "normal"
    reason: str = ""
    recheck_result: str = ""
    recheck_record_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


@dataclass
class ImportBatch:
    id: Optional[int]
    building_id: int
    file_name: str
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    status: str = "draft"
    auto_recheck: bool = False
    imported_by: str = ""
    remark: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ImportError:
    id: Optional[int]
    batch_id: int
    row_number: int
    component_code: str = ""
    error_type: str = ""
    error_message: str = ""
    row_data: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


DISEASE_TYPE_CRACK = "crack"
DISEASE_TYPE_DECAY = "decay"
DISEASE_TYPE_INSECT = "insect"
DISEASE_TYPE_DEFORMATION = "deformation"
DISEASE_TYPE_DEFECT = "defect"
DISEASE_TYPE_OTHER = "other"

DISEASE_TYPES = [
    (DISEASE_TYPE_CRACK, "裂缝"),
    (DISEASE_TYPE_DECAY, "腐朽"),
    (DISEASE_TYPE_INSECT, "虫蛀"),
    (DISEASE_TYPE_DEFORMATION, "变形"),
    (DISEASE_TYPE_DEFECT, "缺损"),
    (DISEASE_TYPE_OTHER, "其他"),
]

DISEASE_SEVERITY_MILD = "mild"
DISEASE_SEVERITY_MODERATE = "moderate"
DISEASE_SEVERITY_SEVERE = "severe"
DISEASE_SEVERITY_DANGEROUS = "dangerous"

DISEASE_SEVERITIES = [
    (DISEASE_SEVERITY_MILD, "轻微"),
    (DISEASE_SEVERITY_MODERATE, "一般"),
    (DISEASE_SEVERITY_SEVERE, "严重"),
    (DISEASE_SEVERITY_DANGEROUS, "危险"),
]

PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
PRIORITY_URGENT = "urgent"

PRIORITIES = [
    (PRIORITY_LOW, "低"),
    (PRIORITY_MEDIUM, "中"),
    (PRIORITY_HIGH, "高"),
    (PRIORITY_URGENT, "紧急"),
]

DISEASE_STATUS_DISCOVERED = "discovered"
DISEASE_STATUS_PENDING = "pending"
DISEASE_STATUS_ASSIGNED = "assigned"
DISEASE_STATUS_IN_PROGRESS = "in_progress"
DISEASE_STATUS_COMPLETED = "completed"
DISEASE_STATUS_ACCEPTED = "accepted"
DISEASE_STATUS_REVIEWED = "reviewed"
DISEASE_STATUS_ARCHIVED = "archived"
DISEASE_STATUS_REJECTED = "rejected"

DISEASE_STATUSES = [
    (DISEASE_STATUS_DISCOVERED, "已发现"),
    (DISEASE_STATUS_PENDING, "待派单"),
    (DISEASE_STATUS_ASSIGNED, "已派单"),
    (DISEASE_STATUS_IN_PROGRESS, "处置中"),
    (DISEASE_STATUS_COMPLETED, "待验收"),
    (DISEASE_STATUS_ACCEPTED, "已验收"),
    (DISEASE_STATUS_REVIEWED, "已复查"),
    (DISEASE_STATUS_ARCHIVED, "已归档"),
    (DISEASE_STATUS_REJECTED, "已驳回"),
]

DISEASE_STATUS_TRANSITIONS = {
    DISEASE_STATUS_DISCOVERED: [DISEASE_STATUS_PENDING, DISEASE_STATUS_ARCHIVED],
    DISEASE_STATUS_PENDING: [DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_ARCHIVED],
    DISEASE_STATUS_ASSIGNED: [DISEASE_STATUS_IN_PROGRESS, DISEASE_STATUS_PENDING, DISEASE_STATUS_ARCHIVED],
    DISEASE_STATUS_IN_PROGRESS: [DISEASE_STATUS_COMPLETED, DISEASE_STATUS_PENDING, DISEASE_STATUS_ARCHIVED],
    DISEASE_STATUS_COMPLETED: [DISEASE_STATUS_ACCEPTED, DISEASE_STATUS_REJECTED, DISEASE_STATUS_IN_PROGRESS],
    DISEASE_STATUS_ACCEPTED: [DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED, DISEASE_STATUS_IN_PROGRESS],
    DISEASE_STATUS_REVIEWED: [DISEASE_STATUS_ARCHIVED, DISEASE_STATUS_IN_PROGRESS],
    DISEASE_STATUS_ARCHIVED: [DISEASE_STATUS_PENDING],
    DISEASE_STATUS_REJECTED: [DISEASE_STATUS_IN_PROGRESS, DISEASE_STATUS_ARCHIVED],
}


@dataclass
class DiseaseRecord:
    id: Optional[int]
    building_id: int
    component_id: int
    component_code: str
    disease_type: str
    severity: str
    priority: str
    status: str = DISEASE_STATUS_PENDING
    description: str = ""
    location: str = ""
    size_length: float = 0.0
    size_width: float = 0.0
    size_depth: float = 0.0
    photo_paths: str = ""
    repair_suggestion: str = ""
    repair_method: str = ""
    estimated_cost: float = 0.0
    handler: str = ""
    plan_date: str = ""
    complete_date: str = ""
    remark: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


@dataclass
class DiseaseTreatment:
    id: Optional[int]
    disease_id: int
    treatment_type: str
    description: str = ""
    handler: str = ""
    treatment_date: str = ""
    photo_paths: str = ""
    remark: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.treatment_date:
            self.treatment_date = datetime.now().strftime("%Y-%m-%d")


@dataclass
class DiseaseStats:
    total_count: int
    pending_count: int
    in_progress_count: int
    completed_count: int
    reviewed_count: int
    by_type: Dict[str, int] = None
    by_severity: Dict[str, int] = None
    by_priority: Dict[str, int] = None
    total_estimated_cost: float = 0.0
    discovered_count: int = 0
    assigned_count: int = 0
    accepted_count: int = 0
    archived_count: int = 0
    rejected_count: int = 0
    by_status: Dict[str, int] = None

    def __post_init__(self):
        if self.by_type is None:
            self.by_type = {}
        if self.by_severity is None:
            self.by_severity = {}
        if self.by_priority is None:
            self.by_priority = {}
        if self.by_status is None:
            self.by_status = {}


@dataclass
class DiseaseStatusHistory:
    id: Optional[int]
    disease_id: int
    from_status: str
    to_status: str
    operator: str = ""
    remark: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class DiseaseAcceptanceRecord:
    id: Optional[int]
    disease_id: int
    acceptance_result: str
    acceptance_opinion: str = ""
    acceptor: str = ""
    acceptance_date: str = ""
    photo_paths: str = ""
    remark: str = ""
    is_review: bool = False
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.acceptance_date:
            self.acceptance_date = datetime.now().strftime("%Y-%m-%d")


ACCEPTANCE_RESULT_PASS = "pass"
ACCEPTANCE_RESULT_FAIL = "fail"
ACCEPTANCE_RESULT_PARTIAL = "partial"

ACCEPTANCE_RESULTS = [
    (ACCEPTANCE_RESULT_PASS, "通过"),
    (ACCEPTANCE_RESULT_FAIL, "不通过"),
    (ACCEPTANCE_RESULT_PARTIAL, "部分通过"),
]


@dataclass
class DiseasePhotoArchive:
    id: Optional[int]
    disease_id: int
    photo_path: str
    photo_type: str
    photo_stage: str
    description: str = ""
    upload_time: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.upload_time:
            self.upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


PHOTO_TYPE_BEFORE = "before"
PHOTO_TYPE_AFTER = "after"
PHOTO_TYPE_PROCESS = "process"
PHOTO_TYPE_OTHER = "other"

PHOTO_TYPES = [
    (PHOTO_TYPE_BEFORE, "修缮前"),
    (PHOTO_TYPE_PROCESS, "修缮中"),
    (PHOTO_TYPE_AFTER, "修缮后"),
    (PHOTO_TYPE_OTHER, "其他"),
]

PHOTO_STAGE_DISCOVERY = "discovery"
PHOTO_STAGE_DIAGNOSIS = "diagnosis"
PHOTO_STAGE_TREATMENT = "treatment"
PHOTO_STAGE_ACCEPTANCE = "acceptance"
PHOTO_STAGE_REVIEW = "review"

PHOTO_STAGES = [
    (PHOTO_STAGE_DISCOVERY, "发现阶段"),
    (PHOTO_STAGE_DIAGNOSIS, "诊断阶段"),
    (PHOTO_STAGE_TREATMENT, "处置阶段"),
    (PHOTO_STAGE_ACCEPTANCE, "验收阶段"),
    (PHOTO_STAGE_REVIEW, "复查阶段"),
]


@dataclass
class WarningRecord:
    id: Optional[int]
    building_id: int
    component_id: int
    component_code: str
    warning_type: str
    warning_level: str
    title: str
    description: str = ""
    source: str = ""
    related_disease_id: Optional[int] = None
    related_record_id: Optional[int] = None
    is_read: bool = False
    is_handled: bool = False
    handle_remark: str = ""
    created_at: str = ""
    handled_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


WARNING_TYPE_DEVIATION = "deviation"
WARNING_TYPE_DISEASE = "disease"
WARNING_TYPE_RISK = "risk"
WARNING_TYPE_DEADLINE = "deadline"

WARNING_TYPES = [
    (WARNING_TYPE_DEVIATION, "偏差预警"),
    (WARNING_TYPE_DISEASE, "病害预警"),
    (WARNING_TYPE_RISK, "风险预警"),
    (WARNING_TYPE_DEADLINE, "期限预警"),
]

WARNING_LEVEL_INFO = "info"
WARNING_LEVEL_WARNING = "warning"
WARNING_LEVEL_DANGER = "danger"
WARNING_LEVEL_CRITICAL = "critical"

WARNING_LEVELS = [
    (WARNING_LEVEL_INFO, "提示"),
    (WARNING_LEVEL_WARNING, "警告"),
    (WARNING_LEVEL_DANGER, "危险"),
    (WARNING_LEVEL_CRITICAL, "严重"),
]


@dataclass
class OperationLog:
    id: Optional[int]
    module: str
    action: str
    target_type: str
    target_id: Optional[int]
    operator: str = ""
    detail: str = ""
    ip_address: str = ""
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


MODULE_BUILDING = "building"
MODULE_COMPONENT = "component"
MODULE_MEASUREMENT = "measurement"
MODULE_IMPORT = "import"
MODULE_RECHECK = "recheck"
MODULE_DISEASE = "disease"
MODULE_REPORT = "report"
MODULE_USER = "user"

MODULES = [
    (MODULE_BUILDING, "建筑管理"),
    (MODULE_COMPONENT, "构件管理"),
    (MODULE_MEASUREMENT, "测量记录"),
    (MODULE_IMPORT, "数据导入"),
    (MODULE_RECHECK, "复测任务"),
    (MODULE_DISEASE, "病害管理"),
    (MODULE_REPORT, "报告生成"),
    (MODULE_USER, "用户管理"),
]

ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_QUERY = "query"
ACTION_IMPORT_DATA = "import"
ACTION_EXPORT = "export"
ACTION_STATUS_CHANGE = "status_change"
ACTION_ACCEPTANCE = "acceptance"
ACTION_ARCHIVE = "archive"

ACTIONS = [
    (ACTION_CREATE, "创建"),
    (ACTION_UPDATE, "更新"),
    (ACTION_DELETE, "删除"),
    (ACTION_QUERY, "查询"),
    (ACTION_IMPORT_DATA, "导入"),
    (ACTION_EXPORT, "导出"),
    (ACTION_STATUS_CHANGE, "状态变更"),
    (ACTION_ACCEPTANCE, "验收"),
    (ACTION_ARCHIVE, "归档"),
]


@dataclass
class DeviationDiseaseLink:
    id: Optional[int]
    component_id: int
    component_code: str
    deviation_level: str
    disease_count: int
    risk_level: str
    assessment: str = ""
    suggestion: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


RISK_LEVEL_LOW = "low"
RISK_LEVEL_MEDIUM = "medium"
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_CRITICAL = "critical"

RISK_LEVELS = [
    (RISK_LEVEL_LOW, "低风险"),
    (RISK_LEVEL_MEDIUM, "中风险"),
    (RISK_LEVEL_HIGH, "高风险"),
    (RISK_LEVEL_CRITICAL, "极高风险"),
]
