"""
管理员审核模块视图
"""
import logging
from datetime import date

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.apartments.models import RentalPlan, RoomType
from apps.audits.models import AuditRecord
from apps.audits.serializers import (
    AuditActionResponseSerializer,
    AuditApproveSerializer,
    AuditDetailSerializer,
    AuditListItemSerializer,
    AuditRejectSerializer,
    ApartmentVerifySerializer,
    MerchantAuditListItemSerializer,
)
from apps.messages_app.models import Message
from core.exceptions import BusinessException, NotFoundException
from core.pagination import StandardPagination
from core.permissions import IsAdmin, IsLandlord
from core.response import ErrorCode, unified_response, UnifiedErrorResponseSerializer
from core.sms import send_sms

logger = logging.getLogger('apps')


# ============================================================
# 商家审核接口
# ============================================================

@extend_schema(
    request=None,
    responses={
        200: MerchantAuditListItemSerializer(many=True),
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
    },
    summary='商家审核记录列表',
    description='商家查看自有房源的审核记录列表。仅 landlord 角色可访问，只能查看自己的房源审核记录。支持分页、按房源名称 keyword 搜索，按提交时间倒序。',
    tags=['商家审核'],
    parameters=[
        {'name': 'keyword', 'in': 'query', 'schema': {'type': 'string'}, 'description': '房源名称关键词，支持模糊匹配'},
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_audit_list(request):
    """
    GET /api/v1/merchant/audits
    商家审核记录列表
    """
    queryset = AuditRecord.objects.filter(
        deleted_at__isnull=True,
        apartment__landlord=request.user,
        status__in=['pending', 'rejected'],
    ).annotate(
        status_order=Case(
            When(status='pending', then=Value(1)),
            When(status='approved', then=Value(2)),
            When(status='rejected', then=Value(3)),
            output_field=IntegerField(),
        )
    ).order_by('status_order', 'created_at', 'id')

    # 按房源名称搜索
    keyword = request.query_params.get('keyword')
    if keyword:
        queryset = queryset.filter(apartment__name__icontains=keyword)

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = MerchantAuditListItemSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


# ============================================================
# 管理员审核接口
# ============================================================

@extend_schema(
    request=None,
    responses={
        200: AuditListItemSerializer(many=True),
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
    },
    summary='审核单列表',
    description='管理员查看审核单列表。支持按 type、status 筛选，支持按房源名称 keyword 搜索，按提交时间倒序。',
    tags=['管理员审核'],
    parameters=[
        {'name': 'type', 'in': 'query', 'schema': {'type': 'string'}, 'description': '审核类型：first_review / change_review'},
        {'name': 'status', 'in': 'query', 'schema': {'type': 'string'}, 'description': '审核状态：pending / approved / rejected'},
        {'name': 'keyword', 'in': 'query', 'schema': {'type': 'string'}, 'description': '房源名称关键词，支持模糊匹配'},
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_list(request):
    """
    GET /api/v1/admin/audits
    审核单列表（管理员）
    """
    queryset = AuditRecord.objects.filter(deleted_at__isnull=True).annotate(
        status_order=Case(
            When(status='pending', then=Value(1)),
            When(status='approved', then=Value(2)),
            When(status='rejected', then=Value(3)),
            output_field=IntegerField(),
        )
    ).order_by('status_order', 'created_at', 'id')

    # 按类型筛选
    audit_type = request.query_params.get('type')
    if audit_type:
        queryset = queryset.filter(type=audit_type)

    # 按状态筛选
    audit_status = request.query_params.get('status')
    if audit_status:
        queryset = queryset.filter(status=audit_status)

    # 按房源名称搜索
    keyword = request.query_params.get('keyword')
    if keyword:
        queryset = queryset.filter(apartment__name__icontains=keyword)

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = AuditListItemSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: AuditDetailSerializer,
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='审核详情',
    description='管理员查看审核单详情。变更审核返回 original_data、submitted_data、changed_fields。',
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_detail(request, id):
    """
    GET /api/v1/admin/audits/{id}
    审核详情（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    serializer = AuditDetailSerializer(audit)
    return unified_response(data=serializer.data)


@extend_schema(
    request=AuditApproveSerializer,
    responses={
        200: AuditActionResponseSerializer,
        400: UnifiedErrorResponseSerializer,
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='通过审核',
    description=(
        '管理员通过审核。首次审核通过将公寓置为 published；'
        '变更审核通过后将 submitted_data 快照覆盖原房源（房型全量替换）。'
    ),
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_approve(request, id):
    """
    POST /api/v1/admin/audits/{id}/approve
    通过审核（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    if audit.status != 'pending':
        raise BusinessException('该审核单已处理，无法再次操作', code=ErrorCode.BUSINESS_ERROR)

    serializer = AuditApproveSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    verified = serializer.validated_data.get('verified', False)
    apartment = audit.apartment
    reviewer = request.user

    with transaction.atomic():
        if audit.type == 'first_review':
            apartment.status = 'published'
            apartment.save(update_fields=['status'])
        elif audit.type == 'change_review':
            _apply_submitted_data(apartment, audit.submitted_data)

        if verified:
            apartment.verified = True
            apartment.save(update_fields=['verified'])

        audit.status = 'approved'
        audit.reviewer = reviewer
        audit.save(update_fields=['status', 'reviewer'])

        # 发送审核通过站内信（核心通知，与审核状态强绑定，保留在事务内）
        _send_approve_message(audit)

    logger.info(f'[AuditApprove] reviewer={reviewer.id}, audit={audit.id}, type={audit.type}')

    return unified_response(
        data={
            'audit_id': audit.id,
            'apartment_id': apartment.id,
            'action': 'approve',
            'status': audit.status,
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=AuditRejectSerializer,
    responses={
        200: AuditActionResponseSerializer,
        400: UnifiedErrorResponseSerializer,
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='驳回审核',
    description=(
        '管理员驳回审核。首次审核驳回将公寓置为 first_rejected；'
        '变更审核驳回保留原房源 published 状态，审核单作废。'
        '驳回后发送站内信与短信通知商家。'
    ),
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '审核单 ID'},
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdmin])
def audit_reject(request, id):
    """
    POST /api/v1/admin/audits/{id}/reject
    驳回审核（管理员）
    """
    try:
        audit = AuditRecord.objects.get(id=id, deleted_at__isnull=True)
    except AuditRecord.DoesNotExist:
        raise NotFoundException('审核单不存在')

    if audit.status != 'pending':
        raise BusinessException('该审核单已处理，无法再次操作', code=ErrorCode.BUSINESS_ERROR)

    serializer = AuditRejectSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    reject_reason = serializer.validated_data['reject_reason']
    apartment = audit.apartment
    reviewer = request.user
    landlord = apartment.landlord

    with transaction.atomic():
        if audit.type == 'first_review':
            # 首次审核驳回：公寓置为 first_rejected
            apartment.status = 'first_rejected'
            apartment.save(update_fields=['status'])
        # 变更审核驳回：原房源保持 published，无需修改

        # 更新审核单状态
        audit.status = 'rejected'
        audit.reject_reason = reject_reason
        audit.reviewer = reviewer
        audit.save(update_fields=['status', 'reject_reason', 'reviewer'])

        # 发送站内信（核心通知，与审核状态强绑定，保留在事务内）
        _send_reject_message(audit, reject_reason)

    # 短信发送移出事务：避免外部服务异常导致审核状态回滚
    if landlord and landlord.phone:
        send_sms(
            phone=landlord.phone,
            template_code='REJECT_NOTIFY',
            params={'reason': reject_reason},
        )

    logger.info(f'[AuditReject] reviewer={reviewer.id}, audit={audit.id}, type={audit.type}')

    return unified_response(
        data={
            'audit_id': audit.id,
            'apartment_id': apartment.id,
            'action': 'reject',
            'status': audit.status,
        },
        code=ErrorCode.SUCCESS,
    )


@extend_schema(
    request=ApartmentVerifySerializer,
    responses={
        200: {'type': 'object', 'properties': {'code': {'type': 'integer'}, 'message': {'type': 'string'}, 'data': {'type': 'object'}}},
        400: UnifiedErrorResponseSerializer,
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='房源核验管理',
    description='管理员设置/取消房源核验标识。仅管理员可操作。',
    tags=['管理员审核'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsAdmin])
def apartment_verify(request, id):
    """
    PUT /api/v1/admin/apartments/{id}/verify
    管理员设置/取消房源核验标识
    """
    from apps.apartments.models import Apartment

    serializer = ApartmentVerifySerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    verified = serializer.validated_data['verified']

    try:
        apartment = Apartment.objects.get(id=id)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    apartment.verified = verified
    apartment.save(update_fields=['verified'])

    logger.info(f'[ApartmentVerify] admin={request.user.id}, apartment={id}, verified={verified}')

    return unified_response(data={
        'apartment_id': apartment.id,
        'verified': apartment.verified,
    })


def _apply_submitted_data(apartment, submitted_data):
    """
    将 submitted_data 快照覆盖到原房源（变更审核通过时）
    """
    # 更新公寓基础字段
    apartment.name = submitted_data.get('name', apartment.name)
    apartment.cover_image = submitted_data.get('cover_image', apartment.cover_image)
    apartment.description = submitted_data.get('description', apartment.description)
    apartment.district_id = submitted_data.get('district_id', apartment.district_id)
    apartment.street_id = submitted_data.get('street_id', apartment.street_id)
    apartment.detail_address = submitted_data.get('detail_address', apartment.detail_address)
    apartment.contact_phone = submitted_data.get('contact_phone', apartment.contact_phone)
    apartment.longitude = submitted_data.get('longitude', apartment.longitude)
    apartment.latitude = submitted_data.get('latitude', apartment.latitude)
    apartment.property_fee = submitted_data.get('property_fee', apartment.property_fee)
    apartment.water_fee = submitted_data.get('water_fee', apartment.water_fee)
    apartment.electric_fee = submitted_data.get('electric_fee', apartment.electric_fee)
    apartment.service_fee = submitted_data.get('service_fee', apartment.service_fee)
    apartment.other_fees = submitted_data.get('other_fees', apartment.other_fees or '')
    apartment.save()

    # 全量替换房型与租金方案
    room_types_data = submitted_data.get('room_types', [])
    if room_types_data:
        # 软删除原有房型（级联软删除租金方案）
        for rt in apartment.room_types.all():
            rt.delete()

        global_min_rent = None
        global_min_area = None
        for rt_data in room_types_data:
            room_type = RoomType.objects.create(
                apartment=apartment,
                name=rt_data['name'],
                images=rt_data.get('images', []),
                facilities=rt_data.get('facilities', []),
                layout_type=rt_data['layout_type'],
                window_type=rt_data['window_type'],
                floor=rt_data['floor'],
                sort=rt_data.get('sort', 0),
                area=rt_data.get('area'),
                available_date=date.fromisoformat(rt_data['available_date']) if rt_data.get('available_date') else None,
            )
            room_area = rt_data.get('area')
            if room_area is not None:
                if global_min_area is None or room_area < global_min_area:
                    global_min_area = room_area

            for rp_data in rt_data.get('rental_plans', []):
                RentalPlan.objects.create(
                    room_type=room_type,
                    lease_term=rp_data['lease_term'],
                    monthly_rent=rp_data['monthly_rent'],
                    payment_method=rp_data['payment_method'],
                )
                if global_min_rent is None or rp_data['monthly_rent'] < global_min_rent:
                    global_min_rent = rp_data['monthly_rent']

        update_fields = []
        if global_min_rent is not None:
            apartment.min_monthly_rent = global_min_rent
            update_fields.append('min_monthly_rent')
        if global_min_area is not None:
            apartment.min_area = global_min_area
            update_fields.append('min_area')
        if update_fields:
            apartment.save(update_fields=update_fields)


def _send_reject_message(audit, reject_reason):
    """
    发送驳回站内信
    """
    apartment = audit.apartment
    landlord = apartment.landlord if apartment else None
    if not landlord:
        return

    msg_type = 'first_rejected' if audit.type == 'first_review' else 'change_rejected'
    title = '房源审核被驳回' if audit.type == 'first_review' else '房源变更审核被驳回'
    content = f'您的房源「{apartment.name}」审核未通过。驳回原因：{reject_reason}'

    Message.objects.create(
        user=landlord,
        type=msg_type,
        title=title,
        content=content,
        related_apartment=apartment,
        related_audit=audit,
    )


def _send_approve_message(audit):
    """
    发送审核通过站内信
    """
    apartment = audit.apartment
    landlord = apartment.landlord if apartment else None
    if not landlord:
        return

    if audit.type == 'first_review':
        title = '房源审核通过'
        content = f'您的房源「{apartment.name}」已通过审核，正式上架。'
    else:
        title = '房源变更审核通过'
        content = f'您的房源「{apartment.name}」的变更已通过审核，已生效。'

    Message.objects.create(
        user=landlord,
        type='audit_approved',
        title=title,
        content=content,
        related_apartment=apartment,
        related_audit=audit,
    )


def _extract_first_error(errors):
    """
    从 serializer.errors 中提取第一个错误信息字符串
    """
    if isinstance(errors, dict):
        for key in errors:
            val = errors[key]
            if isinstance(val, list):
                return str(val[0])
            elif isinstance(val, dict):
                return _extract_first_error(val)
            else:
                return str(val)
    elif isinstance(errors, list):
        return str(errors[0])
    return str(errors)
