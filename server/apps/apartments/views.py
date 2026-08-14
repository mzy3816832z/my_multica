"""
房源模块视图：公共房源列表与详情、商家发布/管理房源接口
"""
import copy
import logging
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Case, When, Value, IntegerField
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated

from apps.apartments.models import Apartment, RentalPlan, RoomType, ApartmentViewLog
from apps.apartments.serializers import (
    ApartmentCreateSerializer,
    ApartmentDetailSerializer,
    ApartmentListItemSerializer,
    ApartmentUpdateSerializer,
    GeocodeRequestSerializer,
    GeocodeResponseSerializer,
    MapConfigResponseSerializer,
    MerchantApartmentDetailSerializer,
    MerchantApartmentListSerializer,
    NearbyPoiSerializer,
    NearbyResponseSerializer,
    MerchantStatsSerializer,
    RoomTypeDetailSerializer,
    get_dict_label,
)
from apps.apartments.map_service import geocode, search_nearby_pois, build_static_map_url
from apps.apartments.utils import backfill_apartment_min_rent, backfill_apartment_min_area
from apps.audits.models import AuditRecord
from apps.metro.models import MetroStation
from core.exceptions import BusinessException, NotFoundException, GoneException
from core.pagination import StandardPagination
from core.permissions import IsLandlord
from core.response import ErrorCode, unified_response, UnifiedErrorResponseSerializer

logger = logging.getLogger('apps')


# ============================================================
# 公共房源接口（公开访问）
# ============================================================

METRO_RADIUS_KM = 1.5


def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(
        radians,
        [float(lat1), float(lon1), float(lat2), float(lon2)],
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371 * c


def _get_client_ip(request):
    """
    获取客户端 IP（优先取 X-Forwarded-For 第一个 IP，用于匿名 PV 去重）
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _record_apartment_view(apartment, request):
    """
    记录房源详情页 PV，按 (用户/匿名 IP + 天) 去重。
    商家查看自己的房源不计入浏览量；记录失败不影响详情响应。
    """
    try:
        user = request.user if request.user.is_authenticated else None
        # 商家查看自己的房源不计入浏览量
        if user and apartment.landlord_id == user.id:
            return

        if user:
            dedupe_key = f'u:{user.id}'
        else:
            dedupe_key = f'a:{_get_client_ip(request)}'

        today = timezone.localdate()
        ApartmentViewLog.objects.get_or_create(
            apartment=apartment,
            dedupe_key=dedupe_key,
            view_date=today,
        )
    except Exception:
        logger.exception('[ApartmentView] record failed for apartment=%s', apartment.id)


SORT_OPTIONS = {
    'latest': ['-updated_at'],
    'price_asc': [F('min_monthly_rent').asc(nulls_last=True), '-updated_at'],
    'price_desc': [F('min_monthly_rent').desc(nulls_last=True), '-updated_at'],
    'area_desc': [F('min_area').desc(nulls_last=True), '-updated_at'],
    'area_asc': [F('min_area').asc(nulls_last=True), '-updated_at'],
}


@extend_schema(
    request=None,
    responses={
        200: ApartmentListItemSerializer(many=True),
    },
    summary='公共房源列表',
    description='仅展示已上架（published）房源，支持组合筛选、排序与分页。筛选条件可叠加，默认按审核通过时间（updated_at）倒序。',
    tags=['公共房源'],
    parameters=[
        {'name': 'keyword', 'in': 'query', 'schema': {'type': 'string'}, 'description': '公寓名称关键词'},
        {'name': 'district_id', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '行政区 ID'},
        {'name': 'street_ids', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'integer'}}, 'description': '街道/镇 ID 数组（多选）'},
        {'name': 'layout_types', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'string'}}, 'description': '户型编码数组（多选）'},
        {'name': 'lease_terms', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'string'}}, 'description': '租期编码数组（多选）'},
        {'name': 'min_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最低月租金'},
        {'name': 'max_price', 'in': 'query', 'schema': {'type': 'integer'}, 'description': '最高月租金'},
        {'name': 'sort', 'in': 'query', 'schema': {'type': 'string'}, 'description': '排序方式：latest(默认) / price_asc / price_desc / area_desc / area_asc'},
        {'name': 'metro_station_ids', 'in': 'query', 'schema': {'type': 'array', 'items': {'type': 'integer'}}, 'description': '地铁站点 ID 数组（多选），筛选距站点 ≤1.5km 的房源'},
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
    sort = request.query_params.get('sort', 'latest')
    ordering = SORT_OPTIONS.get(sort, SORT_OPTIONS['latest'])
    queryset = Apartment.objects.filter(status='published').order_by(*ordering)

    # 关键词搜索（公寓名称 + 详细地址 + 描述），带相关性排序
    keyword = request.query_params.get('keyword')
    if keyword:
        queryset = queryset.filter(
            Q(name__icontains=keyword)
            | Q(detail_address__icontains=keyword)
            | Q(description__icontains=keyword)
        )
        queryset = queryset.annotate(
            search_rank=Case(
                When(name__iexact=keyword, then=Value(4)),
                When(name__icontains=keyword, then=Value(3)),
                When(detail_address__icontains=keyword, then=Value(2)),
                When(description__icontains=keyword, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('-search_rank', '-updated_at')

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

    metro_station_ids = request.query_params.get('metro_station_ids')
    if metro_station_ids:
        try:
            station_ids = [int(x) for x in metro_station_ids.split(',') if x.strip()]
        except ValueError:
            station_ids = []

        if station_ids:
            stations = MetroStation.objects.filter(id__in=station_ids).values('id', 'longitude', 'latitude')
            station_coords = [
                (float(s['latitude']), float(s['longitude']))
                for s in stations
            ]

            if station_coords:
                candidates = list(
                    queryset.filter(latitude__isnull=False, longitude__isnull=False)
                    .values_list('id', 'latitude', 'longitude')
                )

                qualifying_ids = set()
                for apt_id, apt_lat, apt_lon in candidates:
                    apt_lat_f = float(apt_lat)
                    apt_lon_f = float(apt_lon)
                    for st_lat, st_lon in station_coords:
                        if haversine_distance(st_lat, st_lon, apt_lat_f, apt_lon_f) <= METRO_RADIUS_KM:
                            qualifying_ids.add(apt_id)
                            break

                queryset = queryset.filter(id__in=qualifying_ids)
            else:
                queryset = queryset.none()

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

    _record_apartment_view(apartment, request)

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


def _build_compare_item(apartment):
    """
    构建单套公寓的简化对比数据，包含价格/面积/费用明细/设施列表。
    设施标签从系统字典解析（缺失时回退到原始编码）。
    """
    facility_codes = set()
    for rt in apartment.room_types.all().order_by('sort', 'id'):
        for code in (rt.facilities or []):
            facility_codes.add(code)

    facilities = sorted(
        get_dict_label('facility', code) for code in facility_codes
    )

    return {
        'id': apartment.id,
        'name': apartment.name,
        'cover_image': apartment.cover_image,
        'min_monthly_rent': apartment.min_monthly_rent,
        'min_area': float(apartment.min_area) if apartment.min_area is not None else None,
        'fees': {
            'property_fee': apartment.property_fee,
            'water_fee_label': get_dict_label('fee_type', apartment.water_fee),
            'electric_fee_label': get_dict_label('fee_type', apartment.electric_fee),
            'service_fee': apartment.service_fee,
            'other_fees': apartment.other_fees or '',
        },
        'facilities': facilities,
    }


@extend_schema(
    request=None,
    responses={
        200: {
            'type': 'object',
            'properties': {
                'code': {'type': 'integer'},
                'message': {'type': 'string'},
                'data': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'name': {'type': 'string'},
                            'cover_image': {'type': 'string'},
                            'min_monthly_rent': {'type': 'integer', 'nullable': True},
                            'min_area': {'type': 'number', 'nullable': True},
                            'fees': {'type': 'object'},
                            'facilities': {'type': 'array', 'items': {'type': 'string'}},
                        },
                    },
                },
            },
        },
    },
    summary='房源对比',
    description='接收逗号分隔的房源 ID（2-3 个），返回并排展示所需的简化对比数据。',
    tags=['公共房源'],
    parameters=[
        {'name': 'ids', 'in': 'query', 'schema': {'type': 'string'}, 'description': '房源 ID，逗号分隔（2-3 个）'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_compare(request):
    """
    GET /api/v1/apartments/compare
    房源对比：返回简化对比数据
    """
    ids_param = request.query_params.get('ids', '')
    if not ids_param.strip():
        raise BusinessException('请选择要对比的房源', code=ErrorCode.PARAM_ERROR)

    try:
        ids = [int(x) for x in ids_param.split(',') if x.strip()]
    except ValueError:
        raise BusinessException('参数 ids 格式不正确', code=ErrorCode.PARAM_ERROR)

    if not ids:
        raise BusinessException('请选择要对比的房源', code=ErrorCode.PARAM_ERROR)
    if len(ids) < 2:
        raise BusinessException('至少选择2套房源进行对比', code=ErrorCode.PARAM_ERROR)
    if len(ids) > 3:
        raise BusinessException('最多对比3套', code=ErrorCode.PARAM_ERROR)

    apartments = Apartment.objects.filter(id__in=ids, status='published')
    apt_map = {a.id: a for a in apartments}
    ordered = [apt_map[i] for i in ids if i in apt_map]

    result = [_build_compare_item(a) for a in ordered]
    return unified_response(data=result)


# ============================================================
# 地图相关接口
# ============================================================

@extend_schema(
    request=GeocodeRequestSerializer,
    responses={
        200: GeocodeResponseSerializer,
        400: UnifiedErrorResponseSerializer,
    },
    summary='服务端代理地理编码',
    description='将地址文本转换为经纬度坐标。调用高德地理编码 API，返回 longitude/latitude。如果高德 Key 未配置或调用失败，返回 null。',
    tags=['公共房源'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def apartment_geocode(request):
    """
    POST /api/v1/apartments/geocode
    服务端代理地理编码
    """
    serializer = GeocodeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        first_msg = list(serializer.errors.values())[0][0] if isinstance(serializer.errors, dict) else str(serializer.errors)
        raise BusinessException(str(first_msg), code=ErrorCode.PARAM_ERROR)

    address = serializer.validated_data['address']
    if not settings.AMAP_KEY:
        return unified_response(data={}, message='地图服务未配置')

    result = geocode(address)
    if result is None:
        return unified_response(data={}, message='地理编码失败，请检查地址是否正确')

    return unified_response(data={
        'longitude': str(result['longitude']),
        'latitude': str(result['latitude']),
    })


@extend_schema(
    request=None,
    responses={
        200: NearbyResponseSerializer,
        404: UnifiedErrorResponseSerializer,
    },
    summary='房源周边 POI',
    description='返回房源周边 1km 内的 POI 列表（地铁站/公交站/商超）及静态地图 URL。无经纬度房源返回空列表。',
    tags=['公共房源'],
    parameters=[
        {'name': 'id', 'in': 'path', 'schema': {'type': 'integer'}, 'description': '公寓 ID'},
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_nearby(request, id):
    """
    GET /api/v1/apartments/{id}/nearby
    房源周边 POI + 静态地图
    """
    try:
        apartment = Apartment.objects.get(id=id, status='published')
    except Apartment.DoesNotExist:
        raise NotFoundException('房源不存在或未上架')

    if apartment.longitude is None or apartment.latitude is None:
        return unified_response(data={
            'pois': [],
            'static_map_url': '',
        })

    lon = float(apartment.longitude)
    lat = float(apartment.latitude)

    pois = search_nearby_pois(lon, lat, radius=1000)
    static_map_url = build_static_map_url(lon, lat)

    return unified_response(data={
        'pois': pois,
        'static_map_url': static_map_url,
    })


@extend_schema(
    request=None,
    responses={
        200: MapConfigResponseSerializer,
    },
    summary='获取地图配置',
    description='返回前端加载高德 JS API 所需的 Key。',
    tags=['公共房源'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_map_config(request):
    """
    GET /api/v1/apartments/map-config
    获取地图 JS API Key
    """
    return unified_response(data={
        'amap_js_key': settings.AMAP_JS_KEY or settings.AMAP_KEY,
    })


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
    from datetime import timedelta
    from django.db.models import Count, Q

    landlord = request.user
    thirty_days_ago = timezone.localdate() - timedelta(days=30)
    queryset = Apartment.objects.filter(
        landlord=landlord,
        status='published',
    ).annotate(
        favorites_count=Count('favorited_by', distinct=True),
        views_30d=Count(
            'view_logs',
            filter=Q(view_logs__view_date__gte=thirty_days_ago),
            distinct=True,
        ),
    ).order_by('-updated_at')

    paginator = StandardPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = MerchantApartmentListSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: MerchantStatsSerializer,
        401: UnifiedErrorResponseSerializer,
        403: UnifiedErrorResponseSerializer,
    },
    summary='商家数据统计',
    description='返回当前商家所有房源近 30 天浏览量（按用户+天去重）与当前有效收藏总数。',
    tags=['商家房源'],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsLandlord])
def merchant_stats(request):
    """
    GET /api/v1/merchant/stats
    商家数据统计
    """
    from datetime import timedelta
    from apps.favorites.models import Favorite

    landlord = request.user
    thirty_days_ago = timezone.localdate() - timedelta(days=30)

    total_favorites = Favorite.objects.filter(
        apartment__landlord=landlord,
    ).count()

    total_views_30d = ApartmentViewLog.objects.filter(
        apartment__landlord=landlord,
        view_date__gte=thirty_days_ago,
    ).count()

    return unified_response(data={
        'total_views_30d': total_views_30d,
        'total_favorites': total_favorites,
    })


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
            'available_date': rt_data['available_date'].isoformat() if rt_data.get('available_date') else None,
            'rental_plans': plans,
        })
    return result

