"""
房源模块视图：公共房源列表与详情、商家发布/管理房源接口
"""
import copy
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.apartments.models import Apartment, RentalPlan, RoomType
from apps.apartments.serializers import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListItemSerializer,
    ApartmentUpdateSerializer,
    MerchantApartmentDetailSerializer,
    MerchantApartmentListSerializer,
    RoomTypeDetailSerializer,
)
from apps.apartments.utils import backfill_apartment_min_rent, backfill_apartment_min_area
from apps.audits.models import AuditRecord
from core.exceptions import BusinessException, NotFoundException, GoneException
from core.pagination import StandardPagination
from core.response import ErrorCode, unified_response, UnifiedErrorResponseSerializer

logger = logging.getLogger('apps')


# ============================================================
# 公共房源接口（公开访问）
# ============================================================

@extend_schema(
    request=None,
    responses={
        200: ApartmentListItemSerializer(many=True),
    },
    summary='公共房源列表',
    description='仅展示已上架（published）房源，支持组合筛选与分页。筛选条件可叠加，结果按审核通过时间（updated_at）倒序。',
    tags=['公共房源'],
    parameters=[
        {'name': 'keyword', 'in': 'query', 'schema': {'type': 'string'}, 'description': '公寓名称关键词'},
        {'name': 'district_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '行政区 ID'},
        {'name': 'street_ids', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'integer'}}, 'description': '街道/镇 ID 数组（多选）'},
        {'name': 'layout_types', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'string'}}, 'description': '户型编码数组（多选）'},
        {'name': 'lease_terms', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'string'}}, 'description': '租期编码数组（多选）'},
        {'name': 'min_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最低月租金'},
        {'name': 'max_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最高月租金'},
        {'name': 'page', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '页码，默认 1'},
        {'name': 'page_size', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '每页条数，默认 10，最大 100'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_list(request):
    """
    GET /api/v1/apartments
    公共房源列表（仅 published）
    """
    queryset = Apartment.objects.filter(status='published').order_by('-updated_at')

    # 关键词搜索（公寓名称）
    keyword = request.query_params.get('keyword')
    if keyword:
        queryset = queryset.filter(name__icontains=keyword)

    # 行政区筛选
    district_id = request.query_params.get('district_id')
    if district_id:
        try:
            queryset = queryset.filter(district_id=int(district_id))
        except ValueError:
            pass

    # 街道筛选（支持多选）
    street_ids = request.query_params.get('street_ids')
    if street_ids:
        try:
            ids = [int(x) for x in street_ids.split(',') if x.strip()]
            if ids:
                queryset = queryset.filter(street_id__in=ids)
        except ValueError:
            pass

    # 户型筛选（支持多选）
    layout_types = request.query_params.get('layout_types')
    if layout_types:
        types = [x.strip() for x in layout_types.split(',') if x.strip()]
        if types:
            queryset = queryset.filter(room_types__layout_type__in=types).distinct()

    # 租期筛选（支持多选）
    lease_terms = request.query_params.get('lease_terms')
    if lease_terms:
        terms = [x.strip() for x in lease_terms.split(',') if x.strip()]
        if terms:
            queryset = queryset.filter(
                room_types__rental_plans__lease_term__in=terms
            ).distinct()

    # 向后兼容：旧单值参数仍可正常工作
    street_id = request.query_params.get('street_id')
    if street_id and not street_ids:
        try:
            queryset = queryset.filter(street_id=int(street_id))
        except ValueError:
            pass

    layout_type = request.query_params.get('layout_type')
    if layout_type and not layout_types:
        queryset = queryset.filter(room_types__layout_type=layout_type).distinct()

    lease_term = request.query_params.get('lease_term')
    if lease_term and not lease_terms:
        queryset = queryset.filter(
            room_types__rental_plans__lease_term=lease_term
        ).distinct()

    # 价格区间筛选（基于 min_monthly_rent）
    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    if min_price:
        try:
            queryset = queryset.filter(min_monthly_rent__gte=int(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            queryset = queryset.filter(min_monthly_rent__lte=int(max_price))
        except ValueError:
            pass

    # 分页
    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ApartmentListItemSerializer(
        page, many=True, context={'request': request}
    )
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: ApartmentDetailSerializer,
        404: UnifiedErrorResponseSerializer,
        410: UnifiedErrorResponseSerializer,
    },
    summary='房源详情',
    description='返回完整公寓信息、房型卡片列表及当前用户收藏状态（已登录时）。若房源已下架或已删除，返回 410001 提示用户房源已下架。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_detail(request, id):
    """
    GET /api/v1/apartments/{id}
    房源详情
    """
    try:
        apartment = Apartment.all_objects.get(id=id)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    # 若房源已下架或已删除，返回 410 提示用户
    if apartment.status != 'published' or apartment.deleted_at is not None:
        raise GoneException('房源已下架，您可以在收藏列表中取消收藏')

    # 自动回填 min_monthly_rent / min_area（防御性修复历史脏数据）
    if apartment.min_monthly_rent is None:
        backfill_apartment_min_rent(apartment)
    if apartment.min_area is None:
        backfill_apartment_min_area(apartment)

    serializer = ApartmentDetailSerializer(apartment, context={'request': request})
    return unified_response(data=serializer.data)


@extend_schema(
    request=None,
    responses={
        200: RoomTypeDetailSerializer(many=True),
        404: UnifiedErrorResponseSerializer,
    },
    summary='房源下所有房型',
    description='获取指定房源下的所有房型详情（含租金方案）。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_room_types(request, id):
    """
    GET /api/v1/apartments/{id}/room-types
    房源下所有房型
    """
    try:
        apartment = Apartment.objects.get(id=id, status='published')
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    room_types = apartment.room_types.all().order_by('sort', 'id')
    # 预加载租金方案，避免 N+1
    room_types = room_types.prefetch_related('rental_plans')
    serializer = RoomTypeDetailSerializer(room_types, many=True)
    return unified_response(data=serializer.data)


@extend_schema(
    request=None,
    responses={
        200: RoomTypeDetailSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='户型详情',
    description='获取指定户型详情，包含完整租金方案及所属公寓简要信息。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '户型 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def room_type_detail(request, id):
    """
    GET /api/v1/room-types/{id}
    户型详情
    """
    try:
        room_type = RoomType.objects.get(id=id)
    except RoomType.DoesNotExist:
        raise NotFoundException('户型不存在')

    # 校验所属公寓是否已上架
    if room_type.apartment.status != 'published':
        raise NotFoundException('房源不存在或未上架')

    # 预加载租金方案
    room_type.rental_plans.all()  # prefetch 已在序列化器中通过 context 控制，这里直接查
    serializer = RoomTypeDetailSerializer(room_type)
    return unified_response(data=serializer.data)


# ============================================================
# 商家发布房源接口（已有）
# ============================================================

def create_apartment(request):
    """
    POST /api/v1/merchant/apartments
    商家发布房源
    （由 merchant_urls.py 中的外层视图统一添加 @api_view 和 @permission_classes）
    """
    serializer = ApartmentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        # 提取第一个错误信息，返回 PARAM_ERROR
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    data = serializer.validated_data
    landlord = request.user

    with transaction.atomic():
        # 1. 创建公寓
        apartment = Apartment.objects.create(
            landlord=landlord,
            name=data['name'],
            cover_image=data['cover_image'],
            description=data['description'],
            district_id=data['district_id'],
            street_id=data['street_id'],
            detail_address=data['detail_address'],
            contact_phone=data['contact_phone'],
            status='pending_first_review',
            min_monthly_rent=None,
            longitude=data.get('longitude'),
            latitude=data.get('latitude'),
            property_fee=data.get('property_fee'),
            water_fee=data.get('water_fee') or None,
            electric_fee=data.get('electric_fee') or None,
            service_fee=data.get('service_fee'),
            other_fees=data.get('other_fees', ''),
            min_area=None,
        )

        # 2. 创建房型与租金方案，计算最低月租金和最小面积
        global_min_rent = None
        global_min_area = None
        for rt_data in data['room_types']:
            room_type = RoomType.objects.create(
                apartment=apartment,
                name=rt_data['name'],
                images=rt_data['images'],
                facilities=rt_data.get('facilities', []),
                layout_type=rt_data['layout_type'],
                window_type=rt_data['window_type'],
                floor=rt_data['floor'],
                sort=rt_data.get('sort', 0),
                area=rt_data.get('area'),
                orientation=rt_data.get('orientation') or None,
                available_date=rt_data.get('available_date'),
            )

            room_area = rt_data.get('area')
            if room_area is not None:
                if global_min_area is None or room_area < global_min_area:
                    global_min_area = room_area

            for rp_data in rt_data['rental_plans']:
                RentalPlan.objects.create(
                    room_type=room_type,
                    lease_term=rp_data['lease_term'],
                    monthly_rent=rp_data['monthly_rent'],
                    payment_method=rp_data['payment_method'],
                )
                if global_min_rent is None or rp_data['monthly_rent'] < global_min_rent:
                    global_min_rent = rp_data['monthly_rent']

        # 3. 更新公寓最低月租金缓存和最小面积缓存
        update_fields = []
        if global_min_rent is not None:
            apartment.min_monthly_rent = global_min_rent
            update_fields.append('min_monthly_rent')
        if global_min_area is not None:
            apartment.min_area = global_min_area
            update_fields.append('min_area')
        if update_fields:
            apartment.save(update_fields=update_fields)

        # 4. 构建房源快照 JSON
        submitted_data = _build_apartment_snapshot(apartment)

        # 5. 创建首次审核记录
        audit = AuditRecord.objects.create(
            apartment=apartment,
            type='first_review',
            status='pending',
            submitted_data=submitted_data,
        )

    logger.info(f'[CreateApartment] landlord={landlord.id}, apartment={apartment.id}, audit={audit.id}')

    return unified_response(
        data={
            'apartment_id': apartment.id,
            'audit_id': audit.id,
        },
        code=ErrorCode.SUCCESS,
    )





def _extract_first_error(errors):
    """
    从 serializer.errors 中提取第一个错误信息字符串
    """
    if isinstance(errors, dict):
        for key in errors:
            val = errors[key]
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict):
                        result = _extract_first_error(item)
                        if result and result != '{}':
                            return result
                return str(val[0])
            elif isinstance(val, dict):
                return _extract_first_error(val)
            return str(val)
    elif isinstance(errors, list):
        for item in errors:
            if isinstance(item, dict):
                result = _extract_first_error(item)
                if result and result != '{}':
                    return result
        return str(errors[0]) if errors else ''
    return str(errors)


def _build_apartment_snapshot(apartment):
    """
    构建房源完整快照 JSON，包含公寓、房型、租金方案
    """
    room_types_data = []
    for rt in apartment.room_types.all():
        plans = []
        for rp in rt.rental_plans.all():
            plans.append({
                'lease_term': rp.lease_term,
                'monthly_rent': rp.monthly_rent,
                'payment_method': rp.payment_method,
            })
        room_types_data.append({
            'name': rt.name,
            'images': rt.images,
            'facilities': rt.facilities,
            'layout_type': rt.layout_type,
            'window_type': rt.window_type,
            'floor': rt.floor,
            'sort': rt.sort,
            'area': float(rt.area) if rt.area is not None else None,
            'orientation': rt.orientation,
            'available_date': rt.available_date.isoformat() if rt.available_date else None,
            'rental_plans': plans,
        })

    return {
        'name': apartment.name,
        'cover_image': apartment.cover_image,
        'description': apartment.description,
        'district_id': apartment.district_id,
        'street_id': apartment.street_id,
        'detail_address': apartment.detail_address,
        'contact_phone': apartment.contact_phone,
        'longitude': float(apartment.longitude) if apartment.longitude is not None else None,
        'latitude': float(apartment.latitude) if apartment.latitude is not None else None,
        'property_fee': apartment.property_fee,
        'water_fee': apartment.water_fee,
        'electric_fee': apartment.electric_fee,
        'service_fee': apartment.service_fee,
        'other_fees': apartment.other_fees,
        'room_types': room_types_data,
    }


# ============================================================
# 商家已上架房源管理接口（新增）
# ============================================================

def merchant_apartment_list(request):
    """
    GET /api/v1/merchant/apartments
    商家已上架房源列表
    （由 merchant_urls.py 中的外层视图统一添加 @api_view 和 @permission_classes）
    """
    landlord = request.user
    queryset = Apartment.objects.filter(
        landlord=landlord,
        status='published',
    ).order_by('-updated_at')

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = MerchantApartmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


def merchant_apartment_detail(request, id):
    """
    GET /api/v1/merchant/apartments/{id}
    商家自有房源详情
    （由 merchant_urls.py 中的外层视图统一添加 @api_view 和 @permission_classes）
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    serializer = MerchantApartmentDetailSerializer(apartment)
    return unified_response(data=serializer.data)


def merchant_apartment_update(request, id):
    """
    PUT /api/v1/merchant/apartments/{id}
    商家编辑房源
    （由 merchant_urls.py 中的外层视图统一添加 @api_view 和 @permission_classes）
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    serializer = ApartmentUpdateSerializer(data=request.data, instance=apartment)
    if not serializer.is_valid():
        first_msg = _extract_first_error(serializer.errors)
        raise BusinessException(first_msg, code=ErrorCode.PARAM_ERROR)

    data = serializer.validated_data

    # 判断关键字段是否变化
    KEY_FIELDS = ['name', 'district_id', 'street_id', 'detail_address']
    key_changed = False
    for field in KEY_FIELDS:
        if field in data:
            current_val = getattr(apartment, field)
            if current_val != data[field]:
                key_changed = True
                break

    # 构建原房源快照（用于审核记录）
    original_data = _build_apartment_snapshot(apartment)

    with transaction.atomic():
        if key_changed:
            # 生成变更审核单，原房源保持 published
            submitted_data = copy.deepcopy(original_data)
            # 将变更应用到 submitted_data 中
            NEW_APARTMENT_FIELDS = [
                'longitude', 'latitude', 'property_fee', 'water_fee',
                'electric_fee', 'service_fee', 'other_fees',
            ]
            for field in data:
                if field == 'room_types':
                    submitted_data['room_types'] = _build_room_types_from_data(data['room_types'])
                elif field in KEY_FIELDS:
                    submitted_data[field] = data[field]
                elif field == 'cover_image':
                    submitted_data['cover_image'] = data[field]
                elif field == 'description':
                    submitted_data['description'] = data[field]
                elif field == 'contact_phone':
                    submitted_data['contact_phone'] = data[field]
                elif field in NEW_APARTMENT_FIELDS:
                    val = data[field]
                    submitted_data[field] = float(val) if isinstance(val, Decimal) else val

            changed_fields = [f for f in KEY_FIELDS if f in data and getattr(apartment, f) != data[f]]

            audit = AuditRecord.objects.create(
                apartment=apartment,
                type='change_review',
                status='pending',
                submitted_data=submitted_data,
                original_data=original_data,
                changed_fields=changed_fields,
            )

            logger.info(f'[UpdateApartment] change_review created, '
                        f'landlord={landlord.id}, apartment={apartment.id}, audit={audit.id}')

            return unified_response(
                data={
                    'apartment_id': apartment.id,
                    'audit_id': audit.id,
                    'updated': False,
                },
                code=ErrorCode.SUCCESS,
            )
        else:
            # 直接更新房源
            for field in ['name', 'cover_image', 'description', 'contact_phone']:
                if field in data:
                    setattr(apartment, field, data[field])

            if 'district_id' in data:
                apartment.district_id = data['district_id']
            if 'street_id' in data:
                apartment.street_id = data['street_id']
            if 'detail_address' in data:
                apartment.detail_address = data['detail_address']

            NEW_DIRECT_FIELDS = [
                'longitude', 'latitude', 'property_fee', 'water_fee',
                'electric_fee', 'service_fee', 'other_fees',
            ]
            for field in NEW_DIRECT_FIELDS:
                if field in data:
                    setattr(apartment, field, data[field])

            apartment.save()

            # 若传了房型数据，全量替换
            if 'room_types' in data:
                # 软删除原有房型（级联软删除租金方案）
                for rt in apartment.room_types.all():
                    rt.delete()

                global_min_rent = None
                global_min_area = None
                for rt_data in data['room_types']:
                    room_type = RoomType.objects.create(
                        apartment=apartment,
                        name=rt_data['name'],
                        images=rt_data['images'],
                        facilities=rt_data.get('facilities', []),
                        layout_type=rt_data['layout_type'],
                        window_type=rt_data['window_type'],
                        floor=rt_data['floor'],
                        sort=rt_data.get('sort', 0),
                        area=rt_data.get('area'),
                        orientation=rt_data.get('orientation') or None,
                        available_date=rt_data.get('available_date'),
                    )
                    room_area = rt_data.get('area')
                    if room_area is not None:
                        if global_min_area is None or room_area < global_min_area:
                            global_min_area = room_area

                    for rp_data in rt_data['rental_plans']:
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

            logger.info(f'[UpdateApartment] direct update, '
                        f'landlord={landlord.id}, apartment={apartment.id}')

            return unified_response(
                data={
                    'apartment_id': apartment.id,
                    'audit_id': None,
                    'updated': True,
                },
                code=ErrorCode.SUCCESS,
            )


def merchant_apartment_delete(request, id):
    """
    DELETE /api/v1/merchant/apartments/{id}
    商家删除房源
    （由 merchant_urls.py 中的外层视图统一添加 @api_view 和 @permission_classes）
    """
    landlord = request.user
    try:
        apartment = Apartment.objects.get(id=id, landlord=landlord)
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在')

    with transaction.atomic():
        # 软删除关联的未批准审核单
        apartment.audit_records.filter(
            status='pending',
            deleted_at__isnull=True,
        ).update(deleted_at=timezone.now())

        # 软删除关联房型（级联软删除租金方案）
        for rt in apartment.room_types.all():
            rt.delete()

        # 软删除房源
        apartment.deleted_at = timezone.now()
        apartment.save(update_fields=['deleted_at'])

    logger.info(f'[DeleteApartment] landlord={landlord.id}, apartment={id}')

    return unified_response(
        data={
            'apartment_id': id,
            'deleted': True,
        },
        code=ErrorCode.SUCCESS,
    )


def _build_room_types_from_data(room_types_data):
    """
    从请求数据构建房型快照列表
    """
    result = []
    for rt_data in room_types_data:
        plans = []
        for rp_data in rt_data['rental_plans']:
            plans.append({
                'lease_term': rp_data['lease_term'],
                'monthly_rent': rp_data['monthly_rent'],
                'payment_method': rp_data['payment_method'],
            })
        result.append({
            'name': rt_data['name'],
            'images': rt_data['images'],
            'facilities': rt_data.get('facilities', []),
            'layout_type': rt_data['layout_type'],
            'window_type': rt_data['window_type'],
            'floor': rt_data['floor'],
            'sort': rt_data.get('sort', 0),
            'area': float(rt_data['area']) if rt_data.get('area') is not None else None,
            'orientation': rt_data.get('orientation') or None,
            'available_date': rt_data['available_date'].isoformat() if rt_data.get('available_date') else None,
            'rental_plans': plans,
        })
    return result

