import os
from datetime import datetime
from typing import List, Dict

from database import DatabaseManager, Building
from services.deviation_calculator import DeviationCalculator, ComponentDeviation


class ReportGenerator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.calculator = DeviationCalculator(db_manager)

    def generate_text_report(self, building_id: int) -> str:
        building = self.db.get_building(building_id)
        if not building:
            return "建筑不存在"

        deviations = self.calculator.calculate_building_deviations(building_id)
        stats = self.calculator.get_deviation_statistics(building_id)
        abnormal_list = self.calculator.get_abnormal_components(building_id)

        lines = []
        lines.append("=" * 60)
        lines.append("古建筑木构件尺寸偏差检测报告")
        lines.append("=" * 60)
        lines.append(f"建筑名称：{building.name}")
        lines.append(f"建筑编号：{building.code}")
        lines.append(f"建筑位置：{building.location}")
        lines.append(f"报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("-" * 60)
        lines.append("一、总体统计")
        lines.append("-" * 60)
        lines.append(f"构件总数：{stats['total_components']} 件")
        lines.append(f"已检测构件：{stats['has_data_count']} 件")
        lines.append(f"未检测构件：{stats['no_data_count']} 件")
        lines.append(f"合格构件：{stats['normal_count']} 件")
        lines.append(f"异常构件：{stats['abnormal_count']} 件")
        if stats['total_components'] > 0:
            lines.append(f"合格率：{stats['normal_count'] / stats['total_components'] * 100:.1f}%")
        lines.append("")

        lines.append("-" * 60)
        lines.append("二、偏差统计")
        lines.append("-" * 60)
        len_stat = stats['length_stats']
        lines.append(f"长度偏差 - 最小:{len_stat['min']:.2f}  最大:{len_stat['max']:.2f}  平均:{len_stat['avg']:.2f}")
        wid_stat = stats['width_stats']
        lines.append(f"宽度偏差 - 最小:{wid_stat['min']:.2f}  最大:{wid_stat['max']:.2f}  平均:{wid_stat['avg']:.2f}")
        ang_stat = stats['angle_stats']
        lines.append(f"角度偏差 - 最小:{ang_stat['min']:.2f}  最大:{ang_stat['max']:.2f}  平均:{ang_stat['avg']:.2f}")
        lines.append("")

        lines.append("-" * 60)
        lines.append("三、异常构件明细")
        lines.append("-" * 60)
        if abnormal_list:
            for i, dev in enumerate(abnormal_list, 1):
                lines.append(f"{i}. 构件编号：{dev.component.code}")
                lines.append(f"   构件名称：{dev.component.name or '-'}")
                lines.append(f"   构件类型：{dev.component.component_type or '-'}")
                if dev.length_deviation and dev.length_deviation.is_abnormal:
                    lines.append(f"   长度偏差：设计值 {dev.length_deviation.design_value:.2f}，"
                                 f"实测值 {dev.length_deviation.measured_value:.2f}，"
                                 f"偏差 {dev.length_deviation.deviation:+.2f} "
                                 f"({dev.length_deviation.deviation_percent:.1f}%) [异常]")
                if dev.width_deviation and dev.width_deviation.is_abnormal:
                    lines.append(f"   宽度偏差：设计值 {dev.width_deviation.design_value:.2f}，"
                                 f"实测值 {dev.width_deviation.measured_value:.2f}，"
                                 f"偏差 {dev.width_deviation.deviation:+.2f} "
                                 f"({dev.width_deviation.deviation_percent:.1f}%) [异常]")
                if dev.angle_deviation and dev.angle_deviation.is_abnormal:
                    lines.append(f"   角度偏差：设计值 {dev.angle_deviation.design_value:.2f}°，"
                                 f"实测值 {dev.angle_deviation.measured_value:.2f}°，"
                                 f"偏差 {dev.angle_deviation.deviation:+.2f}° "
                                 f"({dev.angle_deviation.deviation_percent:.1f}%) [异常]")
                lines.append("")
        else:
            lines.append("无异常构件")
            lines.append("")

        lines.append("-" * 60)
        lines.append("四、全构件检测明细")
        lines.append("-" * 60)
        lines.append(f"{'序号':<4} {'构件编号':<12} {'构件名称':<12} {'长度偏差':<12} {'宽度偏差':<12} {'角度偏差':<12} {'状态':<6}")
        lines.append("-" * 72)
        for i, dev in enumerate(deviations, 1):
            ld = f"{dev.length_deviation.deviation:+.2f}" if dev.length_deviation else "-"
            wd = f"{dev.width_deviation.deviation:+.2f}" if dev.width_deviation else "-"
            ad = f"{dev.angle_deviation.deviation:+.2f}°" if dev.angle_deviation else "-"
            status = "异常" if dev.is_abnormal else "正常"
            if not dev.latest_record:
                status = "未测"
            lines.append(f"{i:<4} {dev.component.code:<12} {dev.component.name or '-':<12} "
                         f"{ld:<12} {wd:<12} {ad:<12} {status:<6}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("报告结束")
        lines.append("=" * 60)

        return "\n".join(lines)

    def save_report_to_file(self, building_id: int, file_path: str) -> bool:
        try:
            report_text = self.generate_text_report(building_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            return True
        except Exception as e:
            print(f"保存报告失败：{e}")
            return False
