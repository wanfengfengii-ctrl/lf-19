from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from database import DatabaseManager, Component, MeasurementRecord


class FilterStatus(Enum):
    ALL = "all"
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    RECHECK_NEEDED = "recheck_needed"
    NO_DATA = "no_data"


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


@dataclass
class DashboardStats:
    total_components: int
    has_data_count: int
    no_data_count: int
    normal_count: int
    abnormal_count: int
    recheck_pending: int
    recheck_in_progress: int
    recheck_completed: int
    pass_rate: float
    length_stats: Dict
    width_stats: Dict
    angle_stats: Dict
    abnormal_by_type: Dict[str, int]


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

    def filter_deviations(self, building_id: int,
                          status_filter: FilterStatus = FilterStatus.ALL,
                          component_type: str = "",
                          search_keyword: str = "") -> List[ComponentDeviation]:
        all_devs = self.calculate_building_deviations(building_id)
        results = []

        for dev in all_devs:
            has_data = dev.latest_record is not None

            if status_filter == FilterStatus.NORMAL and (dev.is_abnormal or not has_data):
                continue
            if status_filter == FilterStatus.ABNORMAL and (not dev.is_abnormal or not has_data):
                continue
            if status_filter == FilterStatus.RECHECK_NEEDED and (not dev.recheck_needed or not has_data):
                continue
            if status_filter == FilterStatus.NO_DATA and has_data:
                continue

            if component_type and dev.component.component_type != component_type:
                continue

            if search_keyword:
                keyword = search_keyword.lower()
                if (keyword not in dev.component.code.lower() and
                        keyword not in dev.component.name.lower()):
                    continue

            results.append(dev)

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

    def get_dashboard_stats(self, building_id: int) -> DashboardStats:
        stats = self.get_deviation_statistics(building_id)
        recheck_stats = self.db.get_recheck_statistics(building_id)

        abnormal_by_type = {}
        abnormal_list = self.get_abnormal_components(building_id)
        for dev in abnormal_list:
            ctype = dev.component.component_type or "未分类"
            abnormal_by_type[ctype] = abnormal_by_type.get(ctype, 0) + 1

        pass_rate = 0.0
        if stats["total_components"] > 0:
            pass_rate = stats["normal_count"] / stats["total_components"] * 100

        return DashboardStats(
            total_components=stats["total_components"],
            has_data_count=stats["has_data_count"],
            no_data_count=stats["no_data_count"],
            normal_count=stats["normal_count"],
            abnormal_count=stats["abnormal_count"],
            recheck_pending=recheck_stats["pending"],
            recheck_in_progress=recheck_stats["in_progress"],
            recheck_completed=recheck_stats["completed"],
            pass_rate=pass_rate,
            length_stats=stats["length_stats"],
            width_stats=stats["width_stats"],
            angle_stats=stats["angle_stats"],
            abnormal_by_type=abnormal_by_type
        )

    def get_component_types(self, building_id: int) -> List[str]:
        components = self.db.get_components_by_building(building_id)
        types = set()
        for comp in components:
            if comp.component_type:
                types.add(comp.component_type)
        return sorted(list(types))

    def mark_abnormal_for_recheck(self, building_id: int, remark: str = "偏差超过阈值，需复测") -> int:
        abnormal_devs = self.get_abnormal_components(building_id)
        count = 0
        for dev in abnormal_devs:
            if dev.latest_record and not dev.recheck_needed:
                self.db.mark_for_recheck(dev.latest_record.id, remark)
                count += 1
        return count

    def get_top_abnormal_components(self, building_id: int,
                                     limit: int = 10,
                                     dim_type: str = "length") -> List[ComponentDeviation]:
        all_devs = self.calculate_building_deviations(building_id)
        abnormal = [d for d in all_devs if d.is_abnormal]

        def get_deviation_value(dev):
            if dim_type == "length" and dev.length_deviation:
                return abs(dev.length_deviation.deviation)
            elif dim_type == "width" and dev.width_deviation:
                return abs(dev.width_deviation.deviation)
            elif dim_type == "angle" and dev.angle_deviation:
                return abs(dev.angle_deviation.deviation)
            return 0

        abnormal.sort(key=get_deviation_value, reverse=True)
        return abnormal[:limit]
