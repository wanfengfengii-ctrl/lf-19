from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from database import (
    DatabaseManager, DiseaseRecord, DiseaseTreatment, DiseaseStats,
    DiseaseStatusHistory, DiseaseAcceptanceRecord,
    DiseasePhotoArchive, WarningRecord, OperationLog,
    DeviationDiseaseLink,
    DISEASE_TYPE_CRACK, DISEASE_TYPE_DECAY, DISEASE_TYPE_INSECT,
    DISEASE_TYPE_DEFORMATION, DISEASE_TYPE_DEFECT, DISEASE_TYPE_OTHER,
    DISEASE_TYPES,
    DISEASE_SEVERITY_MILD, DISEASE_SEVERITY_MODERATE,
    DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_DANGEROUS,
    DISEASE_SEVERITIES,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT,
    PRIORITIES,
    DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_REVIEWED,
    DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_ASSIGNED,
    DISEASE_STATUS_ACCEPTED, DISEASE_STATUS_ARCHIVED,
    DISEASE_STATUS_REJECTED,
    DISEASE_STATUS_TRANSITIONS, DISEASE_STATUSES,
    ACCEPTANCE_RESULT_PASS, ACCEPTANCE_RESULT_FAIL,
    ACCEPTANCE_RESULT_PARTIAL, ACCEPTANCE_RESULTS,
    PHOTO_TYPE_BEFORE, PHOTO_TYPE_AFTER, PHOTO_TYPE_PROCESS,
    PHOTO_TYPE_OTHER, PHOTO_TYPES,
    PHOTO_STAGE_DISCOVERY, PHOTO_STAGE_DIAGNOSIS,
    PHOTO_STAGE_TREATMENT, PHOTO_STAGE_ACCEPTANCE,
    PHOTO_STAGE_REVIEW, PHOTO_STAGES,
    WARNING_TYPE_DEVIATION, WARNING_TYPE_DISEASE,
    WARNING_TYPE_RISK, WARNING_TYPE_DEADLINE,
    WARNING_LEVEL_INFO, WARNING_LEVEL_WARNING,
    WARNING_LEVEL_DANGER, WARNING_LEVEL_CRITICAL,
    WARNING_LEVELS, WARNING_TYPES,
    MODULE_DISEASE, ACTION_STATUS_CHANGE,
    ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE,
    ACTION_ACCEPTANCE, ACTION_ARCHIVE,
    RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM,
    RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL, RISK_LEVELS,
)
from services.deviation_calculator import DeviationCalculator


@dataclass
class RepairSuggestion:
    disease_type: str
    severity: str
    priority: str
    suggestion: str
    method: str
    estimated_cost: float
    urgency_level: str
    deviation_factor: str = ""


@dataclass
class StatusTransitionResult:
    success: bool
    message: str
    disease: Optional[DiseaseRecord] = None


class DiseaseStateMachine:
    def __init__(self):
        self.transitions = DISEASE_STATUS_TRANSITIONS

    def can_transition(self, from_status: str, to_status: str) -> bool:
        if from_status not in self.transitions:
            return False
        return to_status in self.transitions[from_status]

    def get_allowed_transitions(self, current_status: str) -> List[str]:
        return self.transitions.get(current_status, [])

    def get_status_name(self, status: str) -> str:
        status_map = {code: name for code, name in DISEASE_STATUSES}
        return status_map.get(status, status)


class DiseaseService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.deviation_calc = DeviationCalculator(db_manager)
        self.state_machine = DiseaseStateMachine()

    def assess_risk(self, disease: DiseaseRecord) -> Tuple[str, str]:
        severity_score = {
            DISEASE_SEVERITY_MILD: 1,
            DISEASE_SEVERITY_MODERATE: 2,
            DISEASE_SEVERITY_SEVERE: 3,
            DISEASE_SEVERITY_DANGEROUS: 4,
        }

        base_score = severity_score.get(disease.severity, 1)

        size_score = 0
        if disease.size_length > 0:
            if disease.size_length > 500:
                size_score += 2
            elif disease.size_length > 200:
                size_score += 1
        if disease.size_depth > 0:
            if disease.size_depth > 50:
                size_score += 2
            elif disease.size_depth > 20:
                size_score += 1

        deviation_score = 0
        if disease.component_id:
            dev = self.deviation_calc.calculate_component_deviation(
                self.db.get_component(disease.component_id)
            )
            if dev.is_abnormal:
                deviation_score = 2
            elif dev.latest_record and dev.latest_record.is_recheck:
                deviation_score = 1

        total_score = base_score + size_score + deviation_score

        if total_score >= 6:
            priority = PRIORITY_URGENT
        elif total_score >= 4:
            priority = PRIORITY_HIGH
        elif total_score >= 2:
            priority = PRIORITY_MEDIUM
        else:
            priority = PRIORITY_LOW

        if total_score >= 6:
            final_severity = DISEASE_SEVERITY_DANGEROUS
        elif total_score >= 4:
            final_severity = DISEASE_SEVERITY_SEVERE
        elif total_score >= 2:
            final_severity = DISEASE_SEVERITY_MODERATE
        else:
            final_severity = DISEASE_SEVERITY_MILD

        return final_severity, priority

    def generate_repair_suggestion(self, disease: DiseaseRecord) -> RepairSuggestion:
        suggestions = {
            DISEASE_TYPE_CRACK: self._suggest_crack_repair,
            DISEASE_TYPE_DECAY: self._suggest_decay_repair,
            DISEASE_TYPE_INSECT: self._suggest_insect_repair,
            DISEASE_TYPE_DEFORMATION: self._suggest_deformation_repair,
            DISEASE_TYPE_DEFECT: self._suggest_defect_repair,
            DISEASE_TYPE_OTHER: self._suggest_other_repair,
        }

        suggestion_func = suggestions.get(disease.disease_type, self._suggest_other_repair)
        suggestion, method, cost = suggestion_func(disease)

        deviation_factor = ""
        if disease.component_id:
            component = self.db.get_component(disease.component_id)
            if component:
                dev = self.deviation_calc.calculate_component_deviation(component)
                if dev.is_abnormal:
                    deviation_factor = "构件存在尺寸偏差，需结合偏差情况制定修缮方案"
                elif dev.latest_record and dev.latest_record.is_recheck:
                    deviation_factor = "构件有复测记录，修缮后需再次测量验证"

        return RepairSuggestion(
            disease_type=disease.disease_type,
            severity=disease.severity,
            priority=disease.priority,
            suggestion=suggestion,
            method=method,
            estimated_cost=cost,
            urgency_level=disease.priority,
            deviation_factor=deviation_factor,
        )

    def _suggest_crack_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity
        length = disease.size_length
        depth = disease.size_depth

        if severity == DISEASE_SEVERITY_DANGEROUS or length > 500 or depth > 30:
            suggestion = (
                "裂缝严重，已影响结构安全。建议立即采取加固措施，必要时进行构件替换或补强处理。"
            )
            method = "结构加固 + 环氧树脂灌缝 + 碳纤维加固"
            cost = 5000.0
        elif severity == DISEASE_SEVERITY_SEVERE or length > 200 or depth > 10:
            suggestion = (
                "裂缝较严重，需进行裂缝修补和加固处理，防止裂缝继续扩展。"
            )
            method = "环氧树脂灌缝 + 表面封闭"
            cost = 2000.0
        elif severity == DISEASE_SEVERITY_MODERATE or length > 50:
            suggestion = (
                "裂缝一般，需进行裂缝填补，防止水分和虫害侵入。"
            )
            method = "腻子填补 + 表面油漆修复"
            cost = 800.0
        else:
            suggestion = (
                "轻微裂缝，建议观察为主，定期检查，必要时进行表面封闭处理。"
            )
            method = "表面封闭处理"
            cost = 300.0

        return suggestion, method, cost

    def _suggest_decay_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity
        area = disease.size_length * disease.size_width if disease.size_length and disease.size_width else 0

        if severity == DISEASE_SEVERITY_DANGEROUS or area > 10000:
            suggestion = (
                "腐朽严重，已危及结构安全。建议立即更换腐朽构件或进行大规模加固处理。"
            )
            method = "构件更换 + 防腐处理"
            cost = 8000.0
        elif severity == DISEASE_SEVERITY_SEVERE or area > 2500:
            suggestion = (
                "腐朽较严重，需进行腐朽清理和加固处理，防止腐朽部分需做防腐处理。"
            )
            method = "腐朽清理 + 环氧树脂修补 + 防腐处理"
            cost = 3500.0
        elif severity == DISEASE_SEVERITY_MODERATE or area > 400:
            suggestion = (
                "腐朽一般，需进行表面腐朽清理，做防腐防虫处理。"
            )
            method = "表面清理 + 防腐涂料"
            cost = 1200.0
        else:
            suggestion = (
                "轻微腐朽，建议清理后做表面防腐处理，定期检查。"
            )
            method = "表面清理 + 防腐处理"
            cost = 500.0

        return suggestion, method, cost

    def _suggest_insect_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity

        if severity == DISEASE_SEVERITY_DANGEROUS:
            suggestion = (
                "虫蛀严重，已严重削弱构件承载力。建议更换构件或进行大规模加固，并做全面杀虫处理。"
            )
            method = "构件更换 + 熏蒸杀虫 + 防腐防虫处理"
            cost = 6000.0
        elif severity == DISEASE_SEVERITY_SEVERE:
            suggestion = (
                "虫蛀较严重，需进行杀虫处理和加固，防止虫害继续扩散。"
            )
            method = "熏蒸杀虫 + 环氧树脂填补 + 防虫处理"
            cost = 2500.0
        elif severity == DISEASE_SEVERITY_MODERATE:
            suggestion = (
                "虫蛀一般，需进行杀虫和防虫处理，防止虫害扩散。"
            )
            method = "药物杀虫 + 表面防虫处理"
            cost = 1000.0
        else:
            suggestion = (
                "轻微虫蛀，建议进行预防性防虫处理，定期检查。"
            )
            method = "表面防虫处理"
            cost = 400.0

        return suggestion, method, cost

    def _suggest_deformation_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity

        if severity == DISEASE_SEVERITY_DANGEROUS:
            suggestion = (
                "变形严重，已影响结构安全和使用功能。建议立即进行加固或更换构件。"
            )
            method = "构件校正 + 加固处理，必要时更换"
            cost = 7000.0
        elif severity == DISEASE_SEVERITY_SEVERE:
            suggestion = (
                "变形较严重，需进行校正和加固处理，恢复构件功能。"
            )
            method = "构件校正 + 加固处理"
            cost = 3000.0
        elif severity == DISEASE_SEVERITY_MODERATE:
            suggestion = (
                "变形一般，需进行校正处理，防止变形发展。"
            )
            method = "构件校正 + 支撑加固"
            cost = 1200.0
        else:
            suggestion = (
                "轻微变形，建议观察为主，定期检查变形发展情况。"
            )
            method = "观察监测"
            cost = 300.0

        return suggestion, method, cost

    def _suggest_defect_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity
        area = disease.size_length * disease.size_width if disease.size_length and disease.size_width else 0

        if severity == DISEASE_SEVERITY_DANGEROUS or area > 5000:
            suggestion = (
                "缺损严重，影响结构安全。建议进行补配或更换构件。"
            )
            method = "构件修补 + 加固处理"
            cost = 5500.0
        elif severity == DISEASE_SEVERITY_SEVERE or area > 1000:
            suggestion = (
                "缺损较严重，需进行修补和加固处理。"
            )
            method = "环氧树脂修补 + 加固"
            cost = 2500.0
        elif severity == DISEASE_SEVERITY_MODERATE or area > 100:
            suggestion = (
                "缺损一般，需进行修补处理，恢复构件完整性。"
            )
            method = "木材填补 + 表面修复"
            cost = 1000.0
        else:
            suggestion = (
                "轻微缺损，进行表面修补处理即可。"
            )
            method = "表面修补"
            cost = 300.0

        return suggestion, method, cost

    def _suggest_other_repair(self, disease: DiseaseRecord) -> Tuple[str, str, float]:
        severity = disease.severity

        if severity == DISEASE_SEVERITY_DANGEROUS:
            suggestion = "病害严重，建议请专业人员现场，制定专项修缮方案。"
            method = "专项修缮方案"
            cost = 3000.0
        elif severity == DISEASE_SEVERITY_SEVERE:
            suggestion = "病害较严重，需进行专业检查和处理。"
            method = "专业检查 + 处理"
            cost = 1500.0
        elif severity == DISEASE_SEVERITY_MODERATE:
            suggestion = "病害一般，建议进行常规保养和处理。"
            method = "常规保养处理"
            cost = 600.0
        else:
            suggestion = "轻微病害，建议观察，定期检查。"
            method = "观察监测"
            cost = 200.0

        return suggestion, method, cost

    def create_disease_with_suggestion(self, disease: DiseaseRecord,
                                       operator: str = "") -> DiseaseRecord:
        final_severity, final_priority = self.assess_risk(disease)
        disease.severity = final_severity
        disease.priority = final_priority
        disease.status = DISEASE_STATUS_DISCOVERED

        suggestion = self.generate_repair_suggestion(disease)
        disease.repair_suggestion = suggestion.suggestion
        disease.repair_method = suggestion.method
        disease.estimated_cost = suggestion.estimated_cost

        disease_id = self.db.add_disease_record(disease)
        disease.id = disease_id

        self._record_status_history(disease_id, "", DISEASE_STATUS_DISCOVERED,
                                    operator, "病害记录创建")

        self._log_operation(MODULE_DISEASE, ACTION_CREATE,
                           "disease_record", disease_id, operator,
                           f"创建病害记录: {disease.disease_type}")

        self._check_and_create_warnings(disease)

        self.update_deviation_disease_link(disease.component_id)

        return disease

    def transition_status(self, disease_id: int, to_status: str,
                          operator: str = "", remark: str = "") -> StatusTransitionResult:
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return StatusTransitionResult(success=False, message="病害记录不存在")

        from_status = disease.status

        if not self.state_machine.can_transition(from_status, to_status):
            from_name = self.state_machine.get_status_name(from_status)
            to_name = self.state_machine.get_status_name(to_status)
            allowed = [self.state_machine.get_status_name(s)
                       for s in self.state_machine.get_allowed_transitions(from_status)]
            return StatusTransitionResult(
                success=False,
                message=f"状态流转不合法：从「{from_name}」不能直接流转到「{to_name}」。\n允许的状态：{', '.join(allowed)}"
            )

        if not self._validate_completion_date(disease, to_status):
            return StatusTransitionResult(
                success=False,
                message="完成日期校验失败：请设置有效的完成日期"
            )

        disease.status = to_status

        if to_status in (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
                         DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED):
            if not disease.complete_date:
                disease.complete_date = datetime.now().strftime("%Y-%m-%d")
        elif to_status == DISEASE_STATUS_IN_PROGRESS and not disease.handler:
            if operator:
                disease.handler = operator

        success = self.db.update_disease_record(disease)
        if not success:
            return StatusTransitionResult(success=False, message="状态更新失败")

        self._record_status_history(disease_id, from_status, to_status,
                                    operator, remark)

        self._log_operation(MODULE_DISEASE, ACTION_STATUS_CHANGE,
                           "disease_record", disease_id, operator,
                           f"状态变更: {from_status} -> {to_status}, 备注: {remark}")

        updated_disease = self.db.get_disease_record(disease_id)
        return StatusTransitionResult(
            success=True,
            message=f"状态已变更为「{self.state_machine.get_status_name(to_status)}」",
            disease=updated_disease
        )

    def _validate_completion_date(self, disease: DiseaseRecord,
                                  to_status: str) -> bool:
        if to_status in (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
                         DISEASE_STATUS_REVIEWED):
            if disease.complete_date:
                try:
                    complete_dt = datetime.strptime(disease.complete_date, "%Y-%m-%d")
                    if complete_dt > datetime.now():
                        return False
                except ValueError:
                    return False
            if disease.plan_date:
                try:
                    plan_dt = datetime.strptime(disease.plan_date, "%Y-%m-%d")
                    if disease.complete_date:
                        complete_dt = datetime.strptime(disease.complete_date, "%Y-%m-%d")
                except ValueError:
                    pass
        return True

    def _record_status_history(self, disease_id: int, from_status: str,
                               to_status: str, operator: str = "",
                               remark: str = ""):
        history = DiseaseStatusHistory(
            id=None,
            disease_id=disease_id,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
            remark=remark
        )
        self.db.add_disease_status_history(history)

    def _log_operation(self, module: str, action: str, target_type: str,
                       target_id: Optional[int], operator: str = "",
                       detail: str = ""):
        log = OperationLog(
            id=None,
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            operator=operator,
            detail=detail
        )
        self.db.add_operation_log(log)

    def _check_and_create_warnings(self, disease: DiseaseRecord):
        if disease.severity in (DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_DANGEROUS):
            warning_level = (WARNING_LEVEL_CRITICAL
                             if disease.severity == DISEASE_SEVERITY_DANGEROUS
                             else WARNING_LEVEL_DANGER)
            warning = WarningRecord(
                id=None,
                building_id=disease.building_id,
                component_id=disease.component_id,
                component_code=disease.component_code,
                warning_type=WARNING_TYPE_DISEASE,
                warning_level=warning_level,
                title=f"{disease.disease_type}病害预警",
                description=f"构件 {disease.component_code} 发现严重病害，需及时处理",
                source="病害录入",
                related_disease_id=disease.id,
                is_read=False,
                is_handled=False
            )
            self.db.add_warning(warning)

        if disease.plan_date:
            try:
                plan_dt = datetime.strptime(disease.plan_date, "%Y-%m-%d")
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                days_left = (plan_dt - today).days
                if 0 <= days_left <= 3:
                    warning = WarningRecord(
                        id=None,
                        building_id=disease.building_id,
                        component_id=disease.component_id,
                        component_code=disease.component_code,
                        warning_type=WARNING_TYPE_DEADLINE,
                        warning_level=WARNING_LEVEL_WARNING,
                        title="处理期限临近预警",
                        description=f"病害处理计划日期为 {disease.plan_date}，仅剩 {days_left} 天",
                        source="期限预警",
                        related_disease_id=disease.id,
                        is_read=False,
                        is_handled=False
                    )
                    self.db.add_warning(warning)
            except ValueError:
                pass

    def submit_for_assignment(self, disease_id: int,
                              operator: str = "") -> StatusTransitionResult:
        return self.transition_status(disease_id, DISEASE_STATUS_PENDING,
                                      operator, "提交待派单")

    def assign_disease(self, disease_id: int, handler: str,
                       plan_date: str = "",
                       operator: str = "") -> StatusTransitionResult:
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return StatusTransitionResult(success=False, message="病害记录不存在")

        disease.handler = handler
        if plan_date:
            disease.plan_date = plan_date

        self.db.update_disease_record(disease)

        return self.transition_status(disease_id, DISEASE_STATUS_ASSIGNED,
                                      operator, f"派单给 {handler}")

    def start_treatment(self, disease_id: int,
                        operator: str = "") -> StatusTransitionResult:
        return self.transition_status(disease_id, DISEASE_STATUS_IN_PROGRESS,
                                      operator, "开始处置")

    def complete_treatment(self, disease_id: int, complete_date: str = "",
                           remark: str = "",
                           operator: str = "") -> StatusTransitionResult:
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return StatusTransitionResult(success=False, message="病害记录不存在")

        if complete_date:
            disease.complete_date = complete_date
        self.db.update_disease_record(disease)

        return self.transition_status(disease_id, DISEASE_STATUS_COMPLETED,
                                      operator, remark)

    def accept_disease(self, disease_id: int, acceptance_result: str,
                       acceptance_opinion: str = "", acceptor: str = "",
                       photo_paths: str = "", remark: str = "",
                       operator: str = "") -> StatusTransitionResult:
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return StatusTransitionResult(success=False, message="病害记录不存在")

        record = DiseaseAcceptanceRecord(
            id=None,
            disease_id=disease_id,
            acceptance_result=acceptance_result,
            acceptance_opinion=acceptance_opinion,
            acceptor=acceptor or operator,
            photo_paths=photo_paths,
            remark=remark
        )
        self.db.add_disease_acceptance(record)

        if acceptance_result == ACCEPTANCE_RESULT_PASS:
            result = self.transition_status(disease_id, DISEASE_STATUS_ACCEPTED,
                                            operator, f"验收通过: {acceptance_opinion}")
        elif acceptance_result == ACCEPTANCE_RESULT_PARTIAL:
            result = self.transition_status(disease_id, DISEASE_STATUS_IN_PROGRESS,
                                            operator, f"部分通过，需继续整改: {acceptance_opinion}")
        else:
            result = self.transition_status(disease_id, DISEASE_STATUS_REJECTED,
                                            operator, f"验收不通过，需重新整改: {acceptance_opinion}")

        self._log_operation(MODULE_DISEASE, ACTION_ACCEPTANCE,
                           "disease_record", disease_id, operator or acceptor,
                           f"验收: {acceptance_result}, 意见: {acceptance_opinion}")

        return result

    def review_disease(self, disease_id: int,
                       acceptance_result: str = ACCEPTANCE_RESULT_PASS,
                       acceptance_opinion: str = "",
                       acceptor: str = "",
                       photo_paths: str = "",
                       remark: str = "",
                       operator: str = "") -> StatusTransitionResult:
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return StatusTransitionResult(success=False, message="病害记录不存在")

        record = DiseaseAcceptanceRecord(
            id=None,
            disease_id=disease_id,
            acceptance_result=acceptance_result,
            acceptance_opinion=acceptance_opinion,
            acceptor=acceptor or operator,
            photo_paths=photo_paths,
            remark=remark,
            is_review=True,
        )
        self.db.add_disease_acceptance(record)

        if acceptance_result == ACCEPTANCE_RESULT_PASS:
            result = self.transition_status(disease_id, DISEASE_STATUS_REVIEWED,
                                            operator, f"复查通过: {acceptance_opinion}")
        else:
            result = self.transition_status(disease_id, DISEASE_STATUS_IN_PROGRESS,
                                            operator, f"复查不通过，需重新整改: {acceptance_opinion}")

        self._log_operation(MODULE_DISEASE, ACTION_ACCEPTANCE,
                           "disease_record", disease_id, operator or acceptor,
                           f"复查: {acceptance_result}, 意见: {acceptance_opinion}")

        return result

    def archive_disease(self, disease_id: int,
                        operator: str = "") -> StatusTransitionResult:
        return self.transition_status(disease_id, DISEASE_STATUS_ARCHIVED,
                                      operator, "归档病害")

    def reopen_disease(self, disease_id: int, reason: str = "",
                       operator: str = "") -> StatusTransitionResult:
        return self.transition_status(disease_id, DISEASE_STATUS_PENDING,
                                      operator, f"重新打开: {reason}")

    def add_treatment_record(self, treatment: DiseaseTreatment,
                             operator: str = "") -> int:
        treatment_id = self.db.add_disease_treatment(treatment)

        self._log_operation(MODULE_DISEASE, ACTION_UPDATE,
                           "disease_treatment", treatment_id, operator,
                           f"添加处置记录: {treatment.treatment_type}")

        return treatment_id

    def add_photo_archive(self, photo: DiseasePhotoArchive,
                          operator: str = "") -> int:
        photo_id = self.db.add_disease_photo(photo)

        self._log_operation(MODULE_DISEASE, ACTION_CREATE,
                           "disease_photo", photo_id, operator,
                           f"上传照片: {photo.photo_type} - {photo.photo_stage}")

        return photo_id

    def get_before_after_photos(self, disease_id: int) -> Dict[str, List[DiseasePhotoArchive]]:
        before_photos = self.db.get_photos_by_type(disease_id, PHOTO_TYPE_BEFORE)
        after_photos = self.db.get_photos_by_type(disease_id, PHOTO_TYPE_AFTER)
        process_photos = self.db.get_photos_by_type(disease_id, PHOTO_TYPE_PROCESS)
        return {
            "before": before_photos,
            "process": process_photos,
            "after": after_photos
        }

    def update_deviation_disease_link(self, component_id: int):
        if not component_id:
            return

        component = self.db.get_component(component_id)
        if not component:
            return

        diseases = self.db.get_diseases_by_component(component_id)
        disease_count = len(diseases)

        dev = self.deviation_calc.calculate_component_deviation(component)
        deviation_level = "low"
        if dev.is_abnormal:
            max_dev_rel = 0
            threshold = component.deviation_threshold or 5.0
            if dev.length_deviation:
                rel = abs(dev.length_deviation.deviation) / threshold if threshold > 0 else 0
                max_dev_rel = max(max_dev_rel, rel)
            if dev.width_deviation:
                rel = abs(dev.width_deviation.deviation) / threshold if threshold > 0 else 0
                max_dev_rel = max(max_dev_rel, rel)
            if dev.angle_deviation:
                rel = abs(dev.angle_deviation.deviation) / threshold if threshold > 0 else 0
                max_dev_rel = max(max_dev_rel, rel)

            if max_dev_rel >= 3:
                deviation_level = "critical"
            elif max_dev_rel >= 2:
                deviation_level = "high"
            elif max_dev_rel >= 1:
                deviation_level = "medium"

        dev_risk_map = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        disease_risk = min(disease_count, 3)
        total_risk = dev_risk_map.get(deviation_level, 0) + disease_risk

        if total_risk >= 5:
            risk_level = RISK_LEVEL_CRITICAL
        elif total_risk >= 3:
            risk_level = RISK_LEVEL_HIGH
        elif total_risk >= 1:
            risk_level = RISK_LEVEL_MEDIUM
        else:
            risk_level = RISK_LEVEL_LOW

        assessment = f"偏差等级: {deviation_level}, 病害数量: {disease_count}"
        if risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL):
            suggestion = "建议及时处理，重点关注"
        elif risk_level == RISK_LEVEL_MEDIUM:
            suggestion = "建议定期检查，关注变化"
        else:
            suggestion = "状态良好，正常维护"

        link = DeviationDiseaseLink(
            id=None,
            component_id=component_id,
            component_code=component.code,
            deviation_level=deviation_level,
            disease_count=disease_count,
            risk_level=risk_level,
            assessment=assessment,
            suggestion=suggestion
        )
        self.db.upsert_deviation_disease_link(link)

        if risk_level in (RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL):
            existing_warnings = self.db.get_warnings_by_component(component_id)
            has_risk_warning = any(
                w.warning_type == WARNING_TYPE_RISK and not w.is_handled
                for w in existing_warnings
            )
            if not has_risk_warning:
                warning = WarningRecord(
                    id=None,
                    building_id=component.building_id,
                    component_id=component_id,
                    component_code=component.code,
                    warning_type=WARNING_TYPE_RISK,
                    warning_level=(WARNING_LEVEL_CRITICAL
                                   if risk_level == RISK_LEVEL_CRITICAL
                                   else WARNING_LEVEL_DANGER),
                    title="构件风险预警",
                    description=f"构件 {component.code} 存在较高风险: {assessment}",
                    source="偏差病害联动分析",
                    is_read=False,
                    is_handled=False
                )
                self.db.add_warning(warning)

    def batch_update_risk_assessment(self, building_id: int) -> int:
        return self.db.update_deviation_disease_stats(building_id)

    def get_disease_ledger(self, building_id: int,
                           status: str = None,
                           disease_type: str = None,
                           severity: str = None) -> List[DiseaseRecord]:
        return self.db.get_diseases_by_building(building_id, status, disease_type, severity)

    def get_progress_summary(self, building_id: int) -> Dict[str, any]:
        stats = self.db.get_disease_statistics(building_id)

        completion_rate = 0.0
        if stats.total_count > 0:
            completed_total = (stats.completed_count + stats.accepted_count +
                               stats.reviewed_count + stats.archived_count)
            completion_rate = completed_total / stats.total_count * 100

        pending_urgent = 0
        diseases = self.db.get_diseases_by_building(building_id)
        for d in diseases:
            if d.status in [DISEASE_STATUS_PENDING, DISEASE_STATUS_DISCOVERED,
                            DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS] and \
               d.priority == PRIORITY_URGENT:
                pending_urgent += 1

        return {
            "stats": stats,
            "completion_rate": completion_rate,
            "pending_urgent": pending_urgent,
        }

    def batch_generate_all_suggestions(self, building_id: int) -> int:
        diseases = self.db.get_diseases_by_building(building_id)
        count = 0
        for disease in diseases:
            suggestion = self.generate_repair_suggestion(disease)
            disease.repair_suggestion = suggestion.suggestion
            disease.repair_method = suggestion.method
            disease.estimated_cost = suggestion.estimated_cost
            if self.db.update_disease_record(disease):
                count += 1
        return count

    def get_status_history(self, disease_id: int) -> List[DiseaseStatusHistory]:
        return self.db.get_status_history_by_disease(disease_id)

    def get_acceptance_records(self, disease_id: int) -> List[DiseaseAcceptanceRecord]:
        return self.db.get_acceptance_by_disease(disease_id)

    def check_deadline_warnings(self, building_id: int) -> List[WarningRecord]:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        diseases = self.db.get_diseases_by_building(building_id)
        warnings = []

        for disease in diseases:
            if disease.status in (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
                                  DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED):
                continue
            if not disease.plan_date:
                continue
            try:
                plan_dt = datetime.strptime(disease.plan_date, "%Y-%m-%d")
                days_left = (plan_dt - today).days
                if days_left < 0:
                    warning_level = WARNING_LEVEL_DANGER
                    title = "处理期限已超期"
                    description = f"病害处理计划日期为 {disease.plan_date}，已超期 {abs(days_left)} 天"
                elif days_left <= 3:
                    warning_level = WARNING_LEVEL_WARNING
                    title = "处理期限临近预警"
                    description = f"病害处理计划日期为 {disease.plan_date}，仅剩 {days_left} 天"
                else:
                    continue

                existing = self.db.get_warnings_by_component(disease.component_id)
                has_warning = any(
                    w.warning_type == WARNING_TYPE_DEADLINE and
                    w.related_disease_id == disease.id and
                    not w.is_handled
                    for w in existing
                )
                if not has_warning:
                    warning = WarningRecord(
                        id=None,
                        building_id=building_id,
                        component_id=disease.component_id,
                        component_code=disease.component_code,
                        warning_type=WARNING_TYPE_DEADLINE,
                        warning_level=warning_level,
                        title=title,
                        description=description,
                        source="期限预警",
                        related_disease_id=disease.id,
                        is_read=False,
                        is_handled=False
                    )
                    self.db.add_warning(warning)
                    warnings.append(warning)
            except ValueError:
                pass

        return warnings

    def get_overdue_diseases(self, building_id: int) -> List[DiseaseRecord]:
        today = datetime.now().strftime("%Y-%m-%d")
        diseases = self.db.get_diseases_by_building(building_id)
        overdue = []
        for d in diseases:
            if d.status in (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
                            DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED):
                continue
            if d.plan_date and d.plan_date < today:
                overdue.append(d)
        return overdue

    def get_allowed_status_actions(self, disease: DiseaseRecord) -> List[Tuple[str, str]]:
        actions = []
        current_status = disease.status

        action_map = {
            DISEASE_STATUS_DISCOVERED: [
                (DISEASE_STATUS_PENDING, "提交待派单"),
            ],
            DISEASE_STATUS_PENDING: [
                (DISEASE_STATUS_ASSIGNED, "派单"),
            ],
            DISEASE_STATUS_ASSIGNED: [
                (DISEASE_STATUS_IN_PROGRESS, "开始处置"),
                (DISEASE_STATUS_PENDING, "退回待派单"),
            ],
            DISEASE_STATUS_IN_PROGRESS: [
                (DISEASE_STATUS_COMPLETED, "提交验收"),
                (DISEASE_STATUS_ASSIGNED, "退回派单"),
            ],
            DISEASE_STATUS_COMPLETED: [
                (DISEASE_STATUS_ACCEPTED, "验收通过"),
                (DISEASE_STATUS_REJECTED, "验收不通过"),
                (DISEASE_STATUS_IN_PROGRESS, "继续处置"),
            ],
            DISEASE_STATUS_ACCEPTED: [
                (DISEASE_STATUS_REVIEWED, "完成复查"),
                (DISEASE_STATUS_ARCHIVED, "归档"),
                (DISEASE_STATUS_IN_PROGRESS, "重新处置"),
            ],
            DISEASE_STATUS_REVIEWED: [
                (DISEASE_STATUS_ARCHIVED, "归档"),
                (DISEASE_STATUS_IN_PROGRESS, "重新处置"),
            ],
            DISEASE_STATUS_ARCHIVED: [
                (DISEASE_STATUS_PENDING, "重新打开"),
            ],
            DISEASE_STATUS_REJECTED: [
                (DISEASE_STATUS_IN_PROGRESS, "重新处置"),
                (DISEASE_STATUS_ARCHIVED, "归档"),
            ],
        }

        return action_map.get(current_status, [])

    def get_workflow_steps(self) -> List[Tuple[str, str]]:
        return [
            (DISEASE_STATUS_DISCOVERED, "已发现"),
            (DISEASE_STATUS_PENDING, "待派单"),
            (DISEASE_STATUS_ASSIGNED, "已派单"),
            (DISEASE_STATUS_IN_PROGRESS, "处置中"),
            (DISEASE_STATUS_COMPLETED, "待验收"),
            (DISEASE_STATUS_ACCEPTED, "已验收"),
            (DISEASE_STATUS_REVIEWED, "已复查"),
            (DISEASE_STATUS_ARCHIVED, "已归档"),
        ]
