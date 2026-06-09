import os
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox,
    QGroupBox, QFormLayout, QTextEdit, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QAbstractItemView, QFileDialog,
    QScrollArea, QGridLayout, QDateEdit, QTabWidget, QFrame,
    QSplitter, QStyle, QProgressBar
)
from PySide6.QtCore import Qt, QDate, QSize
from PySide6.QtGui import QFont, QBrush, QColor, QPixmap, QIcon

from database import (
    DatabaseManager, DiseaseRecord, DiseaseStatusHistory,
    DiseaseAcceptanceRecord, DiseasePhotoArchive, WarningRecord,
    ACCEPTANCE_RESULTS, ACCEPTANCE_RESULT_PASS, ACCEPTANCE_RESULT_FAIL,
    ACCEPTANCE_RESULT_PARTIAL,
    PHOTO_TYPES, PHOTO_TYPE_BEFORE, PHOTO_TYPE_AFTER, PHOTO_TYPE_PROCESS,
    PHOTO_STAGES, PHOTO_STAGE_DISCOVERY, PHOTO_STAGE_DIAGNOSIS,
    PHOTO_STAGE_TREATMENT, PHOTO_STAGE_ACCEPTANCE, PHOTO_STAGE_REVIEW,
    DISEASE_STATUSES, DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING,
    DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
    DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED,
    WARNING_TYPES, WARNING_LEVELS, WARNING_LEVEL_INFO,
    WARNING_LEVEL_WARNING, WARNING_LEVEL_DANGER, WARNING_LEVEL_CRITICAL,
)
from services import DiseaseService


class DiseaseAcceptanceDialog(QDialog):
    def __init__(self, parent=None, disease_id: int = None,
                 db_manager: DatabaseManager = None, is_review: bool = False):
        super().__init__(parent)
        self.setWindowTitle("复查验收" if is_review else "整改验收")
        self.setMinimumWidth(500)
        self.disease_id = disease_id
        self.db = db_manager
        self.is_review = is_review
        self._photo_paths = []
        self.service = DiseaseService(db_manager) if db_manager else None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        form_layout = QVBoxLayout(scroll_content)

        basic_group = QGroupBox("验收信息")
        basic_form = QFormLayout()

        self.result_combo = QComboBox()
        for code, name in ACCEPTANCE_RESULTS:
            self.result_combo.addItem(name, code)
        basic_form.addRow("验收结果 *", self.result_combo)

        self.acceptance_date = QDateEdit()
        self.acceptance_date.setCalendarPopup(True)
        self.acceptance_date.setDate(QDate.currentDate())
        basic_form.addRow("验收日期", self.acceptance_date)

        self.acceptance_edit = QLineEdit()
        self.acceptance_edit.setPlaceholderText("请输入验收人姓名")
        basic_form.addRow("验收人 *", self.acceptance_edit)

        basic_group.setLayout(basic_form)
        form_layout.addWidget(basic_group)

        opinion_group = QGroupBox("验收意见")
        opinion_layout = QVBoxLayout(opinion_group)

        self.opinion_edit = QTextEdit()
        self.opinion_edit.setPlaceholderText("请详细描述验收意见...")
        self.opinion_edit.setMaximumHeight(120)
        opinion_layout.addWidget(self.opinion_edit)

        form_layout.addWidget(opinion_group)

        photo_group = QGroupBox("验收照片")
        photo_layout = QVBoxLayout(photo_group)

        photo_btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加照片")
        btn_add.clicked.connect(self._add_photo)
        btn_remove = QPushButton("移除选中")
        btn_remove.clicked.connect(self._remove_photo)
        photo_btn_layout.addWidget(btn_add)
        photo_btn_layout.addWidget(btn_remove)
        photo_btn_layout.addStretch()
        photo_layout.addLayout(photo_btn_layout)

        self.photo_list = QListWidget()
        self.photo_list.setViewMode(QListWidget.IconMode)
        self.photo_list.setIconSize(QSize(120, 90))
        self.photo_list.setResizeMode(QListWidget.Adjust)
        self.photo_list.setMovement(QListWidget.Static)
        self.photo_list.setSpacing(10)
        self.photo_list.setFixedHeight(140)
        photo_layout.addWidget(self.photo_list)

        form_layout.addWidget(photo_group)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认验收")
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

    def get_data(self) -> dict:
        return {
            "disease_id": self.disease_id,
            "acceptance_result": self.result_combo.currentData(),
            "acceptance_date": self.acceptance_date.date().toString("yyyy-MM-dd"),
            "acceptance_person": self.acceptance_edit.text().strip(),
            "acceptance_opinion": self.opinion_edit.toPlainText().strip(),
            "photo_paths": "|".join(self._photo_paths),
            "is_review": self.is_review,
        }

    def accept(self):
        data = self.get_data()
        if not data["acceptance_result"]:
            QMessageBox.warning(self, "提示", "请选择验收结果")
            return
        if not data["acceptance_person"]:
            QMessageBox.warning(self, "提示", "请输入验收人")
            return
        super().accept()


class WorkflowStepWidget(QWidget):
    def __init__(self, steps: list, current_status: str = None, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.current_status = current_status
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        status_map = {code: name for code, name in DISEASE_STATUSES}

        for i, step in enumerate(self.steps):
            status_code = step["status"]
            status_name = status_map.get(status_code, status_code)
            is_completed = self._is_step_completed(status_code)
            is_current = status_code == self.current_status

            step_widget = self._create_step(
                status_name, i + 1, is_completed, is_current,
                i == 0, i == len(self.steps) - 1
            )
            layout.addWidget(step_widget)

    def _is_step_completed(self, status_code: str) -> bool:
        if not self.current_status:
            return False

        step_order = [s["status"] for s in self.steps]
        try:
            current_idx = step_order.index(self.current_status)
            step_idx = step_order.index(status_code)
            return step_idx < current_idx
        except ValueError:
            return False

    def _create_step(self, name: str, num: int, is_completed: bool,
                     is_current: bool, is_first: bool, is_last: bool) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if not is_first:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFixedWidth(30)
            if is_completed:
                line.setStyleSheet("background-color: #2ecc71;")
            else:
                line.setStyleSheet("background-color: #bdc3c7;")
            layout.addWidget(line)

        circle = QLabel()
        circle.setFixedSize(28, 28)
        circle.setAlignment(Qt.AlignCenter)
        circle.setText(str(num))

        if is_current:
            circle.setStyleSheet("""
                QLabel {
                    background-color: #3498db;
                    color: white;
                    border-radius: 14px;
                    font-weight: bold;
                    border: 2px solid #2980b9;
                }
            """)
        elif is_completed:
            circle.setStyleSheet("""
                QLabel {
                    background-color: #2ecc71;
                    color: white;
                    border-radius: 14px;
                    font-weight: bold;
                }
            """)
        else:
            circle.setStyleSheet("""
                QLabel {
                    background-color: #ecf0f1;
                    color: #7f8c8d;
                    border-radius: 14px;
                }
            """)

        layout.addWidget(circle)

        label = QLabel(name)
        if is_current:
            label.setStyleSheet("color: #2980b9; font-weight: bold;")
        elif is_completed:
            label.setStyleSheet("color: #27ae60;")
        else:
            label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(label)

        if not is_last:
            pass

        return widget

    def set_current_status(self, status: str):
        self.current_status = status
        self._clear_layout()
        self._init_ui()

    def _clear_layout(self):
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class DiseasePhotoCompareWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_disease_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("修缮前后对比"))
        top_bar.addStretch()
        layout.addLayout(top_bar)

        compare_layout = QHBoxLayout()

        before_group = QGroupBox("修缮前")
        before_layout = QVBoxLayout(before_group)
        self.before_list = QListWidget()
        self.before_list.setViewMode(QListWidget.IconMode)
        self.before_list.setIconSize(QSize(150, 120))
        self.before_list.setResizeMode(QListWidget.Adjust)
        self.before_list.setMovement(QListWidget.Static)
        self.before_list.setSpacing(8)
        before_layout.addWidget(self.before_list)
        compare_layout.addWidget(before_group, 1)

        after_group = QGroupBox("修缮后")
        after_layout = QVBoxLayout(after_group)
        self.after_list = QListWidget()
        self.after_list.setViewMode(QListWidget.IconMode)
        self.after_list.setIconSize(QSize(150, 120))
        self.after_list.setResizeMode(QListWidget.Adjust)
        self.after_list.setMovement(QListWidget.Static)
        self.after_list.setSpacing(8)
        after_layout.addWidget(self.after_list)
        compare_layout.addWidget(after_group, 1)

        layout.addLayout(compare_layout, 1)

    def set_disease(self, disease_id: int):
        self.current_disease_id = disease_id
        self._refresh()

    def _refresh(self):
        self.before_list.clear()
        self.after_list.clear()

        if not self.current_disease_id or not self.db:
            return

        before_photos = self.db.get_disease_photos_by_type(
            self.current_disease_id, PHOTO_TYPE_BEFORE
        )
        after_photos = self.db.get_disease_photos_by_type(
            self.current_disease_id, PHOTO_TYPE_AFTER
        )

        for photo in before_photos:
            self._add_photo_item(self.before_list, photo)

        for photo in after_photos:
            self._add_photo_item(self.after_list, photo)

    def _add_photo_item(self, list_widget: QListWidget, photo: DiseasePhotoArchive):
        if not photo.photo_path or not os.path.exists(photo.photo_path):
            return

        item = QListWidgetItem()
        pixmap = QPixmap(photo.photo_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(150, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            item.setIcon(QIcon(scaled))
        item.setText(os.path.basename(photo.photo_path))
        item.setToolTip(f"{photo.photo_path}\n{photo.stage or ''}")
        list_widget.addItem(item)

    def clear(self):
        self.before_list.clear()
        self.after_list.clear()
        self.current_disease_id = None


class DiseaseStatusHistoryWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_disease_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["序号", "原状态", "新状态", "操作人", "操作时间", "备注"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.history_table)

    def set_disease(self, disease_id: int):
        self.current_disease_id = disease_id
        self._refresh()

    def _refresh(self):
        self.history_table.setRowCount(0)

        if not self.current_disease_id or not self.db:
            return

        history = self.db.get_disease_status_history(self.current_disease_id)

        status_map = {code: name for code, name in DISEASE_STATUSES}

        self.history_table.setRowCount(len(history))
        for row, record in enumerate(history):
            items = [
                QTableWidgetItem(str(row + 1)),
                QTableWidgetItem(status_map.get(record.from_status, record.from_status) if record.from_status else "-"),
                QTableWidgetItem(status_map.get(record.to_status, record.to_status)),
                QTableWidgetItem(record.operator or "-"),
                QTableWidgetItem(record.created_at),
                QTableWidgetItem(record.remark or "-"),
            ]
            for col, item in enumerate(items):
                self.history_table.setItem(row, col, item)

    def clear(self):
        self.history_table.setRowCount(0)
        self.current_disease_id = None


class WarningListWidget(QWidget):
    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_building_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        filter_bar = QHBoxLayout()
        filter_bar.addWidget(QLabel("类型："))
        self.type_combo = QComboBox()
        self.type_combo.addItem("全部", None)
        for code, name in WARNING_TYPES:
            self.type_combo.addItem(name, code)
        self.type_combo.currentIndexChanged.connect(self._refresh)
        filter_bar.addWidget(self.type_combo)

        filter_bar.addWidget(QLabel("级别："))
        self.level_combo = QComboBox()
        self.level_combo.addItem("全部", None)
        for code, name in WARNING_LEVELS:
            self.level_combo.addItem(name, code)
        self.level_combo.currentIndexChanged.connect(self._refresh)
        filter_bar.addWidget(self.level_combo)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        self.warning_table = QTableWidget()
        self.warning_table.setColumnCount(6)
        self.warning_table.setHorizontalHeaderLabels(
            ["ID", "类型", "级别", "标题", "关联对象", "创建时间", "状态"]
        )
        self.warning_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.warning_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.warning_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.warning_table, 1)

    def set_building(self, building_id: int):
        self.current_building_id = building_id
        self._refresh()

    def _refresh(self):
        self.warning_table.setRowCount(0)

        if not self.current_building_id or not self.db:
            return

        type_filter = self.type_combo.currentData()
        level_filter = self.level_combo.currentData()

        warnings = self.db.get_warning_records(
            building_id=self.current_building_id,
            warning_type=type_filter,
            warning_level=level_filter,
        )

        type_map = {code: name for code, name in WARNING_TYPES}
        level_map = {code: name for code, name in WARNING_LEVELS}

        level_color_map = {
            WARNING_LEVEL_INFO: QColor("#3498db"),
            WARNING_LEVEL_WARNING: QColor("#f39c12"),
            WARNING_LEVEL_DANGER: QColor("#e67e22"),
            WARNING_LEVEL_CRITICAL: QColor("#e74c3c"),
        }

        self.warning_table.setRowCount(len(warnings))
        for row, warn in enumerate(warnings):
            related_text = "-"
            if warn.component_code:
                related_text = f"构件: {warn.component_code}"
            elif warn.disease_id:
                related_text = f"病害: #{warn.disease_id}"

            status_text = "未读" if not warn.is_read else "已读"

            items = [
                QTableWidgetItem(str(warn.id)),
                QTableWidgetItem(type_map.get(warn.warning_type, warn.warning_type)),
                QTableWidgetItem(level_map.get(warn.warning_level, warn.warning_level)),
                QTableWidgetItem(warn.title),
                QTableWidgetItem(related_text),
                QTableWidgetItem(warn.created_at),
                QTableWidgetItem(status_text),
            ]

            color = level_color_map.get(warn.warning_level, QColor("black"))
            for item in items:
                item.setForeground(QBrush(color))

            for col, item in enumerate(items):
                self.warning_table.setItem(row, col, item)

    def clear(self):
        self.warning_table.setRowCount(0)
        self.current_building_id = None
