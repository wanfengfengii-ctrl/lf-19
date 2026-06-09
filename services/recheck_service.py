from typing import List, Optional, Dict
from datetime import datetime

from database import (
    DatabaseManager, RecheckTask, MeasurementRecord, Component,
    RECHECK_STATUS_PENDING, RECHECK_STATUS_IN_PROGRESS,
    RECHECK_STATUS_COMPLETED, RECHECK_STATUS_CANCELLED
)


class RecheckService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_recheck_task(self, building_id: int, component_id: int,
                            record_id: int, reason: str = "",
                            priority: str = "normal",
                            assigned_to: str = "") -> Optional[int]:
        component = self.db.get_component(component_id)
        if not component:
            return None

        if self.db.has_active_recheck_task(component_id):
            return None

        task = RecheckTask(
            id=None,
            building_id=building_id,
            component_id=component_id,
            component_code=component.code,
            record_id=record_id,
            status=RECHECK_STATUS_PENDING,
            assigned_to=assigned_to,
            priority=priority,
            reason=reason
        )
        return self.db.add_recheck_task(task)

    def start_task(self, task_id: int, assigned_to: str = "") -> bool:
        task = self.db.get_recheck_task(task_id)
        if not task or task.status != RECHECK_STATUS_PENDING:
            return False

        updates = {"status": RECHECK_STATUS_IN_PROGRESS}
        if assigned_to:
            updates["assigned_to"] = assigned_to

        return self.db.update_recheck_task(task_id, **updates)

    def complete_task(self, task_id: int, recheck_record_id: int,
                      result: str = "") -> bool:
        task = self.db.get_recheck_task(task_id)
        if not task or task.status not in [RECHECK_STATUS_PENDING, RECHECK_STATUS_IN_PROGRESS]:
            return False

        self.db.clear_recheck_mark(recheck_record_id)

        return self.db.update_recheck_task(
            task_id,
            status=RECHECK_STATUS_COMPLETED,
            recheck_record_id=recheck_record_id,
            recheck_result=result
        )

    def cancel_task(self, task_id: int, reason: str = "") -> bool:
        task = self.db.get_recheck_task(task_id)
        if not task or task.status in [RECHECK_STATUS_COMPLETED, RECHECK_STATUS_CANCELLED]:
            return False

        return self.db.update_recheck_task(
            task_id,
            status=RECHECK_STATUS_CANCELLED,
            recheck_result=reason
        )

    def assign_task(self, task_id: int, assigned_to: str) -> bool:
        task = self.db.get_recheck_task(task_id)
        if not task or task.status == RECHECK_STATUS_COMPLETED:
            return False

        return self.db.update_recheck_task(task_id, assigned_to=assigned_to)

    def get_task(self, task_id: int) -> Optional[RecheckTask]:
        return self.db.get_recheck_task(task_id)

    def get_tasks_by_building(self, building_id: int,
                              status: str = None) -> List[RecheckTask]:
        return self.db.get_recheck_tasks_by_building(building_id, status)

    def get_tasks_by_component(self, component_id: int) -> List[RecheckTask]:
        return self.db.get_recheck_tasks_by_component(component_id)

    def get_statistics(self, building_id: int) -> Dict[str, int]:
        return self.db.get_recheck_statistics(building_id)

    def has_active_recheck_task(self, component_id: int) -> bool:
        return self.db.has_active_recheck_task(component_id)

    def get_task_details(self, task_id: int) -> Optional[Dict]:
        task = self.db.get_recheck_task(task_id)
        if not task:
            return None

        component = self.db.get_component(task.component_id)
        original_record = self.db.get_measurement_record(task.record_id)

        recheck_record = None
        if task.recheck_record_id:
            recheck_record = self.db.get_measurement_record(task.recheck_record_id)

        return {
            "task": task,
            "component": component,
            "original_record": original_record,
            "recheck_record": recheck_record
        }

    def batch_create_from_abnormal(self, building_id: int,
                                   reason: str = "偏差超过阈值，需复测",
                                   priority: str = "normal") -> int:
        from services.deviation_calculator import DeviationCalculator
        calc = DeviationCalculator(self.db)
        abnormal_list = calc.get_abnormal_components(building_id)

        count = 0
        for dev in abnormal_list:
            if dev.latest_record and not self.db.has_active_recheck_task(dev.component.id):
                task_id = self.create_recheck_task(
                    building_id=building_id,
                    component_id=dev.component.id,
                    record_id=dev.latest_record.id,
                    reason=reason,
                    priority=priority
                )
                if task_id:
                    self.db.mark_for_recheck(dev.latest_record.id, reason)
                    count += 1

        return count

    def get_task_status_text(self, status: str) -> str:
        status_map = {
            RECHECK_STATUS_PENDING: "待处理",
            RECHECK_STATUS_IN_PROGRESS: "进行中",
            RECHECK_STATUS_COMPLETED: "已完成",
            RECHECK_STATUS_CANCELLED: "已取消"
        }
        return status_map.get(status, status)

    def get_priority_text(self, priority: str) -> str:
        priority_map = {
            "high": "高",
            "normal": "中",
            "low": "低"
        }
        return priority_map.get(priority, priority)
