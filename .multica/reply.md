## 实现完成：详情页展示升级（F4）

### 改动文件清单

**后端（2 个文件）**

| 文件 | 改动 | 原因 |
|---|---|---|
| `server/seed_data/seed_script.py` | 新增 `fee_type`（民水民电/商水商电/按表计费）和 `facility_group`（基础设施/卫浴/厨房/公共）字典条目 | 支持费用标签翻译和设施分组展示 |
| `server/apps/apartments/serializers.py` | `ApartmentDetailSerializer` 新增 `water_fee_label` 和 `electric_fee_label` 字段（`SerializerMethodField`），通过 `get_dict_label('fee_type', ...)` 查询字典 | 前端可直接获取中文标签，无需额外请求 |

**前端（6 个文件）**

| 文件 | 改动 | 原因 |
|---|---|---|
| `web/src/components/business/FeeDetailCard.vue` | **新建** — 费用明细卡片组件，逐项展示月租金/物业费/水电/服务费/其他费用；空项隐藏行；物业费=0 显示"免物业费"；水费电费同标签合并显示 | 验收标准1 |
| `web/src/components/business/FacilityGroup.vue` | **新建** — 配套设施按分组展示组件，从所有房型聚合设施，按 basic/bathroom/kitchen/public 分组渲染标签，分组名称从 `facility_group` 字典加载 | 验收标准2 |
| `web/src/components/business/PhoneActionSheet.vue` | **新建** — 电话动作面板，点击弹出"拨打/复制"选择，拨打使用 `tel:` 协议直拨，复制写入剪贴板 | 验收标准3 |
| `web/src/views/apartment/ApartmentDetailView.vue` | 集成三个新组件：电话行改为可点击弹出面板，描述下方插入费用卡片和设施分组 | 页面改造 |
| `web/src/types/index.ts` | `Apartment` 接口新增 `property_fee`、`water_fee`、`water_fee_label`、`electric_fee`、`electric_fee_label`、`service_fee`、`other_fees`、`min_area`、`verified` 字段 | 类型同步 |
| `web/src/utils/dictMaps.ts` | 新增 `feeTypeMap` 和 `facilityGroupMap` 硬编码兜底映射 | 字典未就绪时的降级方案 |
| `web/tailwind.config.js` | 新增 `primary`/`success`/`warning`/`danger` 颜色定义 | 电话行为链接色 |

### 验证结果

- **前端构建**：`vue-tsc -b && vite build` 通过，无类型错误
- **后端测试**：环境中无 Django，未运行；但序列化器改动为纯增量（新增字段），不会影响现有接口

### 验收对照

1. ✅ 费用明细：有值显示值，空值隐藏行，物业费=0 显示"免物业费"，服务费=0 显示"无"
2. ✅ 设施分组：按 4 个分组展示标签，分组名从字典加载
3. ✅ 电话交互：点击弹出拨打/复制面板

### 遗留风险

- 设施→分组映射硬编码在 `FacilityGroup.vue` 的 `getFacilityGroup()` 函数中，PRD 要求"分组规则进字典配置"但 `SystemDict` 模型缺少关联字段；后续可通过扩展模型支持
- 需重新执行 `seed_script.py` 以创建 `fee_type` 和 `facility_group` 字典条目
