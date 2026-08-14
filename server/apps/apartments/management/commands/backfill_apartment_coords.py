"""
为存量无坐标房源补齐经纬度

用法：
    python manage.py backfill_apartment_coords [--dry-run]

说明：
    - 遍历 longitude 或 latitude 为空的未删除房源
    - 用「行政区 + 街道 + 详细门牌号」拼接地址调用高德地理编码
    - 成功则写入经纬度；失败跳过并打印汇总
    - AMAP_KEY 未配置时给出提示并直接退出
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.apartments.map_service import geocode
from apps.apartments.models import Apartment


class Command(BaseCommand):
    help = '为存量无坐标房源补齐经纬度（调用高德地理编码）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅打印将补全的坐标，不实际写入数据库',
        )

    def handle(self, *args, **options):
        if not settings.AMAP_KEY:
            self.stdout.write(self.style.WARNING('AMAP_KEY 未配置，无法进行地理编码，命令退出'))
            return

        queryset = Apartment.objects.filter(
            Q(longitude__isnull=True) | Q(latitude__isnull=True)
        )

        total = queryset.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('没有需要补全坐标的房源'))
            return

        self.stdout.write(f'共 {total} 套房源待补全坐标')

        updated = 0
        skipped = 0
        for apartment in queryset.iterator():
            district_name = apartment.district.name if apartment.district else ''
            street_name = apartment.street.name if apartment.street else ''
            address = f'{district_name}{street_name}{apartment.detail_address}'

            result = geocode(address)
            if result is None:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f'跳过 #{apartment.id}（{address}）地理编码失败')
                )
                continue

            self.stdout.write(
                f'#{apartment.id} -> ({result["longitude"]}, {result["latitude"]})'
            )

            if options['dry_run']:
                updated += 1
                continue

            apartment.longitude = result['longitude']
            apartment.latitude = result['latitude']
            apartment.save(update_fields=['longitude', 'latitude'])
            updated += 1

        suffix = '（dry-run 未写入）' if options['dry_run'] else ''
        self.stdout.write(
            self.style.SUCCESS(f'完成：更新 {updated} 套，跳过 {skipped} 套{suffix}')
        )
