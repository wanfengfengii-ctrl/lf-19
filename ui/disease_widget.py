import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QGroupBox, QFormLayout, QTextEdit, QDoubleSpinBox, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QSplitter, QFileDialog,
    QScrollArea, QGridLayout, QSpinBox, QDateEdit, QTabWidget, QFrame,
    QInputDialog
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QBrush, QColor, QPixmap

from database import (
    DatabaseManager, DiseaseRecord, DiseaseTreatment,
    DISEASE_TYPES, DISEASE_SEVERITIES, PRIORITIES, DISEASE_STATUSES,
    DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING,
    DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
    DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED,
    DISEASE_SEVERITY_MILD, DISEASE_SEVERITY_MODERATE,
    DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_DANGEROUS,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT,
)
from services import DiseaseService, RepairSuggestion
from .disease_advanced_widgets import (
    DiseaseAcceptanceDialog, WorkflowStepWidget,
    DiseasePhotoCompareWidget, DiseaseStatusHistoryWidget,
    WarningListWidget,
)


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
        self.complete_date.setSpecialValueText(" ")
        self.complete_date.setMinimumDate(QDate(1900, 1, 1))
        self.complete_date.setDate(QDate(1900, 1, 1))
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

        plan_date_str = self.plan_date.date().toString("yyyy-MM-dd")

        status = self.status_combo.currentData()
        complete_date_str = ""
        if status in (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_REVIEWED):
            if self.complete_date.date() > QDate(1900, 1, 1):
                complete_date_str = self.complete_date.date().toString("yyyy-MM-dd")

        disease = DiseaseRecord(
            id=self.disease.id if self.disease else None,
            building_id=self.disease.building_id if self.disease else self.building_id,
            component_id=component_id or (self.disease.component_id if self.disease else 0),
            component_code=component_code or (self.disease.component_code if self.disease else ""),
            disease_type=self.type_combo.currentData(),
            severity=self.severity_combo.currentData(),
            priority=self.priority_combo.currentData(),
            status=status,
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
            plan_date=plan_date_str,
            complete_date=complete_date_str,
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
        else:
            self.complete_date.setDate(QDate(1900, 1, 1))

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

        filter_bar = QHBoxLayout()

        filter_bar.addWidget(QLabel("状态筛选："))
        self.status_combo = QComboBox()
        self.status_combo.addItem("全部", None)
        for code, name in DISEASE_STATUSES:
            self.status_combo.addItem(name, code)
        self.status_combo.currentIndexChanged.connect(self._refresh_table)
        filter_bar.addWidget(self.status_combo)

        filter_bar.addWidget(QLabel("类型筛选："))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        for code, name in DISEASE_TYPES:
            self.type_combo.addItem(name, code)
        self.type_combo.currentIndexChanged.connect(self._refresh_table)
        filter_bar.addWidget(self.type_combo)

        filter_bar.addWidget(QLabel("等级筛选："))
        self.severity_combo = QComboBox()
        self.severity_combo.addItem("全部", None)
        for code, name in DISEASE_SEVERITIES:
            self.severity_combo.addItem(name, code)
        self.severity_combo.currentIndexChanged.connect(self._refresh_table)
        filter_bar.addWidget(self.severity_combo)

        filter_bar.addStretch()

        btn_add = QPushButton("新增病害")
        btn_add.clicked.connect(self._add_disease)
        btn_edit = QPushButton("编辑病害")
        btn_edit.clicked.connect(self._edit_disease)
        btn_delete = QPushButton("删除病害")
        btn_delete.clicked.connect(self._delete_disease)

        filter_bar.addWidget(btn_add)
        filter_bar.addWidget(btn_edit)
        filter_bar.addWidget(btn_delete)

        main_layout.addLayout(filter_bar)

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

        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)

        action_bar = QHBoxLayout()
        self.workflow_widget = WorkflowStepWidget(
            self.service.get_workflow_steps(), None
        )
        action_bar.addWidget(self.workflow_widget, 1)
        detail_layout.addLayout(action_bar)

        status_action_bar = QHBoxLayout()
        self.btn_assign = QPushButton("派单")
        self.btn_assign.clicked.connect(self._on_assign)
        self.btn_start = QPushButton("开始处置")
        self.btn_start.clicked.connect(self._on_start_treatment)
        self.btn_complete = QPushButton("完成处置")
        self.btn_complete.clicked.connect(self._on_complete_treatment)
        self.btn_accept = QPushButton("整改验收")
        self.btn_accept.clicked.connect(self._on_accept)
        self.btn_review = QPushButton("复查")
        self.btn_review.clicked.connect(self._on_review)
        self.btn_archive = QPushButton("归档")
        self.btn_archive.clicked.connect(self._on_archive)
        self.btn_reopen = QPushButton("重新打开")
        self.btn_reopen.clicked.connect(self._on_reopen)
        self.btn_add_treatment = QPushButton("添加处置记录")
        self.btn_add_treatment.clicked.connect(self._add_treatment)

        for btn in [self.btn_assign, self.btn_start, self.btn_complete,
                    self.btn_accept, self.btn_review, self.btn_archive,
                    self.btn_reopen, self.btn_add_treatment]:
            btn.setEnabled(False)
            status_action_bar.addWidget(btn)

        status_action_bar.addStretch()
        detail_layout.addLayout(status_action_bar)

        self.detail_tabs = QTabWidget()

        detail_tab = QWidget()
        detail_tab_layout = QVBoxLayout(detail_tab)
        detail_tab_layout.setContentsMargins(5, 5, 5, 5)

        self.detail_text = QLabel("请选择一条病害记录查看详情")
        self.detail_text.setWordWrap(True)
        self.detail_text.setStyleSheet("background-color: #f5f5f5; padding: 10px; border-radius: 5px;")
        self.detail_text.setAlignment(Qt.AlignTop)
        detail_tab_layout.addWidget(self.detail_text, 1)

        self.detail_tabs.addTab(detail_tab, "基本信息")

        treatment_tab = QWidget()
        treatment_tab_layout = QVBoxLayout(treatment_tab)
        treatment_tab_layout.setContentsMargins(5, 5, 5, 5)
        self.treatment_list = QListWidget()
        treatment_tab_layout.addWidget(self.treatment_list)
        self.detail_tabs.addTab(treatment_tab, "处置记录")

        self.photo_compare_widget = DiseasePhotoCompareWidget(self.db)
        self.detail_tabs.addTab(self.photo_compare_widget, "图片对比")

        self.status_history_widget = DiseaseStatusHistoryWidget(self.db)
        self.detail_tabs.addTab(self.status_history_widget, "状态历史")

        acceptance_tab = QWidget()
        acceptance_tab_layout = QVBoxLayout(acceptance_tab)
        acceptance_tab_layout.setContentsMargins(5, 5, 5, 5)
        self.acceptance_list = QListWidget()
        acceptance_tab_layout.addWidget(self.acceptance_list)
        self.detail_tabs.addTab(acceptance_tab, "验收记录")

        detail_layout.addWidget(self.detail_tabs, 1)

        splitter.addWidget(detail_container)
        splitter.setSizes([250, 350])

        main_layout.addWidget(splitter, 1)

    def set_building(self, building_id: int):
        if self.current_building_id != building_id:
            self._clear_page_state()
        self.current_building_id = building_id
        self._refresh_table()

    def _clear_page_state(self):
        self.current_disease_id = None
        self.disease_table.clearSelection()
        self.detail_text.setText("请选择一条病害记录查看详情")
        self.treatment_list.clear()
        self.acceptance_list.clear()
        self.photo_compare_widget.clear()
        self.status_history_widget.clear()
        self.workflow_widget.set_current_status(None)
        self._update_action_buttons(None)

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

        status_color_map = {
            DISEASE_STATUS_DISCOVERED: QColor("#95a5a6"),
            DISEASE_STATUS_PENDING: QColor("#f39c12"),
            DISEASE_STATUS_ASSIGNED: QColor("#3498db"),
            DISEASE_STATUS_IN_PROGRESS: QColor("#e67e22"),
            DISEASE_STATUS_COMPLETED: QColor("#9b59b6"),
            DISEASE_STATUS_ACCEPTED: QColor("#2ecc71"),
            DISEASE_STATUS_REVIEWED: QColor("#1abc9c"),
            DISEASE_STATUS_ARCHIVED: QColor("#7f8c8d"),
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
                elif col == 5:
                    color = status_color_map.get(disease.status, QColor("black"))
                    item.setForeground(QBrush(color))
                self.disease_table.setItem(row, col, item)

            self.disease_table.item(row, 0).setData(Qt.UserRole, disease.id)

    def _on_disease_selected(self):
        items = self.disease_table.selectedItems()
        if not items:
            self.current_disease_id = None
            self.detail_text.setText("请选择一条病害记录查看详情")
            self.treatment_list.clear()
            self.acceptance_list.clear()
            self.photo_compare_widget.clear()
            self.status_history_widget.clear()
            self.workflow_widget.set_current_status(None)
            self._update_action_buttons(None)
            return

        row = items[0].row()
        disease_id = self.disease_table.item(row, 0).data(Qt.UserRole)
        self.current_disease_id = disease_id

        disease = self.db.get_disease_record(disease_id)
        if disease:
            self._show_disease_detail(disease)
            self._refresh_treatments(disease_id)
            self._refresh_acceptances(disease_id)
            self.photo_compare_widget.set_disease(disease_id)
            self.status_history_widget.set_disease(disease_id)
            self.workflow_widget.set_current_status(disease.status)
            self._update_action_buttons(disease.status)

    def _update_action_buttons(self, current_status: str):
        has_selection = current_status is not None

        self.btn_assign.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_complete.setEnabled(False)
        self.btn_accept.setEnabled(False)
        self.btn_review.setEnabled(False)
        self.btn_archive.setEnabled(False)
        self.btn_reopen.setEnabled(False)
        self.btn_add_treatment.setEnabled(has_selection)

        if not has_selection:
            return

        actions = self.service.get_allowed_status_actions(current_status)

        self.btn_assign.setEnabled("assign" in actions)
        self.btn_start.setEnabled("start" in actions)
        self.btn_complete.setEnabled("complete" in actions)
        self.btn_accept.setEnabled("accept" in actions)
        self.btn_review.setEnabled("review" in actions)
        self.btn_archive.setEnabled("archive" in actions)
        self.btn_reopen.setEnabled("reopen" in actions)

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

    def _refresh_acceptances(self, disease_id: int):
        self.acceptance_list.clear()
        acceptances = self.db.get_disease_acceptance_records(disease_id)

        result_map = {code: name for code, name in [
            ("pass", "通过"), ("fail", "不通过"), ("partial", "部分通过")
        ]}

        for a in acceptances:
            review_text = "复查" if a.is_review else "验收"
            result_name = result_map.get(a.acceptance_result, a.acceptance_result)
            text = f"[{a.acceptance_date}] {review_text} - {result_name}"
            if a.acceptance_person:
                text += f" - {a.acceptance_person}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, a)
            if a.acceptance_opinion:
                item.setToolTip(a.acceptance_opinion)
            self.acceptance_list.addItem(item)

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
                self._on_disease_selected()
                QMessageBox.information(self, "成功", "病害记录已更新")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败：{str(e)}")

    def _delete_disease(self):
        if not self.current_disease_id:
            QMessageBox.information(self, "提示", "请先选择一条病害记录")
            return

        reply = QMessageBox.question(self, "确认删除",
            "确定要删除这条病害记录吗？所有相关数据也将被删除。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_disease_record(self.current_disease_id):
                self._clear_page_state()
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

    def _on_assign(self):
        if not self.current_disease_id:
            return
        handler, ok = QInputDialog.getText(self, "派单", "请输入负责人姓名：")
        if ok and handler.strip():
            result = self.service.assign_disease(
                self.current_disease_id, handler.strip())
            if result.success:
                self._refresh_after_status()
                QMessageBox.information(self, "成功", result.message)
            else:
                QMessageBox.warning(self, "失败", result.message)

    def _on_start_treatment(self):
        if not self.current_disease_id:
            return
        result = self.service.start_treatment(self.current_disease_id)
        if result.success:
            self._refresh_after_status()
            QMessageBox.information(self, "成功", result.message)
        else:
            QMessageBox.warning(self, "失败", result.message)

    def _on_complete_treatment(self):
        if not self.current_disease_id:
            return

        dlg = DiseaseTreatmentDialog(self, disease_id=self.current_disease_id)
        dlg.setWindowTitle("完成处置")
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                treatment = DiseaseTreatment(**data)
                self.db.add_disease_treatment(treatment)
                result = self.service.complete_treatment(self.current_disease_id)
                if result.success:
                    self._refresh_after_status()
                    QMessageBox.information(self, "成功", result.message)
                else:
                    QMessageBox.warning(self, "失败", result.message)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"操作失败：{str(e)}")

    def _on_accept(self):
        if not self.current_disease_id:
            return
        dlg = DiseaseAcceptanceDialog(self, disease_id=self.current_disease_id,
                                      db_manager=self.db, is_review=False)
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                result = self.service.accept_disease(
                    self.current_disease_id,
                    acceptance_result=data["acceptance_result"],
                    acceptance_person=data["acceptance_person"],
                    acceptance_date=data["acceptance_date"],
                    acceptance_opinion=data["acceptance_opinion"],
                    photo_paths=data["photo_paths"],
                )
                if result.success:
                    self._refresh_after_status()
                    QMessageBox.information(self, "成功", result.message)
                else:
                    QMessageBox.warning(self, "失败", result.message)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"验收失败：{str(e)}")

    def _on_review(self):
        if not self.current_disease_id:
            return
        dlg = DiseaseAcceptanceDialog(self, disease_id=self.current_disease_id,
                                      db_manager=self.db, is_review=True)
        if dlg.exec() == QDialog.Accepted:
            try:
                data = dlg.get_data()
                result = self.service.review_disease(
                    self.current_disease_id,
                    acceptance_result=data["acceptance_result"],
                    acceptance_person=data["acceptance_person"],
                    acceptance_date=data["acceptance_date"],
                    acceptance_opinion=data["acceptance_opinion"],
                    photo_paths=data["photo_paths"],
                )
                if result.success:
                    self._refresh_after_status()
                    QMessageBox.information(self, "成功", result.message)
                else:
                    QMessageBox.warning(self, "失败", result.message)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"复查失败：{str(e)}")

    def _on_archive(self):
        if not self.current_disease_id:
            return
        reply = QMessageBox.question(self, "确认归档",
            "确定要归档这条病害记录吗？归档后将无法直接编辑。",
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            result = self.service.archive_disease(self.current_disease_id)
            if result.success:
                self._refresh_after_status()
                QMessageBox.information(self, "成功", result.message)
            else:
                QMessageBox.warning(self, "失败", result.message)

    def _on_reopen(self):
        if not self.current_disease_id:
            return
        reason, ok = QInputDialog.getText(self, "重新打开", "请输入重新打开的原因：")
        if ok:
            result = self.service.reopen_disease(
                self.current_disease_id, remark=reason)
            if result.success:
                self._refresh_after_status()
                QMessageBox.information(self, "成功", result.message)
            else:
                QMessageBox.warning(self, "失败", result.message)

    def _refresh_after_status(self):
        self._refresh_table()
        self._on_disease_selected()

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

        self.dashboard_tabs = QTabWidget()

        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)

        stats_group = QGroupBox("病害状态总览")
        stats_layout = QGridLayout(stats_group)

        self.card_total = self._create_stat_card("病害总数", "-", "#3498db")
        stats_layout.addWidget(self.card_total, 0, 0)

        status_cards = [
            ("已发现", DISEASE_STATUS_DISCOVERED, "#95a5a6"),
            ("待派单", DISEASE_STATUS_PENDING, "#f39c12"),
            ("已派单", DISEASE_STATUS_ASSIGNED, "#3498db"),
            ("处置中", DISEASE_STATUS_IN_PROGRESS, "#e67e22"),
            ("已完成", DISEASE_STATUS_COMPLETED, "#9b59b6"),
            ("已验收", DISEASE_STATUS_ACCEPTED, "#2ecc71"),
            ("已复查", DISEASE_STATUS_REVIEWED, "#1abc9c"),
            ("已归档", DISEASE_STATUS_ARCHIVED, "#7f8c8d"),
        ]

        for i, (name, code, color) in enumerate(status_cards):
            card = self._create_stat_card(name, "-", color, small=True)
            setattr(self, f"card_{code}", card)
            col = i % 4
            row = (i // 4) + 1
            stats_layout.addWidget(card, row, col)

        overview_layout.addWidget(stats_group)

        key_metrics_group = QGroupBox("关键指标")
        metrics_layout = QHBoxLayout(key_metrics_group)

        self.card_urgent = self._create_stat_card("紧急待处理", "-", "#e74c3c", small=True)
        self.card_severe = self._create_stat_card("严重病害", "-", "#e67e22", small=True)
        self.card_cost = self._create_stat_card("预估总费用", "-", "#9b59b6", small=True)
        self.card_rate = self._create_stat_card("处置完成率", "-", "#1abc9c", small=True)

        metrics_layout.addWidget(self.card_urgent)
        metrics_layout.addWidget(self.card_severe)
        metrics_layout.addWidget(self.card_cost)
        metrics_layout.addWidget(self.card_rate)

        overview_layout.addWidget(key_metrics_group)

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

        overview_layout.addLayout(middle_row, 1)

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

        overview_layout.addWidget(bottom_group, 1)

        self.dashboard_tabs.addTab(overview_tab, "总览")

        warning_tab = QWidget()
        warning_layout = QVBoxLayout(warning_tab)
        self.warning_widget = WarningListWidget(self.db)
        warning_layout.addWidget(self.warning_widget)
        self.dashboard_tabs.addTab(warning_tab, "预警中心")

        risk_tab = QWidget()
        risk_layout = QVBoxLayout(risk_tab)

        risk_info = QLabel("偏差-病害联动风险分析")
        risk_info.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        risk_layout.addWidget(risk_info)

        self.risk_table = QTableWidget()
        self.risk_table.setColumnCount(5)
        self.risk_table.setHorizontalHeaderLabels(
            ["构件编号", "偏差等级", "病害数量", "综合风险等级", "建议措施"]
        )
        self.risk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.risk_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.risk_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        risk_layout.addWidget(self.risk_table, 1)

        btn_risk_refresh = QPushButton("重新计算风险")
        btn_risk_refresh.clicked.connect(self._recalculate_risk)
        risk_layout.addWidget(btn_risk_refresh)

        self.dashboard_tabs.addTab(risk_tab, "风险分析")

        main_layout.addWidget(self.dashboard_tabs, 1)

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
        if self.current_building_id != building_id:
            self._clear_page_state()
        self.current_building_id = building_id
        self.refresh()

    def _clear_page_state(self):
        self._clear_all()

    def refresh(self):
        if not self.current_building_id:
            self._clear_all()
            return

        progress = self.service.get_progress_summary(self.current_building_id)
        stats = progress["stats"]

        self.card_total.setText(
            f"病害总数\n<span style='font-size: 28px; font-weight: bold;'>{stats.total_count}</span>")

        status_codes = [
            DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING,
            DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS,
            DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
            DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED,
        ]

        for code in status_codes:
            card = getattr(self, f"card_{code}", None)
            if card:
                count = stats.by_status.get(code, 0)
                title = card.text().split('\n')[0]
                card.setText(f"{title}\n<span style='font-size: 20px; font-weight: bold;'>{count}</span>")

        severe_count = stats.by_severity.get(DISEASE_SEVERITY_SEVERE, 0) + \
                       stats.by_severity.get(DISEASE_SEVERITY_DANGEROUS, 0)

        pending_active = (stats.by_status.get(DISEASE_STATUS_PENDING, 0) +
                         stats.by_status.get(DISEASE_STATUS_ASSIGNED, 0) +
                         stats.by_status.get(DISEASE_STATUS_IN_PROGRESS, 0))

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
                          if d.status in [DISEASE_STATUS_PENDING, DISEASE_STATUS_ASSIGNED,
                                         DISEASE_STATUS_IN_PROGRESS]
                          and d.priority == PRIORITY_URGENT]

        self.urgent_table.setRowCount(len(urgent_diseases))
        for row, d in enumerate(urgent_diseases):
            self.urgent_table.setItem(row, 0, QTableWidgetItem(d.component_code))
            self.urgent_table.setItem(row, 1, QTableWidgetItem(type_map.get(d.disease_type, d.disease_type)))
            self.urgent_table.setItem(row, 2, QTableWidgetItem(severity_map.get(d.severity, d.severity)))
            self.urgent_table.setItem(row, 3, QTableWidgetItem(priority_map.get(d.priority, d.priority)))
            self.urgent_table.setItem(row, 4, QTableWidgetItem(d.created_at))

        self.warning_widget.set_building(self.current_building_id)

        self._refresh_risk_table()

    def _refresh_risk_table(self):
        if not self.current_building_id or not self.db:
            self.risk_table.setRowCount(0)
            return

        links = self.db.get_deviation_disease_links(self.current_building_id)

        from database import RISK_LEVELS

        risk_level_map = {code: name for code, name in RISK_LEVELS}
        risk_color_map = {
            "low": QColor("#2ecc71"),
            "medium": QColor("#f39c12"),
            "high": QColor("#e67e22"),
            "critical": QColor("#e74c3c"),
        }

        suggestion_map = {
            "low": "常规监控",
            "medium": "加强观察",
            "high": "建议修缮",
            "critical": "紧急处置",
        }

        self.risk_table.setRowCount(len(links))
        for row, link in enumerate(links):
            items = [
                QTableWidgetItem(link.component_code),
                QTableWidgetItem(str(link.deviation_level or "-")),
                QTableWidgetItem(str(link.disease_count)),
                QTableWidgetItem(risk_level_map.get(link.risk_level, link.risk_level)),
                QTableWidgetItem(suggestion_map.get(link.risk_level, "-")),
            ]

            color = risk_color_map.get(link.risk_level, QColor("black"))
            for item in items:
                item.setForeground(QBrush(color))

            for col, item in enumerate(items):
                self.risk_table.setItem(row, col, item)

    def _recalculate_risk(self):
        if not self.current_building_id:
            QMessageBox.information(self, "提示", "请先选择一个建筑")
            return

        try:
            count = self.service.update_all_deviation_disease_links(self.current_building_id)
            self._refresh_risk_table()
            QMessageBox.information(self, "完成", f"已重新计算 {count} 个构件的风险等级")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算失败：{str(e)}")

    def _clear_all(self):
        self.card_total.setText(
            "病害总数\n<span style='font-size: 28px; font-weight: bold;'>-</span>")

        status_codes = [
            DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING,
            DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS,
            DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
            DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED,
        ]
        status_names = {
            DISEASE_STATUS_DISCOVERED: "已发现",
            DISEASE_STATUS_PENDING: "待派单",
            DISEASE_STATUS_ASSIGNED: "已派单",
            DISEASE_STATUS_IN_PROGRESS: "处置中",
            DISEASE_STATUS_COMPLETED: "已完成",
            DISEASE_STATUS_ACCEPTED: "已验收",
            DISEASE_STATUS_REVIEWED: "已复查",
            DISEASE_STATUS_ARCHIVED: "已归档",
        }

        for code in status_codes:
            card = getattr(self, f"card_{code}", None)
            if card:
                name = status_names.get(code, code)
                card.setText(f"{name}\n<span style='font-size: 20px; font-weight: bold;'>-</span>")

        for card in [self.card_urgent, self.card_severe, self.card_cost, self.card_rate]:
            title = card.text().split('\n')[0]
            card.setText(f"{title}\n<span style='font-size: 20px; font-weight: bold;'>-</span>")

        self.type_table.setRowCount(0)
        self.severity_table.setRowCount(0)
        self.priority_table.setRowCount(0)
        self.urgent_table.setRowCount(0)
        self.risk_table.setRowCount(0)
        self.warning_widget.clear()

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
