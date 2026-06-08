import sqlite3
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from .models import Building, Component, MortiseTenon, MeasurementRecord


class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "building_data.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = None
        self._connect()
        self._init_tables()

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
            FOREIGN KEY (tenon_component_id) REFERENCES components(id) ON DELETE CASCADE
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
            created_at TEXT NOT NULL,
            FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_measurement_component_idx ON measurement_records(component_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_measurement_code_idx ON measurement_records(component_code)
        ''')

        self.conn.commit()

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
        cursor.execute(
            """INSERT INTO mortise_tenons 
               (building_id, mortise_component_id, tenon_component_id, joint_type, description, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (mt.building_id, mt.mortise_component_id, mt.tenon_component_id,
             mt.joint_type, mt.description, mt.created_at)
        )
        self.conn.commit()
        return cursor.lastrowid

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
                version, is_recheck, remark, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record.component_id, record.component_code, record.length, record.width,
             record.angle, record.measure_time, record.version,
             1 if record.is_recheck else 0, record.remark, record.created_at)
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
