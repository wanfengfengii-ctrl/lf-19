import sqlite3
import os
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import (
    Building, Component, MortiseTenon, MeasurementRecord,
    RecheckTask, ImportBatch, ImportError,
    RECHECK_STATUS_PENDING, RECHECK_STATUS_IN_PROGRESS,
    RECHECK_STATUS_COMPLETED, RECHECK_STATUS_CANCELLED,
    DiseaseRecord, DiseaseTreatment, DiseaseStats,
    DiseaseStatusHistory, DiseaseAcceptanceRecord,
    DiseasePhotoArchive, WarningRecord, OperationLog,
    DeviationDiseaseLink,
    DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_REVIEWED,
    DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_ASSIGNED,
    DISEASE_STATUS_ACCEPTED, DISEASE_STATUS_ARCHIVED,
    DISEASE_STATUS_REJECTED,
    DISEASE_TYPES, DISEASE_SEVERITIES, PRIORITIES,
    ACCEPTANCE_RESULT_PASS, ACCEPTANCE_RESULT_FAIL,
    PHOTO_TYPE_BEFORE, PHOTO_TYPE_AFTER, PHOTO_TYPE_PROCESS,
    WARNING_LEVEL_INFO, WARNING_LEVEL_WARNING, WARNING_LEVEL_DANGER,
    WARNING_TYPE_DEVIATION, WARNING_TYPE_DISEASE, WARNING_TYPE_RISK,
    MODULE_DISEASE, ACTION_STATUS_CHANGE,
    RISK_LEVEL_LOW, RISK_LEVEL_MEDIUM, RISK_LEVEL_HIGH, RISK_LEVEL_CRITICAL,
)


class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "building_data.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = None
        self._connect()
        self._init_tables()
        self._migrate_tables()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _init_tables(self):
        cursor = self.conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE,
            location TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            name TEXT DEFAULT '',
            component_type TEXT DEFAULT '',
            design_length REAL DEFAULT 0,
            design_width REAL DEFAULT 0,
            design_angle REAL DEFAULT 0,
            deviation_threshold REAL DEFAULT 5.0,
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
            UNIQUE(building_id, code)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mortise_tenons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            mortise_component_id INTEGER NOT NULL,
            tenon_component_id INTEGER NOT NULL,
            joint_type TEXT DEFAULT '',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
            FOREIGN KEY (mortise_component_id) REFERENCES components(id) ON DELETE CASCADE,
            FOREIGN KEY (tenon_component_id) REFERENCES components(id) ON DELETE CASCADE,
            UNIQUE(building_id, mortise_component_id, tenon_component_id)
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS measurement_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id INTEGER NOT NULL,
            component_code TEXT NOT NULL,
            length REAL NOT NULL,
            width REAL NOT NULL,
            angle REAL NOT NULL,
            measure_time TEXT NOT NULL,
            version INTEGER DEFAULT 1,
            is_recheck INTEGER DEFAULT 0,
            remark TEXT DEFAULT '',
            batch_id INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE,
            FOREIGN KEY (batch_id) REFERENCES import_batches(id) ON DELETE SET NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            total_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'draft',
            auto_recheck INTEGER DEFAULT 0,
            imported_by TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS import_errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            row_number INTEGER NOT NULL,
            component_code TEXT DEFAULT '',
            error_type TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            row_data TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (batch_id) REFERENCES import_batches(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS recheck_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            component_code TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            assigned_to TEXT DEFAULT '',
            priority TEXT DEFAULT 'normal',
            reason TEXT DEFAULT '',
            recheck_result TEXT DEFAULT '',
            recheck_record_id INTEGER DEFAULT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE,
            FOREIGN KEY (record_id) REFERENCES measurement_records(id) ON DELETE CASCADE,
            FOREIGN KEY (recheck_record_id) REFERENCES measurement_records(id) ON DELETE SET NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            component_code TEXT NOT NULL,
            disease_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            description TEXT DEFAULT '',
            location TEXT DEFAULT '',
            size_length REAL DEFAULT 0,
            size_width REAL DEFAULT 0,
            size_depth REAL DEFAULT 0,
            photo_paths TEXT DEFAULT '',
            repair_suggestion TEXT DEFAULT '',
            repair_method TEXT DEFAULT '',
            estimated_cost REAL DEFAULT 0,
            handler TEXT DEFAULT '',
            plan_date TEXT DEFAULT '',
            complete_date TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_id INTEGER NOT NULL,
            treatment_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            handler TEXT DEFAULT '',
            treatment_date TEXT DEFAULT '',
            photo_paths TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (disease_id) REFERENCES disease_records(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_id INTEGER NOT NULL,
            from_status TEXT NOT NULL,
            to_status TEXT NOT NULL,
            operator TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (disease_id) REFERENCES disease_records(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_acceptance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_id INTEGER NOT NULL,
            acceptance_result TEXT NOT NULL,
            acceptance_opinion TEXT DEFAULT '',
            acceptor TEXT DEFAULT '',
            acceptance_date TEXT DEFAULT '',
            photo_paths TEXT DEFAULT '',
            remark TEXT DEFAULT '',
            is_review INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (disease_id) REFERENCES disease_records(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS disease_photo_archives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disease_id INTEGER NOT NULL,
            photo_path TEXT NOT NULL,
            photo_type TEXT DEFAULT '',
            photo_stage TEXT DEFAULT '',
            description TEXT DEFAULT '',
            upload_time TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY (disease_id) REFERENCES disease_records(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS warning_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            component_code TEXT NOT NULL,
            warning_type TEXT NOT NULL,
            warning_level TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            source TEXT DEFAULT '',
            related_disease_id INTEGER DEFAULT NULL,
            related_record_id INTEGER DEFAULT NULL,
            is_read INTEGER DEFAULT 0,
            is_handled INTEGER DEFAULT 0,
            handle_remark TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            handled_at TEXT DEFAULT '',
            FOREIGN KEY (building_id) REFERENCES buildings(id) ON DELETE CASCADE,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER DEFAULT NULL,
            operator TEXT DEFAULT '',
            detail TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS deviation_disease_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component_id INTEGER NOT NULL UNIQUE,
            component_code TEXT NOT NULL,
            deviation_level TEXT NOT NULL,
            disease_count INTEGER DEFAULT 0,
            risk_level TEXT NOT NULL,
            assessment TEXT DEFAULT '',
            suggestion TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_measurement_component_idx ON measurement_records(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_measurement_code_idx ON measurement_records(component_code)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_measurement_batch_idx ON measurement_records(batch_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_import_batch_building_idx ON import_batches(building_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_import_error_batch_idx ON import_errors(batch_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recheck_building_idx ON recheck_tasks(building_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recheck_status_idx ON recheck_tasks(status)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_recheck_component_idx ON recheck_tasks(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_building_idx ON disease_records(building_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_component_idx ON disease_records(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_status_idx ON disease_records(status)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_type_idx ON disease_records(disease_type)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_severity_idx ON disease_records(severity)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_treatment_disease_idx ON disease_treatments(disease_id)
        ''')

        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_status_history_disease_idx ON disease_status_history(disease_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_acceptance_disease_idx ON disease_acceptance_records(disease_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_photo_disease_idx ON disease_photo_archives(disease_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_disease_photo_type_idx ON disease_photo_archives(photo_type)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_warning_building_idx ON warning_records(building_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_warning_component_idx ON warning_records(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_warning_type_idx ON warning_records(warning_type)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_warning_level_idx ON warning_records(warning_level)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_operation_module_idx ON operation_logs(module)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_operation_action_idx ON operation_logs(action)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_operation_created_idx ON operation_logs(created_at)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_deviation_disease_component_idx ON deviation_disease_links(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_deviation_disease_risk_idx ON deviation_disease_links(risk_level)
        ''')

        self.conn.commit()

    def _migrate_tables(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(measurement_records)")
            columns = [row['name'] for row in cursor.fetchall()]
            if 'batch_id' not in columns:
                cursor.execute("ALTER TABLE measurement_records ADD COLUMN batch_id INTEGER DEFAULT NULL REFERENCES import_batches(id) ON DELETE SET NULL")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def close(self):
        if self.conn:
            self.conn.close()

    def add_building(self, building: Building) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO buildings (name, code, location, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (building.name, building.code, building.location, building.description, building.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_building(self, building: Building) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE buildings SET name=?, code=?, location=?, description=? WHERE id=?",
            (building.name, building.code, building.location, building.description, building.id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_building(self, building_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM buildings WHERE id=?", (building_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_building(self, building_id: int) -> Optional[Building]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM buildings WHERE id=?", (building_id,))
        row = cursor.fetchone()
        if row:
            return Building(**dict(row))
        return None

    def get_all_buildings(self) -> List[Building]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM buildings ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [Building(**dict(row)) for row in rows]

    def add_component(self, component: Component) -> int:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO components 
                   (building_id, code, name, component_type, design_length, design_width, 
                    design_angle, deviation_threshold, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (component.building_id, component.code, component.name, component.component_type,
                 component.design_length, component.design_width, component.design_angle,
                 component.deviation_threshold, component.description, component.created_at)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"构件编号 {component.code} 在该建筑中已存在")

    def update_component(self, component: Component) -> bool:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """UPDATE components SET code=?, name=?, component_type=?, design_length=?, 
                   design_width=?, design_angle=?, deviation_threshold=?, description=?
                   WHERE id=?""",
                (component.code, component.name, component.component_type,
                 component.design_length, component.design_width, component.design_angle,
                 component.deviation_threshold, component.description, component.id)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValueError(f"构件编号 {component.code} 在该建筑中已存在")

    def delete_component(self, component_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM components WHERE id=?", (component_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_component(self, component_id: int) -> Optional[Component]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM components WHERE id=?", (component_id,))
        row = cursor.fetchone()
        if row:
            return Component(**dict(row))
        return None

    def get_component_by_code(self, building_id: int, code: str) -> Optional[Component]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM components WHERE building_id=? AND code=?", (building_id, code))
        row = cursor.fetchone()
        if row:
            return Component(**dict(row))
        return None

    def get_components_by_building(self, building_id: int) -> List[Component]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM components WHERE building_id=? ORDER BY code", (building_id,))
        rows = cursor.fetchall()
        return [Component(**dict(row)) for row in rows]

    def add_mortise_tenon(self, mt: MortiseTenon) -> int:
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO mortise_tenons 
                   (building_id, mortise_component_id, tenon_component_id, joint_type, description, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (mt.building_id, mt.mortise_component_id, mt.tenon_component_id,
                 mt.joint_type, mt.description, mt.created_at)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("该榫卯关系已存在（同一对构件不能重复创建榫卯关系）")

    def delete_mortise_tenon(self, mt_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM mortise_tenons WHERE id=?", (mt_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_mortise_tenons_by_building(self, building_id: int) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mt.*, 
                   mc.code as mortise_code, mc.name as mortise_name,
                   tc.code as tenon_code, tc.name as tenon_name
            FROM mortise_tenons mt
            JOIN components mc ON mt.mortise_component_id = mc.id
            JOIN components tc ON mt.tenon_component_id = tc.id
            WHERE mt.building_id=?
            ORDER BY mt.created_at DESC
        """, (building_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def add_measurement_record(self, record: MeasurementRecord) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO measurement_records
               (component_id, component_code, length, width, angle, measure_time,
                version, is_recheck, remark, batch_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.component_id, record.component_code, record.length, record.width,
             record.angle, record.measure_time, record.version,
             1 if record.is_recheck else 0, record.remark, record.batch_id, record.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_latest_version(self, component_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(version) as max_ver FROM measurement_records WHERE component_id=?",
            (component_id,)
        )
        row = cursor.fetchone()
        if row and row["max_ver"]:
            return row["max_ver"]
        return 0

    def get_measurements_by_component(self, component_id: int) -> List[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurement_records WHERE component_id=? ORDER BY version DESC",
            (component_id,)
        )
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            records.append(MeasurementRecord(**d))
        return records

    def get_latest_measurement(self, component_id: int) -> Optional[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurement_records WHERE component_id=? ORDER BY version DESC LIMIT 1",
            (component_id,)
        )
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            return MeasurementRecord(**d)
        return None

    def get_measurement_record(self, record_id: int) -> Optional[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM measurement_records WHERE id=?", (record_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            return MeasurementRecord(**d)
        return None

    def get_measurements_by_building(self, building_id: int) -> List[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mr.* FROM measurement_records mr
            JOIN components c ON mr.component_id = c.id
            WHERE c.building_id=?
            ORDER BY mr.component_code, mr.version DESC
        """, (building_id,))
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            records.append(MeasurementRecord(**d))
        return records

    def mark_for_recheck(self, record_id: int, remark: str = "") -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE measurement_records SET is_recheck=1, remark=? WHERE id=?",
            (remark, record_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def clear_recheck_mark(self, record_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE measurement_records SET is_recheck=0 WHERE id=?",
            (record_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_recheck_records(self, building_id: int) -> List[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mr.* FROM measurement_records mr
            JOIN components c ON mr.component_id = c.id
            WHERE c.building_id=? AND mr.is_recheck=1
            ORDER BY mr.component_code
        """, (building_id,))
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            records.append(MeasurementRecord(**d))
        return records

    def check_mortise_tenon_exists(self, building_id: int,
                                   mortise_component_id: int,
                                   tenon_component_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM mortise_tenons
            WHERE building_id=? AND mortise_component_id=? AND tenon_component_id=?
        """, (building_id, mortise_component_id, tenon_component_id))
        return cursor.fetchone() is not None

    def add_import_batch(self, batch: ImportBatch) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO import_batches
               (building_id, file_name, total_count, success_count, error_count,
                status, auto_recheck, imported_by, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (batch.building_id, batch.file_name, batch.total_count, batch.success_count,
             batch.error_count, batch.status, 1 if batch.auto_recheck else 0,
             batch.imported_by, batch.remark, batch.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_import_batch(self, batch_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        cursor = self.conn.cursor()
        fields = []
        values = []
        for key, value in kwargs.items():
            if key == 'auto_recheck':
                value = 1 if value else 0
            fields.append(f"{key}=?")
            values.append(value)
        values.append(batch_id)
        cursor.execute(f"UPDATE import_batches SET {', '.join(fields)} WHERE id=?", values)
        self.conn.commit()
        return cursor.rowcount > 0

    def get_import_batch(self, batch_id: int) -> Optional[ImportBatch]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM import_batches WHERE id=?", (batch_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            d['auto_recheck'] = bool(d['auto_recheck'])
            return ImportBatch(**d)
        return None

    def get_import_batches_by_building(self, building_id: int) -> List[ImportBatch]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM import_batches WHERE building_id=? ORDER BY created_at DESC",
            (building_id,)
        )
        rows = cursor.fetchall()
        batches = []
        for row in rows:
            d = dict(row)
            d['auto_recheck'] = bool(d['auto_recheck'])
            batches.append(ImportBatch(**d))
        return batches

    def add_import_error(self, error: ImportError) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO import_errors
               (batch_id, row_number, component_code, error_type,
                error_message, row_data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (error.batch_id, error.row_number, error.component_code, error.error_type,
             error.error_message, error.row_data, error.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_import_errors_by_batch(self, batch_id: int) -> List[ImportError]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM import_errors WHERE batch_id=? ORDER BY row_number",
            (batch_id,)
        )
        rows = cursor.fetchall()
        return [ImportError(**dict(row)) for row in rows]

    def add_recheck_task(self, task: RecheckTask) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO recheck_tasks
               (building_id, component_id, component_code, record_id, status,
                assigned_to, priority, reason, recheck_result, recheck_record_id,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (task.building_id, task.component_id, task.component_code, task.record_id,
             task.status, task.assigned_to, task.priority, task.reason,
             task.recheck_result, task.recheck_record_id,
             task.created_at, task.updated_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_recheck_task(self, task_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        cursor = self.conn.cursor()
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key}=?")
            values.append(value)
        values.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        fields.append("updated_at=?")
        values.append(task_id)
        cursor.execute(f"UPDATE recheck_tasks SET {', '.join(fields)} WHERE id=?", values)
        self.conn.commit()
        return cursor.rowcount > 0

    def get_recheck_task(self, task_id: int) -> Optional[RecheckTask]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM recheck_tasks WHERE id=?", (task_id,))
        row = cursor.fetchone()
        if row:
            d = dict(row)
            return RecheckTask(**d)
        return None

    def get_recheck_tasks_by_building(self, building_id: int,
                                      status: str = None) -> List[RecheckTask]:
        cursor = self.conn.cursor()
        if status:
            cursor.execute(
                "SELECT * FROM recheck_tasks WHERE building_id=? AND status=? ORDER BY created_at DESC",
                (building_id, status)
            )
        else:
            cursor.execute(
                "SELECT * FROM recheck_tasks WHERE building_id=? ORDER BY created_at DESC",
                (building_id,)
            )
        rows = cursor.fetchall()
        return [RecheckTask(**dict(row)) for row in rows]

    def get_recheck_tasks_by_component(self, component_id: int) -> List[RecheckTask]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM recheck_tasks WHERE component_id=? ORDER BY created_at DESC",
            (component_id,)
        )
        rows = cursor.fetchall()
        return [RecheckTask(**dict(row)) for row in rows]

    def get_recheck_statistics(self, building_id: int) -> Dict[str, int]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM recheck_tasks
            WHERE building_id=? GROUP BY status
        """, (building_id,))
        rows = cursor.fetchall()
        stats = {"pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0, "total": 0}
        for row in rows:
            stats[row["status"]] = row["cnt"]
            stats["total"] += row["cnt"]
        return stats

    def get_measurements_by_batch(self, batch_id: int) -> List[MeasurementRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM measurement_records WHERE batch_id=? ORDER BY component_code, version DESC",
            (batch_id,)
        )
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_recheck'] = bool(d['is_recheck'])
            records.append(MeasurementRecord(**d))
        return records

    def delete_import_batch(self, batch_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM import_batches WHERE id=?", (batch_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def has_active_recheck_task(self, component_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id FROM recheck_tasks
            WHERE component_id=? AND status IN ('pending', 'in_progress')
            LIMIT 1
        """, (component_id,))
        return cursor.fetchone() is not None

    def add_disease_record(self, disease: DiseaseRecord) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO disease_records
               (building_id, component_id, component_code, disease_type, severity,
                priority, status, description, location, size_length, size_width,
                size_depth, photo_paths, repair_suggestion, repair_method,
                estimated_cost, handler, plan_date, complete_date, remark,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (disease.building_id, disease.component_id, disease.component_code,
             disease.disease_type, disease.severity, disease.priority, disease.status,
             disease.description, disease.location, disease.size_length, disease.size_width,
             disease.size_depth, disease.photo_paths, disease.repair_suggestion,
             disease.repair_method, disease.estimated_cost, disease.handler,
             disease.plan_date, disease.complete_date, disease.remark,
             disease.created_at, disease.updated_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_disease_record(self, disease: DiseaseRecord) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            """UPDATE disease_records SET 
               disease_type=?, severity=?, priority=?, status=?, description=?,
               location=?, size_length=?, size_width=?, size_depth=?,
               photo_paths=?, repair_suggestion=?, repair_method=?,
               estimated_cost=?, handler=?, plan_date=?, complete_date=?,
               remark=?, updated_at=?
               WHERE id=?""",
            (disease.disease_type, disease.severity, disease.priority, disease.status,
             disease.description, disease.location, disease.size_length, disease.size_width,
             disease.size_depth, disease.photo_paths, disease.repair_suggestion,
             disease.repair_method, disease.estimated_cost, disease.handler,
             disease.plan_date, disease.complete_date, disease.remark,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), disease.id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_disease_record(self, disease_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM disease_records WHERE id=?", (disease_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_disease_record(self, disease_id: int) -> Optional[DiseaseRecord]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM disease_records WHERE id=?", (disease_id,))
        row = cursor.fetchone()
        if row:
            return DiseaseRecord(**dict(row))
        return None

    def get_diseases_by_building(self, building_id: int,
                                 status: str = None,
                                 disease_type: str = None,
                                 severity: str = None) -> List[DiseaseRecord]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM disease_records WHERE building_id=?"
        params = [building_id]
        if status:
            query += " AND status=?"
            params.append(status)
        if disease_type:
            query += " AND disease_type=?"
            params.append(disease_type)
        if severity:
            query += " AND severity=?"
            params.append(severity)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [DiseaseRecord(**dict(row)) for row in rows]

    def get_diseases_by_component(self, component_id: int) -> List[DiseaseRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_records WHERE component_id=? ORDER BY created_at DESC",
            (component_id,)
        )
        rows = cursor.fetchall()
        return [DiseaseRecord(**dict(row)) for row in rows]

    def get_disease_statistics(self, building_id: int) -> DiseaseStats:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT status, COUNT(*) as cnt FROM disease_records
            WHERE building_id=? GROUP BY status
        """, (building_id,))
        status_rows = cursor.fetchall()
        status_counts = {
            "pending": 0, "in_progress": 0, "completed": 0, "reviewed": 0,
            "discovered": 0, "assigned": 0, "accepted": 0,
            "archived": 0, "rejected": 0
        }
        total = 0
        for row in status_rows:
            status_counts[row["status"]] = row["cnt"]
            total += row["cnt"]

        cursor.execute("""
            SELECT disease_type, COUNT(*) as cnt FROM disease_records
            WHERE building_id=? GROUP BY disease_type
        """, (building_id,))
        type_rows = cursor.fetchall()
        by_type = {}
        for row in type_rows:
            by_type[row["disease_type"]] = row["cnt"]

        cursor.execute("""
            SELECT severity, COUNT(*) as cnt FROM disease_records
            WHERE building_id=? GROUP BY severity
        """, (building_id,))
        severity_rows = cursor.fetchall()
        by_severity = {}
        for row in severity_rows:
            by_severity[row["severity"]] = row["cnt"]

        cursor.execute("""
            SELECT priority, COUNT(*) as cnt FROM disease_records
            WHERE building_id=? GROUP BY priority
        """, (building_id,))
        priority_rows = cursor.fetchall()
        by_priority = {}
        for row in priority_rows:
            by_priority[row["priority"]] = row["cnt"]

        cursor.execute("""
            SELECT COALESCE(SUM(estimated_cost), 0) as total_cost
            FROM disease_records WHERE building_id=?
        """, (building_id,))
        cost_row = cursor.fetchone()
        total_cost = cost_row["total_cost"] if cost_row else 0.0

        return DiseaseStats(
            total_count=total,
            pending_count=status_counts.get("pending", 0),
            in_progress_count=status_counts.get("in_progress", 0),
            completed_count=status_counts.get("completed", 0),
            reviewed_count=status_counts.get("reviewed", 0),
            by_type=by_type,
            by_severity=by_severity,
            by_priority=by_priority,
            total_estimated_cost=total_cost,
            discovered_count=status_counts.get("discovered", 0),
            assigned_count=status_counts.get("assigned", 0),
            accepted_count=status_counts.get("accepted", 0),
            archived_count=status_counts.get("archived", 0),
            rejected_count=status_counts.get("rejected", 0),
            by_status=status_counts.copy()
        )


    def add_disease_treatment(self, treatment: DiseaseTreatment) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO disease_treatments
               (disease_id, treatment_type, description, handler,
                treatment_date, photo_paths, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (treatment.disease_id, treatment.treatment_type, treatment.description,
             treatment.handler, treatment.treatment_date, treatment.photo_paths,
             treatment.remark, treatment.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def delete_disease_treatment(self, treatment_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM disease_treatments WHERE id=?", (treatment_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_treatments_by_disease(self, disease_id: int) -> List[DiseaseTreatment]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_treatments WHERE disease_id=? ORDER BY created_at DESC",
            (disease_id,)
        )
        rows = cursor.fetchall()
        return [DiseaseTreatment(**dict(row)) for row in rows]

    # ==================== 病害状态历史相关方法 ====================

    def add_disease_status_history(self, history: DiseaseStatusHistory) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO disease_status_history
               (disease_id, from_status, to_status, operator, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (history.disease_id, history.from_status, history.to_status,
             history.operator, history.remark, history.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_status_history_by_disease(self, disease_id: int) -> List[DiseaseStatusHistory]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_status_history WHERE disease_id=? ORDER BY created_at DESC",
            (disease_id,)
        )
        rows = cursor.fetchall()
        return [DiseaseStatusHistory(**dict(row)) for row in rows]

    def get_latest_status_history(self, disease_id: int) -> Optional[DiseaseStatusHistory]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_status_history WHERE disease_id=? ORDER BY created_at DESC LIMIT 1",
            (disease_id,)
        )
        row = cursor.fetchone()
        if row:
            return DiseaseStatusHistory(**dict(row))
        return None

    # ==================== 病害验收记录相关方法 ====================

    def add_disease_acceptance(self, record: DiseaseAcceptanceRecord) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO disease_acceptance_records
               (disease_id, acceptance_result, acceptance_opinion, acceptor,
                acceptance_date, photo_paths, remark, is_review, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.disease_id, record.acceptance_result, record.acceptance_opinion,
             record.acceptor, record.acceptance_date, record.photo_paths,
             record.remark, 1 if record.is_review else 0, record.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_acceptance_by_disease(self, disease_id: int) -> List[DiseaseAcceptanceRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_acceptance_records WHERE disease_id=? ORDER BY created_at DESC",
            (disease_id,)
        )
        rows = cursor.fetchall()
        return [DiseaseAcceptanceRecord(**dict(row)) for row in rows]

    def get_latest_acceptance(self, disease_id: int) -> Optional[DiseaseAcceptanceRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_acceptance_records WHERE disease_id=? ORDER BY created_at DESC LIMIT 1",
            (disease_id,)
        )
        row = cursor.fetchone()
        if row:
            return DiseaseAcceptanceRecord(**dict(row))
        return None

    # ==================== 病害图片归档相关方法 ====================

    def add_disease_photo(self, photo: DiseasePhotoArchive) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO disease_photo_archives
               (disease_id, photo_path, photo_type, photo_stage, description,
                upload_time, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (photo.disease_id, photo.photo_path, photo.photo_type,
             photo.photo_stage, photo.description, photo.upload_time,
             photo.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def delete_disease_photo(self, photo_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM disease_photo_archives WHERE id=?", (photo_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_photos_by_disease(self, disease_id: int, photo_type: str = None,
                               photo_stage: str = None) -> List[DiseasePhotoArchive]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM disease_photo_archives WHERE disease_id=?"
        params = [disease_id]
        if photo_type:
            query += " AND photo_type=?"
            params.append(photo_type)
        if photo_stage:
            query += " AND photo_stage=?"
            params.append(photo_stage)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [DiseasePhotoArchive(**dict(row)) for row in rows]

    def get_photos_by_type(self, disease_id: int, photo_type: str) -> List[DiseasePhotoArchive]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM disease_photo_archives WHERE disease_id=? AND photo_type=? ORDER BY created_at DESC",
            (disease_id, photo_type)
        )
        rows = cursor.fetchall()
        return [DiseasePhotoArchive(**dict(row)) for row in rows]

    # ==================== 预警记录相关方法 ====================

    def add_warning(self, warning: WarningRecord) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO warning_records
               (building_id, component_id, component_code, warning_type, warning_level,
                title, description, source, related_disease_id, related_record_id,
                is_read, is_handled, handle_remark, created_at, handled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (warning.building_id, warning.component_id, warning.component_code,
             warning.warning_type, warning.warning_level, warning.title,
             warning.description, warning.source, warning.related_disease_id,
             warning.related_record_id, 1 if warning.is_read else 0,
             1 if warning.is_handled else 0, warning.handle_remark,
             warning.created_at, warning.handled_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_warning(self, warning_id: int, **kwargs) -> bool:
        if not kwargs:
            return False
        cursor = self.conn.cursor()
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ('is_read', 'is_handled'):
                value = 1 if value else 0
            fields.append(f"{key}=?")
            values.append(value)
        values.append(warning_id)
        cursor.execute(f"UPDATE warning_records SET {', '.join(fields)} WHERE id=?", values)
        self.conn.commit()
        return cursor.rowcount > 0

    def get_warning_records(self, building_id: int, warning_type: str = None,
                            warning_level: str = None, is_read: bool = None) -> List[WarningRecord]:
        return self.get_warnings_by_building(
            building_id=building_id,
            is_read=is_read,
            warning_type=warning_type,
            warning_level=warning_level,
        )

    def get_warnings_by_building(self, building_id: int, is_read: bool = None,
                                  warning_type: str = None,
                                  warning_level: str = None) -> List[WarningRecord]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM warning_records WHERE building_id=?"
        params = [building_id]
        if is_read is not None:
            query += " AND is_read=?"
            params.append(1 if is_read else 0)
        if warning_type:
            query += " AND warning_type=?"
            params.append(warning_type)
        if warning_level:
            query += " AND warning_level=?"
            params.append(warning_level)
        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_read'] = bool(d['is_read'])
            d['is_handled'] = bool(d['is_handled'])
            records.append(WarningRecord(**d))
        return records

    def get_warnings_by_component(self, component_id: int) -> List[WarningRecord]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM warning_records WHERE component_id=? ORDER BY created_at DESC",
            (component_id,)
        )
        rows = cursor.fetchall()
        records = []
        for row in rows:
            d = dict(row)
            d['is_read'] = bool(d['is_read'])
            d['is_handled'] = bool(d['is_handled'])
            records.append(WarningRecord(**d))
        return records

    def get_unread_warning_count(self, building_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM warning_records WHERE building_id=? AND is_read=0",
            (building_id,)
        )
        row = cursor.fetchone()
        return row["cnt"] if row else 0

    def mark_warning_read(self, warning_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE warning_records SET is_read=1 WHERE id=?",
            (warning_id,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def mark_warning_handled(self, warning_id: int, handle_remark: str = "") -> bool:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE warning_records SET is_handled=1, handle_remark=?, handled_at=? WHERE id=?",
            (handle_remark, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), warning_id)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== 操作日志相关方法 ====================

    def add_operation_log(self, log: OperationLog) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO operation_logs
               (module, action, target_type, target_id, operator, detail,
                ip_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (log.module, log.action, log.target_type, log.target_id,
             log.operator, log.detail, log.ip_address, log.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_operation_logs(self, module: str = None, action: str = None,
                           target_type: str = None, target_id: int = None,
                           building_id: int = None, action_type: str = None,
                           limit: int = 100, offset: int = 0) -> List[OperationLog]:
        cursor = self.conn.cursor()
        query = "SELECT * FROM operation_logs WHERE 1=1"
        params = []
        if module:
            query += " AND module=?"
            params.append(module)
        action = action or action_type
        if action:
            query += " AND action=?"
            params.append(action)
        if target_type:
            query += " AND target_type=?"
            params.append(target_type)
        if target_id is not None:
            query += " AND target_id=?"
            params.append(target_id)
        if building_id is not None:
            query += " AND detail LIKE ?"
            params.append(f"%建筑ID:{building_id}%")
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [OperationLog(**dict(row)) for row in rows]

    def get_operation_logs_by_target(self, target_type: str, target_id: int,
                                      limit: int = 50) -> List[OperationLog]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM operation_logs WHERE target_type=? AND target_id=? ORDER BY created_at DESC LIMIT ?",
            (target_type, target_id, limit)
        )
        rows = cursor.fetchall()
        return [OperationLog(**dict(row)) for row in rows]

    # ==================== 偏差病害联动相关方法 ====================

    def upsert_deviation_disease_link(self, link: DeviationDiseaseLink) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id FROM deviation_disease_links WHERE component_id=?""",
            (link.component_id,)
        )
        row = cursor.fetchone()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row:
            cursor.execute(
                """UPDATE deviation_disease_links SET
                   component_code=?, deviation_level=?, disease_count=?,
                   risk_level=?, assessment=?, suggestion=?, updated_at=?
                   WHERE component_id=?""",
                (link.component_code, link.deviation_level, link.disease_count,
                 link.risk_level, link.assessment, link.suggestion, now,
                 link.component_id)
            )
            self.conn.commit()
            return row["id"]
        else:
            cursor.execute(
                """INSERT INTO deviation_disease_links
                   (component_id, component_code, deviation_level, disease_count,
                    risk_level, assessment, suggestion, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (link.component_id, link.component_code, link.deviation_level,
                 link.disease_count, link.risk_level, link.assessment,
                 link.suggestion, link.created_at, link.updated_at)
            )
            self.conn.commit()
            return cursor.lastrowid

    def get_deviation_disease_links(self, building_id: int) -> List[DeviationDiseaseLink]:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ddl.* FROM deviation_disease_links ddl
            JOIN components c ON ddl.component_id = c.id
            WHERE c.building_id=?
            ORDER BY ddl.risk_level DESC, ddl.disease_count DESC, ddl.created_at DESC
            """,
            (building_id,)
        )
        rows = cursor.fetchall()
        return [DeviationDiseaseLink(**dict(row)) for row in rows]

    def get_high_risk_components(self, building_id: int,
                                  min_risk_level: str = "high") -> List[DeviationDiseaseLink]:
        cursor = self.conn.cursor()
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        min_level_val = risk_order.get(min_risk_level, 2)
        cursor.execute("""
            SELECT ddl.* FROM deviation_disease_links ddl
            JOIN components c ON ddl.component_id = c.id
            WHERE c.building_id=?
            ORDER BY 
                CASE ddl.risk_level
                    WHEN 'critical' THEN 4
                    WHEN 'high' THEN 3
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 1
                    ELSE 0
                END DESC,
                ddl.disease_count DESC
        """, (building_id,))
        rows = cursor.fetchall()
        links = []
        for row in rows:
            d = dict(row)
            level_val = risk_order.get(d['risk_level'], 0)
            if level_val >= min_level_val:
                links.append(DeviationDiseaseLink(**d))
        return links

    def delete_deviation_disease_link(self, component_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM deviation_disease_links WHERE component_id=?",
                       (component_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_deviation_disease_stats(self, building_id: int) -> int:
        cursor = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            SELECT c.id as component_id, c.code as component_code,
                   c.deviation_threshold,
                   COUNT(dr.id) as disease_count
            FROM components c
            LEFT JOIN disease_records dr ON c.id = dr.component_id
            WHERE c.building_id=?
            GROUP BY c.id
        """, (building_id,))
        rows = cursor.fetchall()
        updated_count = 0
        for row in rows:
            component_id = row["component_id"]
            component_code = row["component_code"]
            disease_count = row["disease_count"] or 0
            deviation_threshold = row["deviation_threshold"] or 5.0

            cursor.execute("""
                SELECT length, width, angle FROM measurement_records
                WHERE component_id=? ORDER BY version DESC LIMIT 1
            """, (component_id,))
            meas_row = cursor.fetchone()
            deviation_level = "low"
            if meas_row:
                component = self.get_component(component_id)
                if component:
                    length_dev = abs(meas_row["length"] - component.design_length)
                    width_dev = abs(meas_row["width"] - component.design_width)
                    angle_dev = abs(meas_row["angle"] - component.design_angle)
                    max_dev_rel = max(
                        length_dev / deviation_threshold if deviation_threshold > 0 else 0,
                        width_dev / deviation_threshold if deviation_threshold > 0 else 0,
                        angle_dev / deviation_threshold if deviation_threshold > 0 else 0
                    )
                    if max_dev_rel >= 3:
                        deviation_level = "critical"
                    elif max_dev_rel >= 2:
                        deviation_level = "high"
                    elif max_dev_rel >= 1:
                        deviation_level = "medium"
                    else:
                        deviation_level = "low"

            risk_level = "low"
            dev_risk = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            disease_risk = min(disease_count, 3)
            total_risk = dev_risk.get(deviation_level, 0) + disease_risk
            if total_risk >= 5:
                risk_level = "critical"
            elif total_risk >= 3:
                risk_level = "high"
            elif total_risk >= 1:
                risk_level = "medium"

            assessment = f"偏差等级: {deviation_level}, 病害数量: {disease_count}"
            suggestion = ""
            if risk_level in ("high", "critical"):
                suggestion = "建议及时处理，重点关注"
            elif risk_level == "medium":
                suggestion = "建议定期检查，关注变化"
            else:
                suggestion = "状态良好，正常维护"

            cursor.execute("""
                SELECT id FROM deviation_disease_links WHERE component_id=?
            """, (component_id,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """UPDATE deviation_disease_links SET
                       component_code=?, deviation_level=?, disease_count=?,
                       risk_level=?, assessment=?, suggestion=?, updated_at=?
                       WHERE component_id=?""",
                    (component_code, deviation_level, disease_count,
                     risk_level, assessment, suggestion, now, component_id)
                )
            else:
                cursor.execute(
                    """INSERT INTO deviation_disease_links
                       (component_id, component_code, deviation_level, disease_count,
                        risk_level, assessment, suggestion, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (component_id, component_code, deviation_level, disease_count,
                     risk_level, assessment, suggestion, now, now)
                )
            updated_count += 1
        self.conn.commit()
        return updated_count
