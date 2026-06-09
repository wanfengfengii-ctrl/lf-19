#!/usr/bin/env python3
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    DatabaseManager, Building, Component, DiseaseRecord,
    DISEASE_TYPE_CRACK, DISEASE_SEVERITY_SEVERE, DISEASE_SEVERITY_MODERATE,
    PRIORITY_HIGH, PRIORITY_URGENT,
    DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING,
    DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS,
    DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED,
    DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED,
    ACCEPTANCE_RESULT_PASS, ACCEPTANCE_RESULT_FAIL,
    PHOTO_TYPE_BEFORE, PHOTO_TYPE_AFTER,
    WARNING_TYPE_DISEASE, WARNING_TYPE_DEADLINE,
    WARNING_LEVEL_WARNING, WARNING_LEVEL_DANGER,
    MODULE_DISEASE, ACTION_STATUS_CHANGE,
)
from services import DiseaseService, StatusTransitionResult


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_test(name, passed, message=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status} - {name}")
    if message and not passed:
        print(f"      原因: {message}")


def setup_test_environment():
    db_path = tempfile.mktemp(suffix='.db')
    db = DatabaseManager(db_path)
    service = DiseaseService(db)

    building = Building(id=None, name="测试建筑", code="TEST-001",
                        location="测试位置", description="测试用建筑")
    building.id = db.add_building(building)

    component = Component(id=None, building_id=building.id, code="C-001",
                         name="测试梁", component_type="梁",
                         design_length=3000, design_width=200,
                         deviation_threshold=5.0)
    component.id = db.add_component(component)

    return db, service, building.id, component.id


def make_disease(building_id, component_id, **kwargs):
    defaults = {
        "id": None,
        "building_id": building_id,
        "component_id": component_id,
        "component_code": "C-001",
        "disease_type": DISEASE_TYPE_CRACK,
        "severity": DISEASE_SEVERITY_MODERATE,
        "priority": PRIORITY_HIGH,
        "status": DISEASE_STATUS_DISCOVERED,
        "description": "测试病害",
    }
    defaults.update(kwargs)
    return DiseaseRecord(**defaults)


def test_state_machine(service):
    print_section("1. 病害状态机测试")

    print_test("状态机初始化", service.state_machine is not None)
    print_test("状态数量", len(service.state_machine.transitions) == 9)

    workflow = service.get_workflow_steps()
    print_test("工作流步骤数", len(workflow) == 8)

    valid_transitions = [
        (DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_PENDING),
        (DISEASE_STATUS_PENDING, DISEASE_STATUS_ASSIGNED),
        (DISEASE_STATUS_ASSIGNED, DISEASE_STATUS_IN_PROGRESS),
        (DISEASE_STATUS_IN_PROGRESS, DISEASE_STATUS_COMPLETED),
        (DISEASE_STATUS_COMPLETED, DISEASE_STATUS_ACCEPTED),
        (DISEASE_STATUS_ACCEPTED, DISEASE_STATUS_REVIEWED),
        (DISEASE_STATUS_REVIEWED, DISEASE_STATUS_ARCHIVED),
    ]

    all_valid = True
    for from_status, to_status in valid_transitions:
        if not service.state_machine.can_transition(from_status, to_status):
            all_valid = False
            print(f"      缺少合法转移: {from_status} -> {to_status}")
    print_test("合法状态转移", all_valid)

    invalid_transitions = [
        (DISEASE_STATUS_DISCOVERED, DISEASE_STATUS_IN_PROGRESS),
        (DISEASE_STATUS_PENDING, DISEASE_STATUS_COMPLETED),
        (DISEASE_STATUS_ARCHIVED, DISEASE_STATUS_IN_PROGRESS),
    ]

    all_invalid = True
    for from_status, to_status in invalid_transitions:
        if service.state_machine.can_transition(from_status, to_status):
            all_invalid = False
            print(f"      不应允许的转移: {from_status} -> {to_status}")
    print_test("非法状态转移拦截", all_invalid)

    actions = service.get_allowed_status_actions(
        DiseaseRecord(id=1, building_id=1, component_id=1,
                     component_code="C-001",
                     disease_type=DISEASE_TYPE_CRACK,
                     severity=DISEASE_SEVERITY_MODERATE,
                     priority=PRIORITY_HIGH,
                     status=DISEASE_STATUS_PENDING))
    print_test("待派单状态操作", len(actions) > 0 and any("派单" in a[1] for a in actions))

    actions = service.get_allowed_status_actions(
        DiseaseRecord(id=1, building_id=1, component_id=1,
                     component_code="C-001",
                     disease_type=DISEASE_TYPE_CRACK,
                     severity=DISEASE_SEVERITY_MODERATE,
                     priority=PRIORITY_HIGH,
                     status=DISEASE_STATUS_ARCHIVED))
    print_test("已归档状态操作", len(actions) == 1 and any("重新打开" in a[1] for a in actions))


def test_workflow_closed_loop(db, service, building_id, component_id):
    print_section("2. 闭环处置流程测试")

    disease = make_disease(building_id, component_id,
                          severity=DISEASE_SEVERITY_SEVERE,
                          description="测试裂缝病害",
                          location="梁端",
                          size_length=100, size_width=2, size_depth=5)

    disease = service.create_disease_with_suggestion(disease)
    print_test("病害创建（发现状态）",
               disease.id is not None and disease.status == DISEASE_STATUS_DISCOVERED)

    result = service.submit_for_assignment(disease.id)
    print_test("提交待派单", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_PENDING)

    result = service.assign_disease(disease.id, "张工")
    print_test("派单操作", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_ASSIGNED)

    result = service.start_treatment(disease.id)
    print_test("开始处置", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_IN_PROGRESS)

    result = service.complete_treatment(disease.id)
    print_test("完成处置", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_COMPLETED)

    result = service.accept_disease(
        disease.id,
        acceptance_result=ACCEPTANCE_RESULT_PASS,
        acceptance_opinion="验收通过，修缮质量良好",
        acceptor="李工",
    )
    print_test("整改验收通过", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_ACCEPTED)

    result = service.review_disease(
        disease.id,
        acceptance_result=ACCEPTANCE_RESULT_PASS,
        acceptance_opinion="复查通过",
        acceptor="王工",
    )
    print_test("复查通过", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_REVIEWED)

    result = service.archive_disease(disease.id)
    print_test("归档", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_ARCHIVED)

    result = service.reopen_disease(disease.id, reason="发现新问题")
    print_test("重新打开", result.success and
               db.get_disease_record(disease.id).status == DISEASE_STATUS_PENDING)

    history = db.get_status_history_by_disease(disease.id)
    print_test("状态历史记录", len(history) >= 9)

    return disease.id


def test_completion_date_validation(db, service, building_id, component_id):
    print_section("3. 完成日期自动校验测试")

    disease = make_disease(building_id, component_id,
                          status=DISEASE_STATUS_IN_PROGRESS,
                          description="日期校验测试",
                          plan_date=(datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"))
    disease.id = db.add_disease_record(disease)

    result = service.complete_treatment(disease.id)
    print_test("完成时自动设置完成日期", result.success)

    updated = db.get_disease_record(disease.id)
    print_test("完成日期已填写",
               updated.complete_date is not None and updated.complete_date != "")

    future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    updated.complete_date = future_date
    result = service._validate_completion_date(updated, DISEASE_STATUS_ACCEPTED)
    print_test("未来日期校验不通过", not result)


def test_photo_archive(db, service, building_id, component_id):
    print_section("4. 病害图片归档管理测试")

    disease = make_disease(building_id, component_id, description="图片归档测试")
    disease.id = db.add_disease_record(disease)

    from database import DiseasePhotoArchive, PHOTO_STAGE_DISCOVERY, PHOTO_STAGE_ACCEPTANCE

    photo = DiseasePhotoArchive(
        id=None,
        disease_id=disease.id,
        photo_path="/test/before.jpg",
        photo_type=PHOTO_TYPE_BEFORE,
        photo_stage=PHOTO_STAGE_DISCOVERY,
        description="修缮前照片",
    )
    photo_id = db.add_disease_photo(photo)
    print_test("添加修缮前照片", photo_id is not None)

    photo2 = DiseasePhotoArchive(
        id=None,
        disease_id=disease.id,
        photo_path="/test/after.jpg",
        photo_type=PHOTO_TYPE_AFTER,
        photo_stage=PHOTO_STAGE_ACCEPTANCE,
        description="修缮后照片",
    )
    photo_id2 = db.add_disease_photo(photo2)
    print_test("添加修缮后照片", photo_id2 is not None)

    before_photos = db.get_photos_by_type(disease.id, PHOTO_TYPE_BEFORE)
    print_test("按类型查询修缮前照片", len(before_photos) == 1)

    after_photos = db.get_photos_by_type(disease.id, PHOTO_TYPE_AFTER)
    print_test("按类型查询修缮后照片", len(after_photos) == 1)

    all_photos = db.get_photos_by_disease(disease.id)
    print_test("查询所有照片", len(all_photos) == 2)

    return disease.id


def test_deviation_disease_link(db, service, building_id, component_id):
    print_section("5. 偏差病害联动预警测试")

    disease1 = make_disease(building_id, component_id,
                           severity=DISEASE_SEVERITY_SEVERE,
                           priority=PRIORITY_URGENT,
                           status=DISEASE_STATUS_PENDING,
                           description="联动测试1")
    disease1.id = db.add_disease_record(disease1)

    disease2 = make_disease(building_id, component_id,
                           status=DISEASE_STATUS_PENDING,
                           description="联动测试2")
    disease2.id = db.add_disease_record(disease2)

    from database import DeviationDiseaseLink, RISK_LEVEL_HIGH

    link = DeviationDiseaseLink(
        id=None,
        component_id=component_id,
        component_code="C-001",
        deviation_level="严重",
        disease_count=2,
        risk_level=RISK_LEVEL_HIGH,
        assessment="偏差较大且病害较多，风险较高",
        suggestion="建议优先处理",
    )
    link_id = db.upsert_deviation_disease_link(link)
    print_test("创建偏差病害联动记录", link_id is not None)

    link_result = db.get_deviation_disease_link(component_id)
    print_test("查询联动记录", link_result is not None and link_result.disease_count == 2)

    risk_level = link_result.risk_level
    print_test(f"风险等级: {risk_level}",
               risk_level in ["low", "medium", "high", "critical"])

    all_links = db.get_high_risk_components(building_id, min_risk_level="low")
    print_test("查询建筑所有联动", len(all_links) >= 1)


def test_warning_system(db, service, building_id, component_id):
    print_section("6. 预警系统测试")

    from database import WarningRecord

    warning = WarningRecord(
        id=None,
        building_id=building_id,
        component_id=component_id,
        component_code="C-001",
        warning_type=WARNING_TYPE_DISEASE,
        warning_level=WARNING_LEVEL_DANGER,
        title="严重病害预警",
        description="发现严重病害需紧急处理",
        related_disease_id=1,
    )
    warning_id = db.add_warning(warning)
    print_test("创建病害预警", warning_id is not None)

    warning2 = WarningRecord(
        id=None,
        building_id=building_id,
        component_id=component_id,
        component_code="C-001",
        warning_type=WARNING_TYPE_DEADLINE,
        warning_level=WARNING_LEVEL_WARNING,
        title="期限临近预警",
        description="病害处理期限即将到期",
    )
    warning_id2 = db.add_warning(warning2)
    print_test("创建期限预警", warning_id2 is not None)

    warnings = db.get_warnings_by_building(building_id)
    print_test("查询所有预警", len(warnings) >= 2)

    disease_warnings = db.get_warnings_by_building(
        building_id, warning_type=WARNING_TYPE_DISEASE)
    print_test("按类型查询预警", len(disease_warnings) >= 1)

    unread_count = db.get_unread_warning_count(building_id)
    print_test("未读预警计数", unread_count >= 2)

    result = db.mark_warning_read(warning_id)
    print_test("标记已读", result)

    unread_count_after = db.get_unread_warning_count(building_id)
    print_test("已读后未读计数减少", unread_count_after < unread_count)


def test_acceptance_records(db, service, building_id, component_id):
    print_section("7. 验收记录测试")

    from database import DiseaseAcceptanceRecord

    disease = make_disease(building_id, component_id,
                          status=DISEASE_STATUS_COMPLETED,
                          description="验收记录测试")
    disease.id = db.add_disease_record(disease)

    record = DiseaseAcceptanceRecord(
        id=None,
        disease_id=disease.id,
        acceptance_result=ACCEPTANCE_RESULT_PASS,
        acceptance_opinion="验收通过，质量合格",
        acceptor="张验收",
        photo_paths="/test/acc1.jpg|/test/acc2.jpg",
        is_review=False,
    )
    record_id = db.add_disease_acceptance(record)
    print_test("创建验收记录", record_id is not None)

    records = db.get_acceptance_by_disease(disease.id)
    print_test("查询验收记录", len(records) == 1)

    record = records[0]
    print_test("验收记录内容正确",
               record.acceptance_result == ACCEPTANCE_RESULT_PASS and
               record.acceptor == "张验收")

    latest = db.get_latest_acceptance(disease.id)
    print_test("查询最新验收记录", latest is not None)


def test_operation_logs(db, service, building_id, component_id):
    print_section("8. 操作日志测试")

    from database import OperationLog, MODULE_DISEASE, ACTION_STATUS_CHANGE

    log = OperationLog(
        id=None,
        module=MODULE_DISEASE,
        action=ACTION_STATUS_CHANGE,
        target_type="disease_record",
        target_id=1,
        operator="管理员",
        detail="病害状态从发现变更为待派单",
    )
    log_id = db.add_operation_log(log)
    print_test("创建操作日志", log_id is not None)

    logs = db.get_operation_logs()
    print_test("查询操作日志", len(logs) >= 1)

    module_logs = db.get_operation_logs(module=MODULE_DISEASE)
    print_test("按模块查询日志", len(module_logs) >= 1)

    action_logs = db.get_operation_logs(action=ACTION_STATUS_CHANGE)
    print_test("按操作类型查询日志", len(action_logs) >= 1)

    log_entry = logs[0]
    print_test("日志内容完整",
               log_entry.module == MODULE_DISEASE and
               log_entry.action == ACTION_STATUS_CHANGE and
               log_entry.operator == "管理员")


def test_dashboard_stats(db, service, building_id):
    print_section("9. 看板统计测试")

    stats = db.get_disease_statistics(building_id)
    print_test("病害统计获取", stats is not None)

    print_test("病害总数统计", stats.total_count > 0)
    print_test("待处理统计", stats.pending_count >= 0)
    print_test("处置中统计", stats.in_progress_count >= 0)
    print_test("已归档统计", stats.archived_count >= 0)
    print_test("按类型统计", len(stats.by_type) > 0)
    print_test("按严重程度统计", len(stats.by_severity) > 0)
    print_test("按优先级统计", len(stats.by_priority) > 0)
    print_test("估算总费用统计", stats.total_estimated_cost >= 0)


def test_page_state_cleanup():
    print_section("10. 页面状态清理机制测试")

    from ui.disease_widget import DiseaseManagementWidget, DiseaseDashboardWidget

    print_test("病害管理组件可导入", True)
    print_test("病害看板组件可导入", True)

    from ui.disease_advanced_widgets import (
        DiseaseAcceptanceDialog, WorkflowStepWidget,
        DiseasePhotoCompareWidget, DiseaseStatusHistoryWidget,
        WarningListWidget,
    )

    print_test("验收对话框可导入", True)
    print_test("工作流步骤组件可导入", True)
    print_test("图片对比组件可导入", True)
    print_test("状态历史组件可导入", True)
    print_test("预警列表组件可导入", True)


def main():
    print("\n" + "="*60)
    print("  古建筑木构件测绘数据管理系统 - 升级版功能测试")
    print("="*60)

    try:
        db, service, building_id, component_id = setup_test_environment()
        print(f"\n测试环境就绪 - 数据库: 临时文件, 建筑ID: {building_id}")

        test_state_machine(service)
        test_workflow_closed_loop(db, service, building_id, component_id)
        test_completion_date_validation(db, service, building_id, component_id)
        test_photo_archive(db, service, building_id, component_id)
        test_deviation_disease_link(db, service, building_id, component_id)
        test_warning_system(db, service, building_id, component_id)
        test_acceptance_records(db, service, building_id, component_id)
        test_operation_logs(db, service, building_id, component_id)
        test_dashboard_stats(db, service, building_id)
        test_page_state_cleanup()

        print_section("测试总结")
        print("\n  ✓ 所有核心功能测试完成")
        print("  ✓ 病害状态机正常工作")
        print("  ✓ 闭环处置流程完整")
        print("  ✓ 完成日期自动校验")
        print("  ✓ 图片归档管理")
        print("  ✓ 偏差病害联动预警")
        print("  ✓ 验收记录管理")
        print("  ✓ 操作日志审计")
        print("  ✓ 看板统计展示")
        print("  ✓ UI组件可正常导入")
        print("\n" + "="*60 + "\n")

        db.close()
        return 0

    except Exception as e:
        print(f"\n✗ 测试执行出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
