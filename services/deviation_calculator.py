from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from database import DatabaseManager, Component, MeasurementRecord


@dataclass
class DeviationItem:
    component_id: int
    component_code: str
    component_name: str
    design_value: float
    measured_value: float
    deviation: float
    deviation_percent: float
    threshold: float
    is_abnormal: bool


@dataclass
class ComponentDeviation:
    component: Component
    length_deviation: Optional[DeviationItem]
    width_deviation: Optional[DeviationItem]
    angle_deviation: Optional[DeviationItem]
    latest_record: Optional[MeasurementRecord]
    is_abnormal: bool
    recheck_needed: bool


class DeviationCalculator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def _calc_deviation(self, design: float, measured: float, threshold: float,
                        component_id: int, component_code: str, component_name: str,
                        dim_type: str) -> DeviationItem:
        deviation = measured - design
        if design != 0:
            deviation_percent = abs(deviation) / abs(design) * 100
        else:
            deviation_percent = 0.0
        is_abnormal = abs(deviation) > threshold
        return DeviationItem(
            component_id=component_id,
            component_code=component_code,
            component_name=component_name,
            design_value=design,
            measured_value=measured,
            deviation=deviation,
            deviation_percent=deviation_percent,
            threshold=threshold,
            is_abnormal=is_abnormal
        )

    def calculate_component_deviation(self, component: Component) -> ComponentDeviation:
        latest_record = self.db.get_latest_measurement(component.id)

        if latest_record is None:
            return ComponentDeviation(
                component=component,
                length_deviation=None,
                width_deviation=None,
                angle_deviation=None,
                latest_record=None,
                is_abnormal=False,
                recheck_needed=False
            )

        threshold = component.deviation_threshold

        length_dev = self._calc_deviation(
            component.design_length, latest_record.length, threshold,
            component.id, component.code, component.name, "length"
        )
        width_dev = self._calc_deviation(
            component.design_width, latest_record.width, threshold,
            component.id, component.code, component.name, "width"
        )
        angle_dev = self._calc_deviation(
            component.design_angle, latest_record.angle, threshold,
            component.id, component.code, component.name, "angle"
        )

        is_abnormal = length_dev.is_abnormal or width_dev.is_abnormal or angle_dev.is_abnormal
        recheck_needed = latest_record.is_recheck

        return ComponentDeviation(
            component=component,
            length_deviation=length_dev,
            width_deviation=width_dev,
            angle_deviation=angle_dev,
            latest_record=latest_record,
            is_abnormal=is_abnormal,
            recheck_needed=recheck_needed
        )

    def calculate_building_deviations(self, building_id: int) -> List[ComponentDeviation]:
        components = self.db.get_components_by_building(building_id)
        results = []
        for comp in components:
            results.append(self.calculate_component_deviation(comp))
        return results

    def get_abnormal_components(self, building_id: int) -> List[ComponentDeviation]:
        all_devs = self.calculate_building_deviations(building_id)
        return [d for d in all_devs if d.is_abnormal]

    def get_deviation_statistics(self, building_id: int) -> Dict:
        all_devs = self.calculate_building_deviations(building_id)
        total = len(all_devs)
        abnormal = sum(1 for d in all_devs if d.is_abnormal)
        normal = total - abnormal
        has_data = sum(1 for d in all_devs if d.latest_record is not None)
        no_data = total - has_data

        length_devs = [d.length_deviation for d in all_devs if d.length_deviation]
        width_devs = [d.width_deviation for d in all_devs if d.width_deviation]
        angle_devs = [d.angle_deviation for d in all_devs if d.angle_deviation]

        def stats(items):
            if not items:
                return {"min": 0, "max": 0, "avg": 0, "avg_percent": 0}
            devs = [abs(x.deviation) for x in items]
            percents = [x.deviation_percent for x in items]
            return {
                "min": min(devs),
                "max": max(devs),
                "avg": sum(devs) / len(devs),
                "avg_percent": sum(percents) / len(percents)
            }

        return {
            "total_components": total,
            "abnormal_count": abnormal,
            "normal_count": normal,
            "has_data_count": has_data,
            "no_data_count": no_data,
            "length_stats": stats(length_devs),
            "width_stats": stats(width_devs),
            "angle_stats": stats(angle_devs)
        }

    def mark_abnormal_for_recheck(self, building_id: int, remark: str = "偏差超过阈值，需复测") -> int:
        abnormal_devs = self.get_abnormal_components(building_id)
        count = 0
        for dev in abnormal_devs:
            if dev.latest_record and not dev.recheck_needed:
                self.db.mark_for_recheck(dev.latest_record.id, remark)
                count += 1
        return count
