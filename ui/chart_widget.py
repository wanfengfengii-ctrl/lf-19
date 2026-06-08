import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Polygon
import matplotlib.pyplot as plt

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt

from typing import List, Optional

from database import Component, MeasurementRecord
from services.deviation_calculator import ComponentDeviation


plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MplWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = MplCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    @property
    def figure(self):
        return self.canvas.fig

    def clear(self):
        self.figure.clear()
        self.canvas.draw_idle()


class SectionChart(MplWidget):
    def plot_component_section(self, component: Component,
                               measurement: Optional[MeasurementRecord] = None):
        self.clear()
        ax = self.figure.add_subplot(111)

        design_w = component.design_width
        design_h = component.design_length
        angle = component.design_angle

        if design_w <= 0:
            design_w = 100
        if design_h <= 0:
            design_h = 200

        ax.set_xlim(-10, design_w + 20)
        ax.set_ylim(-10, design_h + 20)
        ax.set_aspect('equal', adjustable='box')

        rect = Rectangle((0, 0), design_w, design_h,
                         fill=False, edgecolor='blue', linewidth=2,
                         linestyle='--', label='设计尺寸')
        ax.add_patch(rect)

        if measurement:
            meas_w = measurement.width
            meas_h = measurement.length

            offset_x = (design_w - meas_w) / 2
            offset_y = (design_h - meas_h) / 2

            meas_rect = Rectangle((offset_x, offset_y), meas_w, meas_h,
                                  fill=True, alpha=0.3,
                                  edgecolor='red', linewidth=2,
                                  facecolor='red', label='实测尺寸')
            ax.add_patch(meas_rect)

        ax.set_xlabel('宽度 (mm)')
        ax.set_ylabel('长度 (mm)')
        ax.set_title(f'构件 {component.code} 剖面示意图')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        info_text = f"设计：{design_w:.1f} × {design_h:.1f} mm\n角度：{angle:.1f}°"
        if measurement:
            info_text += f"\n实测：{measurement.width:.1f} × {measurement.length:.1f} mm"
            info_text += f"\n测量时间：{measurement.measure_time}"
            info_text += f"\n版本：v{measurement.version}"

        ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
                verticalalignment='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        self.canvas.draw_idle()


class DeviationDistributionChart(MplWidget):
    def plot_deviation_distribution(self, deviations: List[ComponentDeviation],
                                    dim_type: str = "length"):
        self.clear()
        ax = self.figure.add_subplot(111)

        dim_map = {
            "length": ("length_deviation", "长度偏差 (mm)"),
            "width": ("width_deviation", "宽度偏差 (mm)"),
            "angle": ("angle_deviation", "角度偏差 (°)")
        }
        attr_name, ylabel = dim_map.get(dim_type, dim_map["length"])

        codes = []
        dev_values = []
        colors = []
        threshold = 0

        for dev in deviations:
            dim_dev = getattr(dev, attr_name)
            if dim_dev is None:
                continue
            codes.append(dev.component.code)
            dev_values.append(dim_dev.deviation)
            threshold = dim_dev.threshold
            if dim_dev.is_abnormal:
                colors.append('red')
            else:
                colors.append('green')

        if not codes:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    transform=ax.transAxes, fontsize=14, color='gray')
            ax.set_title('偏差分布图')
            self.canvas.draw_idle()
            return

        x = range(len(codes))

        bars = ax.bar(x, dev_values, color=colors, alpha=0.7)

        ax.axhline(y=threshold, color='orange', linestyle='--',
                   linewidth=1.5, label=f'正阈值 ({threshold})')
        ax.axhline(y=-threshold, color='orange', linestyle='--',
                   linewidth=1.5, label=f'负阈值 (-{threshold})')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)

        ax.set_xlabel('构件编号')
        ax.set_ylabel(ylabel)
        ax.set_title('构件尺寸偏差分布图')

        ax.set_xticks(x)
        ax.set_xticklabels(codes, rotation=45, ha='right', fontsize=8)

        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        for bar, val in zip(bars, dev_values):
            height = bar.get_height()
            y_pos = height + (0.5 if height >= 0 else -1.5)
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos,
                    f'{val:+.1f}', ha='center', va='bottom', fontsize=7)

        self.figure.tight_layout()
        self.canvas.draw_idle()


class DeviationStatsChart(MplWidget):
    def plot_stats_pie(self, stats: dict):
        self.clear()

        ax = self.figure.add_subplot(121)

        labels = ['合格', '异常', '未检测']
        sizes = [stats['normal_count'], stats['abnormal_count'], stats['no_data_count']]
        colors = ['#2ecc71', '#e74c3c', '#95a5a6']

        total = sum(sizes)
        if total == 0:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center',
                    transform=ax.transAxes, fontsize=12, color='gray')
        else:
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 10}
            )
            ax.set_title('构件状态分布')

        ax2 = self.figure.add_subplot(122)

        categories = ['长度', '宽度', '角度']
        avg_devs = [
            stats['length_stats']['avg'],
            stats['width_stats']['avg'],
            stats['angle_stats']['avg']
        ]
        max_devs = [
            stats['length_stats']['max'],
            stats['width_stats']['max'],
            stats['angle_stats']['max']
        ]

        x = range(len(categories))
        width = 0.35

        ax2.bar([i - width/2 for i in x], avg_devs, width,
                label='平均偏差', color='#3498db', alpha=0.8)
        ax2.bar([i + width/2 for i in x], max_devs, width,
                label='最大偏差', color='#e67e22', alpha=0.8)

        ax2.set_xlabel('尺寸类型')
        ax2.set_ylabel('偏差值')
        ax2.set_title('各维度偏差统计')
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        self.figure.tight_layout()
        self.canvas.draw_idle()
