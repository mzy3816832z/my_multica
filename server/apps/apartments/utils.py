"""
房源模块工具函数
"""
from django.db.models import Min

from apps.apartments.models import Apartment


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
