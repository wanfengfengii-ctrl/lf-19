import csv
import os
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from database import (
    DatabaseManager, MeasurementRecord, Component,
    ImportBatch, ImportError, RecheckTask,
    RECHECK_STATUS_PENDING
)
from utils.validators import validate_csv_row


class ImportResult:
    def __init__(self):
        self.success_count: int = 0
        self.error_count: int = 0
        self.errors: List[str] = []
        self.new_skipped: List[str] = []
        self.new_components: List[str] = []
        self.auto_recheck_count: int = 0
        self.batch_id: Optional[int] = None
        self.warning_count: int = 0
        self.warnings: List[str] = []

    @property
    def total(self) -> int:
        return self.success_count + self.error_count

    def __str__(self):
        return f"成功导入{self.success_count}条，失败{self.error_count}条"


class CsvImporter:
    REQUIRED_COLUMNS = ["构件编号", "长度", "宽度", "角度", "测量时间"]

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.default_deviation_threshold = 5.0

    def _create_auto_component(self, building_id: int, component_code: str,
                               length: float, width: float, angle: float) -> Component:
        component = Component(
            id=None,
            building_id=building_id,
            code=component_code,
            name=component_code,
            component_type="未分类",
            design_length=length,
            design_width=width,
            design_angle=angle,
            deviation_threshold=self.default_deviation_threshold
        )
        cid = self.db.add_component(component)
        component.id = cid
        return component

    def _is_abnormal(self, component: Component, length: float, width: float, angle: float) -> bool:
        threshold = component.deviation_threshold
        if abs(length - component.design_length) > threshold:
            return True
        if abs(width - component.design_width) > threshold:
            return True
        if abs(angle - component.design_angle) > threshold:
            return True
        return False

    def validate_file_complete(self, file_path: str, building_id: int) -> ImportResult:
        result = ImportResult()

        if not os.path.exists(file_path):
            result.errors.append(f"文件不存在：{file_path}")
            result.error_count += 1
            return result

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in headers]
                if missing_cols:
                    result.errors.append(f"CSV缺少必要列：{', '.join(missing_cols)}")
                    result.error_count += 1
                    return result

                for i, row in enumerate(reader, start=2):
                    result.total
                    is_valid, errors, cleaned = validate_csv_row(row, i)

                    if not is_valid:
                        result.error_count += 1
                        result.errors.extend(errors)
                        continue

                    component = self.db.get_component_by_code(building_id, cleaned["component_code"])

                    if component is None:
                        result.warnings.append(
                            f"第{i}行：构件编号 {cleaned['component_code']} 不存在，将自动创建新构件")
                        result.warning_count += 1
                        result.new_components.append(cleaned["component_code"])
                    else:
                        is_abnormal = self._is_abnormal(
                            component, cleaned["length"], cleaned["width"], cleaned["angle"]
                        )
                        if is_abnormal:
                            result.warnings.append(
                                f"第{i}行：构件 {cleaned['component_code']} 偏差超过阈值，导入后将自动标记需复测")
                            result.warning_count += 1

                    result.success_count += 1

        except UnicodeDecodeError:
            result.errors.append("文件编码错误，请使用UTF-8编码")
            result.error_count += 1
        except Exception as e:
            result.errors.append(f"读取文件失败：{str(e)}")
            result.error_count += 1

        return result

    def import_file(self, file_path: str, building_id: int,
                    auto_mark_recheck: bool = True,
                    create_batch: bool = True,
                    imported_by: str = "") -> ImportResult:
        result = ImportResult()

        if not os.path.exists(file_path):
            result.errors.append(f"文件不存在：{file_path}")
            result.error_count += 1
            return result

        file_name = os.path.basename(file_path)
        batch_id = None
        error_list = []
        success_records = []

        if create_batch:
            batch = ImportBatch(
                id=None,
                building_id=building_id,
                file_name=file_name,
                status="processing",
                auto_recheck=auto_mark_recheck,
                imported_by=imported_by,
                remark=f"导入文件: {file_name}"
            )
            batch_id = self.db.add_import_batch(batch)
            result.batch_id = batch_id

        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in reader.fieldnames]
                if missing_cols:
                    result.errors.append(f"CSV缺少必要列：{', '.join(missing_cols)}")
                    result.error_count += 1
                    if batch_id:
                        self.db.update_import_batch(
                            batch_id, status="failed",
                            remark=f"导入失败：缺少必要列"
                        )
                    return result

                total_count = 0
                for i, row in enumerate(reader, start=2):
                    total_count += 1
                    is_valid, errors, cleaned = validate_csv_row(row, i)

                    if not is_valid:
                        result.error_count += 1
                        result.errors.extend(errors)
                        if batch_id:
                            for err in errors:
                                import_err = ImportError(
                                    id=None,
                                    batch_id=batch_id,
                                    row_number=i,
                                    component_code=cleaned.get("component_code", ""),
                                    error_type="validation_error",
                                    error_message=err,
                                    row_data=json.dumps(row, ensure_ascii=False)
                                )
                                self.db.add_import_error(import_err)
                        continue

                    component = self.db.get_component_by_code(building_id, cleaned["component_code"])

                    if component is None:
                        component = self._create_auto_component(
                            building_id, cleaned["component_code"],
                            cleaned["length"], cleaned["width"], cleaned["angle"]
                        )
                        result.new_components.append(cleaned["component_code"])

                    latest_version = self.db.get_latest_version(component.id)
                    new_version = latest_version + 1

                    is_abnormal = self._is_abnormal(
                        component, cleaned["length"], cleaned["width"], cleaned["angle"]
                    )
                    remark = "偏差超过阈值，自动标记需复测" if (auto_mark_recheck and is_abnormal) else ""

                    record = MeasurementRecord(
                        id=None,
                        component_id=component.id,
                        component_code=cleaned["component_code"],
                        length=cleaned["length"],
                        width=cleaned["width"],
                        angle=cleaned["angle"],
                        measure_time=cleaned["measure_time"],
                        version=new_version,
                        is_recheck=auto_mark_recheck and is_abnormal,
                        remark=remark,
                        batch_id=batch_id
                    )

                    try:
                        rid = self.db.add_measurement_record(record)
                        result.success_count += 1
                        success_records.append((rid, component.id, cleaned["component_code"], is_abnormal))

                        if auto_mark_recheck and is_abnormal:
                            result.auto_recheck_count += 1

                            if not self.db.has_active_recheck_task(component.id):
                                recheck_task = RecheckTask(
                                    id=None,
                                    building_id=building_id,
                                    component_id=component.id,
                                    component_code=cleaned["component_code"],
                                    record_id=rid,
                                    status=RECHECK_STATUS_PENDING,
                                    priority="normal",
                                    reason="导入时自动检测：偏差超过阈值",
                                    assigned_to=""
                                )
                                self.db.add_recheck_task(recheck_task)

                    except Exception as e:
                        result.error_count += 1
                        err_msg = f"第{i}行：导入失败 - {str(e)}"
                        result.errors.append(err_msg)
                        if batch_id:
                            import_err = ImportError(
                                id=None,
                                batch_id=batch_id,
                                row_number=i,
                                component_code=cleaned["component_code"],
                                error_type="database_error",
                                error_message=err_msg,
                                row_data=json.dumps(row, ensure_ascii=False)
                            )
                            self.db.add_import_error(import_err)

                if batch_id:
                    status = "completed" if result.error_count == 0 else "completed_with_errors"
                    self.db.update_import_batch(
                        batch_id,
                        total_count=total_count,
                        success_count=result.success_count,
                        error_count=result.error_count,
                        status=status
                    )

        except UnicodeDecodeError:
            result.errors.append("文件编码错误，请使用UTF-8编码")
            result.error_count += 1
            if batch_id:
                self.db.update_import_batch(batch_id, status="failed", remark="文件编码错误")
        except Exception as e:
            result.errors.append(f"读取文件失败：{str(e)}")
            result.error_count += 1
            if batch_id:
                self.db.update_import_batch(batch_id, status="failed", remark=f"读取失败: {str(e)}")

        return result

    def preview_file(self, file_path: str, max_rows: int = 10) -> Tuple[List[str], List[Dict], List[str], Dict[int, List[str]]]:
        headers = []
        rows = []
        errors = []
        row_errors: Dict[int, List[str]] = {}

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
                    row_index = i + 2
                    rows.append(dict(row))

                    is_valid, row_errs, _ = validate_csv_row(row, row_index)
                    if not is_valid:
                        row_errors[row_index] = row_errs
                        errors.extend(row_errs)

        except Exception as e:
            errors.append(f"读取文件失败：{str(e)}")

        return headers, rows, errors, row_errors

    def count_rows(self, file_path: str) -> int:
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                next(reader, None)
                return sum(1 for _ in reader)
        except Exception:
            return 0

    def rollback_batch(self, batch_id: int) -> bool:
        batch = self.db.get_import_batch(batch_id)
        if not batch:
            return False

        records = self.db.get_measurements_by_batch(batch_id)
        for rec in records:
            tasks = self.db.get_recheck_tasks_by_component(rec.component_id)
            for task in tasks:
                if task.record_id == rec.id:
                    self.db.update_recheck_task(task.id, status="cancelled", recheck_result="导入批次回滚，任务取消")

        self.db.delete_import_batch(batch_id)
        return True
