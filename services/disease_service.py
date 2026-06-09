from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from database import (
    DatabaseManager, DiseaseRecord, DiseaseTreatment, DiseaseStats,
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
    DISEASE_STATUSES,
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


class DiseaseService:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.deviation_calc = DeviationCalculator(db_manager)

    def assess_risk(self, disease: DiseaseRecord) -> Tuple[str, str]:
        """
        综合评估病害风险等级和优先级
        考虑因素：病害严重程度、尺寸大小、构件偏差情况
        """
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
        """
        根据病害类型、严重程度、尺寸偏差等因素生成修缮建议
        """
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

    def create_disease_with_suggestion(self, disease: DiseaseRecord) -> DiseaseRecord:
        """
        创建病害记录并自动生成修缮建议
        """
        final_severity, final_priority = self.assess_risk(disease)
        disease.severity = final_severity
        disease.priority = final_priority

        suggestion = self.generate_repair_suggestion(disease)
        disease.repair_suggestion = suggestion.suggestion
        disease.repair_method = suggestion.method
        disease.estimated_cost = suggestion.estimated_cost

        disease_id = self.db.add_disease_record(disease)
        disease.id = disease_id
        return disease

    def update_disease_status(self, disease_id: int, status: str,
                              handler: str = None, remark: str = None) -> bool:
        """
        更新病害状态
        """
        disease = self.db.get_disease_record(disease_id)
        if not disease:
            return False

        disease.status = status
        if handler:
            disease.handler = handler
        if remark:
            disease.remark = remark

        if status == DISEASE_STATUS_COMPLETED and not disease.complete_date:
            disease.complete_date = datetime.now().strftime("%Y-%m-%d")

        return self.db.update_disease_record(disease)

    def add_treatment_record(self, treatment: DiseaseTreatment) -> int:
        """
        添加处置记录
        """
        return self.db.add_disease_treatment(treatment)

    def get_disease_ledger(self, building_id: int,
                          status: str = None,
                          disease_type: str = None,
                          severity: str = None) -> List[DiseaseRecord]:
        """
        获取病害台账
        """
        return self.db.get_diseases_by_building(building_id, status, disease_type, severity)

    def get_progress_summary(self, building_id: int) -> Dict[str, any]:
        """
        获取处置进度汇总
        """
        stats = self.db.get_disease_statistics(building_id)

        completion_rate = 0.0
        if stats.total_count > 0:
            completion_rate = (stats.completed_count + stats.reviewed_count) / stats.total_count * 100

        pending_urgent = 0
        diseases = self.db.get_diseases_by_building(building_id)
        for d in diseases:
            if d.status in [DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS] and \
               d.priority == PRIORITY_URGENT:
                pending_urgent += 1

        return {
            "stats": stats,
            "completion_rate": completion_rate,
            "pending_urgent": pending_urgent,
        }

    def batch_generate_all_suggestions(self, building_id: int) -> int:
        """
        为建筑所有病害重新生成修缮建议
        """
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
