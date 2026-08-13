"""
高德地图服务代理：地理编码 + 周边POI搜索
"""
import json
import logging
import urllib.request
import urllib.parse
import urllib.error

from django.conf import settings

logger = logging.getLogger('apps')

AMAP_GEOCODE_URL = 'https://restapi.amap.com/v3/geocode/geo'
AMAP_AROUND_URL = 'https://restapi.amap.com/v3/place/around'
AMAP_STATICMAP_URL = 'https://restapi.amap.com/v3/staticmap'


def _get_key():
    return settings.AMAP_KEY


def geocode(address: str) -> dict | None:
    """
    调用高德地理编码 API，返回 {longitude, latitude} 或 None
    """
    key = _get_key()
    if not key:
        logger.warning('[MapService] AMAP_KEY not configured')
        return None

    params = urllib.parse.urlencode({
        'key': key,
        'address': address,
        'city': '上海',
        'output': 'JSON',
    })
    url = f'{AMAP_GEOCODE_URL}?{params}'

    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.error(f'[MapService] geocode error: {e}')
        return None

    if data.get('status') != '1' or data.get('info') != 'OK':
        logger.warning(f'[MapService] geocode failed: {data}')
        return None

    geocodes = data.get('geocodes', [])
    if not geocodes:
        return None

    location = geocodes[0].get('location', '')
    if not location:
        return None

    parts = location.split(',')
    if len(parts) != 2:
        return None

    return {
        'longitude': float(parts[0]),
        'latitude': float(parts[1]),
    }


def search_nearby_pois(longitude: float, latitude: float, radius: int = 1000) -> list[dict]:
    """
    调用高德周边搜索 API，返回 POI 列表 [{name, type, distance, address}]
    类型限定：地铁站(150500)、公交站(150700)、超市(060100)
    """
    key = _get_key()
    if not key:
        logger.warning('[MapService] AMAP_KEY not configured')
        return []

    params = urllib.parse.urlencode({
        'key': key,
        'location': f'{longitude},{latitude}',
        'radius': radius,
        'types': '150500|150700|060100',
        'offset': 20,
        'page': 1,
        'extensions': 'base',
        'output': 'JSON',
    })
    url = f'{AMAP_AROUND_URL}?{params}'

    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            data = json.loads(body)
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as e:
        logger.error(f'[MapService] search_nearby_pois error: {e}')
        return []

    if data.get('status') != '1' or data.get('info') != 'OK':
        logger.warning(f'[MapService] search_nearby_pois failed: {data}')
        return []

    pois = data.get('pois', [])

    type_name_map = {
        '150500': '地铁站',
        '150700': '公交站',
        '060100': '超市/便利店',
    }

    result = []
    for p in pois:
        typecode = (p.get('typecode', '') or '')[:6]
        poi_type = type_name_map.get(typecode, '其他')
        distance_str = p.get('distance', '')
        try:
            distance = int(distance_str) if distance_str else 0
        except (ValueError, TypeError):
            distance = 0
        result.append({
            'name': p.get('name', ''),
            'type': poi_type,
            'distance': distance,
            'address': p.get('address', ''),
        })

    result.sort(key=lambda x: x['distance'])
    return result


def build_static_map_url(longitude: float, latitude: float, width: int = 400, height: int = 200, zoom: int = 15) -> str:
    """
    构建高德静态地图 URL
    """
    key = _get_key()
    if not key:
        return ''
    return (
        f'{AMAP_STATICMAP_URL}?key={key}'
        f'&location={longitude},{latitude}'
        f'&zoom={zoom}'
        f'&size={width}*{height}'
        f'&markers=mid,,A:{longitude},{latitude}'
    )
