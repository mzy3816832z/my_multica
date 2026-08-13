from rest_framework import serializers


class MetroStationSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='站点 ID')
    name = serializers.CharField(max_length=100, help_text='站点名称')
    longitude = serializers.DecimalField(max_digits=10, decimal_places=6, help_text='经度')
    latitude = serializers.DecimalField(max_digits=10, decimal_places=6, help_text='纬度')


class MetroLineSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='线路 ID')
    name = serializers.CharField(max_length=50, help_text='线路名称')
    code = serializers.CharField(max_length=20, help_text='线路编码')
    stations = MetroStationSerializer(many=True, help_text='站点列表')
