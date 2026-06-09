#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心功能测试脚本
"""

import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager, Building, Component, MortiseTenon, MeasurementRecord
from utils.validators import (
    validate_csv_row, validate_component_code, validate_positive_number,
    validate_angle, validate_measure_time
)
from services import CsvImporter, DeviationCalculator, ReportGenerator


def test_validators():
    print("=" * 50)
    print("测试1：数据校验功能")
    print("=" * 50)

    assert validate_component_code("L-001") == True
    assert validate_component_code("") == False
    assert validate_component_code(None) == False
    print("  ✓ 构件编号校验")

    assert validate_positive_number(100) == True
    assert validate_positive_number(0.5) == True
    assert validate_positive_number(0) == False
    assert validate_positive_number(-10) == False
    assert validate_positive_number("abc") == False
    print("  ✓ 正数校验")

    assert validate_angle(0) == True
    assert validate_angle(90) == True
    assert validate_angle(180) == True
    assert validate_angle(-1) == False
    assert validate_angle(181) == False
    assert validate_angle("abc") == False
    print("  ✓ 角度校验")

    valid, normalized = validate_measure_time("2024-01-15 09:30:00")
    assert valid == True
    assert normalized == "2024-01-15 09:30:00"
    print("  ✓ 时间格式-标准格式")

    valid, normalized = validate_measure_time("2024-01-15")
    assert valid == True
    assert normalized == "2024-01-15 00:00:00"
    print("  ✓ 时间格式-仅日期")

    valid, normalized = validate_measure_time("2024/01/15 10:30")
    assert valid == True
    assert "2024-01-15" in normalized
    print("  ✓ 时间格式-斜杠日期")

    valid, _ = validate_measure_time("20240115")
    assert valid == True
    print("  ✓ 时间格式-紧凑日期")

    valid, _ = validate_measure_time("随便写点啥")
    assert valid == False
    print("  ✓ 时间格式-无效文本拒绝")

    valid, _ = validate_measure_time("")
    assert valid == False
    print("  ✓ 时间格式-空值拒绝")

    test_row = {
        "构件编号": "L-001",
        "长度": "2500.5",
        "宽度": "300.0",
        "角度": "90.0",
        "测量时间": "2024-01-15 09:30:00"
    }
    is_valid, errors, cleaned = validate_csv_row(test_row, 2)
    assert is_valid == True
    assert len(errors) == 0
    assert cleaned["component_code"] == "L-001"
    assert cleaned["length"] == 2500.5
    print("  ✓ 正常CSV行校验")

    bad_row = {
        "构件编号": "",
        "长度": "-5",
        "宽度": "abc",
        "角度": "200",
        "测量时间": ""
    }
    is_valid, errors, cleaned = validate_csv_row(bad_row, 3)
    assert is_valid == False
    assert len(errors) >= 4
    print("  ✓ 错误CSV行校验")

    print("  全部校验测试通过！\n")


def test_database():
    print("=" * 50)
    print("测试2：数据库操作")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    db = DatabaseManager(db_path)

    try:
        b1 = Building(id=None, name="测试建筑", code="TEST-001", location="北京", description="测试用建筑")
        bid1 = db.add_building(b1)
        assert bid1 > 0
        print("  ✓ 添加建筑")

        buildings = db.get_all_buildings()
        assert len(buildings) == 1
        assert buildings[0].code == "TEST-001"
        print("  ✓ 查询建筑列表")

        b = db.get_building(bid1)
        assert b is not None
        assert b.name == "测试建筑"
        print("  ✓ 查询单个建筑")

        c1 = Component(id=None, building_id=bid1, code="L-001", name="主梁",
                       component_type="梁", design_length=2500.0, design_width=300.0,
                       design_angle=90.0, deviation_threshold=5.0)
        cid1 = db.add_component(c1)
        assert cid1 > 0
        print("  ✓ 添加构件")

        c2 = Component(id=None, building_id=bid1, code="L-002", name="次梁",
                       component_type="梁", design_length=2000.0, design_width=250.0,
                       design_angle=90.0, deviation_threshold=5.0)
        cid2 = db.add_component(c2)
        assert cid2 > 0

        components = db.get_components_by_building(bid1)
        assert len(components) == 2
        print("  ✓ 查询构件列表")

        comp = db.get_component_by_code(bid1, "L-001")
        assert comp is not None
        assert comp.name == "主梁"
        print("  ✓ 按编号查询构件")

        try:
            c_dup = Component(id=None, building_id=bid1, code="L-001", name="重复")
            db.add_component(c_dup)
            assert False, "应该抛出重复编号异常"
        except ValueError as e:
            print("  ✓ 重复构件编号检测")

        r1 = MeasurementRecord(id=None, component_id=cid1, component_code="L-001",
                               length=2505.5, width=302.0, angle=90.5,
                               measure_time="2024-01-15 09:30:00", version=1)
        rid1 = db.add_measurement_record(r1)
        assert rid1 > 0
        print("  ✓ 添加测量记录")

        version = db.get_latest_version(cid1)
        assert version == 1
        print("  ✓ 查询最新版本号")

        r2 = MeasurementRecord(id=None, component_id=cid1, component_code="L-001",
                               length=2503.0, width=301.0, angle=90.2,
                               measure_time="2024-01-16 09:30:00", version=2)
        rid2 = db.add_measurement_record(r2)
        assert rid2 > 0
        version = db.get_latest_version(cid1)
        assert version == 2
        print("  ✓ 重复测量保留历史版本")

        records = db.get_measurements_by_component(cid1)
        assert len(records) == 2
        print("  ✓ 查询测量历史")

        latest = db.get_latest_measurement(cid1)
        assert latest is not None
        assert latest.version == 2
        print("  ✓ 查询最新测量记录")

        mt = MortiseTenon(id=None, building_id=bid1,
                          mortise_component_id=cid1, tenon_component_id=cid2,
                          joint_type="榫卯连接", description="测试榫卯")
        mt_id = db.add_mortise_tenon(mt)
        assert mt_id > 0
        print("  ✓ 添加榫卯关系")

        mts = db.get_mortise_tenons_by_building(bid1)
        assert len(mts) == 1
        print("  ✓ 查询榫卯关系")

        db.mark_for_recheck(rid2, "偏差过大，需复测")
        latest = db.get_latest_measurement(cid1)
        assert latest.is_recheck == True
        print("  ✓ 标记复测")

        recheck_list = db.get_recheck_records(bid1)
        assert len(recheck_list) >= 1
        print("  ✓ 查询复测列表")

        print("  全部数据库测试通过！\n")

    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_csv_import():
    print("=" * 50)
    print("测试3：CSV导入功能")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    db = DatabaseManager(db_path)

    try:
        b1 = Building(id=None, name="测试建筑", code="TEST-001")
        bid1 = db.add_building(b1)

        for code in ["L-001", "L-002", "L-003", "Z-001", "Z-002",
                     "F-001", "F-002", "C-001", "C-002", "C-003"]:
            comp = Component(id=None, building_id=bid1, code=code, name=code,
                           component_type="梁", design_length=2500.0, design_width=300.0,
                           design_angle=90.0, deviation_threshold=10.0)
            db.add_component(comp)

        importer = CsvImporter(db)

        sample_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_data.csv")
        if os.path.exists(sample_csv):
            result = importer.import_file(sample_csv, bid1)
            print(f"  导入结果：成功{result.success_count}条，失败{result.error_count}条")
            assert result.success_count == 10
            assert result.error_count == 0
            print("  ✓ CSV批量导入成功")

            result2 = importer.import_file(sample_csv, bid1)
            assert result2.success_count == 10
            records = db.get_measurements_by_component(db.get_component_by_code(bid1, "L-001").id)
            assert len(records) == 2
            print("  ✓ 重复导入生成新版本")
        else:
            print("  ⚠  跳过CSV测试（未找到示例文件）")

        bad_csv = os.path.join(tmp_dir, "bad_data.csv")
        with open(bad_csv, 'w', encoding='utf-8') as f:
            f.write("构件编号,长度,宽度,角度,测量时间\n")
            f.write("L-001,2500,300,90,2024-01-15 10:00:00\n")
            f.write("L-002,abc,300,90,2024-01-15 10:00:00\n")
            f.write("L-003,-5,300,90,2024-01-15 10:00:00\n")
            f.write("Z-001,200,300,200,2024-01-15 10:00:00\n")
            f.write("Z-002,200,300,90,这不是时间\n")
            f.write(",200,300,90,2024-01-15\n")

        result3 = importer.import_file(bad_csv, bid1)
        assert result3.error_count >= 4
        print(f"  ✓ 错误数据拒绝导入（失败{result3.error_count}条）")

        headers, rows, errors, row_errors = importer.preview_file(bad_csv, max_rows=10)
        assert len(row_errors) >= 4
        print(f"  ✓ 预览时检测出错误行（共{len(row_errors)}行有问题）")
        assert len(errors) >= 4
        print(f"  ✓ 预览时返回错误详情（共{len(errors)}个错误）")

        print("  CSV导入测试通过！\n")

    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_auto_recheck():
    print("=" * 50)
    print("测试6：自动标记复测功能")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    db = DatabaseManager(db_path)

    try:
        b1 = Building(id=None, name="测试建筑", code="TEST-001")
        bid1 = db.add_building(b1)

        c_normal = Component(id=None, building_id=bid1, code="N-001", name="正常构件",
                           component_type="梁", design_length=2500.0, design_width=300.0,
                           design_angle=90.0, deviation_threshold=5.0)
        db.add_component(c_normal)

        c_abnormal = Component(id=None, building_id=bid1, code="A-001", name="异常构件",
                             component_type="梁", design_length=2500.0, design_width=300.0,
                             design_angle=90.0, deviation_threshold=5.0)
        db.add_component(c_abnormal)

        test_csv = os.path.join(tmp_dir, "test_recheck.csv")
        with open(test_csv, 'w', encoding='utf-8') as f:
            f.write("构件编号,长度,宽度,角度,测量时间\n")
            f.write("N-001,2502.0,301.0,90.0,2024-01-15 10:00:00\n")
            f.write("A-001,2510.0,290.0,88.0,2024-01-15 10:00:00\n")

        importer = CsvImporter(db)

        result = importer.import_file(test_csv, bid1, auto_mark_recheck=True)
        assert result.success_count == 2
        assert result.auto_recheck_count == 1
        print(f"  ✓ 自动标记复测计数正确（{result.auto_recheck_count}条）")

        abnormal_comp = db.get_component_by_code(bid1, "A-001")
        latest = db.get_latest_measurement(abnormal_comp.id)
        assert latest is not None
        assert latest.is_recheck == True
        assert "偏差超过阈值" in latest.remark
        print("  ✓ 异常构件自动标记为需复测")

        normal_comp = db.get_component_by_code(bid1, "N-001")
        latest_n = db.get_latest_measurement(normal_comp.id)
        assert latest_n is not None
        assert latest_n.is_recheck == False
        print("  ✓ 正常构件不标记复测")

        test_csv2 = os.path.join(tmp_dir, "test_recheck_off.csv")
        with open(test_csv2, 'w', encoding='utf-8') as f:
            f.write("构件编号,长度,宽度,角度,测量时间\n")
            f.write("A-001,2515.0,285.0,87.0,2024-01-16 10:00:00\n")

        result2 = importer.import_file(test_csv2, bid1, auto_mark_recheck=False)
        assert result2.success_count == 1
        assert result2.auto_recheck_count == 0
        latest2 = db.get_latest_measurement(abnormal_comp.id)
        assert latest2.is_recheck == False
        print("  ✓ 关闭自动标记时不标记复测")

        recheck_list = db.get_recheck_records(bid1)
        assert len(recheck_list) == 1
        print("  ✓ 复测列表查询正确")

        print("  自动标记复测测试通过！\n")

    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_deviation():
    print("=" * 50)
    print("测试4：偏差计算功能")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    db = DatabaseManager(db_path)

    try:
        b1 = Building(id=None, name="测试建筑", code="TEST-001")
        bid1 = db.add_building(b1)

        c1 = Component(id=None, building_id=bid1, code="L-001", name="正常梁",
                       component_type="梁", design_length=2500.0, design_width=300.0,
                       design_angle=90.0, deviation_threshold=5.0)
        cid1 = db.add_component(c1)

        c2 = Component(id=None, building_id=bid1, code="L-002", name="异常梁",
                       component_type="梁", design_length=2500.0, design_width=300.0,
                       design_angle=90.0, deviation_threshold=5.0)
        cid2 = db.add_component(c2)

        r1 = MeasurementRecord(id=None, component_id=cid1, component_code="L-001",
                               length=2502.0, width=301.0, angle=90.0,
                               measure_time="2024-01-15", version=1)
        db.add_measurement_record(r1)

        r2 = MeasurementRecord(id=None, component_id=cid2, component_code="L-002",
                               length=2510.0, width=290.0, angle=88.0,
                               measure_time="2024-01-15", version=1)
        db.add_measurement_record(r2)

        calc = DeviationCalculator(db)

        comp1 = db.get_component(cid1)
        comp2 = db.get_component(cid2)

        dev1 = calc.calculate_component_deviation(comp1)
        assert dev1.is_abnormal == False
        assert dev1.length_deviation.deviation == 2.0
        print("  ✓ 正常构件偏差计算")

        dev2 = calc.calculate_component_deviation(comp2)
        assert dev2.is_abnormal == True
        assert abs(dev2.length_deviation.deviation) > 5.0
        print("  ✓ 异常构件识别")

        all_devs = calc.calculate_building_deviations(bid1)
        assert len(all_devs) == 2
        print("  ✓ 建筑全量偏差计算")

        abnormal = calc.get_abnormal_components(bid1)
        assert len(abnormal) == 1
        assert abnormal[0].component.code == "L-002"
        print("  ✓ 异常构件列表")

        stats = calc.get_deviation_statistics(bid1)
        assert stats["total_components"] == 2
        assert stats["abnormal_count"] == 1
        assert stats["normal_count"] == 1
        print("  ✓ 偏差统计")

        count = calc.mark_abnormal_for_recheck(bid1)
        assert count == 1
        recheck_list = db.get_recheck_records(bid1)
        assert len(recheck_list) >= 1
        print("  ✓ 自动标记异常复测")

        print("  偏差计算测试全部通过！\n")

    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def test_report():
    print("=" * 50)
    print("测试5：报告生成功能")
    print("=" * 50)

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test.db")
    db = DatabaseManager(db_path)

    try:
        b1 = Building(id=None, name="测试建筑", code="TEST-001", location="北京")
        bid1 = db.add_building(b1)

        for i in range(5):
            comp = Component(id=None, building_id=bid1, code=f"L-{i+1:03d}",
                           name=f"梁{i+1}", component_type="梁",
                           design_length=2500.0, design_width=300.0,
                           design_angle=90.0, deviation_threshold=5.0)
            cid = db.add_component(comp)
            length = 2500.0 + (i - 2) * 3
            rec = MeasurementRecord(id=None, component_id=cid, component_code=f"L-{i+1:03d}",
                                    length=length, width=300.0, angle=90.0,
                                    measure_time="2024-01-15", version=1)
            db.add_measurement_record(rec)

        report_gen = ReportGenerator(db)
        report_text = report_gen.generate_text_report(bid1)

        assert "古建筑木构件尺寸偏差检测报告" in report_text
        assert "测试建筑" in report_text
        assert "总体统计" in report_text
        assert "异常构件明细" in report_text
        assert "全构件检测明细" in report_text
        print("  ✓ 报告内容生成")

        output_file = os.path.join(tmp_dir, "report.txt")
        success = report_gen.save_report_to_file(bid1, output_file)
        assert success == True
        assert os.path.exists(output_file)
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert len(content) > 100
        print("  ✓ 报告保存到文件")

        print("  报告生成测试全部通过！\n")

    finally:
        db.close()
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    print("\n")
    print("🏛️  古建筑木构件测绘数据管理系统 - 核心功能测试")
    print("=" * 60)
    print()

    try:
        test_validators()
        test_database()
        test_csv_import()
        test_deviation()
        test_report()
        test_auto_recheck()

        print("=" * 60)
        print("🎉 所有测试全部通过！")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 发生错误：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
