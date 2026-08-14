"""
房源模块工具函数
"""
from django.db.models import Min

from apps.apartments.models import Apartment


# ============================================================
# 变更审核触发矩阵（A 类必审字段配置）
# ============================================================

# A 类必审字段（公寓级），code 与 system_dict category=audit_sensitive_fields 对应
APARTMENT_AUDIT_FIELDS = [
    'name',
    'district_id',
    'street_id',
    'detail_address',
    'longitude',
    'latitude',
    'cover_image',
]

# A 类必审字段（房型级），code 前缀 room_types.
ROOM_TYPE_AUDIT_FIELDS = ['images', 'layout_type', 'window_type', 'area']

# 默认 A 类必审字段全集（system_dict 未配置时的回退）
DEFAULT_AUDIT_SENSITIVE_FIELDS = (
    APARTMENT_AUDIT_FIELDS
    + [f'room_types.{field}' for field in ROOM_TYPE_AUDIT_FIELDS]
)


def get_audit_sensitive_fields():
    """
    读取 A 类必审字段配置（system_dict category=audit_sensitive_fields）。
    未配置（无任何记录）时回退到默认字段集，保证功能可用且运营可调。
    """
    from apps.dicts.models import SystemDict

    codes = list(
        SystemDict.objects.filter(
            category='audit_sensitive_fields',
            is_active=True,
            deleted_at__isnull=True,
        ).values_list('code', flat=True)
    )
    if not codes:
        return list(DEFAULT_AUDIT_SENSITIVE_FIELDS)
    return codes


def backfill_apartment_min_rent(apartment: Apartment) -> bool:
    """
    根据该房源下所有未删除房型的租金方案，计算并回填 min_monthly_rent。
    返回是否成功回填（True=已更新，False=无有效租金方案）。
    """
    result = apartment.room_types.filter(
        deleted_at__isnull=True
    ).aggregate(
        min_rent=Min('rental_plans__monthly_rent')
    )
    min_rent = result.get('min_rent')
    if min_rent is not None:
        apartment.min_monthly_rent = min_rent
        apartment.save(update_fields=['min_monthly_rent'])
        return True
    return False


def backfill_apartment_min_area(apartment: Apartment) -> bool:
    """
    根据该房源下所有未删除房型的 area，计算并回填 min_area。
    返回是否成功回填（True=已更新，False=无有效面积数据）。
    """
    result = apartment.room_types.filter(
        deleted_at__isnull=True
    ).aggregate(
        min_area=Min('area')
    )
    min_area = result.get('min_area')
    if min_area is not None:
        apartment.min_area = min_area
        apartment.save(update_fields=['min_area'])
        return True
    return False
