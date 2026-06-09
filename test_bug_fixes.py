#!/usr/bin/env python3
"""验证三个bug修复"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager, DISEASE_STATUS_COMPLETED, DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS
from services import DiseaseService


def test_bug_fixes():
    print("=" * 60)
    print("古建筑木构件病害模块 - Bug修复验证")
    print("=" * 60)

    db = DatabaseManager()
    service = DiseaseService(db)

    # 查找建筑
    building_code = "TEST-BUILDING-001"
    building = None
    for b in db.get_all_buildings():
        if b.code == building_code:
            building = b
            break

    if not building:
        print("请先运行 test_disease_with_data.py 创建测试数据")
        return
    building_id = building.id
    print(f"使用建筑: {building.name} ({building.code})")

    # 查找构件
    components = db.get_components_by_building(building_id)
    if not components:
        print("没有找到构件")
        return
    component = components[0]

    print(f"\n使用构件: {component.code} - {component.name}")

    # 创建一个病害
    from database import DiseaseRecord, DISEASE_TYPE_CRACK, DISEASE_SEVERITY_MODERATE, PRIORITY_MEDIUM

    disease = DiseaseRecord(
        id=None,
        building_id=building_id,
        component_id=component.id,
        component_code=component.code,
        disease_type=DISEASE_TYPE_CRACK,
        severity=DISEASE_SEVERITY_MODERATE,
        priority=PRIORITY_MEDIUM,
        status=DISEASE_STATUS_PENDING,
        description="测试裂缝",
        location="梁身",
    )
    disease = service.create_disease_with_suggestion(disease)
    print(f"\n✓ 创建病害，ID: {disease.id}")
    print(f"  初始状态: {disease.status}")
    print(f"  初始完成日期: '{disease.complete_date}'")

    # 测试1：更新为已完成，应该自动设置完成日期
    print("\n" + "=" * 40)
    print("测试1: 状态改为已完成，自动设置完成日期")
    print("=" * 40)

    service.update_disease_status(disease.id, DISEASE_STATUS_COMPLETED, handler="张工")
    updated = db.get_disease_record(disease.id)
    print(f"  状态: {updated.status}")
    print(f"  完成日期: '{updated.complete_date}'")
    assert updated.complete_date, "已完成状态应该有完成日期！"
    print("✓ 测试通过")

    # 测试2：从已完成改回待处理，应该清空完成日期
    print("\n" + "=" * 40)
    print("测试2: 从已完成改回待处理，清空完成日期")
    print("=" * 40)

    service.update_disease_status(disease.id, DISEASE_STATUS_PENDING)
    updated = db.get_disease_record(disease.id)
    print(f"  状态: {updated.status}")
    print(f"  完成日期: '{updated.complete_date}'")
    assert not updated.complete_date, "待处理状态不应该有完成日期！"
    print("✓ 测试通过")

    # 测试3：改为处理中，也不应该有完成日期
    print("\n" + "=" * 40)
    print("测试3: 状态改为处理中，保持无完成日期")
    print("=" * 40)

    service.update_disease_status(disease.id, DISEASE_STATUS_IN_PROGRESS)
    updated = db.get_disease_record(disease.id)
    print(f"  状态: {updated.status}")
    print(f"  完成日期: '{updated.complete_date}'")
    assert not updated.complete_date, "处理中状态不应该有完成日期！"
    print("✓ 测试通过")

    # 测试4：新建病害时没有完成日期
    print("\n" + "=" * 40)
    print("测试4: 新建病害没有完成日期")
    print("=" * 40)

    disease2 = DiseaseRecord(
        id=None,
        building_id=building_id,
        component_id=component.id,
        component_code=component.code,
        disease_type=DISEASE_TYPE_CRACK,
        severity=DISEASE_SEVERITY_MODERATE,
        priority=PRIORITY_MEDIUM,
        status=DISEASE_STATUS_PENDING,
        description="新建测试病害",
    )
    disease2 = service.create_disease_with_suggestion(disease2)
    print(f"  新病害ID: {disease2.id}")
    print(f"  状态: {disease2.status}")
    print(f"  完成日期: '{disease2.complete_date}'")
    assert not disease2.complete_date, "新建病害不应该有完成日期！"
    print("✓ 测试通过")

    # 清理测试数据
    db.delete_disease_record(disease.id)
    db.delete_disease_record(disease2.id)

    print("\n" + "=" * 60)
    print("所有Bug修复验证通过！✓")
    print("=" * 60)


if __name__ == "__main__":
    test_bug_fixes()
