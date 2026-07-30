# H5 UI 自动化测试约定（Test Conventions）

> 本文件沉淀 UI 自动化测试的编写/断言规则，供测试 Agent 与人工评审共同遵守。
> 新增或修改测试用例时，先读本文件。路径：`test/ui/CONVENTIONS.md`

## 1. 断言必须"校验值"，不能只"校验存在"

❌ 反例（过浅，会漏检）：
```python
expect('温馨一居室' in body_text)   # 只校验名称存在
expect('租' in body_text)            # 只校验有个"租"字
```
✅ 正例：断言要落到**具体字段的具体内容/格式**上。

## 2. 字典 / 枚举 / 状态类字段：必须校验"显示中文标签，而非原始编码"

凡是来自系统字典或枚举的字段，页面必须显示**中文 label**，不得直接显示**后端 code**。
断言时反向排除原始编码：

```python
for raw_code in ('one_bedroom', 'two_bedroom', 'studio', 'loft', 'duplex', 'inner', 'outer'):
    expect(raw_code not in body_text, f'字段未翻译为中文标签，显示了原始编码「{raw_code}」')
```

**适用字段清单**（持续补充）：
| 字段 | 原始编码示例 | 应显示的中文 |
|---|---|---|
| 户型 layout_type | one_bedroom / duplex / loft | 一室 / 复式 / LOFT |
| 内外窗 window_type | inner / outer | 内窗 / 外窗 |
| 朝向 orientation | east / south | 东 / 南 |
| 设施 facilities | air_conditioner / wifi | 空调 / WiFi |
| 租期 lease_term | 1_year / 6_month | 1年 / 半年 |
| 支付方式 payment_method | pay_1_deposit_1 | 押一付一 |
| 审核状态 status | pending / approved / rejected | 待审核 / 已通过 / 已驳回 |
| 身份角色 role | tenant / landlord / admin | 租客 / 商家 / 管理员 |

> 历史教训：TC-APT-023 曾因只校验名称存在，放过了"户型/内外窗显示英文编码"的真实缺陷
> （后端 `RoomTypeDetailSerializer` 未返回 `*_label` 字段）。见 commit 47781fb。

## 3. 金额 / 数值类字段：不得出现占位符

```python
expect('¥?' not in body_text and '? /月' not in body_text, '租金显示为占位符')
```
租金、价格、楼层等必须显示真实数值，不能是 `¥?`、`--`、`undefined`、`null`、`NaN`。

## 4. 空值 / 异常渲染兜底

页面文本中不得出现 `undefined`、`null`、`None`、`NaN`、`[object Object]` 等未处理占位：
```python
for bad in ('undefined', 'null', 'None', 'NaN', '[object Object]'):
    expect(bad not in body_text, f'页面出现未处理占位「{bad}」')
```

## 5. 列表类：校验"内容正确"而不仅是"有条数"

- 搜索/筛选后：目标项**在**列表中，且非目标项**不在**列表中（双向断言）。
- 空状态：必须出现 `van-empty` 且文案正确。

## 6. 权限 / 路由守卫：校验"确实跳转/拦截"

```python
expect('/login' in PAGE.url)          # 未登录被拦截到登录页
expect('redirect' in PAGE.url)        # 且保留回跳参数
```

## 7. 证据要求

- 关键步骤截图（操作前 / 操作后各一张），失败用例必须附失败现场截图 + 控制台错误。
- 截图存 `test/report/evidence/`，报告内用相对路径可点击链接。

---
**维护方式**：发现新的漏检模式 → 先把断言加进对应用例 → 再把通用规则补充到本文件。
