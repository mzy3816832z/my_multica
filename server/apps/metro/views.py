import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from core.response import unified_response, UnifiedErrorResponseSerializer
from apps.metro.models import MetroLine
from apps.metro.serializers import MetroLineSerializer

logger = logging.getLogger('apps')


@extend_schema(
    request=None,
    responses={
        200: MetroLineSerializer(many=True),
    },
    summary='地铁线路与站点列表',
    description='返回所有地铁线路及其下属站点（树形结构），按 sort 排序。',
    tags=['地铁'],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def metro_lines(request):
    lines = MetroLine.objects.prefetch_related('stations').all()
    serializer = MetroLineSerializer(lines, many=True)
    return unified_response(data=serializer.data)
