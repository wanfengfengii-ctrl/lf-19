from dataclasses import dataclass
from typing import Optional
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
