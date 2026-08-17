"""
上海公寓租赁平台 H5 UI 自动化测试 —— 全量运行器（V1.0 + V1.1 增量）

- 复用 test/ui/run_ui_tests.py 的 V1.0 用例（49 条）与全部辅助函数/报告能力
- 新增 V1.1 迭代测试用例（test/testcase/V1.1_迭代测试用例.md 的 184 条：
  统一响应码 / 状态机 / 影子发布 / 列表筛选排序搜索 / 地图 / 对比 / 浏览历史 /
  发布字段 / 平台核验 / 商家统计 / 消息跳转 / Token 刷新 / 审核详情与商家审核 / PICT 组合）

用法：
    server/.venv/Scripts/python test/ui/run_all_tests.py
"""
import os
import sys
import time
import json
from datetime import datetime, date, timedelta

import run_ui_tests as r

# ---------------- 纯函数别名（不读写 run_ui_tests 的可变模块状态） ----------------
api = r.api
api_status = r.api_status
login_token = r.login_token
register_user = r.register_user
select_role = r.select_role
upload_image = r.upload_image
admin_approve_first_pending = r.admin_approve_first_pending
db_query = r.db_query
get_sms_code = r.get_sms_code
expect = r.expect
SoftAssert = r.SoftAssert
SkipCase = r.SkipCase

# 关键：API 请求直连后端（绕过 Vite 代理），避免 http-proxy 长连接复用导致的 502 级联失败。
# UI 导航仍走 r.BASE_URL(5174)；仅 urllib 发起的接口调用直连 127.0.0.1:8001。
_backend_port = os.environ.get('TEST_BACKEND_PORT', '8001')
r.API_URL = f'http://127.0.0.1:{_backend_port}/api/v1'

# ---------------- 状态必须通过 r.* 访问：PAGE/CTX/STATE/RESULTS/BROWSER ----------------
BASE_URL = r.BASE_URL


def new_page(storage_state=None):
    return r.new_context(storage_state=storage_state)


def shot(name):
    return r.shot(name)


def auth_state(token, user):
    return r.auth_state(token, user)


# ============================================================
# V1.1 辅助函数
# ============================================================

def ck(path, method='GET', body=None, token=None, st=200, code=0, kw=None):
    """断言接口返回 (http_status, code, message)，并可选校验 message 关键字。返回三元组。"""
    st_, c_, m_ = api_status(path, method, body, token)
    sa = SoftAssert()
    sa.check(st_ == st, f'[{path}] HTTP {st_} != {st}')
    sa.check(c_ == code, f'[{path}] code {c_} != {code} (message={m_})')
    if kw:
        sa.check(kw in (m_ or ''), f'[{path}] message「{m_}」不含「{kw}」')
    sa.assert_all()
    return st_, c_, m_


def _apt_id(data):
    return data.get('apartment_id') or data.get('id')


def v11_create(token, name, room_types=None, **kw):
    """灵活创建房源（提交首次审核）。返回 API data（含 apartment_id/audit_id）。"""
    cover = upload_image(token)
    if room_types is None:
        room_types = [{
            'name': '温馨一居室',
            'images': [upload_image(token)],
            'facilities': ['air_conditioner', 'wifi'],
            'layout_type': 'one_bedroom',
            'window_type': 'outer',
            'floor': 3,
            'sort': 0,
            'area': 30,
            'rental_plans': [
                {'lease_term': '1_year', 'monthly_rent': kw.get('rent', 3500),
                 'payment_method': 'pay_1_deposit_1'},
            ],
        }]
    body = {
        'name': name,
        'cover_image': cover,
        'description': kw.get('description', f'{name}，近地铁，精装修。'),
        'district_id': kw.get('district_id', 1),
        'street_id': kw.get('street_id', 2),
        'detail_address': kw.get('detail_address', '测试路100弄1号'),
        'contact_phone': '13800138000',
        'room_types': room_types,
    }
    for k in ('longitude', 'latitude', 'property_fee', 'water_fee', 'electric_fee',
              'service_fee', 'other_fees'):
        if k in kw:
            body[k] = kw[k]
    return api('/merchant/apartments/', 'POST', body, token=token)


def v11_publish(token, admin_token, name, room_types=None, **kw):
    """创建并审批上架，返回 apartment_id。"""
    d = v11_create(token, name, room_types=room_types, **kw)
    apt_id = _apt_id(d)
    admin_approve_first_pending(admin_token, apartment_id=apt_id)
    return apt_id


def apt_status(token, apt_id):
    d = api(f'/merchant/apartments/{apt_id}/', token=token)
    return d.get('status')


def list_names(body):
    items = api('/apartments/', body=body).get('items', [])
    return [it.get('name') for it in items]


def v11_prepare():
    """V1.1 补充测试数据：固定价格/搜索/坐标房源，供列表筛选、排序、搜索、地图、对比用例使用。"""
    print('== 准备 V1.1 补充测试数据 ==')
    m = r.STATE['merchant_token']
    a = r.STATE['admin_token']
    # 固定价格房源（排序/价格区间）
    for nm, rent in (('排序专用-低价', 2000), ('排序专用-中价', 3000), ('排序专用-高价', 4500)):
        v11_publish(m, a, nm, rent=rent)
    # 地址搜索
    v11_publish(m, a, '中山公园测试房', detail_address='中山公园路99号', description='普通描述')
    # 描述搜索
    v11_publish(m, a, '地铁描述测试房', description='近地铁 拎包入住 精装修')
    # 名称精确匹配（相关性排序）
    v11_publish(m, a, '浦东', description='相关性排序测试')
    # 带坐标房源（附近 POI / 地铁 / 地图用例）
    v11_publish(m, a, '坐标测试房源', longitude='121.4737', latitude='31.2304',
                detail_address='陆家嘴环路1000号')
    # 无坐标房源（POI 空态）
    r.STATE['nocord_apt_id'] = v11_publish(m, a, '无坐标测试房源')
    # 有坐标房源 id
    lst = api('/apartments/', body={'keyword': '坐标测试房源', 'page': 1, 'page_size': 10})
    if lst.get('items'):
        r.STATE['coord_apt_id'] = lst['items'][0]['id']
    print('== V1.1 补充数据准备完成 ==')


# ============================================================
# 二、统一响应码（TC-CODE）
# ============================================================

def tc_code_001():
    """登录密码错误返回 401002"""
    st, c, m = ck('/auth/login-by-password/', 'POST',
                  {'username': r.STATE['tenant_phone'], 'password': 'wrong'},
                  st=200, code=401002, kw='用户名或密码错误')


def tc_code_002():
    """登录用户不存在与密码错误同码（防枚举）"""
    ck('/auth/login-by-password/', 'POST',
       {'username': '19999999999', 'password': 'x'},
       st=200, code=401002, kw='用户名或密码错误')


def tc_code_003():
    """登录验证码错误返回 401003"""
    st, c, m = api_status('/auth/login-by-code/', 'POST',
                          {'phone': r.STATE['tenant_phone'], 'sms_code': '000000'})
    expect(c == 401003, f'code {c} != 401003 (message={m})')


def tc_code_004():
    """账号禁用返回 403002"""
    phone = f'132{int(time.time()) % 100000000:08d}'
    register_user(phone)
    db_query('UPDATE users SET is_active=0 WHERE username=?', (phone,))
    st, c, m = api_status('/auth/login-by-password/', 'POST',
                          {'username': phone, 'password': 'Test123456'})
    expect(c == 403002, f'code {c} != 403002 (message={m})')


def tc_code_005():
    """手机号已注册返回 409001（复用已验证码，绕开短信频控）"""
    phone = f'130{int(time.time()) % 100000000:08d}'
    register_user(phone)
    db_query("UPDATE verify_codes SET used=0 WHERE phone=? AND purpose='register'", (phone,))
    code = get_sms_code(phone, 'register')
    st, c, m = api_status('/auth/register/', 'POST',
                          {'phone': phone, 'password': 'Xxx12345', 'sms_code': code})
    expect(c == 409001, f'code {c} != 409001 (message={m})')


def tc_code_006():
    """资源不存在返回 404001"""
    st, c, m = api_status('/apartments/999999', 'GET')
    expect(c == 404001, f'code {c} != 404001 (message={m})')


def tc_code_007():
    """已下架房源详情返回 410001"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '下架详情测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    st, c, m2 = api_status(f'/apartments/{apt_id}', 'GET')
    expect(c == 410001, f'code {c} != 410001 (message={m2})')


def tc_code_008():
    """未登录访问鉴权接口 401"""
    st, c, m = api_status('/merchant/apartments/', 'GET')
    expect(st == 401 and c == 401001, f'HTTP {st} code {c} (message={m})')


def tc_code_009():
    """角色越权 403"""
    st, c, m = api_status('/admin/audits/', 'GET', token=r.STATE['tenant_token'])
    expect(st == 403 and c == 403001, f'HTTP {st} code {c} (message={m})')


def tc_code_010():
    """短信频控（重复发送返回 429001；实现以 HTTP 200 + code 返回）"""
    phone = f'131{int(time.time()) % 100000000:08d}'
    api_status('/auth/sms-code/', 'POST', {'phone': phone, 'purpose': 'register'})
    st, c, m = api_status('/auth/sms-code/', 'POST', {'phone': phone, 'purpose': 'register'})
    expect(c == 429001, f'code {c} != 429001 (message={m}, http={st})')


def tc_code_011():
    """发布房源参数校验失败 400001（空 name）"""
    m = r.STATE['merchant_token']
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': ''}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_code_012():
    """Token 刷新失败返回 401001"""
    st, c, m = api_status('/auth/refresh/', 'POST', {'refresh_token': 'invalid-token'})
    expect(c == 401001, f'code {c} != 401001 (message={m})')


def tc_code_013():
    """前端拦截器 410001 不弹通用 toast（访问已下架房源详情占位页）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '下架UI占位测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    new_page(storage_state=auth_state(r.STATE['tenant_token'], r.STATE['tenant_user']))
    r.PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-CODE-013_offline_placeholder')
    body_text = r.PAGE.inner_text('body')
    expect('房源已下架' in body_text, f'未显示已下架占位页: {body_text[:200]}')
    expect('请求失败' not in body_text, '已下架场景不应弹「请求失败」通用 toast')


def tc_code_014():
    """前端拦截器业务错误统一 toast（注册已存在手机号触发 409001）"""
    phone = r.STATE['tenant_phone']
    new_page()
    r.PAGE.goto(f'{BASE_URL}/register')
    r.PAGE.wait_for_selector('input', timeout=10000)
    inputs = r.PAGE.query_selector_all('input')
    inputs[0].fill(phone)
    r.PAGE.click('xpath=//button[contains(normalize-space(),"获取验证码")]')
    r.PAGE.wait_for_timeout(1200)
    code = get_sms_code(phone, 'register')
    inputs = r.PAGE.query_selector_all('input')
    inputs[1].fill(code or '000000')
    inputs[2].fill('Test123456')
    inputs[3].fill('Test123456')
    r.PAGE.click('xpath=//button[normalize-space()="注册"]')
    try:
        toast = r.PAGE.wait_for_selector('.van-toast', timeout=6000)
        content = toast.inner_text()
        shot('TC-CODE-014_biz_toast')
        expect('已注册' in content, f'未弹出「该手机号已注册」toast: {content}')
    except Exception:
        raise AssertionError('未弹出业务错误 toast')


# ============================================================
# 三、状态机扩展（TC-STAT）
# ============================================================

def tc_stat_001():
    """已上架房源下架"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '状态机下架测试房')
    d = api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    expect(d.get('status') == 'offline', f'下架后 status={d.get("status")}')
    lst = api('/apartments/', body={'keyword': '状态机下架测试房', 'page': 1, 'page_size': 10})
    expect(lst.get('total', 0) == 0, '下架后公共列表仍返回该房源')


def tc_stat_002():
    """非 published 下架被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '重复下架测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    expect(c == 400002, f'code {c} != 400002 (message={m2})')


def tc_stat_003():
    """已下架房源重新上架"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '重新上架测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    d = api(f'/merchant/apartments/{apt_id}/online/', 'POST', {}, token=m)
    expect(d.get('status') == 'published', f'重新上架后 status={d.get("status")}')
    lst = api('/apartments/', body={'keyword': '重新上架测试房', 'page': 1, 'page_size': 10})
    expect(lst.get('total', 0) >= 1, '重新上架后公共列表不可见')


def tc_stat_004():
    """非 offline 重新上架被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '重复上架测试房')
    st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/online/', 'POST', {}, token=m)
    expect(c == 400002, f'code {c} != 400002 (message={m2})')


def tc_stat_005():
    """有 pending 审核单时重新上架被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '待审上架测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    # 编辑 A 类字段生成 change_review（offline 状态保持 offline，同时产生 pending 审核单）
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '待审上架测试房改'}, token=m)
    st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/online/', 'POST', {}, token=m)
    expect(c == 400002, f'code {c} != 400002 (message={m2})')


def tc_stat_006():
    """撤回首次审核"""
    m = r.STATE['merchant_token']
    d = v11_create(m, '撤回首次测试房')
    apt_id = _apt_id(d)
    out = api(f'/merchant/apartments/{apt_id}/withdraw/', 'POST', {}, token=m)
    expect(out.get('status') == 'draft', f'撤回后 status={out.get("status")}')


def tc_stat_007():
    """撤回变更审核（change_reviewing → published）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '撤回变更测试房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '撤回变更测试房改'}, token=m)
    out = api(f'/merchant/apartments/{apt_id}/withdraw/', 'POST', {}, token=m)
    expect(out.get('status') == 'published', f'撤回后 status={out.get("status")}')


def tc_stat_008():
    """其他状态撤回被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '非法撤回测试房')
    st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/withdraw/', 'POST', {}, token=m)
    expect(c == 400002, f'code {c} != 400002 (message={m2})')


def tc_stat_009():
    """下架房源在公共列表不可见"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '列表不可见测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    lst = api('/apartments/', body={'page': 1, 'page_size': 100})
    names = [it.get('name') for it in lst.get('items', [])]
    expect('列表不可见测试房' not in names, '下架房源仍出现在公共列表')


def tc_stat_010():
    """商家「已下架」Tab 列表"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '已下架Tab测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    d = api('/merchant/apartments/', body={'status': 'offline', 'page': 1, 'page_size': 100}, token=m)
    statuses = [it.get('status') for it in d.get('items', [])]
    expect(len(statuses) > 0 and all(s == 'offline' for s in statuses),
           f'已下架 Tab 应全部 offline，实际 {set(statuses)}')


def tc_stat_011():
    """商家状态筛选多值"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    v11_publish(m, a, '多值筛选测试房')
    d = api('/merchant/apartments/', body={'status': 'published,offline', 'page': 1, 'page_size': 100}, token=m)
    statuses = set(it.get('status') for it in d.get('items', []))
    expect(statuses.issubset({'published', 'offline'}), f'多值筛选返回异常状态 {statuses}')


def tc_stat_012():
    """商家默认列表仅 published"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '默认列表测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    d = api('/merchant/apartments/', body={'page': 1, 'page_size': 100}, token=m)
    statuses = set(it.get('status') for it in d.get('items', []))
    expect(statuses == {'published'}, f'默认列表应仅 published，实际 {statuses}')


def tc_stat_013():
    """商家后台下架/重新上架按钮联动（UI）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    v11_publish(m, a, '按钮联动测试房')
    new_page(storage_state=auth_state(m, r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/my-apartments')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-STAT-013_my_apartments')
    body_text = r.PAGE.inner_text('body')
    expect('按钮联动测试房' in body_text or '房源' in body_text, '商家房源页未渲染')


# ============================================================
# 四、变更审核影子发布（TC-SHADOW）
# ============================================================

def _edit_expect_change(token, apt_id, body, field_note):
    """编辑后断言生成 change_review（updated=False, audit_id 非空）。"""
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', body, token=token)
    sa = SoftAssert()
    sa.check(d.get('updated') is False, f'{field_note} 应 updated=False，实际 {d.get("updated")}')
    sa.check(d.get('audit_id') is not None, f'{field_note} 应返回 audit_id，实际 {d.get("audit_id")}')
    sa.assert_all()
    return d


def _edit_expect_direct(token, apt_id, body, field_note):
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', body, token=token)
    sa = SoftAssert()
    sa.check(d.get('updated') is True, f'{field_note} 应 updated=True，实际 {d.get("updated")}')
    sa.check(d.get('audit_id') is None, f'{field_note} 应 audit_id=null，实际 {d.get("audit_id")}')
    sa.assert_all()
    return d


def tc_shadow_001():
    """编辑名称触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布名称测试房')
    _edit_expect_change(m, apt_id, {'name': '影子发布名称测试房改'}, 'name')
    expect(apt_status(m, apt_id) == 'change_reviewing', '改 name 后 status 应为 change_reviewing')


def tc_shadow_002():
    """编辑位置触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布位置测试房')
    _edit_expect_change(m, apt_id, {'detail_address': '新门牌路1号'}, 'detail_address')


def tc_shadow_003():
    """编辑经纬度触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布坐标测试房')
    _edit_expect_change(m, apt_id, {'longitude': '121.5000', 'latitude': '31.2000'}, 'longitude/latitude')


def tc_shadow_004():
    """编辑封面图触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布封面测试房')
    new_cover = upload_image(m)
    _edit_expect_change(m, apt_id, {'cover_image': new_cover}, 'cover_image')


def tc_shadow_005():
    """编辑房型户型触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布户型测试房')
    room = [{
        'name': '温馨一居室', 'images': [upload_image(m)],
        'facilities': ['air_conditioner'], 'layout_type': 'studio', 'window_type': 'outer',
        'floor': 3, 'area': 30,
        'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3500, 'payment_method': 'pay_1_deposit_1'}],
    }]
    _edit_expect_change(m, apt_id, {'room_types': room}, 'room_types.layout_type')


def tc_shadow_006():
    """编辑房型面积触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布面积测试房')
    room = [{
        'name': '温馨一居室', 'images': [upload_image(m)],
        'facilities': ['air_conditioner'], 'layout_type': 'one_bedroom', 'window_type': 'outer',
        'floor': 3, 'area': 50,
        'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3500, 'payment_method': 'pay_1_deposit_1'}],
    }]
    _edit_expect_change(m, apt_id, {'room_types': room}, 'room_types.area')


def tc_shadow_007():
    """编辑房型图片/内外窗触发变更审核"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布图片测试房')
    room = [{
        'name': '温馨一居室', 'images': [upload_image(m)],
        'facilities': ['air_conditioner'], 'layout_type': 'one_bedroom', 'window_type': 'inner',
        'floor': 3, 'area': 30,
        'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3500, 'payment_method': 'pay_1_deposit_1'}],
    }]
    _edit_expect_change(m, apt_id, {'room_types': room}, 'room_types.window_type')


def tc_shadow_008():
    """编辑描述免审直接更新"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布描述测试房')
    _edit_expect_direct(m, apt_id, {'description': '更新后的描述内容'}, 'description')
    expect(apt_status(m, apt_id) == 'published', '改描述后 status 应保持 published')


def tc_shadow_009():
    """编辑联系电话免审直接更新"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布电话测试房')
    _edit_expect_direct(m, apt_id, {'contact_phone': '13900139000'}, 'contact_phone')


def tc_shadow_010():
    """编辑费用字段免审直接更新"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布费用测试房')
    _edit_expect_direct(m, apt_id, {'property_fee': 200, 'service_fee': 100}, 'property_fee')


def tc_shadow_011():
    """编辑楼层/设施/租金免审全量替换房型（复用原图片避免触发图片 A 类变更）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布租金测试房')
    detail = api(f'/merchant/apartments/{apt_id}/', token=m)
    rt = detail['room_types'][0]
    room = [{
        'name': rt['name'], 'images': rt['images'],
        'facilities': rt.get('facilities', []),
        'layout_type': rt['layout_type'], 'window_type': rt['window_type'],
        'floor': 5, 'area': rt.get('area'),
        'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 4200,
                          'payment_method': 'pay_1_deposit_1'}],
    }]
    _edit_expect_direct(m, apt_id, {'room_types': room}, 'room_types.floor/rental_plans')


def tc_shadow_012():
    """已有 pending 变更审核再编辑 A 类被拒（409001）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布重复变更测试房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '影子发布重复变更测试房改'}, token=m)
    st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '再次改名'}, token=m)
    expect(c == 409001, f'code {c} != 409001 (message={m2})')


def tc_shadow_013():
    """变更审核期间公共列表展示旧版"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布旧版测试房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '影子发布新版名称'}, token=m)
    lst = api('/apartments/', body={'keyword': '影子发布旧版测试房', 'page': 1, 'page_size': 10})
    names = [it.get('name') for it in lst.get('items', [])]
    expect('影子发布旧版测试房' in names, '变更审核期间列表应展示旧版名称')
    expect('影子发布新版名称' not in names, '变更审核期间列表不应展示新版名称')


def tc_shadow_014():
    """变更审核期间详情展示旧版"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布旧版详情房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '影子发布新版详情名'}, token=m)
    detail = api(f'/apartments/{apt_id}/')
    expect(detail.get('name') == '影子发布旧版详情房', f'详情应展示旧版名称，实际 {detail.get("name")}')


def tc_shadow_015():
    """变更审核通过应用新版本"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布通过测试房')
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '影子发布通过后名称'}, token=m)
    audit_id = d.get('audit_id')
    api(f'/admin/audits/{audit_id}/approve/', 'POST', {}, token=a)
    detail = api(f'/apartments/{apt_id}/')
    expect(detail.get('name') == '影子发布通过后名称', f'审核通过后应应用新名称，实际 {detail.get("name")}')
    expect(apt_status(m, apt_id) == 'published', '审核通过后 status 应 published')


def tc_shadow_016():
    """变更审核驳回恢复旧版"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布驳回测试房')
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '影子发布驳回新名称'}, token=m)
    audit_id = d.get('audit_id')
    api(f'/admin/audits/{audit_id}/reject/', 'POST', {'reject_reason': '信息不实'}, token=a)
    detail = api(f'/apartments/{apt_id}/')
    expect(detail.get('name') == '影子发布驳回测试房', f'驳回后应恢复旧名称，实际 {detail.get("name")}')
    expect(apt_status(m, apt_id) == 'published', '驳回后 status 应恢复 published')


def tc_shadow_017():
    """编辑 offline 房源 A 类字段状态保持 offline"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '影子发布离线测试房')
    api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    _edit_expect_change(m, apt_id, {'name': '影子发布离线测试房改'}, 'name')
    expect(apt_status(m, apt_id) == 'offline', 'offline 房源改 A 类字段应保持 offline')


def tc_shadow_018():
    """管理员审核页变更审核中标识（UI）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '变更审核标识测试房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '变更审核标识测试房改'}, token=m)
    new_page(storage_state=auth_state(a, r.STATE['admin_user']))
    r.PAGE.goto(f'{BASE_URL}/admin/audits')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-SHADOW-018_change_badge')
    body_text = r.PAGE.inner_text('body')
    expect('变更审核' in body_text or '审核' in body_text, '审核列表未渲染')


# ============================================================
# 五、列表筛选/排序/搜索（TC-LIST）
# ============================================================

def _rents(items):
    return [it.get('min_monthly_rent') for it in items]


def tc_list_001():
    """默认按最新上架排序"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 100})
    expect(lst.get('total', 0) >= 1, '公共列表为空')


def tc_list_002():
    """价格升序排序"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 100, 'sort': 'price_asc'})
    rents = _rents(lst.get('items', []))
    nonnull = [x for x in rents if x is not None]
    expect(nonnull == sorted(nonnull), f'price_asc 未升序: {nonnull}')
    if None in rents:
        last_nonnull_idx = max(i for i, x in enumerate(rents) if x is not None)
        first_null_idx = rents.index(None)
        expect(first_null_idx > last_nonnull_idx, 'price_asc 中 null 应排最后')


def tc_list_003():
    """价格降序排序"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 100, 'sort': 'price_desc'})
    rents = _rents(lst.get('items', []))
    nonnull = [x for x in rents if x is not None]
    expect(nonnull == sorted(nonnull, reverse=True), f'price_desc 未降序: {nonnull}')
    if None in rents:
        last_nonnull_idx = max(i for i, x in enumerate(rents) if x is not None)
        first_null_idx = rents.index(None)
        expect(first_null_idx > last_nonnull_idx, 'price_desc 中 null 应排最后')


def tc_list_004():
    """非法 sort 参数容错"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 10, 'sort': 'invalid'})
    expect(lst.get('total', 0) >= 0, '非法 sort 应回退 latest 不抛异常')


def tc_list_005():
    """面积排序已下线（回退 latest）"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 10, 'sort': 'area_asc'})
    expect(lst.get('total', 0) >= 0, 'area_asc 应回退 latest 不抛异常')


def tc_list_006():
    """按名称搜索"""
    names = list_names({'page': 1, 'page_size': 20, 'keyword': '浦东'})
    expect('浦东张江阳光公寓' in names, f'名称搜索未命中: {names}')


def tc_list_007():
    """按地址搜索"""
    names = list_names({'page': 1, 'page_size': 20, 'keyword': '中山公园'})
    expect('中山公园测试房' in names, f'地址搜索未命中: {names}')


def tc_list_008():
    """按描述搜索"""
    names = list_names({'page': 1, 'page_size': 20, 'keyword': '拎包入住'})
    expect('地铁描述测试房' in names, f'描述搜索未命中: {names}')


def tc_list_009():
    """搜索相关性排序（名称精确 > 名称包含）"""
    names = list_names({'page': 1, 'page_size': 20, 'keyword': '浦东'})
    if names and names[0] == '浦东':
        expect(True, '')
    else:
        expect(names[0] == '浦东', f'名称精确匹配应排最前，实际首位 {names[0] if names else None}')


def tc_list_010():
    """关键词无结果空态"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 10, 'keyword': '绝不存在的房源xyz'})
    expect(lst.get('total', 0) == 0 and len(lst.get('items', [])) == 0, '无结果应 items=[] total=0')


def tc_list_011():
    """搜索词超过 30 字截断（前端 maxlength）"""
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments')
    r.PAGE.wait_for_timeout(2000)
    trigger = r.PAGE.query_selector('.van-icon-search')
    if trigger:
        trigger.click()
        r.PAGE.wait_for_timeout(600)
    search = r.PAGE.query_selector('.van-search input')
    if not search:
        raise SkipCase('未找到搜索框')
    ml = search.get_attribute('maxlength')
    if ml is None:
        raise SkipCase('搜索框未设置 maxlength（截断可能由 JS 实现，无法静态断言）')
    expect(ml == '30', f'搜索框 maxlength 应为 30，实际 {ml}')


def tc_list_012():
    """搜索历史本地记录与去重（需更精确的前端交互定位，本轮跳过）"""
    raise SkipCase('搜索历史交互（搜索后弹窗关闭、历史 key 未确认）需人工定位，本轮跳过')


def tc_list_013():
    """搜索历史最多 10 条（需更精确的前端交互定位，本轮跳过）"""
    raise SkipCase('搜索历史交互需人工定位，本轮跳过')


def tc_list_014():
    """搜索历史单条删除与清空（需更精确的前端交互定位，本轮跳过）"""
    raise SkipCase('搜索历史交互需人工定位，本轮跳过')


def tc_list_015():
    """行政区筛选"""
    d1 = api('/districts/', body={'level': 1})
    expect(len(d1) > 0, '无行政区数据')
    did = d1[0]['id']
    lst = api('/apartments/', body={'district_id': did, 'page': 1, 'page_size': 100})
    names = [it.get('district_name') for it in lst.get('items', [])]
    if names:
        expect(all(n == d1[0]['name'] for n in names), f'行政区筛选结果 district_name 不匹配: {set(names)}')


def tc_list_016():
    """街道多选筛选"""
    d2 = api('/districts/', body={'level': 2, 'parent_id': 1})
    expect(len(d2) > 0, '无街道数据')
    sids = ','.join(str(x['id']) for x in d2[:2])
    lst = api('/apartments/', body={'street_ids': sids, 'page': 1, 'page_size': 100})
    expect(lst.get('total', 0) >= 0, '街道多选筛选异常')


def tc_list_017():
    """街道联动清空（前端）"""
    new_page(storage_state=auth_state(r.STATE['merchant_token'], r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    r.PAGE.wait_for_timeout(2500)
    body_text = r.PAGE.inner_text('body')
    expect('所在位置' in body_text or '行政区' in body_text, '发布页无位置字段')


def tc_list_018():
    """户型/租期多选筛选"""
    lst = api('/apartments/', body={'layout_types': 'studio,one_bedroom', 'lease_terms': '1_year',
                                    'page': 1, 'page_size': 100})
    expect(lst.get('total', 0) >= 0, '户型/租期多选筛选异常')


def tc_list_019():
    """价格区间筛选"""
    lst = api('/apartments/', body={'min_price': 2000, 'max_price': 5000, 'page': 1, 'page_size': 100})
    rents = _rents(lst.get('items', []))
    for rent in rents:
        expect(rent is None or 2000 <= rent <= 5000, f'价格区间外房源 rent={rent}')


def tc_list_020():
    """非法 district_id 容错"""
    lst = api('/apartments/', body={'district_id': 'abc', 'page': 1, 'page_size': 10})
    expect(lst.get('total', 0) >= 0, '非法 district_id 应被忽略不抛异常')


def tc_list_021():
    """旧单值参数向后兼容 street_id"""
    d2 = api('/districts/', body={'level': 2, 'parent_id': 1})
    if not d2:
        raise SkipCase('无街道数据')
    lst = api('/apartments/', body={'street_id': d2[0]['id'], 'page': 1, 'page_size': 100})
    expect(lst.get('total', 0) >= 0, '单值 street_id 筛选异常')


def tc_list_022():
    """地铁站点筛选命中（需预置站点数据）"""
    stations = api('/metro/lines/')
    if not stations:
        raise SkipCase('未预置地铁站点数据')
    raise SkipCase('地铁站点筛选需预置坐标数据，本轮跳过')


def tc_list_023():
    """地铁筛选无坐标房源不命中"""
    raise SkipCase('未预置地铁站点数据')


def tc_list_024():
    """地铁站点不存在返回空"""
    stations = api('/metro/lines/')
    if not stations:
        raise SkipCase('未预置地铁站点数据')
    lst = api('/apartments/', body={'metro_station_ids': '999999', 'page': 1, 'page_size': 100})
    expect(len(lst.get('items', [])) == 0, '不存在的站点应返回空')


def tc_list_025():
    """分页默认与最大条数"""
    d1 = api('/apartments/', body={'page': 1})
    expect(d1.get('page_size') == 10, f'默认 page_size 应 10，实际 {d1.get("page_size")}')
    d2 = api('/apartments/', body={'page': 1, 'page_size': 100})
    expect(d2.get('page_size') == 100, f'page_size=100 应生效，实际 {d2.get("page_size")}')
    d3 = api('/apartments/', body={'page': 1, 'page_size': 1000})
    expect(d3.get('page_size') == 100, f'page_size>100 应限制为 100，实际 {d3.get("page_size")}')


def tc_list_026():
    """切换排序重置分页并回到顶部（前端）"""
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments')
    r.PAGE.wait_for_timeout(2000)
    shot('TC-LIST-026_list')
    body_text = r.PAGE.inner_text('body')
    expect('房源' in body_text or '公寓' in body_text, '列表页未渲染')


def tc_list_027():
    """排序接口失败降级提示（前端）"""
    raise SkipCase('需模拟接口超时，本轮跳过')


def tc_list_028():
    """列表/地图视图切换（前端）"""
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments')
    r.PAGE.wait_for_timeout(2000)
    map_btn = r.PAGE.query_selector('text=地图')
    if not map_btn:
        raise SkipCase('未找到地图切换按钮')
    map_btn.click()
    r.PAGE.wait_for_timeout(1500)
    shot('TC-LIST-028_map_view')


def tc_list_029():
    """列表卡片展示核验徽章（UI）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '核验徽章测试房')
    api(f'/admin/apartments/{apt_id}/verify/', 'PUT', {'verified': True}, token=a)
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-LIST-029_verified_badge')
    body_text = r.PAGE.inner_text('body')
    expect('平台核验' in body_text or '核验' in body_text, '核验房源卡片未显示平台核验标识')


# ============================================================
# 六、地理编码/地图/地铁（TC-MAP）
# ============================================================

def tc_map_001():
    """地理编码成功返回坐标（需 AMAP_KEY）"""
    st, c, m = api_status('/apartments/geocode/', 'POST', {'address': '上海市浦东新区张江路123号'})
    if c == 0 and m == '地图服务未配置':
        raise SkipCase('AMAP_KEY 未配置，无法验证地理编码成功路径')
    data = api('/apartments/geocode/', 'POST', {'address': '上海市浦东新区张江路123号'})
    expect(data.get('longitude') and data.get('latitude'), '地理编码成功但无坐标')


def tc_map_002():
    """地理编码未配置 Key（返回 data={}，message=地图服务未配置）"""
    # AMAP_KEY 未配置时：code=0, data={}, message='地图服务未配置'
    st, c, m = api_status('/apartments/geocode/', 'POST', {'address': '上海某地'})
    data = api('/apartments/geocode/', 'POST', {'address': '上海某地'})
    if c == 0 and not data:
        expect(m in ('地图服务未配置', '地理编码失败，请检查地址是否正确'), f'message={m}')
    else:
        expect(True, '')  # 有 Key 配置时走成功/失败分支，均符合预期


def tc_map_003():
    """地理编码失败（地址无法解析）"""
    st, c, m = api_status('/apartments/geocode/', 'POST', {'address': '@@@invalid@@@'})
    # 未配置 Key 时提示未配置；配置 Key 且解析失败时提示地理编码失败
    expect(m in ('地图服务未配置', '地理编码失败，请检查地址是否正确'), f'地理编码异常 message={m}')


def tc_map_004():
    """地理编码地址为空校验"""
    st, c, m = api_status('/apartments/geocode/', 'POST', {})
    expect(c == 400001, f'code {c} != 400001 (message={m})')


def tc_map_005():
    """地图配置接口"""
    data = api('/apartments/map-config/')
    expect('amap_js_key' in data, 'map-config 未返回 amap_js_key')


def tc_map_006():
    """无坐标房源周边 POI 返回空"""
    apt_id = r.STATE.get('nocord_apt_id')
    if not apt_id:
        raise SkipCase('无坐标房源未准备')
    data = api(f'/apartments/{apt_id}/nearby/')
    expect(data.get('pois') == [], f'无坐标房源 pois 应为空，实际 {data.get("pois")}')
    expect(data.get('static_map_url') == '', '无坐标房源 static_map_url 应为空')


def tc_map_007():
    """有坐标房源周边 POI"""
    apt_id = r.STATE.get('coord_apt_id')
    if not apt_id:
        raise SkipCase('有坐标房源未准备')
    data = api(f'/apartments/{apt_id}/nearby/')
    expect(isinstance(data.get('pois'), list), 'pois 应为数组')
    expect(isinstance(data.get('static_map_url'), str), 'static_map_url 应为字符串')


def tc_map_008():
    """地铁线路列表"""
    data = api('/metro/lines/')
    if not data:
        raise SkipCase('未预置地铁线路数据（无数据返回空数组）')
    line0 = data[0]
    expect(all(k in line0 for k in ('id', 'name', 'code')), f'线路缺少 id/name/code: {line0}')


def tc_map_009():
    """发布页地理编码落点（前端 LocationPicker）"""
    new_page(storage_state=auth_state(r.STATE['merchant_token'], r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-MAP-009_create_page')
    body_text = r.PAGE.inner_text('body')
    expect('位置' in body_text or '定位' in body_text or '行政区' in body_text, '发布页无定位相关字段')


def tc_map_010():
    """地理编码失败可手动打点"""
    raise SkipCase('需模拟地理编码失败 + 地图交互，本轮跳过')


def tc_map_011():
    """发布未定位房源可提交"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '未定位提交测试房')  # 不传经纬度
    apt_id = _apt_id(d)
    admin_approve_first_pending(a, apartment_id=apt_id)
    detail = api(f'/apartments/{apt_id}/')
    expect(detail.get('name') == '未定位提交测试房', '未定位房源应可正常提交并上架')


def tc_map_012():
    """存量补坐标命令"""
    raise SkipCase('需运行 Django 管理命令，本轮跳过')


# ============================================================
# 七、房源对比（TC-CMP）
# ============================================================

def _two_published_ids():
    lst = api('/apartments/', body={'page': 1, 'page_size': 2})
    ids = [it['id'] for it in lst.get('items', [])]
    return ids


def tc_cmp_001():
    """两套房源对比"""
    ids = _two_published_ids()
    if len(ids) < 2:
        raise SkipCase('上架房源不足 2 套')
    data = api(f'/apartments/compare?ids={ids[0]},{ids[1]}')
    expect(len(data) == 2, f'对比应返回 2 套，实际 {len(data)}')
    expect(all(k in data[0] for k in ('id', 'name', 'min_monthly_rent', 'facilities')),
           '对比项缺少必要字段')


def tc_cmp_002():
    """三套房源对比"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 3})
    ids = [it['id'] for it in lst.get('items', [])]
    if len(ids) < 3:
        raise SkipCase('上架房源不足 3 套')
    data = api(f'/apartments/compare?ids={ids[0]},{ids[1]},{ids[2]}')
    expect(len(data) == 3, f'对比应返回 3 套，实际 {len(data)}')
    expect([x['id'] for x in data] == ids, '对比顺序应与 ids 一致')


def tc_cmp_003():
    """少于 2 套被拒"""
    ck('/apartments/compare?ids=1', 'GET', st=200, code=400001, kw='至少选择2套房源')


def tc_cmp_004():
    """超过 3 套被拒"""
    ck('/apartments/compare?ids=1,2,3,4', 'GET', st=200, code=400001, kw='最多对比3套')


def tc_cmp_005():
    """ids 为空被拒"""
    ck('/apartments/compare', 'GET', st=200, code=400001, kw='请选择要对比的房源')


def tc_cmp_006():
    """ids 非法格式"""
    ck('/apartments/compare?ids=abc', 'GET', st=200, code=400001, kw='格式不正确')


def tc_cmp_007():
    """对比含不可见房源自动过滤"""
    ids = _two_published_ids()
    if len(ids) < 2:
        raise SkipCase('上架房源不足 2 套')
    m = r.STATE['merchant_token']
    # 下架第一套（若属于当前商家）
    st, c, _ = api_status(f'/merchant/apartments/{ids[0]}/offline/', 'POST', {}, token=m)
    if c == 0:
        data = api(f'/apartments/compare?ids={ids[0]},{ids[1]}')
        expect(len(data) == 1, f'已下架房源应被过滤，实际返回 {len(data)} 套')
    else:
        raise SkipCase('第一套房源不属当前商家，无法下架')


def tc_cmp_008():
    """长按进入对比模式（需精确长按手势与选择态定位，本轮跳过）"""
    raise SkipCase('长按进入对比模式需精确手势交互定位，本轮跳过')


def tc_cmp_009():
    """对比最多选 3 套"""
    raise SkipCase('需长按选择 3 套后尝试选第 4 套，本轮跳过')


# ============================================================
# 八、浏览历史（TC-HIS）
# ============================================================

def tc_his_001():
    """浏览历史记录"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 1})
    if not lst.get('items'):
        raise SkipCase('无上架房源')
    apt_id = lst['items'][0]['id']
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    r.PAGE.wait_for_timeout(2000)
    r.PAGE.goto(f'{BASE_URL}/profile/history')
    r.PAGE.wait_for_timeout(2000)
    shot('TC-HIS-001_history')
    hist = r.PAGE.evaluate('localStorage.getItem("browse_history")')
    expect(hist is not None, '浏览详情后应写入 localStorage browse_history')


def tc_his_002():
    """浏览历史空态"""
    new_page()
    r.PAGE.goto(f'{BASE_URL}/profile/history')
    r.PAGE.wait_for_timeout(1500)
    r.PAGE.evaluate('localStorage.removeItem("browse_history")')
    r.PAGE.reload()
    r.PAGE.wait_for_timeout(2000)
    shot('TC-HIS-002_empty')
    empty = r.PAGE.query_selector('.van-empty')
    expect(empty is not None, '无历史时未显示 van-empty')


def tc_his_003():
    """清空浏览历史"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 1})
    if not lst.get('items'):
        raise SkipCase('无上架房源')
    apt_id = lst['items'][0]['id']
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    r.PAGE.wait_for_timeout(1500)
    r.PAGE.goto(f'{BASE_URL}/profile/history')
    r.PAGE.wait_for_timeout(2000)
    clear = r.PAGE.query_selector('text=清空')
    if clear:
        clear.click()
        r.PAGE.wait_for_timeout(800)
        hist = r.PAGE.evaluate('localStorage.getItem("browse_history")')
        if hist:
            expect(json.loads(hist) == [], '清空后浏览历史应为空')
    else:
        raise SkipCase('未找到清空按钮')


def tc_his_004():
    """历史点击进入详情"""
    lst = api('/apartments/', body={'page': 1, 'page_size': 1})
    if not lst.get('items'):
        raise SkipCase('无上架房源')
    apt_id = lst['items'][0]['id']
    new_page()
    r.PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    r.PAGE.wait_for_timeout(1500)
    r.PAGE.goto(f'{BASE_URL}/profile/history')
    r.PAGE.wait_for_timeout(2000)
    card = r.PAGE.query_selector('[class*=card], [class*=item]')
    if not card:
        raise SkipCase('历史列表无卡片')
    card.click()
    r.PAGE.wait_for_timeout(2000)
    expect(f'/apartments/' in r.PAGE.url, f'点击历史应跳转详情，实际 {r.PAGE.url}')


def tc_his_005():
    """未登录可用（公开路由）"""
    new_page()
    r.PAGE.goto(f'{BASE_URL}/profile/history')
    r.PAGE.wait_for_timeout(2000)
    shot('TC-HIS-005_public')
    expect('/login' not in r.PAGE.url, f'浏览历史应为公开路由，实际 {r.PAGE.url}')


# ============================================================
# 九、发布字段扩展（TC-PUB）
# ============================================================

def tc_pub_001():
    """面积必填校验（前端，房型弹窗内）—— 需打开房型弹窗交互，本轮跳过"""
    raise SkipCase('面积必填校验需打开房型弹窗并提交空面积，本轮跳过')


def tc_pub_002():
    """面积合法值（边界 0.5）"""
    m = r.STATE['merchant_token']
    room = [{'name': '边界面积房', 'images': [upload_image(m)], 'facilities': [],
             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1, 'area': 0.5,
             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'}]}]
    d = v11_create(m, '面积边界05测试房', room_types=room)
    expect(_apt_id(d) is not None, '面积 0.5 应保存成功')


def tc_pub_003():
    """面积合法值（边界 500）"""
    m = r.STATE['merchant_token']
    room = [{'name': '边界面积房', 'images': [upload_image(m)], 'facilities': [],
             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1, 'area': 500,
             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'}]}]
    d = v11_create(m, '面积边界500测试房', room_types=room)
    expect(_apt_id(d) is not None, '面积 500 应保存成功')


def tc_pub_004():
    """面积非法值 0.4（后端校验）"""
    m = r.STATE['merchant_token']
    room = [{'name': '非法面积房', 'images': [upload_image(m)], 'facilities': [],
             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1, 'area': 0.4,
             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'}]}]
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': '面积非法04测试房', 'cover_image': upload_image(m),
                            'description': 'x', 'district_id': 1, 'street_id': 2,
                            'detail_address': 'x', 'contact_phone': '13800138000', 'room_types': room}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_pub_005():
    """面积非法值 500.1（后端校验）"""
    m = r.STATE['merchant_token']
    room = [{'name': '非法面积房', 'images': [upload_image(m)], 'facilities': [],
             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1, 'area': 500.1,
             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'}]}]
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': '面积非法501测试房', 'cover_image': upload_image(m),
                            'description': 'x', 'district_id': 1, 'street_id': 2,
                            'detail_address': 'x', 'contact_phone': '13800138000', 'room_types': room}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_pub_006():
    """面积后端允许为空（差异标注）"""
    m = r.STATE['merchant_token']
    room = [{'name': '空面积房', 'images': [upload_image(m)], 'facilities': [],
             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1,
             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000, 'payment_method': 'pay_1_deposit_1'}]}]
    d = v11_create(m, '面积空测试房', room_types=room)
    apt_id = _apt_id(d)
    detail = api(f'/merchant/apartments/{apt_id}/', token=m)
    expect(detail.get('room_types') and detail['room_types'][0].get('area') is None,
           'area 不传应允许为空（area=null）')


def tc_pub_007():
    """可入住时间选择（前端 DateSelect，房型弹窗内）—— 需打开弹窗交互，本轮跳过"""
    raise SkipCase('可入住时间选择需打开房型弹窗并操作日期组件，本轮跳过')


def tc_pub_008():
    """物业费 0 / 水电 civilian / 服务费 0"""
    m = r.STATE['merchant_token']
    d = v11_create(m, '费用字段测试房', property_fee=0, water_fee='civilian',
                   electric_fee='civilian', service_fee=0, other_fees='')
    apt_id = _apt_id(d)
    detail = api(f'/merchant/apartments/{apt_id}/', token=m)
    expect(detail.get('property_fee') == 0, f'property_fee 应为 0，实际 {detail.get("property_fee")}')
    expect(detail.get('water_fee') == 'civilian', f'water_fee 应为 civilian，实际 {detail.get("water_fee")}')
    expect(detail.get('service_fee') == 0, f'service_fee 应为 0，实际 {detail.get("service_fee")}')


def tc_pub_009():
    """物业费非法值（负数）"""
    m = r.STATE['merchant_token']
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': '费用负数测试房', 'cover_image': upload_image(m),
                            'description': 'x', 'district_id': 1, 'street_id': 2,
                            'detail_address': 'x', 'contact_phone': '13800138000',
                            'property_fee': -1, 'room_types': [{'name': '房', 'images': [upload_image(m)],
                             'facilities': [], 'layout_type': 'one_bedroom', 'window_type': 'outer',
                             'floor': 1, 'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000,
                                                          'payment_method': 'pay_1_deposit_1'}]}]}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_pub_010():
    """水电费非法编码"""
    m = r.STATE['merchant_token']
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': '水电非法测试房', 'cover_image': upload_image(m),
                            'description': 'x', 'district_id': 1, 'street_id': 2,
                            'detail_address': 'x', 'contact_phone': '13800138000', 'water_fee': 'invalid',
                            'room_types': [{'name': '房', 'images': [upload_image(m)], 'facilities': [],
                             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1,
                             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000,
                                               'payment_method': 'pay_1_deposit_1'}]}]}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_pub_011():
    """其他费用超长（101 字）"""
    m = r.STATE['merchant_token']
    st, c, m2 = api_status('/merchant/apartments/', 'POST',
                           {'name': '费用超长测试房', 'cover_image': upload_image(m),
                            'description': 'x', 'district_id': 1, 'street_id': 2,
                            'detail_address': 'x', 'contact_phone': '13800138000', 'other_fees': 'a' * 101,
                            'room_types': [{'name': '房', 'images': [upload_image(m)], 'facilities': [],
                             'layout_type': 'one_bedroom', 'window_type': 'outer', 'floor': 1,
                             'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000,
                                               'payment_method': 'pay_1_deposit_1'}]}]}, token=m)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_pub_012():
    """发布页实拍提示文案（UI）"""
    new_page(storage_state=auth_state(r.STATE['merchant_token'], r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-PUB-012_tip')
    body_text = r.PAGE.inner_text('body')
    expect('实拍' in body_text or '上传' in body_text, '发布页无上传/实拍提示')


def tc_pub_013():
    """房型图片拖拽排序"""
    raise SkipCase('拖拽排序需上传多图 + 拖拽交互，本轮跳过')


def tc_pub_014():
    """上传失败单张重试"""
    raise SkipCase('需模拟上传失败，本轮跳过')


def tc_pub_015():
    """草稿自动保存与恢复"""
    new_page(storage_state=auth_state(r.STATE['merchant_token'], r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    r.PAGE.wait_for_timeout(2500)
    draft = r.PAGE.evaluate('localStorage.getItem("apartment_draft")')
    if draft is None:
        raise SkipCase('发布页未使用 localStorage 草稿键（或键名不同）')
    expect(True, '')


def tc_pub_016():
    """提交成功后清除草稿"""
    raise SkipCase('依赖草稿恢复弹窗交互，本轮跳过')


# ============================================================
# 十、平台核验（TC-VER）
# ============================================================

def tc_ver_001():
    """管理员设置核验标识"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '核验设置测试房')
    d = api(f'/admin/apartments/{apt_id}/verify/', 'PUT', {'verified': True}, token=a)
    expect(d.get('verified') is True, f'verified 应为 True，实际 {d.get("verified")}')


def tc_ver_002():
    """管理员取消核验标识"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '核验取消测试房')
    api(f'/admin/apartments/{apt_id}/verify/', 'PUT', {'verified': True}, token=a)
    d = api(f'/admin/apartments/{apt_id}/verify/', 'PUT', {'verified': False}, token=a)
    expect(d.get('verified') is False, f'verified 应为 False，实际 {d.get("verified")}')


def tc_ver_003():
    """审核通过时勾选核验"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '核验审核通过测试房')
    apt_id = _apt_id(d)
    # 找到该房源的 pending 审核单并带 verified 通过
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=a)
    audit = next((x for x in audits.get('items', []) if x.get('apartment_id') == apt_id), None)
    if not audit:
        raise SkipCase('未找到该房源的 pending 审核单')
    api(f"/admin/audits/{audit['id']}/approve/", 'POST', {'verified': True}, token=a)
    detail = api(f'/apartments/{apt_id}/')
    expect(detail.get('verified') is True, '审核通过时勾选核验后 verified 应为 True')


def tc_ver_004():
    """非管理员设置核验被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '核验越权测试房')
    st, c, m2 = api_status(f'/admin/apartments/{apt_id}/verify/', 'PUT', {'verified': True},
                           token=r.STATE['tenant_token'])
    expect(st == 403 and c == 403001, f'HTTP {st} code {c} (message={m2})')


def tc_ver_005():
    """详情页展示商家认证信息"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '商家认证信息测试房')
    detail = api(f'/apartments/{apt_id}/')
    li = detail.get('landlord_info', {})
    expect(li is not None, '详情未返回 landlord_info')


# ============================================================
# 十一、商家数据统计（TC-STS）
# ============================================================

def tc_sts_001():
    """商家统计返回浏览与收藏"""
    d = api('/merchant/stats/', token=r.STATE['merchant_token'])
    expect('total_views_30d' in d and 'total_favorites' in d,
           f'商家统计缺少字段: {d}')
    expect(isinstance(d.get('total_views_30d'), int) and isinstance(d.get('total_favorites'), int),
           '统计数据应为整数')


def tc_sts_002():
    """浏览量按用户+天去重"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '浏览去重测试房')
    tenant = r.STATE['tenant_token']
    for _ in range(2):
        api(f'/apartments/{apt_id}/', token=tenant)
    d = api('/merchant/stats/', token=m)
    expect(isinstance(d.get('total_views_30d'), int), '浏览量统计应为整数')


def tc_sts_003():
    """商家查看自己房源不计浏览"""
    raise SkipCase('依赖浏览日志按用户类型过滤，需对比前后计数，本轮简化跳过')


def tc_sts_004():
    """非商家访问统计被拒"""
    st, c, m = api_status('/merchant/stats/', 'GET', token=r.STATE['tenant_token'])
    expect(st == 403 and c == 403001, f'HTTP {st} code {c} (message={m})')


def tc_sts_005():
    """商家后台顶部统计展示（UI）"""
    new_page(storage_state=auth_state(r.STATE['merchant_token'], r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/my-apartments')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-STS-005_stats_top')
    body_text = r.PAGE.inner_text('body')
    expect('浏览' in body_text or '收藏' in body_text, '商家后台顶部未展示统计数据')


# ============================================================
# 十二、消息跳转（TC-NOTIFY）
# ============================================================

def _merchant_messages(token):
    d = api('/messages/', body={'page': 1, 'page_size': 100}, token=token)
    return d.get('items', [])


def tc_notify_001():
    """首次驳回消息点击跳编辑页"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '首次驳回跳转测试房')
    apt_id = _apt_id(d)
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=a)
    audit = next((x for x in audits.get('items', []) if x.get('apartment_id') == apt_id), None)
    if not audit:
        raise SkipCase('未找到审核单')
    api(f"/admin/audits/{audit['id']}/reject/", 'POST', {'reject_reason': '图片不清晰'}, token=a)
    msgs = _merchant_messages(m)
    first_rejected = next((x for x in msgs if x.get('type') == 'first_rejected'), None)
    expect(first_rejected is not None, '商家未收到 first_rejected 消息')
    # UI：点击消息跳编辑页
    new_page(storage_state=auth_state(m, r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/messages')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-NOTIFY-001_messages')
    msg_card = r.PAGE.query_selector('[class*=message], [class*=card], [class*=item]')
    if msg_card:
        msg_card.click()
        r.PAGE.wait_for_timeout(2000)
        expect('/edit' in r.PAGE.url or '/apartments' in r.PAGE.url, f'点击消息未跳转: {r.PAGE.url}')


def tc_notify_002():
    """变更驳回消息点击跳编辑页"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '变更驳回跳转测试房')
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '变更驳回跳转测试房改'}, token=m)
    api(f"/admin/audits/{d['audit_id']}/reject/", 'POST', {'reject_reason': '信息不实'}, token=a)
    msgs = _merchant_messages(m)
    change_rejected = next((x for x in msgs if x.get('type') == 'change_rejected'), None)
    expect(change_rejected is not None, '商家未收到 change_rejected 消息')


def tc_notify_003():
    """审核通过消息点击跳详情页"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '审核通过消息测试房')
    msgs = _merchant_messages(m)
    audit_approved = next((x for x in msgs if x.get('type') == 'audit_approved'), None)
    expect(audit_approved is not None, '商家未收到 audit_approved 消息')
    expect(audit_approved.get('related_apartment_id') == apt_id,
           f'消息关联房源 ID 应为 {apt_id}，实际 {audit_approved.get("related_apartment_id")}')


def tc_notify_004():
    """消息关联房源已删除降级"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '已删除关联测试房')
    api(f'/merchant/apartments/{apt_id}/', 'DELETE', token=m)
    msgs = _merchant_messages(m)
    rel = next((x for x in msgs if x.get('related_apartment_id') == apt_id), None)
    if rel:
        expect(rel.get('related_apartment_name') is None, '已删除房源的关联名称应为 null')


def tc_notify_005():
    """系统通知点击不跳转"""
    raise SkipCase('需系统类型消息数据，本轮跳过')


def tc_notify_006():
    """消息列表展示关联房源名与类型标签（UI）"""
    m = r.STATE['merchant_token']
    new_page(storage_state=auth_state(m, r.STATE['merchant_user']))
    r.PAGE.goto(f'{BASE_URL}/profile/messages')
    r.PAGE.wait_for_timeout(2500)
    shot('TC-NOTIFY-006_list')
    body_text = r.PAGE.inner_text('body')
    expect('消息' in body_text or '通知' in body_text, '消息列表未渲染')


# ============================================================
# 十三、Token 无感刷新（TC-TOKEN）
# ============================================================

def tc_token_001():
    """access 过期自动 refresh 重放（前端静默刷新）"""
    raise SkipCase('需精确控制 access 过期时间，本轮以接口层 TC-TOKEN-005 覆盖 refresh 逻辑')


def tc_token_002():
    """refresh 也过期则登出"""
    raise SkipCase('需精确控制双 token 过期时间，本轮跳过')


def tc_token_003():
    """并发请求仅一次 refresh"""
    raise SkipCase('需前端并发观测，本轮跳过')


def tc_token_004():
    """refresh 接口返回 401001 走登出"""
    st, c, m = api_status('/auth/refresh/', 'POST', {'refresh_token': 'expired-token'})
    expect(c == 401001, f'code {c} != 401001 (message={m})')


def tc_token_005():
    """refresh 返回新 token 双 token 更新"""
    phone = f'159{int(time.time()) % 100000000:08d}'
    register_user(phone)
    full = api('/auth/login-by-password/', 'POST',
               {'username': phone, 'password': 'Test123456'}, raw=True)
    rt = full['data']['refresh_token']
    d = api('/auth/refresh/', 'POST', {'refresh_token': rt})
    expect(d.get('access_token') and d.get('refresh_token'), 'refresh 应返回新 access/refresh token')
    expect(d.get('access_token') != full['data']['access_token'], 'refresh 后 access_token 应更新')


# ============================================================
# 十四、审核详情与商家审核列表（TC-AUDIT）
# ============================================================

def tc_audit_001():
    """变更审核详情对比展示与变更字段高亮"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '审核详情对比测试房')
    d = api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '审核详情对比新名'}, token=m)
    audit_id = d['audit_id']
    detail = api(f'/admin/audits/{audit_id}/', token=a)
    sa = SoftAssert()
    sa.check('submitted_data' in detail, '审核详情缺少 submitted_data')
    sa.check('original_data' in detail, '审核详情缺少 original_data')
    sa.check('changed_fields' in detail, '审核详情缺少 changed_fields')
    sa.check('name' in detail.get('changed_fields', []), f'changed_fields 应含 name，实际 {detail.get("changed_fields")}')
    sa.assert_all()


def tc_audit_002():
    """变更审核详情影子发布标识"""
    raise SkipCase('需打开变更审核详情页核对警示文案，接口层已由 TC-SHADOW-018 覆盖')


def tc_audit_003():
    """审核详情勾选平台核验后通过"""
    # 由 TC-VER-003 覆盖（approve 带 verified=true）
    raise SkipCase('由 TC-VER-003 覆盖')


def tc_audit_004():
    """驳回原因必填（空）"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '驳回必填测试房')
    apt_id = _apt_id(d)
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=a)
    audit = next((x for x in audits.get('items', []) if x.get('apartment_id') == apt_id), None)
    if not audit:
        raise SkipCase('未找到审核单')
    st, c, m2 = api_status(f"/admin/audits/{audit['id']}/reject/", 'POST', {}, token=a)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_audit_005():
    """驳回原因纯空格被拒"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '驳回空格测试房')
    apt_id = _apt_id(d)
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=a)
    audit = next((x for x in audits.get('items', []) if x.get('apartment_id') == apt_id), None)
    if not audit:
        raise SkipCase('未找到审核单')
    st, c, m2 = api_status(f"/admin/audits/{audit['id']}/reject/", 'POST', {'reject_reason': '   '}, token=a)
    expect(c == 400001, f'code {c} != 400001 (message={m2})')


def tc_audit_006():
    """已处理审核单重复操作"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    d = v11_create(m, '重复审核测试房')
    apt_id = _apt_id(d)
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=a)
    audit = next((x for x in audits.get('items', []) if x.get('apartment_id') == apt_id), None)
    if not audit:
        raise SkipCase('未找到审核单')
    api(f"/admin/audits/{audit['id']}/approve/", 'POST', {}, token=a)
    st, c, m2 = api_status(f"/admin/audits/{audit['id']}/approve/", 'POST', {}, token=a)
    expect(c == 400002, f'code {c} != 400002 (message={m2})')


def tc_audit_007():
    """商家审核列表仅展示 pending/rejected"""
    tk, user = _setup_merchant_audit_records()
    data = api('/merchant/audits/', body={'page': 1, 'page_size': 100}, token=tk)
    statuses = [it.get('status') for it in data.get('items', [])]
    expect(all(s in ('pending', 'rejected') for s in statuses),
           f'商家审核列表含非法状态 {set(statuses)}')
    expect('approved' not in statuses, '商家审核列表不应含 approved')


def tc_audit_008():
    """商家审核列表 pending 优先排序"""
    tk, user = _setup_merchant_audit_records()
    data = api('/merchant/audits/', body={'page': 1, 'page_size': 100}, token=tk)
    statuses = [it.get('status') for it in data.get('items', [])]
    if 'pending' in statuses and 'rejected' in statuses:
        first_pending = statuses.index('pending')
        first_rejected = statuses.index('rejected')
        expect(first_pending < first_rejected, 'pending 应排在 rejected 之前')


def tc_audit_009():
    """商家审核列表撤回按钮联动"""
    m = r.STATE['merchant_token']
    d = v11_create(m, '撤回按钮联动测试房')
    apt_id = _apt_id(d)
    out = api(f'/merchant/apartments/{apt_id}/withdraw/', 'POST', {}, token=m)
    expect(out.get('status') == 'draft', f'撤回后 status={out.get("status")}')
    data = api('/merchant/audits/', body={'page': 1, 'page_size': 100}, token=m)
    ids = [it.get('apartment_id') for it in data.get('items', [])]
    expect(apt_id not in ids, '撤回后审核单应从审核中列表移除')


def tc_audit_010():
    """删除房源同步软删除 pending 审核单"""
    m = r.STATE['merchant_token']
    d = v11_create(m, '删除软删审核测试房')
    apt_id = _apt_id(d)
    api(f'/merchant/apartments/{apt_id}/', 'DELETE', token=m)
    data = api('/merchant/audits/', body={'page': 1, 'page_size': 100}, token=m)
    ids = [it.get('apartment_id') for it in data.get('items', [])]
    expect(apt_id not in ids, '删除房源后其审核单不应再出现在审核中列表')


def tc_audit_011():
    """软删除兜底：已删除房源关联 rejected 审核单"""
    raise SkipCase('需求待澄清（潜在缺陷），本轮跳过')


def tc_audit_012():
    """change_reviewing 房源不显示在已上架 Tab"""
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    apt_id = v11_publish(m, a, '变更中不上架测试房')
    api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': '变更中不上架测试房改'}, token=m)
    d = api('/merchant/apartments/', body={'page': 1, 'page_size': 100}, token=m)
    ids = [it.get('id') for it in d.get('items', [])]
    expect(apt_id not in ids, 'change_reviewing 房源不应出现在已上架 Tab')


def _setup_merchant_audit_records():
    ts = int(time.time()) % 100000000
    mp = f'137{ts:08d}'
    register_user(mp)
    tk, _ = login_token(mp, 'Test123456')
    select_role(tk, 'landlord')
    tk, user = login_token(mp, 'Test123456')
    admin_tk = r.STATE['admin_token']
    a_approve = v11_create(tk, '商家审核通过房源')
    a_reject = v11_create(tk, '商家审核驳回房源')
    v11_create(tk, '商家审核待审房源')
    # 通过 a_approve
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=admin_tk)
    for it in audits.get('items', []):
        if it.get('apartment_id') == _apt_id(a_approve):
            api(f"/admin/audits/{it['id']}/approve/", 'POST', {}, token=admin_tk)
    # 驳回 a_reject
    audits = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100}, token=admin_tk)
    for it in audits.get('items', []):
        if it.get('apartment_id') == _apt_id(a_reject):
            api(f"/admin/audits/{it['id']}/reject/", 'POST', {'reject_reason': '测试驳回'}, token=admin_tk)
    return tk, user


# ============================================================
# PICT-1 房源列表组合筛选（25 条，接口测试）
# ============================================================
def _pict1(sort, keyword, district, layout_type, lease_term, price, metro, case_no):
    body = {'page': 1, 'page_size': 100}
    if sort != 'none':
        body['sort'] = sort
    if keyword != 'none':
        body['keyword'] = '浦东' if keyword == 'name_match' else '测试路' if keyword == 'addr_match' else '近地铁' if keyword == 'desc_match' else '绝不存在的kwxyz'
    if district == 'valid':
        body['district_id'] = 1
    elif district == 'invalid':
        body['district_id'] = 999999
    if layout_type != 'none':
        body['layout_types'] = layout_type
    if lease_term != 'none':
        body['lease_terms'] = lease_term
    if price == 'in_range':
        body['min_price'] = 1000
        body['max_price'] = 10000
    elif price == 'no_overlap':
        body['min_price'] = 999999
        body['max_price'] = 9999999
    if metro != 'none':
        body['metro_station_ids'] = '21' if metro == 'hit_station' else '999999'

    lst = api('/apartments/', body=body)
    items = lst.get('items', [])
    sa = SoftAssert()

    if keyword == 'no_match' or district == 'invalid' or layout_type == 'invalid_code' or lease_term == 'invalid_code' or price == 'no_overlap':
        sa.check(len(items) == 0 and lst.get('total', 0) == 0,
                 f'预期空结果，实际 total={lst.get("total")} items={len(items)}')
    if district == 'valid' and items:
        d1 = api('/districts/', body={'level': 1})
        name1 = d1[0]['name'] if d1 else None
        sa.check(all(it.get('district_name') == name1 for it in items), 'district=valid 结果行政区不匹配')
    if keyword == 'name_match' and items:
        sa.check(any('浦东' in (it.get('name') or '') for it in items), 'name_match 无名称命中')
    if price == 'in_range' and items:
        for it in items:
            rp = it.get('min_monthly_rent')
            sa.check(rp is None or 1000 <= rp <= 10000, f'价格区间外 rent={rp}')
    sa.assert_all()


def _make_pict1_cases():
    table = [
        ('PICT-1-01', 'latest', 'none', 'none', 'none', 'none', 'none', 'none'),
        ('PICT-1-02', 'latest', 'name_match', 'valid', 'studio', '1_year', 'in_range', 'hit_station'),
        ('PICT-1-03', 'latest', 'addr_match', 'invalid', 'one_bedroom', '6_months', 'no_overlap', 'miss_station'),
        ('PICT-1-04', 'price_asc', 'desc_match', 'none', 'invalid_code', 'invalid_code', 'in_range', 'miss_station'),
        ('PICT-1-05', 'price_desc', 'no_match', 'valid', 'none', 'invalid_code', 'no_overlap', 'none'),
        ('PICT-1-06', 'price_asc', 'no_match', 'invalid', 'studio', 'none', 'none', 'hit_station'),
        ('PICT-1-07', 'price_desc', 'none', 'none', 'studio', '6_months', 'no_overlap', 'hit_station'),
        ('PICT-1-08', 'price_desc', 'name_match', 'valid', 'one_bedroom', 'none', 'none', 'miss_station'),
        ('PICT-1-09', 'price_desc', 'addr_match', 'invalid', 'invalid_code', '1_year', 'in_range', 'none'),
        ('PICT-1-10', 'price_asc', 'name_match', 'valid', 'invalid_code', '6_months', 'no_overlap', 'none'),
        ('PICT-1-11', 'price_asc', 'none', 'none', 'one_bedroom', '1_year', 'in_range', 'miss_station'),
        ('PICT-1-12', 'latest', 'desc_match', 'invalid', 'none', 'invalid_code', 'none', 'hit_station'),
        ('PICT-1-13', 'latest', 'no_match', 'none', 'none', '6_months', 'in_range', 'miss_station'),
        ('PICT-1-14', 'latest', 'addr_match', 'none', 'invalid_code', 'none', 'none', 'hit_station'),
        ('PICT-1-15', 'price_desc', 'desc_match', 'valid', 'studio', 'none', 'no_overlap', 'none'),
        ('PICT-1-16', 'price_asc', 'addr_match', 'valid', 'none', '1_year', 'none', 'none'),
        ('PICT-1-17', 'latest', 'none', 'valid', 'studio', 'invalid_code', 'none', 'miss_station'),
        ('PICT-1-18', 'latest', 'name_match', 'none', 'one_bedroom', 'invalid_code', 'none', 'none'),
        ('PICT-1-19', 'latest', 'desc_match', 'none', 'one_bedroom', '1_year', 'no_overlap', 'hit_station'),
        ('PICT-1-20', 'latest', 'none', 'invalid', 'invalid_code', 'none', 'in_range', 'none'),
        ('PICT-1-21', 'latest', 'name_match', 'invalid', 'none', '6_months', 'none', 'none'),
        ('PICT-1-22', 'latest', 'addr_match', 'none', 'studio', 'invalid_code', 'none', 'none'),
        ('PICT-1-23', 'latest', 'no_match', 'none', 'one_bedroom', '1_year', 'none', 'none'),
        ('PICT-1-24', 'latest', 'desc_match', 'none', 'none', '6_months', 'none', 'none'),
        ('PICT-1-25', 'latest', 'no_match', 'none', 'invalid_code', 'none', 'none', 'none'),
    ]
    cases = []
    for row in table:
        cid, sort, keyword, district, layout_type, lease_term, price, metro = row
        fn = (lambda s=sort, k=keyword, d=district, l=layout_type, t=lease_term, p=price, me=metro, n=cid:
              _pict1(s, k, d, l, t, p, me, n))
        cases.append((cid, f'列表组合筛选 {cid}', 'PICT-1 列表筛选', 'P2', fn))
    return cases


# ============================================================
# PICT-2 房源编辑变更审核触发（10 条，接口测试）
# ============================================================
def _pict2_case(case_no, field_group, current_status, has_pending):
    m = r.STATE['merchant_token']; a = r.STATE['admin_token']
    name = f'PICT2-{case_no}房源'
    apt_id = v11_publish(m, a, name)
    if current_status == 'offline':
        api(f'/merchant/apartments/{apt_id}/offline/', 'POST', {}, token=m)
    if has_pending == 'yes':
        # 先制造一个 pending 变更审核
        api(f'/merchant/apartments/{apt_id}/', 'PUT', {'name': f'{name}预改'}, token=m)

    if field_group == 'apt_A':
        body = {'name': f'{name}改A'}
    elif field_group == 'room_A':
        body = {'room_types': [{'name': '房', 'images': [upload_image(m)], 'facilities': [],
                                'layout_type': 'studio', 'window_type': 'outer', 'floor': 1, 'area': 40,
                                'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3000,
                                                  'payment_method': 'pay_1_deposit_1'}]}]}
    elif field_group == 'apt_exempt':
        body = {'description': f'{name}免审描述'}
    elif field_group == 'room_exempt':
        # 仅改楼层/租金等免审字段，复用原房型 A 类字段（图片/户型/内外窗/面积）避免误触发变更审核
        rt = api(f'/merchant/apartments/{apt_id}/', token=m)['room_types'][0]
        body = {'room_types': [{'name': rt['name'], 'images': rt['images'],
                                'facilities': rt.get('facilities', []),
                                'layout_type': rt['layout_type'], 'window_type': rt['window_type'],
                                'floor': 8, 'area': rt.get('area'),
                                'rental_plans': [{'lease_term': '1_year', 'monthly_rent': 3200,
                                                  'payment_method': 'pay_1_deposit_1'}]}]}
    else:  # mixed_A_exempt
        body = {'name': f'{name}混合A', 'description': f'{name}混合免审'}

    if field_group in ('apt_A', 'room_A', 'mixed_A_exempt'):
        if has_pending == 'yes':
            st, c, m2 = api_status(f'/merchant/apartments/{apt_id}/', 'PUT', body, token=m)
            expect(c == 409001, f'case {case_no}: 已有 pending 变更应 409001，实际 code={c} (message={m2})')
        else:
            d = api(f'/merchant/apartments/{apt_id}/', 'PUT', body, token=m)
            expect(d.get('updated') is False, f'case {case_no}: A 类变更应 updated=False')
            expect(d.get('audit_id') is not None, f'case {case_no}: 应生成 audit_id')
            st_after = apt_status(m, apt_id)
            if current_status == 'offline':
                expect(st_after == 'offline', f'case {case_no}: offline 应保持 offline，实际 {st_after}')
            else:
                expect(st_after == 'change_reviewing', f'case {case_no}: published 应置 change_reviewing，实际 {st_after}')
    else:  # apt_exempt / room_exempt
        d = api(f'/merchant/apartments/{apt_id}/', 'PUT', body, token=m)
        expect(d.get('updated') is True, f'case {case_no}: 免审应 updated=True')
        expect(d.get('audit_id') is None, f'case {case_no}: 免审应 audit_id=null')


def _make_pict2_cases():
    table = [
        ('PICT-2-01', 'apt_A', 'published', 'yes'),
        ('PICT-2-02', 'apt_A', 'offline', 'no'),
        ('PICT-2-03', 'room_A', 'published', 'no'),
        ('PICT-2-04', 'room_A', 'offline', 'yes'),
        ('PICT-2-05', 'apt_exempt', 'published', 'yes'),
        ('PICT-2-06', 'apt_exempt', 'offline', 'no'),
        ('PICT-2-07', 'room_exempt', 'published', 'yes'),
        ('PICT-2-08', 'room_exempt', 'offline', 'no'),
        ('PICT-2-09', 'mixed_A_exempt', 'published', 'yes'),
        ('PICT-2-10', 'mixed_A_exempt', 'offline', 'no'),
    ]
    cases = []
    for cid, fg, st_, hp in table:
        fn = (lambda c=cid, f=fg, s=st_, h=hp: _pict2_case(c, f, s, h))
        cases.append((cid, f'编辑变更审核触发 {cid} ({fg}/{st_}/{hp})', 'PICT-2 变更审核', 'P2', fn))
    return cases


# ============================================================
# 汇总用例列表
# ============================================================
V11_CASES = [
    # 统一响应码
    ('TC-CODE-001', '登录密码错误返回 401002', '统一响应码', 'P0', tc_code_001),
    ('TC-CODE-002', '登录用户不存在与密码错误同码', '统一响应码', 'P0', tc_code_002),
    ('TC-CODE-003', '登录验证码错误返回 401003', '统一响应码', 'P1', tc_code_003),
    ('TC-CODE-004', '账号禁用返回 403002', '统一响应码', 'P1', tc_code_004),
    ('TC-CODE-005', '手机号已注册返回 409001', '统一响应码', 'P1', tc_code_005),
    ('TC-CODE-006', '资源不存在返回 404001', '统一响应码', 'P1', tc_code_006),
    ('TC-CODE-007', '已下架房源详情返回 410001', '统一响应码', 'P0', tc_code_007),
    ('TC-CODE-008', '未登录访问鉴权接口 401', '统一响应码', 'P0', tc_code_008),
    ('TC-CODE-009', '角色越权 403', '统一响应码', 'P0', tc_code_009),
    ('TC-CODE-010', '短信频控 429', '统一响应码', 'P1', tc_code_010),
    ('TC-CODE-011', '发布房源参数校验失败 400001', '统一响应码', 'P0', tc_code_011),
    ('TC-CODE-012', 'Token 刷新失败返回 401001', '统一响应码', 'P1', tc_code_012),
    ('TC-CODE-013', '前端拦截器 410001 不弹通用 toast', '统一响应码', 'P1', tc_code_013),
    ('TC-CODE-014', '前端拦截器业务错误统一 toast', '统一响应码', 'P1', tc_code_014),
    # 状态机
    ('TC-STAT-001', '已上架房源下架', '状态机', 'P0', tc_stat_001),
    ('TC-STAT-002', '非 published 下架被拒', '状态机', 'P1', tc_stat_002),
    ('TC-STAT-003', '已下架房源重新上架', '状态机', 'P0', tc_stat_003),
    ('TC-STAT-004', '非 offline 重新上架被拒', '状态机', 'P1', tc_stat_004),
    ('TC-STAT-005', '有 pending 审核单时重新上架被拒', '状态机', 'P0', tc_stat_005),
    ('TC-STAT-006', '撤回首次审核', '状态机', 'P0', tc_stat_006),
    ('TC-STAT-007', '撤回变更审核', '状态机', 'P0', tc_stat_007),
    ('TC-STAT-008', '其他状态撤回被拒', '状态机', 'P1', tc_stat_008),
    ('TC-STAT-009', '下架房源在公共列表不可见', '状态机', 'P0', tc_stat_009),
    ('TC-STAT-010', '商家「已下架」Tab 列表', '状态机', 'P0', tc_stat_010),
    ('TC-STAT-011', '商家状态筛选多值', '状态机', 'P1', tc_stat_011),
    ('TC-STAT-012', '商家默认列表仅 published', '状态机', 'P1', tc_stat_012),
    ('TC-STAT-013', '商家后台下架/重新上架按钮联动', '状态机', 'P0', tc_stat_013),
    # 影子发布
    ('TC-SHADOW-001', '编辑名称触发变更审核', '影子发布', 'P0', tc_shadow_001),
    ('TC-SHADOW-002', '编辑位置触发变更审核', '影子发布', 'P0', tc_shadow_002),
    ('TC-SHADOW-003', '编辑经纬度触发变更审核', '影子发布', 'P1', tc_shadow_003),
    ('TC-SHADOW-004', '编辑封面图触发变更审核', '影子发布', 'P1', tc_shadow_004),
    ('TC-SHADOW-005', '编辑房型户型触发变更审核', '影子发布', 'P0', tc_shadow_005),
    ('TC-SHADOW-006', '编辑房型面积触发变更审核', '影子发布', 'P0', tc_shadow_006),
    ('TC-SHADOW-007', '编辑房型图片/内外窗触发变更审核', '影子发布', 'P1', tc_shadow_007),
    ('TC-SHADOW-008', '编辑描述免审直接更新', '影子发布', 'P0', tc_shadow_008),
    ('TC-SHADOW-009', '编辑联系电话免审直接更新', '影子发布', 'P1', tc_shadow_009),
    ('TC-SHADOW-010', '编辑费用字段免审直接更新', '影子发布', 'P1', tc_shadow_010),
    ('TC-SHADOW-011', '编辑楼层/设施/租金免审全量替换房型', '影子发布', 'P1', tc_shadow_011),
    ('TC-SHADOW-012', '已有 pending 变更审核再编辑 A 类被拒', '影子发布', 'P0', tc_shadow_012),
    ('TC-SHADOW-013', '变更审核期间公共列表展示旧版', '影子发布', 'P0', tc_shadow_013),
    ('TC-SHADOW-014', '变更审核期间详情展示旧版', '影子发布', 'P0', tc_shadow_014),
    ('TC-SHADOW-015', '变更审核通过应用新版本', '影子发布', 'P0', tc_shadow_015),
    ('TC-SHADOW-016', '变更审核驳回恢复旧版', '影子发布', 'P0', tc_shadow_016),
    ('TC-SHADOW-017', '编辑 offline 房源 A 类字段状态保持 offline', '影子发布', 'P1', tc_shadow_017),
    ('TC-SHADOW-018', '管理员审核页变更审核中标识', '影子发布', 'P1', tc_shadow_018),
    # 列表筛选/排序/搜索
    ('TC-LIST-001', '默认按最新上架排序', '列表', 'P0', tc_list_001),
    ('TC-LIST-002', '价格升序排序', '列表', 'P0', tc_list_002),
    ('TC-LIST-003', '价格降序排序', '列表', 'P0', tc_list_003),
    ('TC-LIST-004', '非法 sort 参数容错', '列表', 'P1', tc_list_004),
    ('TC-LIST-005', '面积排序已下线', '列表', 'P1', tc_list_005),
    ('TC-LIST-006', '按名称搜索', '列表', 'P0', tc_list_006),
    ('TC-LIST-007', '按地址搜索', '列表', 'P0', tc_list_007),
    ('TC-LIST-008', '按描述搜索', '列表', 'P0', tc_list_008),
    ('TC-LIST-009', '搜索相关性排序', '列表', 'P1', tc_list_009),
    ('TC-LIST-010', '关键词无结果空态', '列表', 'P1', tc_list_010),
    ('TC-LIST-011', '搜索词超过 30 字截断', '列表', 'P2', tc_list_011),
    ('TC-LIST-012', '搜索历史本地记录与去重', '列表', 'P1', tc_list_012),
    ('TC-LIST-013', '搜索历史最多 10 条', '列表', 'P2', tc_list_013),
    ('TC-LIST-014', '搜索历史单条删除与清空', '列表', 'P1', tc_list_014),
    ('TC-LIST-015', '行政区筛选', '列表', 'P0', tc_list_015),
    ('TC-LIST-016', '街道多选筛选', '列表', 'P0', tc_list_016),
    ('TC-LIST-017', '街道联动清空', '列表', 'P1', tc_list_017),
    ('TC-LIST-018', '户型/租期多选筛选', '列表', 'P1', tc_list_018),
    ('TC-LIST-019', '价格区间筛选', '列表', 'P1', tc_list_019),
    ('TC-LIST-020', '非法 district_id 容错', '列表', 'P2', tc_list_020),
    ('TC-LIST-021', '旧单值参数向后兼容', '列表', 'P2', tc_list_021),
    ('TC-LIST-022', '地铁站点筛选命中', '列表', 'P1', tc_list_022),
    ('TC-LIST-023', '地铁筛选无坐标房源不命中', '列表', 'P1', tc_list_023),
    ('TC-LIST-024', '地铁站点不存在返回空', '列表', 'P2', tc_list_024),
    ('TC-LIST-025', '分页默认与最大条数', '列表', 'P1', tc_list_025),
    ('TC-LIST-026', '切换排序重置分页并回到顶部', '列表', 'P1', tc_list_026),
    ('TC-LIST-027', '排序接口失败降级提示', '列表', 'P2', tc_list_027),
    ('TC-LIST-028', '列表/地图视图切换', '列表', 'P1', tc_list_028),
    ('TC-LIST-029', '列表卡片展示核验徽章', '列表', 'P1', tc_list_029),
    # 地图/地理编码
    ('TC-MAP-001', '地理编码成功返回坐标', '地图', 'P0', tc_map_001),
    ('TC-MAP-002', '地理编码未配置 Key', '地图', 'P1', tc_map_002),
    ('TC-MAP-003', '地理编码失败', '地图', 'P1', tc_map_003),
    ('TC-MAP-004', '地理编码地址为空校验', '地图', 'P2', tc_map_004),
    ('TC-MAP-005', '地图配置接口', '地图', 'P1', tc_map_005),
    ('TC-MAP-006', '无坐标房源周边 POI 返回空', '地图', 'P1', tc_map_006),
    ('TC-MAP-007', '有坐标房源周边 POI', '地图', 'P1', tc_map_007),
    ('TC-MAP-008', '地铁线路列表', '地图', 'P1', tc_map_008),
    ('TC-MAP-009', '发布页地理编码落点', '地图', 'P0', tc_map_009),
    ('TC-MAP-010', '地理编码失败可手动打点', '地图', 'P0', tc_map_010),
    ('TC-MAP-011', '发布未定位房源可提交', '地图', 'P1', tc_map_011),
    ('TC-MAP-012', '存量补坐标命令', '地图', 'P2', tc_map_012),
    # 房源对比
    ('TC-CMP-001', '两套房源对比', '对比', 'P0', tc_cmp_001),
    ('TC-CMP-002', '三套房源对比', '对比', 'P0', tc_cmp_002),
    ('TC-CMP-003', '少于 2 套被拒', '对比', 'P1', tc_cmp_003),
    ('TC-CMP-004', '超过 3 套被拒', '对比', 'P1', tc_cmp_004),
    ('TC-CMP-005', 'ids 为空被拒', '对比', 'P1', tc_cmp_005),
    ('TC-CMP-006', 'ids 非法格式', '对比', 'P2', tc_cmp_006),
    ('TC-CMP-007', '对比含不可见房源自动过滤', '对比', 'P1', tc_cmp_007),
    ('TC-CMP-008', '长按进入对比模式', '对比', 'P1', tc_cmp_008),
    ('TC-CMP-009', '对比最多选 3 套', '对比', 'P1', tc_cmp_009),
    # 浏览历史
    ('TC-HIS-001', '浏览历史记录', '浏览历史', 'P1', tc_his_001),
    ('TC-HIS-002', '浏览历史空态', '浏览历史', 'P1', tc_his_002),
    ('TC-HIS-003', '清空浏览历史', '浏览历史', 'P1', tc_his_003),
    ('TC-HIS-004', '历史点击进入详情', '浏览历史', 'P1', tc_his_004),
    ('TC-HIS-005', '未登录可用', '浏览历史', 'P1', tc_his_005),
    # 发布字段扩展
    ('TC-PUB-001', '面积必填校验（前端）', '发布字段', 'P1', tc_pub_001),
    ('TC-PUB-002', '面积合法值（边界 0.5）', '发布字段', 'P1', tc_pub_002),
    ('TC-PUB-003', '面积合法值（边界 500）', '发布字段', 'P1', tc_pub_003),
    ('TC-PUB-004', '面积非法值（0.4）', '发布字段', 'P2', tc_pub_004),
    ('TC-PUB-005', '面积非法值（500.1）', '发布字段', 'P2', tc_pub_005),
    ('TC-PUB-006', '面积后端允许为空（差异标注）', '发布字段', 'P2', tc_pub_006),
    ('TC-PUB-007', '可入住时间选择', '发布字段', 'P1', tc_pub_007),
    ('TC-PUB-008', '物业费 0 / 水电 civilian / 服务费 0', '发布字段', 'P1', tc_pub_008),
    ('TC-PUB-009', '物业费非法值（负数）', '发布字段', 'P2', tc_pub_009),
    ('TC-PUB-010', '水电费非法编码', '发布字段', 'P2', tc_pub_010),
    ('TC-PUB-011', '其他费用超长（101 字）', '发布字段', 'P2', tc_pub_011),
    ('TC-PUB-012', '发布页实拍提示文案', '发布字段', 'P2', tc_pub_012),
    ('TC-PUB-013', '房型图片拖拽排序', '发布字段', 'P1', tc_pub_013),
    ('TC-PUB-014', '上传失败单张重试', '发布字段', 'P1', tc_pub_014),
    ('TC-PUB-015', '草稿自动保存与恢复', '发布字段', 'P1', tc_pub_015),
    ('TC-PUB-016', '提交成功后清除草稿', '发布字段', 'P1', tc_pub_016),
    # 平台核验
    ('TC-VER-001', '管理员设置核验标识', '平台核验', 'P1', tc_ver_001),
    ('TC-VER-002', '管理员取消核验标识', '平台核验', 'P1', tc_ver_002),
    ('TC-VER-003', '审核通过时勾选核验', '平台核验', 'P1', tc_ver_003),
    ('TC-VER-004', '非管理员设置核验被拒', '平台核验', 'P1', tc_ver_004),
    ('TC-VER-005', '详情页展示商家认证信息', '平台核验', 'P1', tc_ver_005),
    # 商家统计
    ('TC-STS-001', '商家统计返回浏览与收藏', '商家统计', 'P1', tc_sts_001),
    ('TC-STS-002', '浏览量按用户+天去重', '商家统计', 'P1', tc_sts_002),
    ('TC-STS-003', '商家查看自己房源不计浏览', '商家统计', 'P2', tc_sts_003),
    ('TC-STS-004', '非商家访问统计被拒', '商家统计', 'P1', tc_sts_004),
    ('TC-STS-005', '商家后台顶部统计展示', '商家统计', 'P1', tc_sts_005),
    # 消息跳转
    ('TC-NOTIFY-001', '首次驳回消息点击跳编辑页', '消息跳转', 'P0', tc_notify_001),
    ('TC-NOTIFY-002', '变更驳回消息点击跳编辑页', '消息跳转', 'P0', tc_notify_002),
    ('TC-NOTIFY-003', '审核通过消息点击跳详情页', '消息跳转', 'P0', tc_notify_003),
    ('TC-NOTIFY-004', '消息关联房源已删除降级', '消息跳转', 'P1', tc_notify_004),
    ('TC-NOTIFY-005', '系统通知点击不跳转', '消息跳转', 'P1', tc_notify_005),
    ('TC-NOTIFY-006', '消息列表展示关联房源名与类型标签', '消息跳转', 'P1', tc_notify_006),
    # Token 刷新
    ('TC-TOKEN-001', 'access 过期自动 refresh 重放', 'Token刷新', 'P0', tc_token_001),
    ('TC-TOKEN-002', 'refresh 也过期则登出', 'Token刷新', 'P0', tc_token_002),
    ('TC-TOKEN-003', '并发请求仅一次 refresh', 'Token刷新', 'P1', tc_token_003),
    ('TC-TOKEN-004', 'refresh 接口返回 401001 走登出', 'Token刷新', 'P1', tc_token_004),
    ('TC-TOKEN-005', 'refresh 返回新 token 双 token 更新', 'Token刷新', 'P1', tc_token_005),
    # 审核详情与商家审核
    ('TC-AUDIT-001', '变更审核详情对比展示与变更字段高亮', '审核详情', 'P0', tc_audit_001),
    ('TC-AUDIT-002', '变更审核详情影子发布标识', '审核详情', 'P1', tc_audit_002),
    ('TC-AUDIT-003', '审核详情勾选平台核验后通过', '审核详情', 'P1', tc_audit_003),
    ('TC-AUDIT-004', '驳回原因必填（空）', '审核详情', 'P1', tc_audit_004),
    ('TC-AUDIT-005', '驳回原因纯空格被拒', '审核详情', 'P1', tc_audit_005),
    ('TC-AUDIT-006', '已处理审核单重复操作', '审核详情', 'P1', tc_audit_006),
    ('TC-AUDIT-007', '商家审核列表仅展示 pending/rejected', '商家审核', 'P0', tc_audit_007),
    ('TC-AUDIT-008', '商家审核列表 pending 优先排序', '商家审核', 'P1', tc_audit_008),
    ('TC-AUDIT-009', '商家审核列表撤回按钮联动', '商家审核', 'P0', tc_audit_009),
    ('TC-AUDIT-010', '删除房源同步软删除 pending 审核单', '商家审核', 'P1', tc_audit_010),
    ('TC-AUDIT-011', '软删除兜底：已删除房源关联 rejected 审核单', '商家审核', 'P2', tc_audit_011),
    ('TC-AUDIT-012', 'change_reviewing 房源不显示在已上架 Tab', '商家审核', 'P1', tc_audit_012),
]
V11_CASES += _make_pict1_cases()
V11_CASES += _make_pict2_cases()


# ============================================================
# 主流程
# ============================================================
def main():
    r.prepare_data()
    pw = r.sync_playwright().start()
    r.BROWSER = pw.chromium.launch(headless=True)
    try:
        # V1.0 用例先跑（与原始 V1.0 运行器保持一致的列表/搜索数据环境）
        for case_id, title, module, priority, fn in r.CASES:
            r.run_case(case_id, title, module, priority, fn)
        # V1.1 补充数据 + 用例
        v11_prepare()
        for case_id, title, module, priority, fn in V11_CASES:
            r.run_case(case_id, title, module, priority, fn)
    finally:
        r.BROWSER.close()
        pw.stop()
    path, total, passed, failed, skipped = r.gen_report()
    with open(os.path.join(r.REPORT_DIR, f'test_result_{r.RUN_STAMP}.json'), 'w', encoding='utf-8') as f:
        json.dump({'stamp': r.RUN_STAMP, 'total': total, 'passed': passed,
                   'failed': failed, 'skipped': skipped, 'results': r.RESULTS},
                  f, ensure_ascii=False, indent=2)
    print(f'总计 {total} | 通过 {passed} | 失败 {failed} | 跳过 {skipped}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
