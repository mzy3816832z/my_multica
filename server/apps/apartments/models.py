"""
房源、房型、租金方案模型
"""
from django.db import models
from core.models import BaseModel, SoftDeleteManager, AllObjectsManager


class Apartment(BaseModel):
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('pending_first_review', '待首次审核'),
        ('first_rejected', '首次审核驳回'),
        ('published', '已上架'),
    ]

    landlord = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='apartments',
        verbose_name='商家',
    )
    name = models.CharField(
        max_length=50,
        verbose_name='公寓名称',
    )
    cover_image = models.CharField(
        max_length=500,
        verbose_name='公寓总览图 URL',
    )
    description = models.TextField(
        verbose_name='公寓描述',
    )
    district = models.ForeignKey(
        'districts.District',
        on_delete=models.PROTECT,
        related_name='apartments',
        verbose_name='行政区',
    )
    street = models.ForeignKey(
        'districts.District',
        on_delete=models.PROTECT,
        related_name='street_apartments',
        verbose_name='街道/镇',
    )
    detail_address = models.CharField(
        max_length=200,
        verbose_name='详细门牌号',
    )
    contact_phone = models.CharField(
        max_length=11,
        verbose_name='联系电话',
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='状态',
    )
    min_monthly_rent = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='最低月租金（缓存）',
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='经度',
    )
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name='纬度',
    )
    property_fee = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='物业费（元/月）',
    )
    water_fee = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='水费编码',
    )
    electric_fee = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        verbose_name='电费编码',
    )
    service_fee = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='服务费（元/月）',
    )
    other_fees = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='其他费用说明',
    )
    min_area = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='最小面积（缓存）',
    )
    verified = models.BooleanField(
        default=False,
        verbose_name='是否认证',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'apartments'
        verbose_name = '公寓房源'
        verbose_name_plural = '公寓房源'
        indexes = [
            models.Index(fields=['landlord']),
            models.Index(fields=['status', 'deleted_at']),
            models.Index(fields=['district', 'deleted_at']),
            models.Index(fields=['min_monthly_rent']),
            models.Index(fields=['min_area']),
            models.Index(fields=['verified']),
        ]

    def __str__(self):
        return self.name


class RoomType(BaseModel):
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.CASCADE,
        related_name='room_types',
        verbose_name='所属公寓',
    )
    name = models.CharField(
        max_length=50,
        verbose_name='房型名称',
    )
    images = models.JSONField(
        default=list,
        verbose_name='房型图片 URL 数组',
    )
    facilities = models.JSONField(
        default=list,
        verbose_name='设施编码数组',
    )
    layout_type = models.CharField(
        max_length=30,
        verbose_name='户型编码',
    )
    window_type = models.CharField(
        max_length=30,
        verbose_name='内外窗编码',
    )
    floor = models.IntegerField(
        verbose_name='楼层',
    )
    sort = models.IntegerField(
        default=0,
        verbose_name='展示排序',
    )
    area = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='面积（㎡）',
    )
    available_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='可入住日期',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'room_types'
        verbose_name = '房型'
        verbose_name_plural = '房型'
        indexes = [
            models.Index(fields=['apartment', 'deleted_at']),
        ]

    def __str__(self):
        return self.name


class RentalPlan(BaseModel):
    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name='rental_plans',
        verbose_name='所属房型',
    )
    lease_term = models.CharField(
        max_length=30,
        verbose_name='租期编码',
    )
    monthly_rent = models.IntegerField(
        verbose_name='月租金（元）',
    )
    payment_method = models.CharField(
        max_length=30,
        verbose_name='支付方式编码',
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'rental_plans'
        verbose_name = '租期租金方案'
        verbose_name_plural = '租期租金方案'
        indexes = [
            models.Index(fields=['room_type', 'deleted_at']),
        ]

    def __str__(self):
        return f'{self.room_type.name} - {self.lease_term}({self.monthly_rent}元)'


class ApartmentViewLog(BaseModel):
    """
    房源浏览日志

    详情页 PV 去重统计：按 (房源, 去重键, 日期) 唯一。
    去重键 = 登录用户 ID 或匿名访客 IP，实现"按用户+天"去重。
    """
    apartment = models.ForeignKey(
        Apartment,
        on_delete=models.CASCADE,
        related_name='view_logs',
        verbose_name='房源',
    )
    dedupe_key = models.CharField(
        max_length=64,
        verbose_name='去重键（用户 ID 或匿名 IP）',
    )
    view_date = models.DateField(
        verbose_name='浏览日期',
    )

    objects = models.Manager()
    all_objects = AllObjectsManager()

    class Meta:
        db_table = 'apartment_view_logs'
        verbose_name = '房源浏览日志'
        verbose_name_plural = '房源浏览日志'
        indexes = [
            models.Index(fields=['apartment', 'view_date']),
            models.Index(fields=['view_date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['apartment', 'dedupe_key', 'view_date'],
                name='unique_apartment_viewer_date',
            ),
        ]

    def __str__(self):
        return f'View({self.apartment_id} - {self.dedupe_key} - {self.view_date})'
