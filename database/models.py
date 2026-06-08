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
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
