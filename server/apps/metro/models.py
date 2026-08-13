from django.db import models
from core.models import BaseModel, SoftDeleteManager


class MetroLine(BaseModel):
    name = models.CharField(max_length=50, verbose_name='线路名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='线路编码')
    sort = models.IntegerField(default=0, verbose_name='排序')

    objects = SoftDeleteManager()

    class Meta:
        db_table = 'metro_lines'
        verbose_name = '地铁线路'
        verbose_name_plural = '地铁线路'
        ordering = ['sort', 'id']

    def __str__(self):
        return f'{self.name}({self.code})'


class MetroStation(BaseModel):
    line = models.ForeignKey(
        MetroLine,
        on_delete=models.CASCADE,
        related_name='stations',
        verbose_name='所属线路',
    )
    name = models.CharField(max_length=100, verbose_name='站点名称')
    longitude = models.DecimalField(
        max_digits=10, decimal_places=6,
        verbose_name='经度',
    )
    latitude = models.DecimalField(
        max_digits=10, decimal_places=6,
        verbose_name='纬度',
    )
    sort = models.IntegerField(default=0, verbose_name='排序')

    objects = SoftDeleteManager()

    class Meta:
        db_table = 'metro_stations'
        verbose_name = '地铁站点'
        verbose_name_plural = '地铁站点'
        ordering = ['sort', 'id']

    def __str__(self):
        return f'{self.line.name}-{self.name}'
