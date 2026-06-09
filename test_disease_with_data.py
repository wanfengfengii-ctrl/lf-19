#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
病害模块完整测试脚本 - 含测试数据创建
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    DatabaseManager, Building, Component, DiseaseRecord, DiseaseTreatment,
    DISEASE_TYPE_CRACK, DISEASE_TYPE_DECAY, DISEASE_TYPE_INSECT,
    DISEASE_TYPE_DEFORMATION, DISEASE_TYPE_DEFECT,
    DISEASE_SEVERITY_MILD, DISEASE_SEVERITY_MODERATE,
    DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_DANGEROUS,
    DISEASE_STATUS_PENDING, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_REVIEWED,
    PRIORITY_LOW, PRIORITY_MEDIUM, PRIORITY_HIGH, PRIORITY_URGENT,
)
from services import DiseaseService


def test_disease_module():
    print("=" * 60)
    print("古建筑木构件病害档案与修缮建议模块 - 完整功能测试")
    print("=" * 60)

    db = DatabaseManager()
    service = DiseaseService(db)

    building_code = "TEST-BUILDING-001"
    existing = None
    for b in db.get_all_buildings():
        if b.code == building_code:
            existing = b
            break

    if existing:
        building = existing
        print(f"\n使用现有测试建筑: {building.name}")
    else:
        print("\n创建测试建筑...")
        building = Building(
            id=None,
            name="测试古建筑",
            code=building_code,
            location="测试地点",
            description="用于病害模块测试的建筑",
        )
        bid = db.add_building(building)
        building.id = bid
        print(f"✓ 测试建筑创建成功, ID: {bid}")

    components = db.get_components_by_building(building.id)
    if not components:
        print("\n创建测试构件...")
        comp_data = [
            {"code": "L-001", "name": "主梁", "type": "梁", "length": 5000, "width": 300, "angle": 90},
            {"code": "Z-001", "name": "前檐柱", "type": "柱", "length": 4500, "width": 400, "angle": 90},
            {"code": "F-001", "name": "额枋", "type": "枋", "length": 3500, "width": 250, "angle": 90},
        ]
        for d in comp_data:
            comp = Component(
                id=None,
                building_id=building.id,
                code=d["code"],
                name=d["name"],
                component_type=d["type"],
                design_length=d["length"],
                design_width=d["width"],
                design_angle=d["angle"],
                deviation_threshold=5.0,
                description="测试构件",
            )
            db.add_component(comp)
        components = db.get_components_by_building(building.id)
        print(f"✓ 创建了 {len(components)} 个测试构件")

    comp = components[0]
    print(f"\n使用测试构件: {comp.code} - {comp.name}")

    print("\n" + "=" * 40)
    print("测试1: 病害记录创建与自动风险评估")
    print("=" * 40)

    test_diseases = [
        {
            "type": DISEASE_TYPE_CRACK,
            "severity": DISEASE_SEVERITY_MODERATE,
            "desc": "梁身中部出现纵向裂缝，宽度约2mm",
            "location": "梁身中部",
            "length": 350.0,
            "width": 0.0,
            "depth": 10.0,
        },
        {
            "type": DISEASE_TYPE_DECAY,
            "severity": DISEASE_SEVERITY_SEVERE,
            "desc": "梁端底部出现腐朽，面积较大",
            "location": "梁端底部",
            "length": 200.0,
            "width": 150.0,
            "depth": 30.0,
        },
        {
            "type": DISEASE_TYPE_INSECT,
            "severity": DISEASE_SEVERITY_MILD,
            "desc": "发现少量虫蛀痕迹",
            "location": "梁侧面",
            "length": 0.0,
            "width": 0.0,
            "depth": 0.0,
        },
    ]

    created_diseases = []
    for i, td in enumerate(test_diseases):
        disease = DiseaseRecord(
            id=None,
            building_id=building.id,
            component_id=comp.id,
            component_code=comp.code,
            disease_type=td["type"],
            severity=td["severity"],
            priority=PRIORITY_MEDIUM,
            description=td["desc"],
            location=td["location"],
            size_length=td["length"],
            size_width=td["width"],
            size_depth=td["depth"],
        )
        result = service.create_disease_with_suggestion(disease)
        created_diseases.append(result)

        type_names = {code: name for code, name in [
            (DISEASE_TYPE_CRACK, "裂缝"),
            (DISEASE_TYPE_DECAY, "腐朽"),
            (DISEASE_TYPE_INSECT, "虫蛀"),
            (DISEASE_TYPE_DEFORMATION, "变形"),
            (DISEASE_TYPE_DEFECT, "缺损"),
        ]}
        sev_names = {code: name for code, name in [
            (DISEASE_SEVERITY_MILD, "轻微"),
            (DISEASE_SEVERITY_MODERATE, "一般"),
            (DISEASE_SEVERITY_SEVERE, "严重"),
            (DISEASE_SEVERITY_DANGEROUS, "危险"),
        ]}
        pri_names = {code: name for code, name in [
            (PRIORITY_LOW, "低"),
            (PRIORITY_MEDIUM, "中"),
            (PRIORITY_HIGH, "高"),
            (PRIORITY_URGENT, "紧急"),
        ]}

        print(f"  [{i+1}] {type_names.get(td['type'], td['type'])} (ID: {result.id})")
        print(f"      初始等级: {sev_names.get(td['severity'], td['severity'])} "
              f"→ 评估后: {sev_names.get(result.severity, result.severity)}")
        print(f"      初始优先级: {pri_names.get(PRIORITY_MEDIUM, '中')} "
              f"→ 评估后: {pri_names.get(result.priority, result.priority)}")
        print(f"      修缮方法: {result.repair_method}")
        print(f"      预估费用: ¥{result.estimated_cost:,.2f}")

    print("\n" + "=" * 40)
    print("测试2: 病害台账查询与统计")
    print("=" * 40)

    all_diseases = db.get_diseases_by_building(building.id)
    print(f"✓ 病害总数: {len(all_diseases)} 条")

    stats = db.get_disease_statistics(building.id)
    print(f"\n  状态分布:")
    print(f"    - 待处理: {stats.pending_count}")
    print(f"    - 处理中: {stats.in_progress_count}")
    print(f"    - 已完成: {stats.completed_count}")
    print(f"    - 已复查: {stats.reviewed_count}")

    type_names = {
        DISEASE_TYPE_CRACK: "裂缝",
        DISEASE_TYPE_DECAY: "腐朽",
        DISEASE_TYPE_INSECT: "虫蛀",
        DISEASE_TYPE_DEFORMATION: "变形",
        DISEASE_TYPE_DEFECT: "缺损",
    }
    print(f"\n  按类型分布:")
    for dtype, count in stats.by_type.items():
        print(f"    - {type_names.get(dtype, dtype)}: {count}")

    sev_names = {
        DISEASE_SEVERITY_MILD: "轻微",
        DISEASE_SEVERITY_MODERATE: "一般",
        DISEASE_SEVERITY_SEVERE: "严重",
        DISEASE_SEVERITY_DANGEROUS: "危险",
    }
    print(f"\n  按严重程度分布:")
    for sev, count in stats.by_severity.items():
        print(f"    - {sev_names.get(sev, sev)}: {count}")

    print(f"\n  预估总费用: ¥{stats.total_estimated_cost:,.2f}")

    print("\n" + "=" * 40)
    print("测试3: 按条件筛选病害")
    print("=" * 40)

    pending_diseases = db.get_diseases_by_building(
        building.id, status=DISEASE_STATUS_PENDING
    )
    print(f"✓ 待处理病害: {len(pending_diseases)} 条")

    crack_diseases = db.get_diseases_by_building(
        building.id, disease_type=DISEASE_TYPE_CRACK
    )
    print(f"✓ 裂缝病害: {len(crack_diseases)} 条")

    severe_diseases = db.get_diseases_by_building(
        building.id, severity=DISEASE_SEVERITY_SEVERE
    )
    print(f"✓ 严重级病害: {len(severe_diseases)} 条")

    print("\n" + "=" * 40)
    print("测试4: 处置记录管理")
    print("=" * 40)

    if created_diseases:
        disease = created_diseases[0]

        treatments_data = [
            {"type": "初步检查", "desc": "已完成现场勘查，测量裂缝尺寸", "handler": "张工"},
            {"type": "方案制定", "desc": "已制定环氧树脂灌缝方案", "handler": "李工"},
        ]

        for td in treatments_data:
            treatment = DiseaseTreatment(
                id=None,
                disease_id=disease.id,
                treatment_type=td["type"],
                description=td["desc"],
                handler=td["handler"],
            )
            tid = db.add_disease_treatment(treatment)
            print(f"✓ 添加处置记录: {td['type']} (ID: {tid})")

        treatments = db.get_treatments_by_disease(disease.id)
        print(f"\n该病害共有 {len(treatments)} 条处置记录:")
        for t in treatments:
            print(f"  - [{t.treatment_date}] {t.treatment_type} - {t.handler}")

    print("\n" + "=" * 40)
    print("测试5: 病害状态流转")
    print("=" * 40)

    if created_diseases:
        disease = created_diseases[0]

        print(f"初始状态: {disease.status}")

        service.update_disease_status(
            disease.id, DISEASE_STATUS_IN_PROGRESS,
            handler="王工", remark="开始处理"
        )
        d = db.get_disease_record(disease.id)
        print(f"→ 处理中 (负责人: {d.handler})")

        service.update_disease_status(
            disease.id, DISEASE_STATUS_COMPLETED,
            handler="王工", remark="修缮完成"
        )
        d = db.get_disease_record(disease.id)
        print(f"→ 已完成 (完成日期: {d.complete_date})")

    print("\n" + "=" * 40)
    print("测试6: 处置进度汇总")
    print("=" * 40)

    progress = service.get_progress_summary(building.id)
    print(f"✓ 处置完成率: {progress['completion_rate']:.1f}%")
    print(f"✓ 紧急待处理: {progress['pending_urgent']} 条")

    print("\n" + "=" * 40)
    print("测试7: 批量重新生成修缮建议")
    print("=" * 40)

    count = service.batch_generate_all_suggestions(building.id)
    print(f"✓ 已为 {count} 条病害重新生成修缮建议")

    print("\n" + "=" * 60)
    print("所有测试通过! ✓")
    print("=" * 60)
    print("\n提示: 测试数据已保留，可在UI中查看效果")
    print(f"建筑名称: {building.name} ({building.code})")


if __name__ == "__main__":
    try:
        test_disease_module()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
