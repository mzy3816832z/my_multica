"""
房源模块工具函数
"""
from django.db.models import Min

from apps.apartments.models import Apartment


# 对外可见的房源状态（影子发布：变更审核中的房源继续展示旧版）
PUBLIC_VISIBLE_STATUSES = ('published', 'change_reviewing')


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
