#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
病害模块测试脚本
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    DatabaseManager, DiseaseRecord, DiseaseTreatment,
    DISEASE_TYPE_CRACK, DISEASE_TYPE_DECAY, DISEASE_TYPE_INSECT,
    DISEASE_SEVERITY_MILD, DISEASE_SEVERITY_MODERATE,
    DISEASE_SEVERITY_SEVERE, DISEASE_STATUS_PENDING,
    DISEASE_STATUS_IN_PROGRESS, DISEASE_STATUS_COMPLETED,
)
from services import DiseaseService


def test_disease_module():
    print("=" * 60)
    print("古建筑木构件病害档案与修缮建议模块 - 功能测试")
    print("=" * 60)

    db = DatabaseManager()
    service = DiseaseService(db)

    buildings = db.get_all_buildings()
    if not buildings:
        print("请先创建至少一个建筑和构件后再测试")
        return

    building = buildings[0]
    print(f"\n测试建筑: {building.name} ({building.code})")

    components = db.get_components_by_building(building.id)
    if not components:
        print("请先创建至少一个构件后再测试")
        return

    comp = components[0]
    print(f"测试构件: {comp.code} - {comp.name}")

    print("\n" + "=" * 40)
    print("1. 测试病害记录创建与风险评估")
    print("=" * 40)

    disease = DiseaseRecord(
        id=None,
        building_id=building.id,
        component_id=comp.id,
        component_code=comp.code,
        disease_type=DISEASE_TYPE_CRACK,
        severity=DISEASE_SEVERITY_MODERATE,
        priority='medium',
        description='梁端出现纵向裂缝，需观察发展趋势',
        location='梁端北侧',
        size_length=180.0,
        size_width=0.0,
        size_depth=8.0,
    )

    result = service.create_disease_with_suggestion(disease)
    print(f"✓ 病害创建成功, ID: {result.id}")
    print(f"  - 病害类型: {result.disease_type}")
    print(f"  - 初始等级: {DISEASE_SEVERITY_MODERATE} -> 评估后: {result.severity}")
    print(f"  - 初始优先级: medium -> 评估后: {result.priority}")
    print(f"  - 修缮建议: {result.repair_suggestion[:60]}...")
    print(f"  - 修缮方法: {result.repair_method}")
    print(f"  - 预估费用: ¥{result.estimated_cost:,.2f}")

    print("\n" + "=" * 40)
    print("2. 测试病害记录查询")
    print("=" * 40)

    diseases = db.get_diseases_by_building(building.id)
    print(f"✓ 该建筑共有 {len(diseases)} 条病害记录")

    stats = db.get_disease_statistics(building.id)
    print(f"  - 总数: {stats.total_count}")
    print(f"  - 待处理: {stats.pending_count}")
    print(f"  - 处理中: {stats.in_progress_count}")
    print(f"  - 已完成: {stats.completed_count}")
    print(f"  - 预估总费用: ¥{stats.total_estimated_cost:,.2f}")
    print(f"  - 按类型分布: {stats.by_type}")
    print(f"  - 按严重程度分布: {stats.by_severity}")

    print("\n" + "=" * 40)
    print("3. 测试处置记录添加")
    print("=" * 40)

    treatment = DiseaseTreatment(
        id=None,
        disease_id=result.id,
        treatment_type='初步检查',
        description='已完成初步检查，裂缝宽度约2mm，需定期观察',
        handler='张工',
        treatment_date='2024-01-15',
        remark='暂无明显发展趋势',
    )
    treatment_id = db.add_disease_treatment(treatment)
    print(f"✓ 处置记录添加成功, ID: {treatment_id}")

    treatments = db.get_treatments_by_disease(result.id)
    print(f"  - 该病害共有 {len(treatments)} 条处置记录")

    print("\n" + "=" * 40)
    print("4. 测试病害状态更新")
    print("=" * 40)

    success = service.update_disease_status(
        result.id, DISEASE_STATUS_IN_PROGRESS,
        handler='李工', remark='已安排处理'
    )
    print(f"✓ 状态更新成功: {success}")

    updated = db.get_disease_record(result.id)
    print(f"  - 当前状态: {updated.status}")
    print(f"  - 负责人: {updated.handler}")

    print("\n" + "=" * 40)
    print("5. 测试修缮建议重新生成")
    print("=" * 40)

    count = service.batch_generate_all_suggestions(building.id)
    print(f"✓ 已为 {count} 条病害重新生成修缮建议")

    print("\n" + "=" * 40)
    print("6. 测试获取处置进度汇总")
    print("=" * 40)

    progress = service.get_progress_summary(building.id)
    print(f"✓ 处置完成率: {progress['completion_rate']:.1f}%")
    print(f"  - 紧急待处理: {progress['pending_urgent']} 条")

    print("\n" + "=" * 40)
    print("7. 清理测试数据")
    print("=" * 40)

    db.delete_disease_record(result.id)
    print("✓ 测试数据已清理")

    print("\n" + "=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_disease_module()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
