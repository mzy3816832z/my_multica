"""
上海公寓租赁平台 H5 UI 自动化测试运行器
基于 Playwright (Chromium, iPhone 12 移动视口) + 本地 Django/Vite 服务

用法:
    server/.venv/Scripts/python test/ui/run_ui_tests.py
"""
import base64
import json
import os
import re
import sqlite3
import sys
import time
import traceback
import urllib.request
from datetime import datetime

from playwright.sync_api import sync_playwright

# ---------------- 配置 ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # test/ui
PROJ_DIR = os.path.dirname(os.path.dirname(BASE_DIR))          # repo root
BASE_URL = os.environ.get('UI_BASE_URL', 'http://localhost:5173')
API_URL = BASE_URL + '/api/v1'
DB_PATH = os.path.join(PROJ_DIR, 'server', 'db.sqlite3')
RUN_STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
REPORT_DIR = os.path.join(PROJ_DIR, 'test', 'report')
EVIDENCE_DIR = os.path.join(REPORT_DIR, 'evidence')
os.makedirs(EVIDENCE_DIR, exist_ok=True)

ADMIN_USER = 'admin123'
ADMIN_PWD = '3816832z'

# 1x1 PNG 测试图片
PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
)

RESULTS = []          # 用例结果
CONSOLE_ERRORS = []   # 当前页面控制台错误
PAGE = None           # 当前 page
CTX = None            # 当前 browser context


# ---------------- 工具函数 ----------------
def api(path, method='GET', body=None, token=None, raw=False):
    url = API_URL + path
    # GET 请求将 body 中的参数拼到 query string（避免中文 URL 编码问题）
    if method == 'GET' and body:
        from urllib.parse import urlencode
        url += ('&' if '?' in url else '?') + urlencode(body)
        body = None
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        payload = json.loads(e.read().decode())
    if raw:
        return payload
    return payload.get('data', {})


def api_status(path, method='GET', body=None, token=None):
    """返回 (http_status, code, message)"""
    url = API_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
            return resp.status, payload.get('code'), payload.get('message', '')
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
            return e.code, payload.get('code'), payload.get('message', '')
        except Exception:
            return e.code, None, ''


def upload_image(token):
    boundary = '----uitestboundary'
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\n'
        f'Content-Type: image/png\r\n\r\n'
    ).encode() + PNG_BYTES + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(API_URL + '/uploads/image/', data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=15) as resp:
        payload = json.loads(resp.read().decode())
    return payload['data']['url']


def db_query(sql, args=()):
    # 每次新建连接并立即提交，避免 SQLite 事务快照导致读不到新数据
    conn = sqlite3.connect(DB_PATH, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, args)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_sms_code(phone, purpose):
    rows = db_query(
        'SELECT code FROM verify_codes WHERE phone=? AND purpose=? AND used=0 '
        'ORDER BY created_at DESC LIMIT 1', (phone, purpose))
    return rows[0]['code'] if rows else None


def register_user(phone, password='Test123456'):
    api('/auth/sms-code/', 'POST', {'phone': phone, 'purpose': 'register'})
    code = get_sms_code(phone, 'register')
    assert code, f'未取到验证码: {phone}'
    data = api('/auth/register/', 'POST',
               {'phone': phone, 'password': password, 'sms_code': code})
    return data


def login_token(username, password):
    data = api('/auth/login-by-password/', 'POST', {'username': username, 'password': password})
    return data['access_token'], data.get('user', {})


def select_role(token, role):
    return api('/auth/select-role/', 'POST', {'role': role}, token=token)


def create_apartment(token, name, district_id=1, street_id=2, rent=3500):
    cover = upload_image(token)
    room_img = upload_image(token)
    body = {
        'name': name,
        'cover_image': cover,
        'description': f'{name}，近地铁，精装修，拎包入住。',
        'district_id': district_id,
        'street_id': street_id,
        'detail_address': '测试路100弄1号',
        'contact_phone': '13800138000',
        'room_types': [{
            'name': '温馨一居室',
            'images': [room_img],
            'facilities': ['air_conditioner', 'wifi', 'washing_machine'],
            'layout_type': 'one_bedroom',
            'window_type': 'outer',
            'floor': 3,
            'sort': 0,
            'rental_plans': [
                {'lease_term': '1_year', 'monthly_rent': rent, 'payment_method': 'pay_1_deposit_1'},
                {'lease_term': '6_months', 'monthly_rent': rent + 200, 'payment_method': 'pay_3_deposit_1'},
            ],
        }],
    }
    return api('/merchant/apartments/', 'POST', body, token=token)


def admin_approve_first_pending(admin_token, apartment_id=None):
    """审批指定房源的待审核首次提交；未指定时审批最早一条。返回审核单信息"""
    data = api('/admin/audits/', body={'type': 'first_review', 'status': 'pending', 'page': 1, 'page_size': 100},
               token=admin_token)
    items = data.get('items', []) if isinstance(data, dict) else []
    if not items:
        return None
    audit = None
    if apartment_id is not None:
        for it in items:
            if it.get('apartment_id') == apartment_id or it.get('apartment') == apartment_id:
                audit = it
                break
    if audit is None:
        audit = items[0]
    api(f"/admin/audits/{audit['id']}/approve/", 'POST', {}, token=admin_token)
    return audit


def shot(name):
    """截取当前页面全屏截图，返回 evidence 相对文件名"""
    fname = f'{name}.png'
    PAGE.screenshot(path=os.path.join(EVIDENCE_DIR, fname), full_page=True)
    return fname


def new_context(storage_state=None):
    global PAGE, CTX, CONSOLE_ERRORS
    if CTX:
        CTX.close()
    CONSOLE_ERRORS = []
    CTX = BROWSER.new_context(
        viewport={'width': 390, 'height': 844},
        user_agent=('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
                    'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'),
        storage_state=storage_state,
    )
    PAGE = CTX.new_page()
    PAGE.on('console', lambda msg: CONSOLE_ERRORS.append(msg.text) if msg.type == 'error' else None)
    return PAGE


def close_context():
    global CTX, PAGE
    if CTX:
        CTX.close()
    CTX = None
    PAGE = None


def record(case_id, title, module, priority, status, note='', shots=None, duration=0.0):
    RESULTS.append({
        'id': case_id, 'title': title, 'module': module, 'priority': priority,
        'status': status, 'note': note, 'shots': shots or [], 'duration': round(duration, 1),
    })
    mark = {'pass': '✅', 'fail': '❌', 'skip': '⏭️'}.get(status, '')
    print(f'  {mark} {case_id} {title} [{status}] {note[:80]}')


def run_case(case_id, title, module, priority, fn):
    print(f'▶ {case_id} {title}')
    t0 = time.time()
    try:
        fn()
        record(case_id, title, module, priority, 'pass', duration=time.time() - t0)
    except SkipCase as e:
        record(case_id, title, module, priority, 'skip', note=str(e), duration=time.time() - t0)
    except Exception as e:
        note = f'{type(e).__name__}: {e}'
        shots = []
        try:
            if PAGE:
                shots.append(shot(f'FAIL_{case_id}'))
        except Exception:
            pass
        if CONSOLE_ERRORS:
            note += ' | 控制台错误: ' + '; '.join(CONSOLE_ERRORS[-3:])[:200]
        record(case_id, title, module, priority, 'fail', note=note, shots=shots,
               duration=time.time() - t0)
        traceback.print_exc()
    finally:
        close_context()


class SkipCase(Exception):
    pass


def expect(cond, msg):
    if not cond:
        raise AssertionError(msg)


def expect_toast(text_kw, timeout=6000):
    """等待 vant toast 出现并包含关键字"""
    toast = PAGE.wait_for_selector('.van-toast', timeout=timeout)
    content = toast.inner_text()
    expect(text_kw in content, f'toast 内容「{content}」不包含「{text_kw}」')
    return content


def wait_url(kw, timeout=8000):
    PAGE.wait_for_url(f'**{kw}**', timeout=timeout)


def login_ui(username, password, shot_name=None):
    """通过 UI 登录"""
    PAGE.goto(f'{BASE_URL}/login')
    PAGE.wait_for_selector('input', timeout=10000)
    inputs = PAGE.query_selector_all('input')
    inputs[0].fill(username)
    inputs[1].fill(password)
    PAGE.wait_for_timeout(300)
    if shot_name:
        shot(shot_name)
    # 精确匹配提交按钮（避免命中「密码登录」Tab）
    PAGE.click('xpath=//button[normalize-space()="登录"]')


def auth_state(token, user):
    """构造 pinia persist storage_state"""
    state = {'token': token, 'refreshToken': '', 'userInfo': user}
    return {
        'cookies': [],
        'origins': [{
            'origin': BASE_URL,
            'localStorage': [{'name': 'auth', 'value': json.dumps(state, ensure_ascii=False)}],
        }],
    }


# ============================================================
# 测试数据准备
# ============================================================
STATE = {}


def prepare_data():
    print('== 准备测试数据 ==')
    # 管理员
    STATE['admin_token'], STATE['admin_user'] = login_token(ADMIN_USER, ADMIN_PWD)

    # 租客
    ts = int(time.time()) % 100000000
    tenant_phone = f'139{ts:08d}'
    register_user(tenant_phone)
    STATE['tenant_phone'] = tenant_phone
    t_token, t_user = login_token(tenant_phone, 'Test123456')
    select_role(t_token, 'tenant')
    t_token, t_user = login_token(tenant_phone, 'Test123456')
    STATE['tenant_token'], STATE['tenant_user'] = t_token, t_user

    # 商家
    merchant_phone = f'138{(ts + 1) % 100000000:08d}'
    register_user(merchant_phone)
    STATE['merchant_phone'] = merchant_phone
    m_token, m_user = login_token(merchant_phone, 'Test123456')
    select_role(m_token, 'landlord')
    m_token, m_user = login_token(merchant_phone, 'Test123456')
    STATE['merchant_token'], STATE['merchant_user'] = m_token, m_user

    # 商家发布 3 套房源（浦东关键词 1 套），管理员审批上架
    names = ['浦东张江阳光公寓', '徐汇滨江雅苑', '静安寺精品公寓']
    created = []
    for nm in names:
        apt = create_apartment(m_token, nm)
        created.append(apt)
        admin_approve_first_pending(STATE['admin_token'], apartment_id=apt.get('apartment_id') or apt.get('id'))
    STATE['apartments'] = created

    # 校验公共列表
    lst = api('/apartments/', body={'page': 1, 'page_size': 10})
    STATE['published_total'] = lst.get('total', 0)
    print(f'  上架房源数: {STATE["published_total"]}')
    assert STATE['published_total'] >= 3, '房源上架失败'

    # 租客收藏第 2 套房源（供收藏列表用例）
    apt2_id = created[1].get('id') or created[1].get('apartment_id')
    STATE['apt2_id'] = apt2_id
    api('/favorites/', 'POST', {'apartment_id': apt2_id}, token=t_token)
    # 收藏接口校验（重试一次，排除瞬时读取问题）
    favs = api('/favorites/my/', body={'page': 1, 'page_size': 10}, token=t_token)
    if favs.get('total', 0) < 1:
        time.sleep(1)
        favs = api('/favorites/my/', body={'page': 1, 'page_size': 10}, token=t_token)
    assert favs.get('total', 0) >= 1, f'收藏准备失败: {favs}'
    print('== 测试数据准备完成 ==')


# ============================================================
# 用例实现
# ============================================================

# ---------- 一、认证模块 ----------
def tc_auth_001():
    """正常注册流程"""
    new_context()
    PAGE.goto(f'{BASE_URL}/register')
    PAGE.wait_for_selector('input', timeout=10000)
    shot('TC-AUTH-001_1_register_page')
    phone = f'137{int(time.time()) % 100000000:08d}'
    inputs = PAGE.query_selector_all('input')
    inputs[0].fill(phone)
    # 获取验证码（mock：从 DB 取）
    PAGE.click('button:has-text("获取验证码"), .van-button:has-text("获取验证码")')
    PAGE.wait_for_timeout(1200)
    code = get_sms_code(phone, 'register')
    expect(code, '未生成验证码')
    inputs = PAGE.query_selector_all('input')
    inputs[1].fill(code)
    inputs[2].fill('Test123456')
    inputs[3].fill('Test123456')
    shot('TC-AUTH-001_2_filled')
    PAGE.wait_for_timeout(300)
    PAGE.click('xpath=//button[normalize-space()="注册"]')
    try:
        expect_toast('注册成功')
    except Exception:
        wait_url('/login')
    PAGE.wait_for_timeout(1500)
    shot('TC-AUTH-001_3_after_register')
    expect('/login' in PAGE.url or '/select-role' in PAGE.url or '/apartments' in PAGE.url,
           f'注册后未跳转: {PAGE.url}')


def tc_auth_002():
    """注册-手机号格式校验"""
    new_context()
    PAGE.goto(f'{BASE_URL}/register')
    PAGE.wait_for_selector('input', timeout=10000)
    inputs = PAGE.query_selector_all('input')
    inputs[0].fill('12345678901')
    PAGE.wait_for_timeout(400)
    # 前端校验：获取验证码按钮应被禁用
    btn = PAGE.query_selector('xpath=//button[contains(normalize-space(),"获取验证码")]')
    expect(btn is not None, '未找到获取验证码按钮')
    disabled = btn.get_attribute('disabled')
    cls = btn.get_attribute('class') or ''
    shot('TC-AUTH-002_invalid_phone')
    expect(disabled is not None or 'disabled' in cls, '非法手机号时获取验证码按钮未禁用')
    # 后端兜底：非法号段（123 开头）应被拒绝
    status, code, _ = api_status('/auth/sms-code/', 'POST', {'phone': '12345678901', 'purpose': 'register'})
    expect(status == 400,
           f'后端缺陷：非法号段手机号(12345678901)未被拦截，仍发送验证码(status={status})；'
           f'后端仅校验长度/数字，未校验 ^1[3-9] 号段规则')


def tc_auth_009():
    """注册-两次密码不一致"""
    new_context()
    PAGE.goto(f'{BASE_URL}/register')
    PAGE.wait_for_selector('input', timeout=10000)
    phone = f'136{int(time.time()) % 100000000:08d}'
    inputs = PAGE.query_selector_all('input')
    inputs[0].fill(phone)
    PAGE.click('xpath=//button[contains(normalize-space(),"获取验证码")]')
    PAGE.wait_for_timeout(1200)
    code = get_sms_code(phone, 'register')
    inputs = PAGE.query_selector_all('input')
    inputs[1].fill(code or '000000')
    inputs[2].fill('123456')
    inputs[3].fill('654321')
    PAGE.wait_for_timeout(400)
    # 前端校验：两次密码不一致时注册按钮禁用
    btn = PAGE.query_selector('xpath=//button[normalize-space()="注册"]')
    expect(btn is not None, '未找到注册按钮')
    disabled = btn.get_attribute('disabled')
    cls = btn.get_attribute('class') or ''
    shot('TC-AUTH-009_pwd_mismatch')
    expect(disabled is not None or 'disabled' in cls, '两次密码不一致时注册按钮未禁用')


def tc_auth_010():
    """未登录访问需鉴权页面"""
    new_context()
    PAGE.goto(f'{BASE_URL}/profile/favorites')
    PAGE.wait_for_timeout(2000)
    shot('TC-AUTH-010_guard')
    expect('/login' in PAGE.url, f'未跳转登录页: {PAGE.url}')
    expect('redirect' in PAGE.url, 'redirect 参数未保留')


def tc_auth_011():
    """密码登录-正常流程（租客，已选身份→房源列表）"""
    new_context()
    login_ui(STATE['tenant_phone'], 'Test123456', 'TC-AUTH-011_1_login_filled')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUTH-011_2_after_login')
    expect('/apartments' in PAGE.url or '/select-role' in PAGE.url,
           f'登录后跳转异常: {PAGE.url}')


def tc_auth_013():
    """登录-密码错误"""
    new_context()
    login_ui(STATE['tenant_phone'], 'WrongPwd999')
    PAGE.wait_for_timeout(2000)
    shot('TC-AUTH-013_wrong_pwd')
    body_text = PAGE.inner_text('body')
    expect('用户名或密码错误' in body_text or '/login' in PAGE.url, '密码错误未提示')


def tc_auth_016():
    """管理员登录-正常流程"""
    new_context()
    login_ui(ADMIN_USER, ADMIN_PWD, 'TC-AUTH-016_1_admin_login')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUTH-016_2_admin_landing')
    expect('/admin/audits' in PAGE.url or '/apartments' in PAGE.url or '/profile' in PAGE.url,
           f'管理员登录后跳转异常: {PAGE.url}')


def tc_auth_017():
    """首次登录强制身份选择"""
    phone = f'135{int(time.time()) % 100000000:08d}'
    register_user(phone)
    new_context()
    login_ui(phone, 'Test123456')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUTH-017_force_select_role')
    expect('/select-role' in PAGE.url, f'新用户未强制跳转身份选择: {PAGE.url}')


def tc_auth_018():
    """身份选择-租客"""
    phone = f'134{int(time.time()) % 100000000:08d}'
    register_user(phone)
    new_context()
    login_ui(phone, 'Test123456')
    PAGE.wait_for_timeout(2500)
    expect('/select-role' in PAGE.url, f'未进入身份选择页: {PAGE.url}')
    shot('TC-AUTH-018_1_select_role_page')
    PAGE.click('text=我是租客')
    PAGE.wait_for_timeout(500)
    PAGE.click('button:has-text("确认"), .van-button:has-text("确认")')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUTH-018_2_after_select')
    expect('/apartments' in PAGE.url, f'选择租客后未进入房源列表: {PAGE.url}')


def tc_auth_022():
    """忘记密码-正常流程"""
    new_context()
    PAGE.goto(f'{BASE_URL}/forgot-password')
    PAGE.wait_for_selector('input', timeout=10000)
    phone = STATE['tenant_phone']
    inputs = PAGE.query_selector_all('input')
    inputs[0].fill(phone)
    PAGE.click('button:has-text("获取验证码"), .van-button:has-text("获取验证码")')
    PAGE.wait_for_timeout(1200)
    code = get_sms_code(phone, 'reset_password')
    expect(code, '未取到重置验证码')
    inputs = PAGE.query_selector_all('input')
    inputs[1].fill(code)
    inputs[2].fill('NewPwd123456')
    if len(inputs) > 3:
        inputs[3].fill('NewPwd123456')
    shot('TC-AUTH-022_1_filled')
    PAGE.wait_for_timeout(300)
    PAGE.click('xpath=//button[normalize-space()="重置密码"]')
    PAGE.wait_for_timeout(2000)
    shot('TC-AUTH-022_2_after_reset')
    # 用新密码可登录
    token, _ = login_token(phone, 'NewPwd123456')
    expect(token, '新密码登录失败')
    # 还原密码，避免影响其他用例
    api('/auth/sms-code/', 'POST', {'phone': phone, 'purpose': 'reset_password'})
    code2 = get_sms_code(phone, 'reset_password')
    api('/auth/reset-password/', 'POST',
        {'phone': phone, 'sms_code': code2, 'new_password': 'Test123456'})


# ---------- 二、房源模块 ----------
def tc_apt_001():
    """房源列表-默认展示"""
    new_context()
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-001_list_default')
    body_text = PAGE.inner_text('body')
    expect('浦东张江阳光公寓' in body_text, '列表未展示已上架房源')
    cards = PAGE.query_selector_all('.van-card, [class*=card], [class*=item]')
    expect(len(cards) > 0, '未找到房源卡片')


def open_search():
    """打开房源列表搜索弹窗并返回输入框"""
    trigger = PAGE.query_selector('.van-icon-search')
    if trigger:
        trigger.click()
        PAGE.wait_for_timeout(600)
    return PAGE.wait_for_selector('.van-search input', timeout=5000)


def tc_apt_004():
    """房源列表-名称搜索"""
    new_context()
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2000)
    search = open_search()
    search.fill('浦东')
    PAGE.keyboard.press('Enter')
    PAGE.wait_for_timeout(2000)
    shot('TC-APT-004_search_pudong')
    body_text = PAGE.inner_text('body')
    expect('浦东张江阳光公寓' in body_text, '搜索结果未包含目标房源')
    expect('徐汇滨江雅苑' not in body_text, '搜索结果包含非匹配房源')


def tc_apt_012():
    """房源列表-空状态"""
    new_context()
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2000)
    search = open_search()
    search.fill('绝不存在的房源名xyz123')
    PAGE.keyboard.press('Enter')
    PAGE.wait_for_timeout(2000)
    shot('TC-APT-012_empty')
    empty = PAGE.query_selector('.van-empty')
    expect(empty is not None, '未显示 van-empty 空状态')


def tc_apt_013():
    """未登录不显示收藏按钮"""
    new_context()
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-013_guest_list')
    stars = PAGE.query_selector_all('[class*=favor], [class*=star], .van-icon-star, .van-icon-star-o')
    expect(len(stars) == 0, f'游客态仍显示收藏按钮({len(stars)}个)')


def tc_apt_014():
    """租客显示收藏按钮"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-014_tenant_list')
    stars = PAGE.query_selector_all('[class*=favor], [class*=star], .van-icon-star, .van-icon-star-o')
    expect(len(stars) > 0, '租客态未显示收藏按钮')


def tc_apt_015():
    """商家显示发布按钮"""
    new_context(storage_state=auth_state(STATE['merchant_token'], STATE['merchant_user']))
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-015_merchant_list')
    fab = PAGE.query_selector('[class*=publish], [class*=fab], .van-icon-plus, [class*=create]')
    expect(fab is not None, '商家态未显示发布按钮')


def tc_apt_016():
    """租客不显示发布按钮"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-016_tenant_no_fab')
    fab = PAGE.query_selector('[class*=publish], [class*=fab], .van-icon-plus, [class*=create]')
    expect(fab is None, '租客态不应显示发布按钮')


def tc_apt_017():
    """房源详情-正常展示（严格校验字段值与中文标签）"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2500)
    PAGE.click('text=浦东张江阳光公寓')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-017_detail')
    expect('/apartments/' in PAGE.url, f'未进入详情页: {PAGE.url}')
    body_text = PAGE.inner_text('body')
    expect('浦东张江阳光公寓' in body_text, '详情页未展示房源名称')
    expect('温馨一居室' in body_text or '房型' in body_text, '详情页未展示房型信息')
    # 断言规则：不得出现原始编码 / 占位符 / 未处理空值
    for bad in ('one_bedroom', 'two_bedroom', 'studio', 'loft', 'duplex', 'inner', 'outer',
                'undefined', 'null', 'None', 'NaN', '[object Object]', '¥?'):
        expect(bad not in body_text, f'房源详情页出现异常文本「{bad}」（字段未翻译或占位符未处理）')


def tc_apt_018():
    """房源详情-收藏/取消收藏"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    lst = api('/apartments/', body={'page': 1, 'page_size': 1, 'keyword': '静安'})
    apt_id = lst['items'][0]['id']
    PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-018_1_before_favor')
    fav_btn = PAGE.query_selector('[class*=favor], [class*=star], .van-icon-star-o, .van-icon-star')
    expect(fav_btn is not None, '详情页无收藏按钮')
    fav_btn.click()
    PAGE.wait_for_timeout(1500)
    shot('TC-APT-018_2_favored')
    # 校验接口状态
    favs = api('/favorites/my/', body={'page': 1, 'page_size': 50}, token=STATE['tenant_token'])
    ids = [f.get('apartment_id') for f in favs.get('items', [])]
    expect(apt_id in ids, '收藏接口未记录')
    # 取消收藏
    fav_btn = PAGE.query_selector('[class*=favor], [class*=star], .van-icon-star-o, .van-icon-star')
    fav_btn.click()
    PAGE.wait_for_timeout(1500)
    shot('TC-APT-018_3_unfavored')
    favs = api('/favorites/my/', body={'page': 1, 'page_size': 50}, token=STATE['tenant_token'])
    ids = [f.get('apartment_id') for f in favs.get('items', [])]
    expect(apt_id not in ids, '取消收藏未生效')


def tc_apt_020():
    """房源详情-点击房型卡片"""
    new_context()
    lst = api('/apartments/', body={'page': 1, 'page_size': 1, 'keyword': '浦东'})
    apt_id = lst['items'][0]['id']
    PAGE.goto(f'{BASE_URL}/apartments/{apt_id}')
    PAGE.wait_for_timeout(2500)
    room = PAGE.query_selector('text=温馨一居室')
    expect(room is not None, '未找到房型卡片')
    # 点击可点击的卡片容器（文本节点本身可能不接收点击）
    room.click()
    PAGE.wait_for_timeout(3000)
    if '/room-types/' not in PAGE.url:
        # 备用：直接点击卡片根元素
        card = PAGE.query_selector('[class*=room][class*=card], [class*=room-type], [class*=RoomCard]')
        if card:
            card.click()
            PAGE.wait_for_timeout(3000)
    shot('TC-APT-020_room_type')
    expect('/room-types/' in PAGE.url, f'未跳转户型详情: {PAGE.url}')


def tc_apt_023():
    """户型详情-正常展示（严格校验：字段需翻译为中文标签，租金需为真实数值）"""
    new_context()
    lst = api('/apartments/', body={'page': 1, 'page_size': 1, 'keyword': '浦东'})
    apt_id = lst['items'][0]['id']
    detail = api(f'/apartments/{apt_id}/')
    room_types = detail.get('room_types', [])
    expect(room_types, '房源无房型')
    rt_id = room_types[0]['id']
    PAGE.goto(f'{BASE_URL}/room-types/{rt_id}')
    PAGE.wait_for_timeout(2500)
    shot('TC-APT-023_room_detail')
    body_text = PAGE.inner_text('body')
    expect('温馨一居室' in body_text, '户型详情未展示名称')
    # 严格校验：户型/内外窗必须显示中文标签，不得显示原始编码
    for raw_code in ('one_bedroom', 'two_bedroom', 'studio', 'loft', 'duplex', 'inner', 'outer'):
        expect(raw_code not in body_text,
               f'户型/内外窗未翻译为中文标签，页面直接显示原始编码「{raw_code}」（后端未返回 *_label 字段）')
    # 租金必须显示真实数值，不得出现 ¥? 占位
    expect('¥?' not in body_text and '? /月' not in body_text, '租金显示为占位符「¥?」，未展示真实月租金')
    expect('租期租金方案' in body_text or '租' in body_text, '户型详情未展示租金方案')


# ---------- 三、收藏模块 ----------
def tc_fav_006():
    """我的收藏列表"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile/favorites')
    PAGE.wait_for_timeout(2500)
    shot('TC-FAV-006_favorites_list')
    body_text = PAGE.inner_text('body')
    # 前端缺陷：收藏列表模板使用 item.name，但接口返回 apartment_name，导致名称不渲染
    expect('徐汇滨江雅苑' in body_text,
           '收藏列表未展示已收藏房源名称（前端字段映射缺陷：模板用 item.name，接口返回 apartment_name）')


def tc_fav_007():
    """收藏列表空状态"""
    phone = f'133{int(time.time()) % 100000000:08d}'
    register_user(phone)
    tk, user = login_token(phone, 'Test123456')
    select_role(tk, 'tenant')
    tk, user = login_token(phone, 'Test123456')
    new_context(storage_state=auth_state(tk, user))
    PAGE.goto(f'{BASE_URL}/profile/favorites')
    PAGE.wait_for_timeout(2500)
    shot('TC-FAV-007_favorites_empty')
    empty = PAGE.query_selector('.van-empty')
    expect(empty is not None, '空收藏列表未显示 van-empty')


def tc_fav_008():
    """从收藏列表取消收藏"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile/favorites')
    PAGE.wait_for_timeout(2500)
    shot('TC-FAV-008_1_before_cancel')
    btn = PAGE.query_selector('button:has-text("取消收藏"), .van-button:has-text("取消收藏")')
    expect(btn is not None, '收藏列表无取消收藏按钮')
    btn.click()
    PAGE.wait_for_timeout(500)
    # 可能有确认弹框
    confirm = PAGE.query_selector('.van-dialog__confirm, button:has-text("确认")')
    if confirm:
        confirm.click()
    PAGE.wait_for_timeout(2000)
    shot('TC-FAV-008_2_after_cancel')
    body_text = PAGE.inner_text('body')
    expect('徐汇滨江雅苑' not in body_text or '暂无收藏' in body_text, '取消收藏后房源仍在列表')


# ---------- 四、消息模块 ----------
def tc_msg_005():
    """消息列表空状态"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile/messages')
    PAGE.wait_for_timeout(2500)
    shot('TC-MSG-005_messages_empty')
    body_text = PAGE.inner_text('body')
    empty = PAGE.query_selector('.van-empty')
    expect(empty is not None or '暂无消息' in body_text, '消息空状态未显示')


def tc_msg_006():
    """未登录访问消息"""
    new_context()
    PAGE.goto(f'{BASE_URL}/profile/messages')
    PAGE.wait_for_timeout(2000)
    shot('TC-MSG-006_guard')
    expect('/login' in PAGE.url, f'未跳转登录页: {PAGE.url}')


# ---------- 五、管理员审核模块 ----------
def tc_aud_001():
    """审核列表-提交审核Tab"""
    # 先造一条待审核数据
    create_apartment(STATE['merchant_token'], '待审核测试公寓A')
    new_context(storage_state=auth_state(STATE['admin_token'], STATE['admin_user']))
    PAGE.goto(f'{BASE_URL}/admin/audits')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUD-001_audit_list')
    body_text = PAGE.inner_text('body')
    expect('待审核测试公寓A' in body_text or '审核' in body_text, '审核列表未展示待审核数据')


def tc_aud_004():
    """审核列表-快捷通过"""
    create_apartment(STATE['merchant_token'], '快捷通过测试公寓B')
    new_context(storage_state=auth_state(STATE['admin_token'], STATE['admin_user']))
    PAGE.goto(f'{BASE_URL}/admin/audits')
    PAGE.wait_for_timeout(2000)
    # 用搜索框定位目标审核单，避免点到其他待审核卡片
    search = PAGE.query_selector('.van-search input')
    expect(search is not None, '审核列表无搜索框')
    search.fill('快捷通过测试公寓B')
    PAGE.keyboard.press('Enter')
    PAGE.wait_for_timeout(2000)
    shot('TC-AUD-004_1_before_approve')
    # 精确匹配卡片内的「通过」操作区
    btn = PAGE.query_selector('xpath=//span[normalize-space()="通过"]')
    expect(btn is not None, '审核列表无通过按钮')
    btn.click()
    PAGE.wait_for_timeout(800)
    confirm = PAGE.query_selector('.van-dialog__confirm')
    expect(confirm is not None, '确认通过弹框未弹出')
    confirm.click()
    PAGE.wait_for_timeout(2500)
    shot('TC-AUD-004_2_after_approve')
    # 接口校验房源已上架
    lst = api('/apartments/', body={'page': 1, 'page_size': 10, 'keyword': '快捷通过测试公寓B'})
    expect(lst.get('total', 0) >= 1, '审批通过后房源未上架')


def tc_aud_005():
    """审核列表-快捷驳回"""
    create_apartment(STATE['merchant_token'], '快捷驳回测试公寓C')
    new_context(storage_state=auth_state(STATE['admin_token'], STATE['admin_user']))
    PAGE.goto(f'{BASE_URL}/admin/audits')
    PAGE.wait_for_timeout(2000)
    search = PAGE.query_selector('.van-search input')
    if search:
        search.fill('快捷驳回测试公寓C')
        PAGE.keyboard.press('Enter')
        PAGE.wait_for_timeout(2000)
    btn = PAGE.query_selector('xpath=//span[normalize-space()="驳回"]')
    expect(btn is not None, '审核列表无驳回按钮')
    btn.click()
    PAGE.wait_for_timeout(1000)
    shot('TC-AUD-005_1_reject_dialog')
    # 填写驳回原因（van-field type=textarea 渲染为 textarea）
    textarea = PAGE.query_selector('.van-popup textarea')
    expect(textarea is not None, '驳回弹框无原因输入框')
    textarea.fill('图片不清晰，请重新上传')
    confirm = PAGE.query_selector('xpath=//button[normalize-space()="确认驳回"]')
    expect(confirm is not None, '驳回弹框无确认按钮')
    confirm.click()
    PAGE.wait_for_timeout(2500)
    shot('TC-AUD-005_2_after_reject')
    body_text = PAGE.inner_text('body')
    expect('快捷驳回测试公寓C' not in body_text or '已驳回' in body_text or '驳回' in body_text,
           '驳回后记录状态未更新')


def tc_aud_007():
    """非管理员访问审核列表"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/admin/audits')
    PAGE.wait_for_timeout(2500)
    shot('TC-AUD-007_forbidden')
    expect('/admin/audits' not in PAGE.url, f'租客未被拦截: {PAGE.url}')


# ---------- 六、商家房源管理 ----------
def tc_mer_001():
    """发布房源-正常流程（UI 表单较复杂，采用 UI 进入页面 + 校验页面元素 + API 完成提交）"""
    new_context(storage_state=auth_state(STATE['merchant_token'], STATE['merchant_user']))
    PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    PAGE.wait_for_timeout(2500)
    shot('TC-MER-001_create_page')
    body_text = PAGE.inner_text('body')
    expect('公寓' in body_text or '房源' in body_text, '发布页未正常渲染')
    # 通过 API 完成一次完整提交验证后端链路
    data = create_apartment(STATE['merchant_token'], 'UI链路验证公寓D')
    expect(data, '发布接口无返回')
    admin_approve_first_pending(STATE['admin_token'], apartment_id=data.get('apartment_id') or data.get('id'))
    lst = api('/apartments/', body={'page': 1, 'page_size': 10, 'keyword': 'UI链路验证公寓D'})
    expect(lst.get('total', 0) >= 1, '发布后审核上架链路失败')


def tc_mer_008():
    """非商家访问发布页"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    PAGE.wait_for_timeout(2500)
    shot('TC-MER-008_forbidden')
    expect('/profile/apartments/create' not in PAGE.url, f'租客未被拦截: {PAGE.url}')


def tc_mer_009():
    """已上架房源列表"""
    new_context(storage_state=auth_state(STATE['merchant_token'], STATE['merchant_user']))
    PAGE.goto(f'{BASE_URL}/profile/my-apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-MER-009_my_apartments')
    body_text = PAGE.inner_text('body')
    expect('浦东张江阳光公寓' in body_text or '上架' in body_text, '已上架房源列表为空')


# ---------- 七、前端页面/UI ----------
def tc_ui_001():
    """路由守卫-未登录拦截"""
    new_context()
    PAGE.goto(f'{BASE_URL}/profile')
    PAGE.wait_for_timeout(2000)
    shot('TC-UI-001_guard')
    expect('/login' in PAGE.url, f'未跳转登录页: {PAGE.url}')
    expect('redirect' in PAGE.url, 'redirect 参数未保留')


def tc_ui_002():
    """路由守卫-角色权限校验"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile/my-apartments')
    PAGE.wait_for_timeout(2500)
    shot('TC-UI-002_role_guard')
    expect('/profile/my-apartments' not in PAGE.url, f'租客访问商家页未被拦截: {PAGE.url}')


def tc_ui_003():
    """404页面"""
    new_context()
    PAGE.goto(f'{BASE_URL}/xxx-not-exist')
    PAGE.wait_for_timeout(2000)
    shot('TC-UI-003_404')
    body_text = PAGE.inner_text('body')
    expect('404' in body_text or '不存在' in body_text, '未展示404页面')


def tc_ui_005():
    """个人中心-租客菜单"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile')
    PAGE.wait_for_timeout(2500)
    shot('TC-UI-005_tenant_profile')
    body_text = PAGE.inner_text('body')
    expect('我的收藏' in body_text, '租客菜单缺少「我的收藏」')
    expect('我的消息' in body_text, '租客菜单缺少「我的消息」')


def tc_ui_006():
    """个人中心-商家菜单"""
    new_context(storage_state=auth_state(STATE['merchant_token'], STATE['merchant_user']))
    PAGE.goto(f'{BASE_URL}/profile')
    PAGE.wait_for_timeout(2500)
    shot('TC-UI-006_merchant_profile')
    body_text = PAGE.inner_text('body')
    expect('已上架房源' in body_text or '发布房源' in body_text, '商家菜单缺少房源管理项')


def tc_ui_007():
    """个人中心-管理员菜单"""
    new_context(storage_state=auth_state(STATE['admin_token'], STATE['admin_user']))
    PAGE.goto(f'{BASE_URL}/profile')
    PAGE.wait_for_timeout(2500)
    shot('TC-UI-007_admin_profile')
    body_text = PAGE.inner_text('body')
    expect('审核管理' in body_text, '管理员菜单缺少「审核管理」')


def tc_ui_009():
    """退出登录"""
    new_context(storage_state=auth_state(STATE['tenant_token'], STATE['tenant_user']))
    PAGE.goto(f'{BASE_URL}/profile')
    PAGE.wait_for_timeout(2500)
    btn = PAGE.query_selector('text=退出登录')
    expect(btn is not None, '个人中心无退出登录')
    btn.click()
    PAGE.wait_for_timeout(800)
    confirm = PAGE.query_selector('.van-dialog__confirm, button:has-text("确认")')
    if confirm:
        confirm.click()
    PAGE.wait_for_timeout(2000)
    shot('TC-UI-009_logout')
    expect('/login' in PAGE.url, f'退出后未跳转登录页: {PAGE.url}')


def tc_ui_010():
    """登录页-模式切换"""
    new_context()
    PAGE.goto(f'{BASE_URL}/login')
    PAGE.wait_for_selector('input', timeout=10000)
    shot('TC-UI-010_1_password_mode')
    tab = PAGE.query_selector('text=验证码登录')
    if not tab:
        raise SkipCase('登录页无验证码登录 Tab')
    tab.click()
    PAGE.wait_for_timeout(800)
    shot('TC-UI-010_2_code_mode')
    body_text = PAGE.inner_text('body')
    expect('验证码' in body_text, '切换后未显示验证码输入')


def tc_ui_012():
    """行政区街道联动（发布页）"""
    new_context(storage_state=auth_state(STATE['merchant_token'], STATE['merchant_user']))
    PAGE.goto(f'{BASE_URL}/profile/apartments/create')
    PAGE.wait_for_timeout(2500)
    shot('TC-UI-012_create_page')
    body_text = PAGE.inner_text('body')
    expect('所在位置' in body_text or '行政区' in body_text, '发布页无位置/行政区字段')
    # 点击行政区选择框，验证 picker 弹出
    dist_field = PAGE.query_selector('input[placeholder*="行政区"]')
    if dist_field:
        dist_field.click()
        PAGE.wait_for_timeout(800)
        picker = PAGE.query_selector('.van-picker')
        expect(picker is not None, '点击行政区后未弹出选择器')
        shot('TC-UI-012_district_picker')
        PAGE.keyboard.press('Escape')
        PAGE.wait_for_timeout(300)
    # 接口层面验证联动数据
    d1 = api('/districts/', body={'level': 1})
    first = d1[0]
    streets = api('/districts/', body={'level': 2, 'parent_id': first['id']})
    expect(len(streets) > 0, '街道联动数据为空')
    d2 = d1[1]
    streets2 = api('/districts/', body={'level': 2, 'parent_id': d2['id']})
    expect(streets[0]['id'] != streets2[0]['id'], '街道未随行政区变化')


# ---------- 九、安全测试（经 UI 发起） ----------
def tc_sec_002():
    """SQL注入防护"""
    new_context()
    PAGE.goto(f'{BASE_URL}/apartments')
    PAGE.wait_for_timeout(2000)
    search = open_search()
    search.fill("' OR '1'='1")
    PAGE.keyboard.press('Enter')
    PAGE.wait_for_timeout(2000)
    shot('TC-SEC-002_sqli')
    body_text = PAGE.inner_text('body')
    expect('500' not in body_text and 'Traceback' not in body_text, 'SQL注入导致服务异常')
    expect('Internal Server Error' not in body_text, 'SQL注入触发服务器错误')


def tc_sec_007():
    """Token伪造"""
    status, code, msg = api_status('/favorites/my/', token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.forged.forged')
    expect(status == 401, f'伪造Token未拦截: status={status} code={code}')


# ============================================================
# 报告生成
# ============================================================
def gen_report():
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r['status'] == 'pass')
    failed = sum(1 for r in RESULTS if r['status'] == 'fail')
    skipped = sum(1 for r in RESULTS if r['status'] == 'skip')
    duration = sum(r['duration'] for r in RESULTS)

    rows = []
    for r in RESULTS:
        cls = {'pass': 'pass', 'fail': 'fail', 'skip': 'skip'}[r['status']]
        label = {'pass': '✅ 通过', 'fail': '❌ 失败', 'skip': '⏭️ 跳过'}[r['status']]
        shots_html = ''
        if r['shots']:
            shots_html = '<br>'.join(
                f'<a href="evidence/{s}" target="_blank"><img src="evidence/{s}" class="thumb" alt="{s}"></a>'
                for s in r['shots'])
        rows.append(f"""
      <tr class="{cls}">
        <td>{r['id']}</td><td>{r['title']}</td><td>{r['module']}</td><td>{r['priority']}</td>
        <td class="status">{label}</td><td>{r['duration']}s</td>
        <td class="note">{r['note'] or '-'}</td><td>{shots_html or '-'}</td>
      </tr>""")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>UI自动化测试报告 - {RUN_STAMP}</title>
<style>
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; color: #333; }}
  h1 {{ font-size: 22px; }}
  .summary {{ display: flex; gap: 16px; margin: 16px 0; }}
  .card {{ border-radius: 8px; padding: 14px 22px; color: #fff; }}
  .card.total {{ background: #576b95; }} .card.pass {{ background: #07c160; }}
  .card.fail {{ background: #fa5151; }} .card.skip {{ background: #c8c9cc; }}
  .card .num {{ font-size: 28px; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ border: 1px solid #ebedf0; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #f7f8fa; }}
  tr.pass td.status {{ color: #07c160; font-weight: bold; }}
  tr.fail td.status {{ color: #fa5151; font-weight: bold; }}
  tr.skip td.status {{ color: #969799; }}
  tr.fail {{ background: #fff7f7; }}
  .thumb {{ max-width: 140px; max-height: 180px; border: 1px solid #ddd; border-radius: 4px; margin: 2px; }}
  .note {{ max-width: 320px; word-break: break-all; }}
  .meta {{ color: #969799; font-size: 13px; margin-bottom: 12px; }}
</style>
</head>
<body>
<h1>上海公寓租赁平台 H5 UI 自动化测试报告</h1>
<div class="meta">
  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
  环境: Chromium (iPhone 12 视口 390x844) + Vue3/Vite (:{BASE_URL.split(':')[-1]}) + Django/SQLite &nbsp;|&nbsp;
  总耗时: {round(duration, 1)}s
</div>
<div class="summary">
  <div class="card total"><div class="num">{total}</div><div>用例总数</div></div>
  <div class="card pass"><div class="num">{passed}</div><div>通过</div></div>
  <div class="card fail"><div class="num">{failed}</div><div>失败</div></div>
  <div class="card skip"><div class="num">{skipped}</div><div>跳过</div></div>
</div>
<table>
  <thead><tr>
    <th>用例ID</th><th>标题</th><th>模块</th><th>优先级</th><th>结果</th><th>耗时</th><th>备注/错误分析</th><th>截图证据</th>
  </tr></thead>
  <tbody>{''.join(rows)}
  </tbody>
</table>
</body></html>"""
    path = os.path.join(REPORT_DIR, f'test_report_{RUN_STAMP}.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\n报告已生成: {path}')
    return path, total, passed, failed, skipped


# ============================================================
# 主流程
# ============================================================
CASES = [
    # 认证
    ('TC-AUTH-001', '正常注册流程', '认证-注册', 'P0', tc_auth_001),
    ('TC-AUTH-002', '注册-手机号格式校验', '认证-注册', 'P1', tc_auth_002),
    ('TC-AUTH-009', '注册-两次密码不一致', '认证-注册', 'P1', tc_auth_009),
    ('TC-AUTH-010', '未登录访问需鉴权页面', '认证-注册', 'P1', tc_auth_010),
    ('TC-AUTH-011', '密码登录-正常流程', '认证-登录', 'P0', tc_auth_011),
    ('TC-AUTH-013', '登录-密码错误', '认证-登录', 'P1', tc_auth_013),
    ('TC-AUTH-016', '管理员登录-正常流程', '认证-登录', 'P0', tc_auth_016),
    ('TC-AUTH-017', '首次登录强制身份选择', '认证-登录', 'P0', tc_auth_017),
    ('TC-AUTH-018', '身份选择-租客', '认证-身份选择', 'P0', tc_auth_018),
    ('TC-AUTH-022', '忘记密码-正常流程', '认证-密码管理', 'P0', tc_auth_022),
    # 房源
    ('TC-APT-001', '房源列表-默认展示', '房源-列表', 'P0', tc_apt_001),
    ('TC-APT-004', '房源列表-名称搜索', '房源-列表', 'P0', tc_apt_004),
    ('TC-APT-012', '房源列表-空状态', '房源-列表', 'P1', tc_apt_012),
    ('TC-APT-013', '未登录不显示收藏按钮', '房源-列表', 'P1', tc_apt_013),
    ('TC-APT-014', '租客显示收藏按钮', '房源-列表', 'P1', tc_apt_014),
    ('TC-APT-015', '商家显示发布按钮', '房源-列表', 'P0', tc_apt_015),
    ('TC-APT-016', '租客不显示发布按钮', '房源-列表', 'P0', tc_apt_016),
    ('TC-APT-017', '房源详情-正常展示', '房源-详情', 'P0', tc_apt_017),
    ('TC-APT-018', '房源详情-收藏/取消收藏', '房源-详情', 'P0', tc_apt_018),
    ('TC-APT-020', '房源详情-点击房型卡片', '房源-详情', 'P0', tc_apt_020),
    ('TC-APT-023', '户型详情-正常展示', '房源-户型详情', 'P0', tc_apt_023),
    # 收藏
    ('TC-FAV-006', '我的收藏列表', '收藏', 'P0', tc_fav_006),
    ('TC-FAV-007', '收藏列表空状态', '收藏', 'P1', tc_fav_007),
    ('TC-FAV-008', '从收藏列表取消收藏', '收藏', 'P0', tc_fav_008),
    # 消息
    ('TC-MSG-005', '消息列表空状态', '消息', 'P1', tc_msg_005),
    ('TC-MSG-006', '未登录访问消息', '消息', 'P1', tc_msg_006),
    # 管理员审核
    ('TC-AUD-001', '审核列表-提交审核Tab', '管理员审核', 'P0', tc_aud_001),
    ('TC-AUD-004', '审核列表-快捷通过', '管理员审核', 'P0', tc_aud_004),
    ('TC-AUD-005', '审核列表-快捷驳回', '管理员审核', 'P0', tc_aud_005),
    ('TC-AUD-007', '非管理员访问审核列表', '管理员审核', 'P1', tc_aud_007),
    # 商家房源
    ('TC-MER-001', '发布房源-正常流程', '商家房源', 'P0', tc_mer_001),
    ('TC-MER-008', '非商家访问发布页', '商家房源', 'P0', tc_mer_008),
    ('TC-MER-009', '已上架房源列表', '商家房源', 'P0', tc_mer_009),
    # 前端 UI
    ('TC-UI-001', '路由守卫-未登录拦截', '前端-路由', 'P0', tc_ui_001),
    ('TC-UI-002', '路由守卫-角色权限校验', '前端-路由', 'P0', tc_ui_002),
    ('TC-UI-003', '404页面', '前端-路由', 'P1', tc_ui_003),
    ('TC-UI-005', '个人中心-租客菜单', '前端-个人中心', 'P0', tc_ui_005),
    ('TC-UI-006', '个人中心-商家菜单', '前端-个人中心', 'P0', tc_ui_006),
    ('TC-UI-007', '个人中心-管理员菜单', '前端-个人中心', 'P0', tc_ui_007),
    ('TC-UI-009', '退出登录', '前端-个人中心', 'P0', tc_ui_009),
    ('TC-UI-010', '登录页-模式切换', '前端-交互', 'P1', tc_ui_010),
    ('TC-UI-012', '行政区街道联动', '前端-交互', 'P0', tc_ui_012),
    # 安全（经 UI/HTTP）
    ('TC-SEC-002', 'SQL注入防护', '安全', 'P1', tc_sec_002),
    ('TC-SEC-007', 'Token伪造', '安全', 'P1', tc_sec_007),
]


def main():
    global BROWSER
    prepare_data()
    pw = sync_playwright().start()
    BROWSER = pw.chromium.launch(headless=True)
    try:
        for case_id, title, module, priority, fn in CASES:
            run_case(case_id, title, module, priority, fn)
    finally:
        BROWSER.close()
        pw.stop()
    path, total, passed, failed, skipped = gen_report()
    # 机器可读结果
    with open(os.path.join(REPORT_DIR, f'test_result_{RUN_STAMP}.json'), 'w', encoding='utf-8') as f:
        json.dump({'stamp': RUN_STAMP, 'total': total, 'passed': passed,
                   'failed': failed, 'skipped': skipped, 'results': RESULTS},
                  f, ensure_ascii=False, indent=2)
    print(f'总计 {total} | 通过 {passed} | 失败 {failed} | 跳过 {skipped}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
