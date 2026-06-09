import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QGroupBox, QFormLayout, QTextEdit, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter, QFileDialog,
    QScrollArea, QGridLayout, QSpinBox, QDateEdit, QTabWidget, QFrame
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QBrush, QColor, QPixmap

from database import (
    DatabaseManager, DiseaseRecord, DiseaseTreatment,
    DISEASE_TYPES, DISEASE_SEVERITIES, PRIORITIES, DISEASE_STATUSES,
    DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_REVIEWED,
    DISEASE_SEVERITY_MILD, DISEASE_SEVERITY_MODERATE,
    DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_DANGEROUS,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT,
)
from services import DiseaseService, RepairSuggestion


class DiseaseDialog(QDialog):
    def __init__(self, parent=None, disease: DiseaseRecord = None,
                 db_manager: DatabaseManager = None, building_id: int = None):
        super().__init__(parent)
        self.setWindowTitle("病害记录" if disease else "新增病害")
        self.setMinimumWidth(550)
        self.disease = disease
        self.db = db_manager
        self.building_id = building_id
        self._photo_paths = []
        self.service = DiseaseService(db_manager) if db_manager else None

        if disease and disease.photo_paths:
            self._photo_paths = [p for p in disease.photo_paths.split("|") if p]

        self._init_ui()

        if disease:
            self._load_data(disease)

    def _init_ui(self):
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)

        basic_group = QGroupBox("基本信息")
        basic_form = QFormLayout()

        if self.building_id and self.db:
            components = self.db.get_components_by_building(self.building_id)
            self.component_combo = QComboBox()
            for comp in components:
                self.component_combo.addItem(f"{comp.code} - {comp.name}", comp.id)
            basic_form.addRow("所属构件 *", self.component_combo)

        self.type_combo = QComboBox()
        for code, name in DISEASE_TYPES:
            self.type_combo.addItem(name, code)
        basic_form.addRow("病害类型 *", self.type_combo)

        self.severity_combo = QComboBox()
        for code, name in DISEASE_SEVERITIES:
            self.severity_combo.addItem(name, code)
        basic_form.addRow("病害等级", self.severity_combo)

        self.priority_combo = QComboBox()
        for code, name in PRIORITIES:
            self.priority_combo.addItem(name, code)
        basic_form.addRow("处理优先级", self.priority_combo)

        self.status_combo = QComboBox()
        for code, name in DISEASE_STATUSES:
            self.status_combo.addItem(name, code)
        basic_form.addRow("状态", self.status_combo)

        basic_group.setLayout(basic_form)
        form_layout.addWidget(basic_group)

        desc_group = QGroupBox("病害详情")
        desc_form = QFormLayout()

        self.location_edit = QLineEdit()
        self.location_edit.setPlaceholderText("例如：梁端北侧、柱身中部等")
        desc_form.addRow("病害位置", self.location_edit)

        size_layout = QHBoxLayout()
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(0, 10000)
        self.length_spin.setSuffix(" mm")
        self.length_spin.setDecimals(1)
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0, 10000)
        self.width_spin.setSuffix(" mm")
        self.width_spin.setDecimals(1)
        self.depth_spin = QDoubleSpinBox()
        self.depth_spin.setRange(0, 1000)
        self.depth_spin.setSuffix(" mm")
        self.depth_spin.setDecimals(1)
        size_layout.addWidget(QLabel("长:"))
        size_layout.addWidget(self.length_spin)
        size_layout.addWidget(QLabel("宽:"))
        size_layout.addWidget(self.width_spin)
        size_layout.addWidget(QLabel("深:"))
        size_layout.addWidget(self.depth_spin)
        desc_form.addRow("病害尺寸", size_layout)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("请详细描述病害情况...")
        desc_form.addRow("病害描述", self.desc_edit)

        desc_group.setLayout(desc_form)
        form_layout.addWidget(desc_group)

        photo_group = QGroupBox("病害照片")
        photo_layout = QVBoxLayout(photo_group)

        photo_btn_layout = QHBoxLayout()
        self.btn_add_photo = QPushButton("添加照片")
        self.btn_add_photo.clicked.connect(self._add_photo)
        self.btn_remove_photo = QPushButton("移除选中")
        self.btn_remove_photo.clicked.connect(self._remove_photo)
        photo_btn_layout.addWidget(self.btn_add_photo)
        photo_btn_layout.addWidget(self.btn_remove_photo)
        photo_btn_layout.addStretch()
        photo_layout.addLayout(photo_btn_layout)

        self.photo_list = QListWidget()
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QPixmap(120, 90).size())
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setMovement(QListWidget.Static)
        self.photo_list.setSpacing(10)
        self.photo_list.setFixedHeight(150)
        photo_layout.addWidget(self.photo_list)

        form_layout.addWidget(photo_group)

        repair_group = QGroupBox("修缮建议")
        repair_layout = QVBoxLayout(repair_group)

        btn_layout = QHBoxLayout()
        self.btn_generate_suggestion = QPushButton("自动生成建议")
        self.btn_generate_suggestion.clicked.connect(self._generate_suggestion)
        btn_layout.addWidget(self.btn_generate_suggestion)
        btn_layout.addStretch()
        repair_layout.addLayout(btn_layout)

        self.suggestion_edit = QTextEdit()
        self.suggestion_edit.setMaximumHeight(60)
        self.suggestion_edit.setPlaceholderText("修缮建议...")
        repair_layout.addWidget(QLabel("修缮建议："))
        repair_layout.addWidget(self.suggestion_edit)

        self.method_edit = QLineEdit()
        self.method_edit.setPlaceholderText("修缮方法...")
        repair_layout.addWidget(QLabel("修缮方法："))
        repair_layout.addWidget(self.method_edit)

        cost_layout = QHBoxLayout()
        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 100000)
        self.cost_spin.setPrefix("¥ ")
        self.cost_spin.setDecimals(2)
        cost_layout.addWidget(QLabel("预估费用："))
        cost_layout.addWidget(self.cost_spin)
        cost_layout.addStretch()
        repair_layout.addLayout(cost_layout)

        form_layout.addWidget(repair_group)

        handler_group = QGroupBox("处置信息")
        handler_form = QFormLayout()

        self.handler_edit = QLineEdit()
        handler_form.addRow("负责人", self.handler_edit)

        self.plan_date = QDateEdit()
        self.plan_date.setCalendarPopup(True)
        self.plan_date.setDate(QDate.currentDate())
        handler_form.addRow("计划处理日期", self.plan_date)

        self.complete_date = QDateEdit()
        self.complete_date.setCalendarPopup(True)
        self.complete_date.setDate(QDate.currentDate())
        self.complete_date.setSpecialValueText(" ")
        handler_form.addRow("完成日期", self.complete_date)

        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        handler_form.addRow("备注", self.remark_edit)

        handler_group.setLayout(handler_form)
        form_layout.addWidget(handler_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _add_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择照片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if file_path:
            self._photo_paths.append(file_path)
            item = QListWidgetItem()
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                from PySide6.QtGui import QIcon
                item.setIcon(QIcon(scaled))
            item.setText(os.path.basename(file_path))
            item.setToolTip(file_path)
            item.setData(Qt.UserRole, file_path)
            self.photo_list.addItem(item)

    def _remove_photo(self):
        current = self.photo_list.currentItem()
        if current:
            path = current.data(Qt.UserRole)
            if path in self._photo_paths:
                self._photo_paths.remove(path)
            self.photo_list.takeItem(self.photo_list.row(current))

    def _generate_suggestion(self):
        if not self.service:
            QMessageBox.information(self, "提示", "服务不可用")
            return

        disease = self._build_disease_obj()
        try:
            suggestion = self.service.generate_repair_suggestion(disease)
            self.suggestion_edit.setPlainText(suggestion.suggestion)
            self.method_edit.setText(suggestion.method)
            self.cost_spin.setValue(suggestion.estimated_cost)

            if suggestion.deviation_factor:
                QMessageBox.information(self, "提示",
                    f"已生成修缮建议\n\n{suggestion.deviation_factor}")
            else:
                QMessageBox.information(self, "提示", "修缮建议已生成")
        except Exception as e:
            QMessageBox.warning(self, "提示", f"生成建议失败：{str(e)}")

    def _build_disease_obj(self) -> DiseaseRecord:
        component_id = None
        component_code = ""
        if self.building_id and self.db:
            component_id = self.component_combo.currentData()
            component_code = self.component_combo.currentText().split(" - ")[0]

        disease = DiseaseRecord(
            id=self.disease.id if self.disease else None,
            building_id=self.disease.building_id if self.disease else self.building_id,
            component_id=component_id or (self.disease.component_id if self.disease else 0),
            component_code=component_code or (self.disease.component_code if self.disease else ""),
            disease_type=self.type_combo.currentData(),
            severity=self.severity_combo.currentData(),
            priority=self.priority_combo.currentData(),
            status=self.status_combo.currentData(),
            description=self.desc_edit.toPlainText().strip(),
            location=self.location_edit.text().strip(),
            size_length=self.length_spin.value(),
            size_width=self.width_spin.value(),
            size_depth=self.depth_spin.value(),
            photo_paths="|".join(self._photo_paths),
            repair_suggestion=self.suggestion_edit.toPlainText().strip(),
            repair_method=self.method_edit.text().strip(),
            estimated_cost=self.cost_spin.value(),
            handler=self.handler_edit.text().strip(),
            plan_date=self.plan_date.date().toString("yyyy-MM-dd"),
            complete_date=self.complete_date.date().toString("yyyy-MM-dd"),
            remark=self.remark_edit.toPlainText().strip(),
        )
        return disease

    def _load_data(self, disease: DiseaseRecord):
        if hasattr(self, 'component_combo') and disease.component_id:
            idx = self.component_combo.findData(disease.component_id)
            if idx >= 0:
                self.component_combo.setCurrentIndex(idx)

        idx = self.type_combo.findData(disease.disease_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        idx = self.severity_combo.findData(disease.severity)
        if idx >= 0:
            self.severity_combo.setCurrentIndex(idx)

        idx = self.priority_combo.findData(disease.priority)
        if idx >= 0:
            self.priority_combo.setCurrentIndex(idx)

        idx = self.status_combo.findData(disease.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        self.location_edit.setText(disease.location)
        self.length_spin.setValue(disease.size_length)
        self.width_spin.setValue(disease.size_width)
        self.depth_spin.setValue(disease.size_depth)
        self.desc_edit.setPlainText(disease.description)
        self.suggestion_edit.setPlainText(disease.repair_suggestion)
        self.method_edit.setText(disease.repair_method)
        self.cost_spin.setValue(disease.estimated_cost)
        self.handler_edit.setText(disease.handler)

        if disease.plan_date:
            self.plan_date.setDate(QDate.fromString(disease.plan_date, "yyyy-MM-dd"))
        if disease.complete_date:
            self.complete_date.setDate(QDate.fromString(disease.complete_date, "yyyy-MM-dd"))

        self.remark_edit.setPlainText(disease.remark)

    def get_data(self) -> dict:
        disease = self._build_disease_obj()
        return disease.__dict__

    def accept(self):
        data = self.get_data()
        if not data.get("disease_type"):
            QMessageBox.warning(self, "提示", "请选择病害类型")
            return
        if not data.get("severity"):
            QMessageBox.warning(self, "提示", "请选择病害等级")
            return
        if self.building_id and not data.get("component_id"):
            QMessageBox.warning(self, "提示", "请选择所属构件")
            return
        super().accept()


class DiseaseTreatmentDialog(QDialog):
    def __init__(self, parent=None, disease_id: int = None):
        super().__init__(parent)
        self.setWindowTitle("添加处置记录")
        self.setMinimumWidth(450)
        self.disease_id = disease_id
        self._photo_paths = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        self.type_edit = QLineEdit()
        self.type_edit.setPlaceholderText("例如：检查、加固、修补等")
        form.addRow("处置类型 *", self.type_edit)

        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(100)
        self.desc_edit.setPlaceholderText("请详细描述处置过程和结果...")
        form.addRow("处置描述 *", self.desc_edit)

        self.handler_edit = QLineEdit()
        form.addRow("处理人", self.handler_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("处理日期", self.date_edit)

        photo_group = QGroupBox("处置照片")
        photo_layout = QVBoxLayout(photo_group)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加照片")
        btn_add.clicked.connect(self._add_photo)
        btn_remove = QPushButton("移除选中")
        btn_remove.clicked.connect(self._remove_photo)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_remove)
        btn_layout.addStretch()
        photo_layout.addLayout(btn_layout)

        self.photo_list = QListWidget()
        self.photo_list.setFixedHeight(100)
        photo_layout.addWidget(self.photo_list)

        layout.addLayout(form)
        layout.addWidget(photo_group)

        self.remark_edit = QTextEdit()
        self.remark_edit.setMaximumHeight(60)
        form.addRow("备注", self.remark_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _add_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择照片", "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        if file_path:
            self._photo_paths.append(file_path)
            item = QListWidgetItem(os.path.basename(file_path))
            item.setToolTip(file_path)
            item.setData(Qt.UserRole, file_path)
            self.photo_list.addItem(item)

    def _remove_photo(self):
        current = self.photo_list.currentItem()
        if current:
            path = current.data(Qt.UserRole)
            if path in self._photo_paths:
                self._photo_paths.remove(path)
            self.photo_list.takeItem(self.photo_list.row(current))

    def get_data(self) -> dict:
        return {
            "disease_id": self.disease_id,
            "treatment_type": self.type_edit.text().strip(),
            "description": self.desc_edit.toPlainText().strip(),
            "handler": self.handler_edit.text().strip(),
            "treatment_date": self.date_edit.date().toString("yyyy-MM-dd"),
            "photo_paths": "|".join(self._photo_paths),
            "remark": self.remark_edit.toPlainText().strip(),
        }

    def accept(self):
        data = self.get_data()
        if not data["treatment_type"]:
            QMessageBox.warning(self, "提示", "请输入处置类型")
            return
        if not data["description"]:
            QMessageBox.warning(self, "提示", "请输入处置描述")
            return
        super().accept()


class DiseaseManagementWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.service = DiseaseService(db_manager)
        self.current_building_id = None
        self.current_disease_id = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()

        top_bar.addWidget(QLabel("状态筛选："))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", None)
        for code, name in DISEASE_STATUSES:
            self.status_combo.addItem(name, code)
        self.status_combo.currentIndexChanged.connect(self._refresh_table)
        top_bar.addWidget(self.status_combo)

        top_bar.addWidget(QLabel("类型筛选："))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        for code, name in DISEASE_TYPES:
            self.type_combo.addItem(name, code)
        self.type_combo.currentIndexChanged.connect(self._refresh_table)
        top_bar.addWidget(self.type_combo)

        top_bar.addWidget(QLabel("等级筛选："))
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("全部", None)
        for code, name in DISEASE_SEVERITIES:
            self.severity_combo.addItem(name, code)
        self.severity_combo.currentIndexChanged.connect(self._refresh_table)
        top_bar.addWidget(self.severity_combo)

        top_bar.addStretch()

        btn_add = QPushButton("新增病害")
        btn_add.clicked.connect(self._add_disease)
        btn_edit = QPushButton("编辑病害")
        btn_edit.clicked.connect(self._edit_disease)
        btn_delete = QPushButton("删除病害")
        btn_delete.clicked.connect(self._delete_disease)
        btn_treatment = QPushButton("添加处置")
        btn_treatment.clicked.connect(self._add_treatment)

        top_bar.addWidget(btn_add)
        top_bar.addWidget(btn_edit)
        top_bar.addWidget(btn_delete)
        top_bar.addWidget(btn_treatment)

        main_layout.addLayout(top_bar)

        splitter = QSplitter(Qt.Vertical)

        self.disease_table = QTableWidget()
        self.disease_table.setColumnCount(10)
        self.disease_table.setHorizontalHeaderLabels(
            ["ID", "构件编号", "病害类型", "等级", "优先级", "状态",
             "位置", "尺寸(mm)", "预估费用", "创建时间"]
        )
        self.disease_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disease_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.disease_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.disease_table.itemSelectionChanged.connect(self._on_disease_selected)
        splitter.addWidget(self.disease_table)

        detail_group = QGroupBox("病害详情")
        detail_layout = QVBoxLayout(detail_group)

        self.detail_text = QLabel("请选择一条病害记录查看详情")
        self.detail_text.setWordWrap(True)
        self.detail_text.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        self.detail_text.setAlignment(Qt.AlignTop)
        detail_layout.addWidget(self.detail_text, 1)

        treatment_group = QGroupBox("处置记录")
        treatment_layout = QVBoxLayout(treatment_group)
        self.treatment_list = QListWidget()
        treatment_layout.addWidget(self.treatment_list)

        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.addWidget(detail_group)
        bottom_splitter.addWidget(treatment_group)
        bottom_splitter.setSizes([300, 200])

        splitter.addWidget(bottom_splitter)
        splitter.setSizes([300, 200])

        main_layout.addWidget(splitter, 1)

    def set_building(self, building_id: int):
        self.current_building_id = building_id
        self._refresh_table()

    def _refresh_table(self):
        if not self.current_building_id:
            self.disease_table.setRowCount(0)
            return

        status_filter = self.status_combo.currentData()
        type_filter = self.type_combo.currentData()
        severity_filter = self.severity_combo.currentData()

        diseases = self.db.get_diseases_by_building(
            self.current_building_id,
            status=status_filter,
            disease_type=type_filter,
            severity=severity_filter
        )

        self.disease_table.setRowCount(len(diseases))

        type_map = {code: name for code, name in DISEASE_TYPES}
        severity_map = {code: name for code, name in DISEASE_SEVERITIES}
        priority_map = {code: name for code, name in PRIORITIES}
        status_map = {code: name for code, name in DISEASE_STATUSES}

        severity_color_map = {
            DISEASE_SEVERITY_MILD: QColor("#2ecc71"),
            DISEASE_SEVERITY_MODERATE: QColor("#f39c12"),
            DISEASE_SEVERITY_SEVERE: QColor("#e67e22"),
            DISEASE_SEVERITY_DANGEROUS: QColor("#e74c3c"),
        }

        priority_color_map = {
            PRIORITY_LOW: QColor("#2ecc71"),
            PRIORITY_MEDIUM: QColor("#3498db"),
            PRIORITY_HIGH: QColor("#e67e22"),
            PRIORITY_URGENT: QColor("#e74c3c"),
        }

        for row, disease in enumerate(diseases):
            size_str = ""
            if disease.size_length > 0:
                size_str += f"{disease.size_length:.0f}"
            if disease.size_width > 0:
                size_str += f"×{disease.size_width:.0f}"
            if disease.size_depth > 0:
                size_str += f"×{disease.size_depth:.0f}"

            items = [
                QTableWidgetItem(str(disease.id)),
                QTableWidgetItem(disease.component_code),
                QTableWidgetItem(type_map.get(disease.disease_type, disease.disease_type)),
                QTableWidgetItem(severity_map.get(disease.severity, disease.severity)),
                QTableWidgetItem(priority_map.get(disease.priority, disease.priority)),
                QTableWidgetItem(status_map.get(disease.status, disease.status)),
                QTableWidgetItem(disease.location or "-"),
                QTableWidgetItem(size_str or "-"),
                QTableWidgetItem(f"¥{disease.estimated_cost:,.0f}"),
                QTableWidgetItem(disease.created_at),
            ]

            for col, item in enumerate(items):
                if col == 3:
                    color = severity_color_map.get(disease.severity, QColor("black"))
                    item.setForeground(QBrush(color))
                elif col == 4:
                    color = priority_color_map.get(disease.priority, QColor("black"))
                    item.setForeground(QBrush(color))
                self.disease_table.setItem(row, col, item)

            self.disease_table.item(row, 0).setData(Qt.UserRole, disease.id)

    def _on_disease_selected(self):
        items = self.disease_table.selectedItems()
        if not items:
            self.current_disease_id = None
            self.detail_text.setText("请选择一条病害记录查看详情")
            self.treatment_list.clear()
            return

        row = items[0].row()
        disease_id = self.disease_table.item(row, 0).data(Qt.UserRole)
        self.current_disease_id = disease_id

        disease = self.db.get_disease_record(disease_id)
        if disease:
            self._show_disease_detail(disease)
            self._refresh_treatments(disease_id)

    def _show_disease_detail(self, disease: DiseaseRecord):
        type_map = {code: name for code, name in DISEASE_TYPES}
        severity_map = {code: name for code, name in DISEASE_SEVERITIES}
        priority_map = {code: name for code, name in PRIORITIES}
        status_map = {code: name for code, name in DISEASE_STATUSES}

        size_str = ""
        if disease.size_length > 0:
            size_str += f"长度: {disease.size_length:.1f}mm "
        if disease.size_width > 0:
            size_str += f"宽度: {disease.size_width:.1f}mm "
        if disease.size_depth > 0:
            size_str += f"深度: {disease.size_depth:.1f}mm"

        detail_html = f"""
        <div style='padding: 5px;'>
        <p><b>构件编号：</b>{disease.component_code}</p>
        <p><b>病害类型：</b>{type_map.get(disease.disease_type, disease.disease_type)}</p>
        <p><b>病害等级：</b>{severity_map.get(disease.severity, disease.severity)}</p>
        <p><b>优先级：</b>{priority_map.get(disease.priority, disease.priority)}</p>
        <p><b>状态：</b>{status_map.get(disease.status, disease.status)}</p>
        <p><b>位置：</b>{disease.location or '-'}</p>
        <p><b>尺寸：</b>{size_str or '-'}</p>
        <p><b>描述：</b>{disease.description or '-'}</p>
        <hr>
        <p><b>修缮建议：</b></p>
        <p style='color: #2c3e50;'>{disease.repair_suggestion or '-'}</p>
        <p><b>修缮方法：</b>{disease.repair_method or '-'}</p>
        <p><b>预估费用：</b>¥{disease.estimated_cost:,.2f}</p>
        <hr>
        <p><b>负责人：</b>{disease.handler or '-'}</p>
        <p><b>计划日期：</b>{disease.plan_date or '-'}</p>
        <p><b>完成日期：</b>{disease.complete_date or '-'}</p>
        <p><b>备注：</b>{disease.remark or '-'}</p>
        </div>
        """
        self.detail_text.setText(detail_html)
        self.detail_text.setTextFormat(Qt.RichText)

    def _refresh_treatments(self, disease_id: int):
        self.treatment_list.clear()
        treatments = self.db.get_treatments_by_disease(disease_id)

        for t in treatments:
            text = f"[{t.treatment_date}] {t.treatment_type}"
            if t.handler:
                text += f" - {t.handler}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, t)
            if t.description:
                item.setToolTip(t.description)
            self.treatment_list.addItem(item)

    def _add_disease(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return

        dlg = DiseaseDialog(self, db_manager=self.db, building_id=self.current_building_id)
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                disease = DiseaseRecord(**data)
                disease = self.service.create_disease_with_suggestion(disease)
                self._refresh_table()
                QMessageBox.information(self, "成功",
                    f"病害记录已添加，已自动生成修缮建议\n预估费用：¥{disease.estimated_cost:,.2f}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def _edit_disease(self):
        if not self.current_disease_id:
            QMessageBox.information(self, "提示", "请先选择一条病害记录")
            return

        disease = self.db.get_disease_record(self.current_disease_id)
        if not disease:
            return

        dlg = DiseaseDialog(self, disease=disease, db_manager=self.db,
                           building_id=disease.building_id)
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                for key, value in data.items():
                    if hasattr(disease, key) and key != 'id':
                        setattr(disease, key, value)

                self.db.update_disease_record(disease)
                self._refresh_table()
                QMessageBox.information(self, "成功", "病害记录已更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def _delete_disease(self):
        if not self.current_disease_id:
            QMessageBox.information(self, "提示", "请先选择一条病害记录")
            return

        reply = QMessageBox.question(self, "确认删除",
            "确定要删除这条病害记录吗？所有处置记录也将被删除。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_disease_record(self.current_disease_id):
                self._refresh_table()
                QMessageBox.information(self, "成功", "病害记录已删除")
            else:
                QMessageBox.critical(self, "错误", "删除失败")

    def _add_treatment(self):
        if not self.current_disease_id:
            QMessageBox.information(self, "提示", "请先选择一条病害记录")
            return

        dlg = DiseaseTreatmentDialog(self, disease_id=self.current_disease_id)
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                treatment = DiseaseTreatment(**data)
                self.db.add_disease_treatment(treatment)
                self._refresh_treatments(self.current_disease_id)
                QMessageBox.information(self, "成功", "处置记录已添加")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加失败：{str(e)}")

    def refresh(self):
        self._refresh_table()


class DiseaseDashboardWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.service = DiseaseService(db_manager)
        self.current_building_id = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        stats_group = QGroupBox("病害总览")
        stats_layout = QGridLayout(stats_group)

        self.card_total = self._create_stat_card("病害总数", "-", "#3498db")
        self.card_pending = self._create_stat_card("待处理", "-", "#f39c12")
        self.card_in_progress = self._create_stat_card("处理中", "-", "#3498db")
        self.card_completed = self._create_stat_card("已完成", "-", "#2ecc71")

        stats_layout.addWidget(self.card_total, 0, 0)
        stats_layout.addWidget(self.card_pending, 0, 1)
        stats_layout.addWidget(self.card_in_progress, 0, 2)
        stats_layout.addWidget(self.card_completed, 0, 3)

        self.card_urgent = self._create_stat_card("紧急待处理", "-", "#e74c3c", small=True)
        self.card_severe = self._create_stat_card("严重病害", "-", "#e67e22", small=True)
        self.card_cost = self._create_stat_card("预估总费用", "-", "#9b59b6", small=True)
        self.card_rate = self._create_stat_card("处置完成率", "-", "#1abc9c", small=True)

        stats_layout.addWidget(self.card_urgent, 1, 0)
        stats_layout.addWidget(self.card_severe, 1, 1)
        stats_layout.addWidget(self.card_cost, 1, 2)
        stats_layout.addWidget(self.card_rate, 1, 3)

        main_layout.addWidget(stats_group)

        middle_row = QHBoxLayout()

        type_group = QGroupBox("按病害类型分布")
        type_layout = QVBoxLayout(type_group)
        self.type_table = QTableWidget()
        self.type_table.setColumnCount(2)
        self.type_table.setHorizontalHeaderLabels(["病害类型", "数量"])
        self.type_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.type_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        type_layout.addWidget(self.type_table)
        middle_row.addWidget(type_group, 1)

        severity_group = QGroupBox("按严重程度分布")
        severity_layout = QVBoxLayout(severity_group)
        self.severity_table = QTableWidget()
        self.severity_table.setColumnCount(2)
        self.severity_table.setHorizontalHeaderLabels(["严重程度", "数量"])
        self.severity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.severity_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        severity_layout.addWidget(self.severity_table)
        middle_row.addWidget(severity_group, 1)

        priority_group = QGroupBox("按优先级分布")
        priority_layout = QVBoxLayout(priority_group)
        self.priority_table = QTableWidget()
        self.priority_table.setColumnCount(2)
        self.priority_table.setHorizontalHeaderLabels(["优先级", "数量"])
        self.priority_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.priority_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        priority_layout.addWidget(self.priority_table)
        middle_row.addWidget(priority_group, 1)

        main_layout.addLayout(middle_row, 1)

        bottom_group = QGroupBox("待处理紧急病害")
        bottom_layout = QVBoxLayout(bottom_group)
        self.urgent_table = QTableWidget()
        self.urgent_table.setColumnCount(5)
        self.urgent_table.setHorizontalHeaderLabels(
            ["构件编号", "病害类型", "等级", "优先级", "创建时间"]
        )
        self.urgent_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.urgent_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.urgent_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        bottom_layout.addWidget(self.urgent_table)

        main_layout.addWidget(bottom_group, 1)

        btn_row = QHBoxLayout()
        btn_refresh = QPushButton("刷新数据")
        btn_refresh.clicked.connect(self.refresh)
        btn_regenerate = QPushButton("重新生成所有修缮建议")
        btn_regenerate.clicked.connect(self._regenerate_all_suggestions)
        btn_row.addWidget(btn_refresh)
        btn_row.addWidget(btn_regenerate)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

    def _create_stat_card(self, title: str, value: str, color: str, small: bool = False) -> QLabel:
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                border-radius: 8px;
                padding: {10 if small else 20}px;
                font-size: {12 if small else 14}px;
            }}
        """)
        label.setText(f"{title}\n<span style='font-size: {20 if small else 28}px; font-weight: bold;'>{value}</span>")
        label.setTextFormat(Qt.RichText)
        return label

    def set_building(self, building_id: int):
        self.current_building_id = building_id
        self.refresh()

    def refresh(self):
        if not self.current_building_id:
            self._clear_all()
            return

        progress = self.service.get_progress_summary(self.current_building_id)
        stats = progress["stats"]

        self.card_total.setText(
            f"病害总数\n<span style='font-size: 28px; font-weight: bold;'>{stats.total_count}</span>")
        self.card_pending.setText(
            f"待处理\n<span style='font-size: 28px; font-weight: bold;'>{stats.pending_count}</span>")
        self.card_in_progress.setText(
            f"处理中\n<span style='font-size: 28px; font-weight: bold;'>{stats.in_progress_count}</span>")
        self.card_completed.setText(
            f"已完成\n<span style='font-size: 28px; font-weight: bold;'>{stats.completed_count + stats.reviewed_count}</span>")

        severe_count = stats.by_severity.get(DISEASE_SEVERITY_SEVERE, 0) + \
                       stats.by_severity.get(DISEASE_SEVERITY_DANGEROUS, 0)

        self.card_urgent.setText(
            f"紧急待处理\n<span style='font-size: 20px; font-weight: bold;'>{progress['pending_urgent']}</span>")
        self.card_severe.setText(
            f"严重病害\n<span style='font-size: 20px; font-weight: bold;'>{severe_count}</span>")
        self.card_cost.setText(
            f"预估总费用\n<span style='font-size: 20px; font-weight: bold;'>¥{stats.total_estimated_cost:,.0f}</span>")
        self.card_rate.setText(
            f"处置完成率\n<span style='font-size: 20px; font-weight: bold;'>{progress['completion_rate']:.1f}%</span>")

        type_map = {code: name for code, name in DISEASE_TYPES}
        type_items = sorted(stats.by_type.items(), key=lambda x: x[1], reverse=True)
        self.type_table.setRowCount(len(type_items))
        for row, (code, count) in enumerate(type_items):
            self.type_table.setItem(row, 0, QTableWidgetItem(type_map.get(code, code)))
            self.type_table.setItem(row, 1, QTableWidgetItem(str(count)))

        severity_map = {code: name for code, name in DISEASE_SEVERITIES}
        severity_order = [DISEASE_SEVERITY_DANGEROUS, DISEASE_SEVERITY_SEVERE,
                         DISEASE_SEVERITY_MODERATE, DISEASE_SEVERITY_MILD]
        self.severity_table.setRowCount(len(severity_order))
        for row, code in enumerate(severity_order):
            count = stats.by_severity.get(code, 0)
            self.severity_table.setItem(row, 0, QTableWidgetItem(severity_map.get(code, code)))
            self.severity_table.setItem(row, 1, QTableWidgetItem(str(count)))

        priority_map = {code: name for code, name in PRIORITIES}
        priority_order = [PRIORITY_URGENT, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW]
        self.priority_table.setRowCount(len(priority_order))
        for row, code in enumerate(priority_order):
            count = stats.by_priority.get(code, 0)
            self.priority_table.setItem(row, 0, QTableWidgetItem(priority_map.get(code, code)))
            self.priority_table.setItem(row, 1, QTableWidgetItem(str(count)))

        diseases = self.db.get_diseases_by_building(self.current_building_id)
        urgent_diseases = [d for d in diseases
                          if d.status in [DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS]
                          and d.priority == PRIORITY_URGENT]

        self.urgent_table.setRowCount(len(urgent_diseases))
        for row, d in enumerate(urgent_diseases):
            self.urgent_table.setItem(row, 0, QTableWidgetItem(d.component_code))
            self.urgent_table.setItem(row, 1, QTableWidgetItem(type_map.get(d.disease_type, d.disease_type)))
            self.urgent_table.setItem(row, 2, QTableWidgetItem(severity_map.get(d.severity, d.severity)))
            self.urgent_table.setItem(row, 3, QTableWidgetItem(priority_map.get(d.priority, d.priority)))
            self.urgent_table.setItem(row, 4, QTableWidgetItem(d.created_at))

    def _clear_all(self):
        for card in [self.card_total, self.card_pending, self.card_in_progress,
                    self.card_completed, self.card_urgent, self.card_severe,
                    self.card_cost, self.card_rate]:
            card.setText(card.text().split('\n')[0] + "\n<span style='font-size: 28px; font-weight: bold;'>-</span>")

        self.type_table.setRowCount(0)
        self.severity_table.setRowCount(0)
        self.priority_table.setRowCount(0)
        self.urgent_table.setRowCount(0)

    def _regenerate_all_suggestions(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return

        reply = QMessageBox.question(self, "确认",
            "确定要重新生成所有病害的修缮建议吗？\n这将覆盖现有的建议内容。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            count = self.service.batch_generate_all_suggestions(self.current_building_id)
            QMessageBox.information(self, "完成", f"已重新生成 {count} 条病害的修缮建议")
            self.refresh()
