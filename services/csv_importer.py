import csv
import os
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from database import DatabaseManager, MeasurementRecord, Component
from utils.validators import validate_csv_row


class ImportResult:
    def __init__(self):
        self.success_count: int = 0
        self.error_count: int = 0
        self.errors: List[str] = []
        self.new_skipped: List[str] = []
        self.new_components: List[str] = []

    @property
    def total(self) -> int:
        return self.success_count + self.error_count

    def __str__(self):
        return f"成功导入{self.success_count}条，失败{self.error_count}条"


class CsvImporter:
    REQUIRED_COLUMNS = ["构件编号", "长度", "宽度", "角度", "测量时间"]

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def import_file(self, file_path: str, building_id: int) -> ImportResult:
        result = ImportResult()

        if not os.path.exists(file_path):
            result.errors.append(f"文件不存在：{file_path}")
            result.error_count += 1
            return result

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in reader.fieldnames]
                if missing_cols:
                    result.errors.append(f"CSV缺少必要列：{', '.join(missing_cols)}")
                    result.error_count += 1
                    return result

                for i, row in enumerate(reader, start=2):
                    is_valid, errors, cleaned = validate_csv_row(row, i)

                    if not is_valid:
                        result.error_count += 1
                        result.errors.extend(errors)
                        continue

                    component = self.db.get_component_by_code(building_id, cleaned["component_code"])

                    if component is None:
                        result.errors.append(f"第{i}行：构件编号 {cleaned['component_code']} 不存在于当前建筑，已跳过")
                        result.new_skipped.append(f"第{i}行：{cleaned['component_code']} 不存在")
                        result.error_count += 1
                        continue

                    latest_version = self.db.get_latest_version(component.id)
                    new_version = latest_version + 1

                    record = MeasurementRecord(
                        id=None,
                        component_id=component.id,
                        component_code=cleaned["component_code"],
                        length=cleaned["length"],
                        width=cleaned["width"],
                        angle=cleaned["angle"],
                        measure_time=cleaned["measure_time"],
                        version=new_version,
                        is_recheck=False,
                        remark=""
                    )

                    try:
                        self.db.add_measurement_record(record)
                        result.success_count += 1
                    except Exception as e:
                        result.error_count += 1
                        result.errors.append(f"第{i}行：导入失败 - {str(e)}")

        except UnicodeDecodeError:
            result.errors.append("文件编码错误，请使用UTF-8编码")
            result.error_count += 1
        except Exception as e:
            result.errors.append(f"读取文件失败：{str(e)}")
            result.error_count += 1

        return result

    def preview_file(self, file_path: str, max_rows: int = 10) -> Tuple[List[str], List[Dict], List[str]]:
        headers = []
        rows = []
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in headers]
                if missing_cols:
                    errors.append(f"缺少必要列：{', '.join(missing_cols)}")

                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    rows.append(dict(row))

        except Exception as e:
            errors.append(f"读取文件失败：{str(e)}")

        return headers, rows, errors
