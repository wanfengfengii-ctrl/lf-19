import sys
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QInputDialog, QFileDialog, QComboBox,
    QSplitter, QGroupBox, QFormLayout, QTextEdit, QDoubleSpinBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QBrush, QColor

from database import DatabaseManager, Building, Component, MortiseTenon, MeasurementRecord
from services import CsvImporter, DeviationCalculator, ReportGenerator
from services.deviation_calculator import ComponentDeviation
from .chart_widget import SectionChart, DeviationDistributionChart, DeviationStatsChart


class BuildingDialog(QDialog):
    def __init__(self, parent=None, building: Building = None):
        super().__init__(parent)
        self.setWindowTitle("建筑信息" if building else "新增建筑")
        self.setMinimumWidth(400)
        self.building = building

        layout = QVBoxLayout()
        form = QFormLayout()

        self.name_edit = QLineEdit()
        self.code_edit = QLineEdit()
        self.location_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)

        form.addRow("建筑名称 *", self.name_edit)
        form.addRow("建筑编号 *", self.code_edit)
        form.addRow("所在位置", self.location_edit)
        form.addRow("描述", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        if building:
            self.name_edit.setText(building.name)
            self.code_edit.setText(building.code)
            self.location_edit.setText(building.location)
            self.desc_edit.setPlainText(building.description)

    def get_data(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "code": self.code_edit.text().strip(),
            "location": self.location_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip()
        }

    def accept(self):
        data = self.get_data()
        if not data["name"]:
            QMessageBox.warning(self, "提示", "请输入建筑名称")
            return
        if not data["code"]:
            QMessageBox.warning(self, "提示", "请输入建筑编号")
            return
        super().accept()


class ComponentDialog(QDialog):
    def __init__(self, parent=None, component: Component = None):
        super().__init__(parent)
        self.setWindowTitle("构件信息" if component else "新增构件")
        self.setMinimumWidth(420)
        self.component = component

        layout = QVBoxLayout()
        form = QFormLayout()

        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        self.type_combo.addItems(["梁", "柱", "枋", "檩", "椽", "斗拱", "其他"])

        self.design_length = QDoubleSpinBox()
        self.design_length.setRange(0, 100000)
        self.design_length.setDecimals(2)
        self.design_length.setSuffix(" mm")

        self.design_width = QDoubleSpinBox()
        self.design_width.setRange(0, 100000)
        self.design_width.setDecimals(2)
        self.design_width.setSuffix(" mm")

        self.design_angle = QDoubleSpinBox()
        self.design_angle.setRange(0, 180)
        self.design_angle.setDecimals(2)
        self.design_angle.setSuffix(" °")

        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0, 1000)
        self.threshold.setDecimals(2)
        self.threshold.setValue(5.0)
        self.threshold.setSuffix(" mm")

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(60)

        form.addRow("构件编号 *", self.code_edit)
        form.addRow("构件名称", self.name_edit)
        form.addRow("构件类型", self.type_combo)
        form.addRow("设计长度", self.design_length)
        form.addRow("设计宽度", self.design_width)
        form.addRow("设计角度", self.design_angle)
        form.addRow("偏差阈值", self.threshold)
        form.addRow("描述", self.desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        if component:
            self.code_edit.setText(component.code)
            self.name_edit.setText(component.name)
            idx = self.type_combo.findText(component.component_type)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)
            else:
                self.type_combo.setEditText(component.component_type)
            self.design_length.setValue(component.design_length)
            self.design_width.setValue(component.design_width)
            self.design_angle.setValue(component.design_angle)
            self.threshold.setValue(component.deviation_threshold)
            self.desc_edit.setPlainText(component.description)

    def get_data(self) -> dict:
        return {
            "code": self.code_edit.text().strip(),
            "name": self.name_edit.text().strip(),
            "component_type": self.type_combo.currentText().strip(),
            "design_length": self.design_length.value(),
            "design_width": self.design_width.value(),
            "design_angle": self.design_angle.value(),
            "deviation_threshold": self.threshold.value(),
            "description": self.desc_edit.toPlainText().strip()
        }

    def accept(self):
        data = self.get_data()
        if not data["code"]:
            QMessageBox.warning(self, "提示", "请输入构件编号")
            return
        if data["design_length"] <= 0:
            QMessageBox.warning(self, "提示", "设计长度必须大于0")
            return
        if data["design_width"] <= 0:
            QMessageBox.warning(self, "提示", "设计宽度必须大于0")
            return
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("古建筑木构件测绘数据管理系统")
        self.resize(1200, 800)

        self.db = DatabaseManager()
        self.csv_importer = CsvImporter(self.db)
        self.deviation_calc = DeviationCalculator(self.db)
        self.report_gen = ReportGenerator(self.db)

        self.current_building_id = None
        self.current_component_id = None

        self._init_ui()
        self._refresh_building_list()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        left_panel = QWidget()
        left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(left_panel)

        left_layout.addWidget(QLabel("建筑列表"))
        self.building_list = QListWidget()
        self.building_list.currentItemChanged.connect(self._on_building_selected)
        left_layout.addWidget(self.building_list, 1)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("新增")
        btn_add.clicked.connect(self._add_building)
        btn_edit = QPushButton("编辑")
        btn_edit.clicked.connect(self._edit_building)
        btn_del = QPushButton("删除")
        btn_del.clicked.connect(self._delete_building)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_del)
        left_layout.addLayout(btn_layout)

        main_layout.addWidget(left_panel)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)

        self._init_component_tab()
        self._init_mortise_tab()
        self._init_import_tab()
        self._init_analysis_tab()
        self._init_report_tab()

        self.statusBar().showMessage("就绪")

    def _init_component_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("构件列表"))
        btn_add_comp = QPushButton("新增构件")
        btn_add_comp.clicked.connect(self._add_component)
        btn_edit_comp = QPushButton("编辑构件")
        btn_edit_comp.clicked.connect(self._edit_component)
        btn_del_comp = QPushButton("删除构件")
        btn_del_comp.clicked.connect(self._delete_component)
        top_bar.addStretch()
        top_bar.addWidget(btn_add_comp)
        top_bar.addWidget(btn_edit_comp)
        top_bar.addWidget(btn_del_comp)
        layout.addLayout(top_bar)

        self.component_table = QTableWidget()
        self.component_table.setColumnCount(8)
        self.component_table.setHorizontalHeaderLabels(
            ["编号", "名称", "类型", "设计长度", "设计宽度", "设计角度", "偏差阈值", "描述"]
        )
        self.component_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.component_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.component_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.component_table.itemSelectionChanged.connect(self._on_component_selected)
        layout.addWidget(self.component_table, 1)

        bottom_group = QGroupBox("构件测量历史")
        bottom_layout = QVBoxLayout(bottom_group)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(
            ["版本", "长度", "宽度", "角度", "测量时间", "是否复测"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        bottom_layout.addWidget(self.history_table)
        layout.addWidget(bottom_group)

        self.tabs.addTab(tab, "构件管理")

    def _init_mortise_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("榫卯关系列表"))
        btn_add = QPushButton("添加榫卯关系")
        btn_add.clicked.connect(self._add_mortise_tenon)
        btn_del = QPushButton("删除")
        btn_del.clicked.connect(self._delete_mortise_tenon)
        top_bar.addStretch()
        top_bar.addWidget(btn_add)
        top_bar.addWidget(btn_del)
        layout.addLayout(top_bar)

        self.mortise_table = QTableWidget()
        self.mortise_table.setColumnCount(5)
        self.mortise_table.setHorizontalHeaderLabels(
            ["卯构件", "榫构件", "连接类型", "描述", "创建时间"]
        )
        self.mortise_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.mortise_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.mortise_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.mortise_table, 1)

        self.tabs.addTab(tab, "榫卯关系")

    def _init_import_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        file_group = QGroupBox("CSV文件导入")
        file_layout = QVBoxLayout(file_group)

        row1 = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择CSV文件...")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._browse_csv)
        row1.addWidget(self.file_path_edit, 1)
        row1.addWidget(btn_browse)
        file_layout.addLayout(row1)

        row2 = QHBoxLayout()
        btn_preview = QPushButton("预览数据")
        btn_preview.clicked.connect(self._preview_csv)
        btn_import = QPushButton("导入数据")
        btn_import.clicked.connect(self._import_csv)
        row2.addWidget(btn_preview)
        row2.addWidget(btn_import)
        row2.addStretch()
        file_layout.addLayout(row2)

        layout.addWidget(file_group)

        splitter = QSplitter(Qt.Vertical)

        preview_group = QGroupBox("数据预览")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_table = QTableWidget()
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_layout.addWidget(self.preview_table)
        splitter.addWidget(preview_group)

        error_group = QGroupBox("错误与警告")
        error_layout = QVBoxLayout(error_group)
        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setStyleSheet("color: red;")
        error_layout.addWidget(self.error_text)
        splitter.addWidget(error_group)

        splitter.setSizes([300, 200])
        layout.addWidget(splitter, 1)

        self.tabs.addTab(tab, "数据导入")

    def _init_analysis_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)

        stats_group = QGroupBox("统计概览")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("请选择建筑")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        left_layout.addWidget(stats_group)

        list_group = QGroupBox("构件偏差列表")
        list_layout = QVBoxLayout(list_group)
        self.deviation_list = QListWidget()
        self.deviation_list.currentItemChanged.connect(self._on_deviation_selected)
        list_layout.addWidget(self.deviation_list)
        left_layout.addWidget(list_group, 1)

        btn_layout = QHBoxLayout()
        btn_mark = QPushButton("标记异常复测")
        btn_mark.clicked.connect(self._mark_abnormal_recheck)
        btn_layout.addWidget(btn_mark)
        left_layout.addLayout(btn_layout)

        layout.addWidget(left_panel)

        right_panel = QTabWidget()

        chart1_tab = QWidget()
        chart1_layout = QVBoxLayout(chart1_tab)
        self.section_chart = SectionChart()
        chart1_layout.addWidget(self.section_chart)
        right_panel.addTab(chart1_tab, "构件剖面图")

        chart2_tab = QWidget()
        chart2_layout = QVBoxLayout(chart2_tab)

        chart2_top = QHBoxLayout()
        chart2_top.addWidget(QLabel("显示维度："))
        self.dim_combo = QComboBox()
        self.dim_combo.addItems(["长度", "宽度", "角度"])
        self.dim_combo.currentIndexChanged.connect(self._update_deviation_chart)
        chart2_top.addWidget(self.dim_combo)
        chart2_top.addStretch()
        chart2_layout.addLayout(chart2_top)

        self.deviation_chart = DeviationDistributionChart()
        chart2_layout.addWidget(self.deviation_chart, 1)
        right_panel.addTab(chart2_tab, "偏差分布图")

        chart3_tab = QWidget()
        chart3_layout = QVBoxLayout(chart3_tab)
        self.stats_chart = DeviationStatsChart()
        chart3_layout.addWidget(self.stats_chart)
        right_panel.addTab(chart3_tab, "统计图表")

        layout.addWidget(right_panel, 1)

        self.tabs.addTab(tab, "偏差分析")

    def _init_report_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        top_bar = QHBoxLayout()
        btn_generate = QPushButton("生成报告")
        btn_generate.clicked.connect(self._generate_report)
        btn_save = QPushButton("保存为文件")
        btn_save.clicked.connect(self._save_report)
        top_bar.addWidget(btn_generate)
        top_bar.addWidget(btn_save)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.report_text, 1)

        self.tabs.addTab(tab, "报告生成")

    def _refresh_building_list(self):
        self.building_list.clear()
        buildings = self.db.get_all_buildings()
        for b in buildings:
            item = QListWidgetItem(f"{b.name} ({b.code})")
            item.setData(Qt.UserRole, b.id)
            self.building_list.addItem(item)

        if buildings:
            self.building_list.setCurrentRow(0)
        else:
            self.current_building_id = None
            self._clear_all_data()

    def _on_building_selected(self, current, previous):
        if current is None:
            self.current_building_id = None
            self._clear_all_data()
            return
        self.current_building_id = current.data(Qt.UserRole)
        self._refresh_component_table()
        self._refresh_mortise_table()
        self._refresh_deviation_analysis()

    def _clear_all_data(self):
        self.component_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.mortise_table.setRowCount(0)
        self.preview_table.setRowCount(0)
        self.error_text.clear()
        self.deviation_list.clear()
        self.stats_label.setText("请选择建筑")
        self.section_chart.clear()
        self.deviation_chart.clear()
        self.stats_chart.clear()
        self.report_text.clear()

    def _add_building(self):
        dlg = BuildingDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                building = Building(
                    id=None, name=data["name"], code=data["code"],
                    location=data["location"], description=data["description"]
                )
                bid = self.db.add_building(building)
                self._refresh_building_list()
                self.statusBar().showMessage(f"建筑添加成功，ID：{bid}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def _edit_building(self):
        item = self.building_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        bid = item.data(Qt.UserRole)
        building = self.db.get_building(bid)
        if not building:
            return
        dlg = BuildingDialog(self, building)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                building.name = data["name"]
                building.code = data["code"]
                building.location = data["location"]
                building.description = data["description"]
                self.db.update_building(building)
                self._refresh_building_list()
                self.statusBar().showMessage("建筑信息已更新", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def _delete_building(self):
        item = self.building_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        bid = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, "确认删除",
                                     "确定要删除该建筑及其所有相关数据吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_building(bid):
                self._refresh_building_list()
                self.statusBar().showMessage("建筑已删除", 3000)
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def _refresh_component_table(self):
        if not self.current_building_id:
            self.component_table.setRowCount(0)
            return
        components = self.db.get_components_by_building(self.current_building_id)
        self.component_table.setRowCount(len(components))
        for row, comp in enumerate(components):
            self.component_table.setItem(row, 0, QTableWidgetItem(comp.code))
            self.component_table.setItem(row, 1, QTableWidgetItem(comp.name))
            self.component_table.setItem(row, 2, QTableWidgetItem(comp.component_type))
            self.component_table.setItem(row, 3, QTableWidgetItem(f"{comp.design_length:.2f}"))
            self.component_table.setItem(row, 4, QTableWidgetItem(f"{comp.design_width:.2f}"))
            self.component_table.setItem(row, 5, QTableWidgetItem(f"{comp.design_angle:.2f}"))
            self.component_table.setItem(row, 6, QTableWidgetItem(f"{comp.deviation_threshold:.2f}"))
            self.component_table.setItem(row, 7, QTableWidgetItem(comp.description))

            item = self.component_table.item(row, 0)
            item.setData(Qt.UserRole, comp.id)

    def _on_component_selected(self):
        items = self.component_table.selectedItems()
        if not items:
            self.current_component_id = None
            return
        row = items[0].row()
        item = self.component_table.item(row, 0)
        self.current_component_id = item.data(Qt.UserRole)
        self._refresh_history_table()

    def _refresh_history_table(self):
        if not self.current_component_id:
            self.history_table.setRowCount(0)
            return
        records = self.db.get_measurements_by_component(self.current_component_id)
        self.history_table.setRowCount(len(records))
        for row, rec in enumerate(records):
            self.history_table.setItem(row, 0, QTableWidgetItem(f"v{rec.version}"))
            self.history_table.setItem(row, 1, QTableWidgetItem(f"{rec.length:.2f}"))
            self.history_table.setItem(row, 2, QTableWidgetItem(f"{rec.width:.2f}"))
            self.history_table.setItem(row, 3, QTableWidgetItem(f"{rec.angle:.2f}"))
            self.history_table.setItem(row, 4, QTableWidgetItem(rec.measure_time))
            self.history_table.setItem(row, 5, QTableWidgetItem("是" if rec.is_recheck else "否"))

    def _add_component(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        dlg = ComponentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                comp = Component(
                    id=None, building_id=self.current_building_id,
                    code=data["code"], name=data["name"],
                    component_type=data["component_type"],
                    design_length=data["design_length"],
                    design_width=data["design_width"],
                    design_angle=data["design_angle"],
                    deviation_threshold=data["deviation_threshold"],
                    description=data["description"]
                )
                cid = self.db.add_component(comp)
                self._refresh_component_table()
                self._refresh_deviation_analysis()
                self.statusBar().showMessage(f"构件添加成功，ID：{cid}", 3000)
            except ValueError as e:
                QMessageBox.warning(self, "提示", str(e))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def _edit_component(self):
        if not self.current_component_id:
            QMessageBox.information(self, "提示", "请先选择一个构件")
            return
        comp = self.db.get_component(self.current_component_id)
        if not comp:
            return
        dlg = ComponentDialog(self, comp)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            try:
                comp.code = data["code"]
                comp.name = data["name"]
                comp.component_type = data["component_type"]
                comp.design_length = data["design_length"]
                comp.design_width = data["design_width"]
                comp.design_angle = data["design_angle"]
                comp.deviation_threshold = data["deviation_threshold"]
                comp.description = data["description"]
                self.db.update_component(comp)
                self._refresh_component_table()
                self._refresh_deviation_analysis()
                self.statusBar().showMessage("构件信息已更新", 3000)
            except ValueError as e:
                QMessageBox.warning(self, "提示", str(e))
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def _delete_component(self):
        if not self.current_component_id:
            QMessageBox.information(self, "提示", "请先选择一个构件")
            return
        reply = QMessageBox.question(self, "确认删除",
                                     "确定要删除该构件及其所有测量记录吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_component(self.current_component_id):
                self._refresh_component_table()
                self._refresh_deviation_analysis()
                self.current_component_id = None
                self.statusBar().showMessage("构件已删除", 3000)
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def _refresh_mortise_table(self):
        if not self.current_building_id:
            self.mortise_table.setRowCount(0)
            return
        mts = self.db.get_mortise_tenons_by_building(self.current_building_id)
        self.mortise_table.setRowCount(len(mts))
        for row, mt in enumerate(mts):
            self.mortise_table.setItem(row, 0, QTableWidgetItem(mt["mortise_code"]))
            self.mortise_table.setItem(row, 1, QTableWidgetItem(mt["tenon_code"]))
            self.mortise_table.setItem(row, 2, QTableWidgetItem(mt["joint_type"]))
            self.mortise_table.setItem(row, 3, QTableWidgetItem(mt["description"]))
            self.mortise_table.setItem(row, 4, QTableWidgetItem(mt["created_at"]))

            item = self.mortise_table.item(row, 0)
            item.setData(Qt.UserRole, mt["id"])

    def _add_mortise_tenon(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        components = self.db.get_components_by_building(self.current_building_id)
        if len(components) < 2:
            QMessageBox.information(self, "提示", "该建筑至少需要两个构件才能创建榫卯关系")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("添加榫卯关系")
        dlg.setMinimumWidth(350)
        layout = QVBoxLayout(dlg)
        form = QFormLayout()

        mortise_combo = QComboBox()
        tenon_combo = QComboBox()
        type_edit = QLineEdit()
        desc_edit = QLineEdit()

        for comp in components:
            mortise_combo.addItem(f"{comp.code} - {comp.name}", comp.id)
            tenon_combo.addItem(f"{comp.code} - {comp.name}", comp.id)

        if len(components) > 1:
            tenon_combo.setCurrentIndex(1)

        form.addRow("卯构件", mortise_combo)
        form.addRow("榫构件", tenon_combo)
        form.addRow("连接类型", type_edit)
        form.addRow("描述", desc_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() == QDialog.Accepted:
            mortise_id = mortise_combo.currentData()
            tenon_id = tenon_combo.currentData()
            if mortise_id == tenon_id:
                QMessageBox.warning(self, "提示", "卯构件和榫构件不能相同")
                return
            try:
                mt = MortiseTenon(
                    id=None, building_id=self.current_building_id,
                    mortise_component_id=mortise_id,
                    tenon_component_id=tenon_id,
                    joint_type=type_edit.text().strip(),
                    description=desc_edit.text().strip()
                )
                self.db.add_mortise_tenon(mt)
                self._refresh_mortise_table()
                self.statusBar().showMessage("榫卯关系已添加", 3000)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def _delete_mortise_tenon(self):
        items = self.mortise_table.selectedItems()
        if not items:
            QMessageBox.information(self, "提示", "请先选择一条记录")
            return
        row = items[0].row()
        item = self.mortise_table.item(row, 0)
        mt_id = item.data(Qt.UserRole)

        reply = QMessageBox.question(self, "确认删除", "确定要删除这条榫卯关系吗？",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_mortise_tenon(mt_id):
                self._refresh_mortise_table()
                self.statusBar().showMessage("榫卯关系已删除", 3000)
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def _browse_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择CSV文件", "", "CSV文件 (*.csv)")
        if file_path:
            self.file_path_edit.setText(file_path)

    def _preview_csv(self):
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, "提示", "请先选择CSV文件")
            return
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "提示", "文件不存在")
            return

        headers, rows, errors = self.csv_importer.preview_file(file_path, max_rows=20)

        if headers:
            self.preview_table.setColumnCount(len(headers))
            self.preview_table.setHorizontalHeaderLabels(headers)
            self.preview_table.setRowCount(len(rows))
            for row_idx, row_data in enumerate(rows):
                for col_idx, header in enumerate(headers):
                    self.preview_table.setItem(
                        row_idx, col_idx,
                        QTableWidgetItem(str(row_data.get(header, "")))
                    )
            self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        error_msg = "\n".join(errors) if errors else "预览成功，格式正确"
        self.error_text.setText(error_msg)

    def _import_csv(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.information(self, "提示", "请先选择CSV文件")
            return

        reply = QMessageBox.question(self, "确认导入",
                                     "确定要导入数据吗？\n重复测量数据将保留历史版本。",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        try:
            result = self.csv_importer.import_file(file_path, self.current_building_id)

            msg = f"导入完成！\n成功：{result.success_count} 条\n失败：{result.error_count} 条"
            if result.errors:
                self.error_text.setText("\n".join(result.errors))
                msg += "\n详细错误请查看下方列表"

            QMessageBox.information(self, "导入结果", msg)

            self._refresh_deviation_analysis()
            self._refresh_component_table()
            if self.current_component_id:
                self._refresh_history_table()
            self.statusBar().showMessage(
                f"导入完成：成功{result.success_count}条，失败{result.error_count}条", 5000
            )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")

    def _refresh_deviation_analysis(self):
        if not self.current_building_id:
            self.deviation_list.clear()
            self.stats_label.setText("请选择建筑")
            self.section_chart.clear()
            self.deviation_chart.clear()
            self.stats_chart.clear()
            return

        deviations = self.deviation_calc.calculate_building_deviations(self.current_building_id)
        stats = self.deviation_calc.get_deviation_statistics(self.current_building_id)

        self._all_deviations = deviations

        self.deviation_list.clear()
        for dev in deviations:
            text = dev.component.code
            if dev.latest_record is None:
                text += " (无数据)"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor("#888888")))
            elif dev.is_abnormal:
                text += " [异常]"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor("red")))
            else:
                text += " [正常]"
                item = QListWidgetItem(text)
                item.setForeground(QBrush(QColor("green")))
            item.setData(Qt.UserRole, dev)
            self.deviation_list.addItem(item)

        stats_text = (
            f"构件总数：{stats['total_components']}\n"
            f"已检测：{stats['has_data_count']}\n"
            f"合格：{stats['normal_count']}\n"
            f"异常：{stats['abnormal_count']}\n"
        )
        if stats['total_components'] > 0:
            rate = stats['normal_count'] / stats['total_components'] * 100
            stats_text += f"合格率：{rate:.1f}%"
        self.stats_label.setText(stats_text)

        self._update_deviation_chart()
        self.stats_chart.plot_stats_pie(stats)

        if deviations:
            self.deviation_list.setCurrentRow(0)

    def _update_deviation_chart(self):
        if not hasattr(self, '_all_deviations') or not self._all_deviations:
            return
        dim_map = {0: "length", 1: "width", 2: "angle"}
        dim_type = dim_map.get(self.dim_combo.currentIndex(), "length")
        self.deviation_chart.plot_deviation_distribution(self._all_deviations, dim_type)

    def _on_deviation_selected(self, current, previous):
        if current is None:
            self.section_chart.clear()
            return
        dev: ComponentDeviation = current.data(Qt.UserRole)
        if dev is None:
            return

        self.section_chart.plot_component_section(dev.component, dev.latest_record)

    def _mark_abnormal_recheck(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        count = self.deviation_calc.mark_abnormal_for_recheck(self.current_building_id)
        QMessageBox.information(self, "操作完成", f"已标记 {count} 个异常构件需要复测")
        self._refresh_deviation_analysis()

    def _generate_report(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        report = self.report_gen.generate_text_report(self.current_building_id)
        self.report_text.setText(report)
        self.statusBar().showMessage("报告已生成", 3000)

    def _save_report(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return
        building = self.db.get_building(self.current_building_id)
        default_name = f"{building.name}_偏差报告.txt" if building else "偏差报告.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存报告", default_name, "文本文件 (*.txt)"
        )
        if file_path:
            if self.report_gen.save_report_to_file(self.current_building_id, file_path):
                QMessageBox.information(self, "成功", f"报告已保存到：\n{file_path}")
                self.statusBar().showMessage("报告已保存", 3000)
            else:
                QMessageBox.critical(self, "错误", "保存失败")

    def closeEvent(self, event):
        self.db.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
