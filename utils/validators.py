import re
from typing import Dict, List, Tuple


class ValidationError(Exception):
    pass


def validate_component_code(code: str) -> bool:
    if not code or not isinstance(code, str):
        return False
    code = code.strip()
    if len(code) == 0:
        return False
    return True


def validate_positive_number(value) -> bool:
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_angle(value) -> bool:
    try:
        num = float(value)
        return 0 <= num <= 180
    except (ValueError, TypeError):
        return False


def validate_csv_row(row_data: Dict, row_index: int) -> Tuple[bool, List[str], Dict]:
    errors = []
    cleaned = {}

    component_code = str(row_data.get("构件编号", "")).strip()
    if not component_code:
        errors.append(f"第{row_index}行：构件编号不能为空")
    elif not validate_component_code(component_code):
        errors.append(f"第{row_index}行：构件编号格式无效")
    cleaned["component_code"] = component_code

    length_str = str(row_data.get("长度", "")).strip()
    try:
        length = float(length_str)
        if not validate_positive_number(length):
            errors.append(f"第{row_index}行：长度必须大于0，当前值为{length_str}")
        cleaned["length"] = length
    except (ValueError, TypeError):
        errors.append(f"第{row_index}行：长度格式无效，当前值为{length_str}")
        cleaned["length"] = None

    width_str = str(row_data.get("宽度", "")).strip()
    try:
        width = float(width_str)
        if not validate_positive_number(width):
            errors.append(f"第{row_index}行：宽度必须大于0，当前值为{width_str}")
        cleaned["width"] = width
    except (ValueError, TypeError):
        errors.append(f"第{row_index}行：宽度格式无效，当前值为{width_str}")
        cleaned["width"] = None

    angle_str = str(row_data.get("角度", "")).strip()
    try:
        angle = float(angle_str)
        if not validate_angle(angle):
            errors.append(f"第{row_index}行：角度必须在0-180之间，当前值为{angle_str}")
        cleaned["angle"] = angle
    except (ValueError, TypeError):
        errors.append(f"第{row_index}行：角度格式无效，当前值为{angle_str}")
        cleaned["angle"] = None

    measure_time = str(row_data.get("测量时间", "")).strip()
    if not measure_time:
        errors.append(f"第{row_index}行：测量时间不能为空")
    cleaned["measure_time"] = measure_time

    is_valid = len(errors) == 0
    return is_valid, errors, cleaned
