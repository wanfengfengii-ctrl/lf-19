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

DISEASE_STATUS_PENDING = "pending"
DISEASE_STATUS_IN_PROGRESS = "in_progress"
DISEASE_STATUS_COMPLETED = "completed"
DISEASE_STATUS_REVIEWED = "reviewed"

DISEASE_STATUSES = [
    (DISEASE_STATUS_PENDING, "待处理"),
    (DISEASE_STATUS_IN_PROGRESS, "处理中"),
    (DISEASE_STATUS_COMPLETED, "已完成"),
    (DISEASE_STATUS_REVIEWED, "已复查"),
]


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

    def __post_init__(self):
        if self.by_type is None:
            self.by_type = {}
        if self.by_severity is None:
            self.by_severity = {}
        if self.by_priority is None:
            self.by_priority = {}
