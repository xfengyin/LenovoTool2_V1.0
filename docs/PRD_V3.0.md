# 电池监控大屏 V3.0 — 产品需求文档（PRD）

> **版本**：V3.0  
> **日期**：2026-07-16  
> **作者**：嵌入式上位机专家审查  
> **状态**：待评审  

---

## 一、项目背景与现状

### 1.1 项目概述

Lenovo Battery Tool 是一款基于 PySide6 的电池监控上位机软件，通过 SMBus 协议与 BMS（电池管理系统）通信，实时读取电池寄存器数据并展示。当前版本 V2.0 已实现基础监控功能，界面采用科技感数据大屏风格。

### 1.2 现状审查发现

| 维度 | 现状 | 问题 |
|------|------|------|
| 数据采集 | 14 个主寄存器原子快照 | **cycle_count 真实模式恒为 0**（未读 0x17） |
| 电芯级数据 | 协议层已支持 cell1-4 电压（Block 0x23） | **主窗口未展示**，仅日志窗口可见 |
| 多通道温度 | 支持 0x08(电芯) + 0x3B(FET) | **FET 温度未采集**，仅显示单通道 |
| 告警系统 | 阈值已配置（温度 60℃ / SOH 20%） | **仅用于颜色着色**，无弹窗/声音/日志告警 |
| 历史趋势 | 图表窗口 deque(500) 内存缓存 | **无持久化**，关闭即丢失 |
| 数据导出 | 仅日志窗口支持 CSV | **主监控数据无导出**，图表数据无导出 |
| 性能监控 | MetricsService 已实现 | **未接入主流程**，无法展示采样延迟 |
| 死代码 | 8+ 个废弃 widget / 重复 DI 容器 | 增加维护负担 |
| 配置一致性 | yaml 与代码默认值存在分歧 | 窗口尺寸/gauge title 异常 |

### 1.3 竞品参考

参考 WGCLOUD、Grafana、Sugar BI 等数据监控大屏的交互模式，本方案目标是让电池监控大屏达到企业级监控中心的视觉密度和功能丰富度。

---

## 二、目标与范围

### 2.1 产品目标

1. **信息密度提升**：从当前 21 个展示字段扩展到 40+ 个数据点
2. **电芯级可视化**：展示 4 芯电压 + 压差分析 + 均衡状态
3. **多通道温度**：电芯温度 + FET 温度 + 环境温度（如可读）
4. **实时告警**：基于阈值的视觉/声音/日志三级告警
5. **历史持久化**：SQLite 本地存储，支持跨会话趋势分析
6. **数据导出**：主监控数据 + 图表数据 CSV 导出
7. **通信诊断**：SMBus 通信质量监控（延迟/错误率/重试）

### 2.2 不包含

- 远程上报 / 云端同步（后续版本）
- OTA 升级 / 固件刷写
- 多电池包并联管理

---

## 三、功能需求

### 3.1 P0 — 必须修复的 Bug

| ID | 描述 | 影响范围 |
|----|------|----------|
| BUG-01 | `DLLInterface.read_all_main_registers()` 未读取 0x17 CycleCount，导致真实硬件下循环次数恒为 0 | [dll_interface.py](file:///workspace/src/lenovo_tool/core/dll_interface.py) |
| BUG-02 | `config/settings.yaml` 中 `gauge.title` 含异常空格，加载后覆盖代码默认值导致标题显示异常 | [settings.yaml](file:///workspace/config/settings.yaml) |
| BUG-03 | 图表窗口底部 3 个信息栏（电压范围/电流范围/温度峰值）初始化为 "--" 后从未更新 | [chart_window.py](file:///workspace/src/lenovo_tool/ui/chart_window.py) |
| BUG-04 | yaml 中 `log_scan_interval_ms` / `csv.include_timestamp` 已定义但代码未消费 | [config_manager.py](file:///workspace/src/lenovo_tool/utils/config_manager.py) |

### 3.2 P1 — 核心功能增强

#### 3.2.1 电芯电压监控面板

**需求描述**：在主窗口中列新增电芯电压监控面板，展示 4 芯独立电压、压差分析、均衡状态。

**数据来源**：SMBus Block Read 0x23（cell1-cell4 voltage, offset 4/6/8/10, 每个 2 bytes big-endian）

**界面设计**：

```
┌─ 电芯电压 ──────────────────────┐
│                                  │
│  Cell 1   ████░░░░  4128 mV      │
│  Cell 2   ████░░░░  4132 mV      │
│  Cell 3   ████░░░░  4125 mV      │
│  Cell 4   ████░░░░  4130 mV      │
│                                  │
│  压差: 7 mV    均衡: ● 正常      │
│  最低: Cell 3 (4125 mV)          │
│  最高: Cell 2 (4132 mV)          │
│                                  │
└──────────────────────────────────┘
```

**规则**：
- 每芯电压显示为水平条形图 + 数值，颜色按范围：>4250mV 红色 / 3700-4250mV 绿色 / <3700mV 橙色
- 压差 = max(cells) - min(cells)，压差 >50mV 显示橙色警告，>100mV 显示红色告警
- 均衡状态：压差 <30mV 显示"正常"(绿)，30-50mV 显示"关注"(黄)，>50mV 显示"异常"(红)

**新增数据模型字段**：

```python
@dataclass(frozen=True, slots=True)
class CellVoltage:
    cell1: int  # mV
    cell2: int
    cell3: int
    cell4: int

    @property
    def spread(self) -> int:
        return max(self.cell1, self.cell2, self.cell3, self.cell4) - \
               min(self.cell1, self.cell2, self.cell3, self.cell4)
```

#### 3.2.2 多通道温度监控

**需求描述**：扩展温度展示为双通道（电芯温度 + FET 温度），增加温差告警。

**数据来源**：0x08 Temperature（已有）+ 0x3B FETTemperature（新增采集）

**界面设计**：在左列环形指标区域，将单个 TEMP 环改为双环嵌套（外环=电芯温度，内环=FET温度），下方增加温差数值。

```
      ┌──────┐
     ╱  42°C  ╲     ← 外环：电芯温度
    │  ┌────┐ │
    │  │38°C│  │    ← 内环：FET温度
     ╲ └────┘╱
      └──────┘
    温差: 4°C ●正常
```

**规则**：
- FET 温度 >80℃ 触发告警
- 电芯与 FET 温差 >20℃ 触发关注
- 温度环形指标颜色：<45℃ 青色 / 45-60℃ 橙色 / >60℃ 红色

#### 3.2.3 SMBus 通信诊断面板

**需求描述**：在右列新增通信诊断面板，展示实时通信质量指标。

**数据来源**：接入已有的 `MetricsService`，由 `DataWorker` 每次采集后更新。

**界面设计**：

```
┌─ 通信诊断 ──────────────────────┐
│                                  │
│  采样延迟    12.3 ms    ●正常    │
│  ████████░░░░░░░░░░░░░  41%     │
│                                  │
│  最大延迟    45.2 ms             │
│  错误次数    0 次                │
│  错误率      0.00%               │
│  连续成功    1,247 次            │
│                                  │
│  通信状态    ● 在线              │
│  从机地址    0x16                │
│                                  │
└──────────────────────────────────┘
```

**规则**：
- 采样延迟条形图：0-50ms 绿色 / 50-200ms 橙色 / >200ms 红色
- 错误率 >1% 显示橙色，>5% 显示红色
- 连续 3 次采集失败显示"离线"

#### 3.2.4 实时告警系统

**需求描述**：基于阈值的实时告警，支持视觉高亮、声音提示、告警日志。

**告警规则表**：

| 告警ID | 条件 | 级别 | 默认阈值 | 可配置 |
|--------|------|------|----------|--------|
| ALM-01 | 电芯温度 > 阈值 | 严重 | 60℃ | ✅ |
| ALM-02 | FET 温度 > 阈值 | 严重 | 80℃ | ✅ |
| ALM-03 | SOH < 阈值 | 警告 | 50% | ✅ |
| ALM-04 | RSOC < 阈值 | 警告 | 20% | ✅ |
| ALM-05 | 电压 > 设计电压 ×1.05 | 严重 | - | ❌ |
| ALM-06 | 电压 < 设计电压 ×0.9 | 警告 | - | ❌ |
| ALM-07 | 电芯压差 > 阈值 | 警告 | 50mV | ✅ |
| ALM-08 | 采样延迟 > 阈值 | 警告 | 200ms | ✅ |
| ALM-09 | 通信连续失败 ≥3 次 | 严重 | - | ❌ |
| ALM-10 | 预测寿命 < 阈值 | 警告 | 6 月 | ✅ |

**告警行为**：
- **视觉**：对应面板边框闪烁红色（QPropertyAnimation 透明度循环），告警图标显示在顶部标题栏
- **声音**：严重级别播放系统提示音（可选关闭）
- **日志**：写入 `logs/alerts_{date}.log`，包含时间戳、告警ID、当前值、阈值
- **去抖**：同一告警 10 秒内不重复触发
- **恢复**：条件解除后自动清除告警状态，记录恢复时间

**界面设计**：
- 顶部标题栏右侧增加告警铃铛图标（带数字角标）
- 点击展开告警列表面板（浮动）

#### 3.2.5 图表窗口增强

**需求描述**：补全缺失曲线、底部信息栏、时间轴格式化、数据导出。

**新增曲线**：
- FCC 趋势曲线（青色，Y 轴 3000-12000 mAh）
- RM 趋势曲线（蓝色，Y 轴 3000-12000 mAh）
- 电芯压差曲线（橙色，Y 轴 0-200 mV）
- FET 温度曲线（紫色，Y 轴 0-120℃）

**布局调整**：从 3×2 网格改为 4×2 网格（8 条曲线），或提供曲线选择 Tab。

**底部信息栏**：
- 电压范围：minV ~ maxV mV（会话极值）
- 电流范围：minA ~ maxA mA（会话极值）
- 温度峰值：maxTemp ℃（会话极值）
- 采样数：N 次
- 通信延迟：avg/max ms

**X 轴时间格式化**：`HH:MM:SS` 格式，按采样间隔自适应刻度密度。

**数据导出**：图表窗口新增"导出 CSV"按钮，导出当前缓存的全量时序数据。

#### 3.2.6 电池状态字解码面板

**需求描述**：展示 0x16 BatteryStatus 寄存器的位域解码结果。

**数据来源**：0x16 BatteryStatus（SBS 标准状态字，16 bit）

**位域定义**（SBS Specification）：

| Bit | 含义 | 显示 |
|-----|------|------|
| 15 | OVER Charged Alarm | 过充告警 |
| 14 | OVER Temp Alarm | 过温告警 |
| 13 | Terminal Discharge Alarm | 终止放电告警 |
| 12 | Remaining Capacity Alarm | 剩余容量告警 |
| 11 | Remaining Time Alarm | 剩余时间告警 |
| 7-4 | Charger Status[3:0] | 充电器状态 |
| 3 | INIT | 初始化 |
| 2 | DISCHARGE/CHARGE | 放电/充电 |
| 1 | FULL Charged | 充满 |
| 0 | EMPTY | 空电量 |

**界面设计**：在右列新增小型面板，以指示灯矩阵展示各 bit 状态。

```
┌─ 电池状态字 0x16 ───────────────┐
│                                  │
│  ● 过充  ● 过温  ○ 终止放电      │
│  ○ 容量  ○ 时间  ──────────      │
│  充电器: 充电中                   │
│  ● 初始化  ● 充电中  ○ 充满      │
│                                  │
│  原始值: 0x0084                  │
│                                  │
└──────────────────────────────────┘
```

### 3.3 P2 — 增强功能

#### 3.3.1 SQLite 历史持久化

**需求描述**：将每次采样数据持久化到本地 SQLite 数据库，支持跨会话查询和趋势分析。

**数据库设计**：

```sql
CREATE TABLE battery_samples (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,           -- 会话ID（UUID）
    timestamp   DATETIME NOT NULL,       -- 采样时间
    voltage     INTEGER,                 -- mV
    current     INTEGER,                 -- mA
    temperature REAL,                    -- ℃
    rsoc        INTEGER,                 -- %
    soh         INTEGER,                 -- %
    fcc         INTEGER,                 -- mAh
    rm          INTEGER,                 -- mAh
    cell1       INTEGER,                 -- mV
    cell2       INTEGER,
    cell3       INTEGER,
    cell4       INTEGER,
    fet_temp    REAL,                    -- ℃
    pl1         INTEGER,                 -- W
    pl2         INTEGER,
    pl4         INTEGER,
    delay_ms    REAL,                    -- 采集延迟
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_session_ts ON battery_samples(session_id, timestamp);
```

**功能**：
- 每次开始监控自动创建新会话
- 采样数据异步写入（buffer 100 条批量插入）
- 历史趋势查询：选择日期范围，展示曲线
- 自动清理：默认保留 30 天数据，可配置
- 数据库路径：`data/battery_history.db`（可配置）

#### 3.3.2 历史趋势查询窗口

**需求描述**：新增历史数据查询窗口，支持按时间范围查询并展示趋势曲线。

**界面设计**：
- 日期范围选择器（开始日期 ~ 结束日期）
- 指标选择（电压/电流/温度/RSOC/SOH/FCC/RM/压差）
- 趋势曲线图（pyqtgraph）
- 统计摘要（均值/最大/最小/标准差）
- 导出按钮

#### 3.3.3 充放电统计面板

**需求描述**：展示累计充放电统计信息。

**数据来源**：Block 0x30（Total Charged / F/W Run Time / HiVolt Time / HiTemp Time）

**界面设计**：

```
┌─ 充放电统计 ────────────────────┐
│                                  │
│  累计充电量      12,450 mAh       │
│  累计放电量      10,830 mAh       │
│  充放电效率      87.0%            │
│                                  │
│  高压运行时长    142h (12.5%)     │
│  高温运行时长    8h (0.7%)        │
│  固件运行时长    1,136h           │
│                                  │
└──────────────────────────────────┘
```

#### 3.3.4 充电策略信息面板

**需求描述**：展示充电控制相关寄存器的详细信息。

**数据来源**：0x14 ChargingCurrent / 0x15 ChargingVoltage / 0x11 RunTimeToEmpty / 0x12 AverageTimeToEmpty / 0x13 AverageTimeToFull

**界面设计**：

```
┌─ 充电策略 ──────────────────────┐
│                                  │
│  充电电流限制    3,200 mA        │
│  充电电压限制    17,400 mV       │
│                                  │
│  预计剩余运行    4h 32min        │
│  预计放空时间    4h 15min        │
│  预计充满时间    1h 20min        │
│                                  │
│  当前充电模式    智能快充 ●ON    │
│  夜间充电模式    ●OFF            │
│                                  │
└──────────────────────────────────┘
```

#### 3.3.5 电池信息详情面板

**需求描述**：展示电池静态信息（型号/序列号/制造日期/化学体系）。

**数据来源**：Block 0x21 ManufacturerName / 0x22 DeviceName / 0x1C ManufacturerData / 0x1B ManufacturerDate

**界面设计**：

```
┌─ 电池信息 ──────────────────────┐
│                                  │
│  制造商          Sunwoda          │
│  设备名称        L19Dxxx          │
│  制造日期        2024-W12         │
│  序列号          SN-20240315-xxx  │
│  化学体系        Li-Ion           │
│  设计容量        5,000 mAh        │
│  设计电压        15,480 mV        │
│                                  │
└──────────────────────────────────┘
```

### 3.4 P3 — 优化项

#### 3.4.1 死代码清理

| 文件 | 原因 | 操作 |
|------|------|------|
| `ui/view_models/chart_view_model.py` | ChartWindow 未引用 | 删除 |
| `utils/di_container.py` | 与 `core/di_container.py` 重复 | 删除 |
| `ui/widgets/chart_widget.py` | 旧版滚动图，已被 ChartWindow 替代 | 删除 |
| `ui/widgets/gauge_widget.py` | 已被 HalfGaugeWidget 替代 | 删除 |
| `ui/widgets/lcd_display.py` | 未使用 | 删除 |
| `ui/widgets/life_prediction_widget.py` | 已被 HalfGaugeWidget 替代 | 删除 |
| `ui/widgets/performance_limits.py` | 未使用 | 删除 |
| `ui/widgets/sparkline_widget.py` | 未使用 | 删除 |
| `ui/widgets/status_badge.py` | 未使用（已用 _mk_mode_card 替代） | 删除 |
| `ui/widgets/battery_data_panel.py` | 未使用 | 删除 |

#### 3.4.2 寿命预测算法统一

将 `dll_interface.py:life_prediction()` 和 `services/life_prediction.py:predict_life_months()` 合并为单一实现，DLL 层仅读取原始寄存器值，算法统一在 service 层。

#### 3.4.3 配置一致性修复

- 修正 `settings.yaml` 中 `gauge.title` 异常空格
- 统一窗口尺寸默认值（yaml 与代码一致）
- 消费 `log_scan_interval_ms` 和 `csv.include_timestamp` 配置项
- 统一 DLL 搜索路径

#### 3.4.4 图表 X 轴时间格式化

将 `time.time()` 原始时间戳格式化为 `HH:MM:SS`，按采样间隔自适应刻度密度。

#### 3.4.5 日志窗口增强

- 增加暂停/继续按钮
- 增加滚动锁定开关
- 寄存器值变化时高亮闪烁
- 寄存器含义 tooltip

---

## 四、界面布局设计

### 4.1 主窗口布局（V3.0）

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      ⚡ 电池监控大屏                    系统状态：监控中  │
│                                          告警: 🔔(2)        2026-07-16   │
├──────────────────────────────────────────────────────────────────────────┤
│ [开始] [停止] [图表] [日志] [历史]              [快充] [夜充] [告警设置] │
├────────────────────┬───────────────────────┬─────────────────────────────┤
│                    │                       │                             │
│  ┌─ 寿命预测 ──┐  │  ┌─ 容量指标 ──────┐  │  ┌─ 健康评估 ──────────┐  │
│  │             │  │  │ FCC    RM        │  │  │ SOH      循环次数    │  │
│  │   24 月     │  │  │ 4850   3210      │  │  │ 92%      247         │  │
│  │  (半圆仪表)  │  │  │ RSOC   电流      │  │  │ 衰减率: 8.0%  ████░  │  │
│  │             │  │  │ 66%    -320mA    │  │  └─────────────────────┘  │
│  └─────────────┘  │  └──────────────────┘  │                            │
│                    │                       │  ┌─ 电芯电压 ──────────┐  │
│  ┌─ 电池状态 ──┐  │  ┌─ 电芯状态 ──────┐  │  │ Cell1 ████ 4128 mV  │  │
│  │ RSOC  SOH   │  │  │   (电池图标)     │  │  │ Cell2 ████ 4132 mV  │  │
│  │ 66%   92%   │  │  │      66%        │  │  │ Cell3 ████ 4125 mV  │  │
│  │      ┌────┐ │  │  │   (充电中)       │  │  │ Cell4 ████ 4130 mV  │  │
│  │ TEMP │38°C│ │  │  │                 │  │  │ 压差: 7mV  均衡:正常 │  │
│  │ 42°C └────┘ │  │  │ FCC ████░ 4850  │  │  └─────────────────────┘  │
│  │  FET:38℃    │  │  │ RM  ███░░ 3210  │  │                            │
│  └─────────────┘  │  └──────────────────┘  │  ┌─ 充电策略 ──────────┐  │
│                    │                       │  │ 充电限制: 3200mA     │  │
│  ┌─ 运行状态 ─┐   │  ┌─ 电压详情 ──────┐  │  │ 电压限制: 17400mV    │  │
│  │ ● 充电中    │   │  │ 当前 16480 mV   │  │  │ 预计充满: 1h20min    │  │
│  │ ● 循环 247  │   │  │ 设计 15480 mV   │  │  │ 预计放空: 4h15min    │  │
│  │ ● 2024-03   │   │  │ 最低 15200 mV   │  │  └─────────────────────┘  │
│  │ ● 最高 45℃  │   │  │ 最高 16520 mV   │  │                            │
│  └─────────────┘   │  └──────────────────┘  │  ┌─ 通信诊断 ──────────┐  │
│                    │                       │  │ 延迟 12.3ms  错误 0  │  │
│  ┌─ 状态字 ───┐   │  ┌─ 会话统计 ──────┐  │  │ 连续成功 1247 次     │  │
│  │ 0x16: 0x84 │   │  │ 采样 1247 次    │  │  │ 通信状态: ● 在线     │  │
│  │ ●充电 ●初始化│  │  │ 均压 16450 mV   │  │  └─────────────────────┘  │
│  └─────────────┘   │  │ 均流 -315 mA    │  │                            │
│                    │  │ 均温 38.5 ℃     │  │  ┌─ 充电模式 ──────────┐  │
│                    │  │ 均功率 5.2 W    │  │  │  ⚡快充   🌙夜充      │  │
│                    │  └──────────────────┘  │  │   ON       OFF       │  │
│                    │                       │  └─────────────────────┘  │
├────────────────────┴───────────────────────┴─────────────────────────────┤
│ 运行: 02:34:15                              采样: 2026-07-16 14:32:15   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.2 面板清单（V3.0 vs V2.0 对比）

| 位置 | V2.0 面板 | V3.0 面板 | 变化 |
|------|-----------|-----------|------|
| 顶部 | 装饰标题栏 | 装饰标题栏 + **告警铃铛** | 新增告警入口 |
| 控制栏 | 4 按钮 + 2 模式 | 5 按钮 + 2 模式 + **告警设置** | 新增历史/告警 |
| 左列-1 | 寿命预测 | 寿命预测 | 不变 |
| 左列-2 | 环形指标(3) | 环形指标(3) + **双通道温度** | FET 温度新增 |
| 左列-3 | 运行状态 | 运行状态 | 不变 |
| 左列-4 | — | **电池状态字解码** | 新增 |
| 中列-1 | KPI 卡(4) | KPI 卡(4) | 不变 |
| 中列-2 | 电池图标+容量条 | 电池图标+容量条 | 不变 |
| 中列-3 | 电压详情 | 电压详情 | 不变 |
| 中列-4 | — | **会话统计**（从右列移入） | 位置调整 |
| 右列-1 | 健康评估 | 健康评估 | 不变 |
| 右列-2 | 功率限制 | **电芯电压** | 新增（替换功率限制） |
| 右列-3 | 充电模式 | **充电策略** | 新增 |
| 右列-4 | 会话统计 | **通信诊断** | 新增 |
| 右列-5 | — | **充电模式**（保留） | 位置下移 |

### 4.3 图表窗口布局（V3.0）

```
┌─ 实时监控图表 ──────────────────────────────────────────┐
│                                                          │
│  ┌─ 电压 ──────┐  ┌─ 电流 ──────┐  ┌─ 温度 ──────┐    │
│  │             │  │             │  │  电芯       │    │
│  │  16480 mV   │  │  -320 mA    │  │  42℃        │    │
│  │             │  │             │  │  FET 38℃    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
│  ┌─ RSOC ──────┐  ┌─ SOH ───────┐  ┌─ 功率 ──────┐    │
│  │             │  │             │  │             │    │
│  │  66%        │  │  92%        │  │  -5.2W      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
│  ┌─ FCC ───────┐  ┌─ RM ────────┐  ┌─ 压差 ──────┐    │
│  │  4850 mAh   │  │  3210 mAh   │  │  7 mV       │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
│                                                          │
│  [清空] [导出CSV]          采样: 1247 | 延迟: 12.3ms    │
└──────────────────────────────────────────────────────────┘
```

### 4.4 新增窗口

#### 历史趋势窗口
- 日期范围选择器
- 指标选择下拉框
- 趋势曲线图
- 统计摘要表格
- 导出按钮

#### 告警设置窗口
- 告警规则开关列表
- 阈值输入框
- 声音开关
- 测试按钮

---

## 五、数据模型变更

### 5.1 BatterySnapshot 扩展

```python
@dataclass(frozen=True, slots=True)
class CellVoltage:
    """电芯电压数据"""
    cell1: int  # mV
    cell2: int
    cell3: int
    cell4: int

    @property
    def spread(self) -> int:
        """最大压差"""
        vals = [self.cell1, self.cell2, self.cell3, self.cell4]
        return max(vals) - min(vals)

    @property
    def is_balanced(self) -> bool:
        """是否均衡（压差 <30mV）"""
        return self.spread < 30


@dataclass(frozen=True, slots=True)
class BatterySnapshot:
    # === 现有字段（21个）===
    timestamp: datetime
    voltage: int
    current: int
    temperature: float
    rsoc: int
    soh: int
    fcc: int
    rm: int
    dc: int
    dv: int
    battery_mode: str
    pl1: int
    pl2: int
    pl4: int
    predicted_life_months: int
    cycle_count: int
    first_usage_time: str
    charge_state: str
    max_temperature: float
    min_voltage: int
    max_voltage: int

    # === V3.0 新增字段 ===
    cell_voltages: CellVoltage | None = None       # 电芯电压（Block 0x23）
    fet_temperature: float | None = None            # FET 温度（0x3B）
    battery_status: int | None = None               # 状态字原始值（0x16）
    charging_current: int | None = None             # 充电电流限制（0x14）
    charging_voltage: int | None = None             # 充电电压限制（0x15）
    runtime_to_empty: int | None = None             # 预计放空时间（0x11, min）
    avg_time_to_empty: int | None = None            # 平均放空时间（0x12, min）
    avg_time_to_full: int | None = None             # 平均充满时间（0x13, min）
    manufacturer: str | None = None                 # 制造商（Block 0x21）
    device_name: str | None = None                  # 设备名称（Block 0x22）
    manufacturer_date: str | None = None            # 制造日期（0x1B）
```

### 5.2 新增数据模型

```python
@dataclass(frozen=True, slots=True)
class AlertEvent:
    """告警事件"""
    alert_id: str           # ALM-01 ~ ALM-10
    level: str              # "critical" | "warning"
    message: str            # 告警描述
    current_value: float    # 当前值
    threshold: float        # 阈值
    timestamp: datetime
    recovered: bool = False


@dataclass(frozen=True, slots=True)
class CommMetrics:
    """通信质量指标"""
    sample_count: int
    success_count: int
    error_count: int
    avg_delay_ms: float
    max_delay_ms: float
    min_delay_ms: float
    consecutive_success: int
    is_online: bool
```

---

## 六、技术方案

### 6.1 电芯电压采集

在 `DLLInterface.read_all_main_registers()` 中新增 Block 0x23 读取：

```python
# 在 read_all_main_registers 方法中新增
try:
    block = self.read_block(0x23, 1, 9)  # cell voltage block
    if block and len(block) >= 10:
        cell1 = int.from_bytes(block[4:6], 'big')
        cell2 = int.from_bytes(block[6:8], 'big')
        cell3 = int.from_bytes(block[8:10], 'big')
        cell4 = int.from_bytes(block[10:12], 'big') if len(block) >= 12 else 0
        data["cell_voltages"] = (cell1, cell2, cell3, cell4)
except Exception:
    data["cell_voltages"] = None
```

同时在 `DLLInterface` 中新增 0x17 CycleCount 读取和 0x3B FETTemperature 读取。

### 6.2 告警系统架构

```
DataWorker → DataAcquisitionService → BatterySnapshot
                                          │
                                          ▼
                                    AlertEngine
                                    ├── 规则评估
                                    ├── 去抖控制
                                    ├── 状态跟踪
                                    └── 信号发射
                                          │
                           ┌──────────────┼──────────────┐
                           ▼              ▼              ▼
                      UI 高亮         声音提示      日志写入
                  (QAnimation)    (QSoundEffect)  (alert.log)
```

### 6.3 SQLite 持久化

```python
class HistoryRepository:
    """历史数据持久化仓库"""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._buffer: list[BatterySnapshot] = []
        self._buffer_size = 100
        self._init_db()

    def insert(self, snapshot: BatterySnapshot) -> None:
        self._buffer.append(snapshot)
        if len(self._buffer) >= self._buffer_size:
            self._flush()

    def _flush(self) -> None:
        # 批量 INSERT
        ...

    def query_range(
        self, start: datetime, end: datetime
    ) -> list[BatterySnapshot]:
        # SELECT ... WHERE timestamp BETWEEN
        ...

    def cleanup_old(self, days: int = 30) -> int:
        # DELETE WHERE timestamp < datetime('now', '-N days')
        ...
```

### 6.4 通信诊断接入

在 `DataWorker.run()` 中包裹计时器，每次采集后更新 `MetricsService`：

```python
def run(self):
    while self._running:
        t0 = time.perf_counter()
        try:
            snapshot = self._service.acquire()
            delay_ms = (time.perf_counter() - t0) * 1000
            self._metrics.record_sample(delay_ms, success=True)
            self.data_ready.emit(snapshot)
        except Exception as e:
            self._metrics.record_sample(0, success=False, error=e)
            self.error_occurred.emit(e)
```

---

## 七、配置项扩展

### 7.1 新增配置项

```yaml
# config/settings.yaml 新增

# 告警配置
alerts:
  temperature_critical: 60.0      # ℃
  fet_temperature_critical: 80.0  # ℃
  soh_warning: 50                 # %
  rsoc_warning: 20                # %
  cell_spread_warning: 50         # mV
  delay_warning_ms: 200           # ms
  life_warning_months: 6          # 月
  sound_enabled: true
  debounce_seconds: 10

# 历史持久化
history:
  enabled: true
  db_path: "data/battery_history.db"
  retention_days: 30
  buffer_size: 100

# 电芯电压
cell_voltage:
  high_threshold: 4250            # mV
  low_threshold: 3700             # mV
  spread_warning: 50              # mV
  spread_critical: 100            # mV
  balanced_threshold: 30          # mV
```

---

## 八、验收标准

### 8.1 P0 Bug 修复

| 验收项 | 标准 |
|--------|------|
| BUG-01 | 真实硬件模式下循环次数显示正确值 |
| BUG-02 | settings.yaml 加载后 gauge title 无异常空格 |
| BUG-03 | 图表窗口底部信息栏显示会话极值 |
| BUG-04 | log_scan_interval_ms 配置生效 |

### 8.2 P1 功能验收

| 验收项 | 标准 |
|--------|------|
| 电芯电压面板 | 4 芯电压实时显示，压差计算正确，均衡状态颜色正确 |
| 多通道温度 | 电芯温度 + FET 温度双环显示，温差数值正确 |
| 通信诊断面板 | 延迟/错误率/连续成功数实时更新，离线检测生效 |
| 告警系统 | 10 条规则全部可触发，视觉/声音/日志三种通道生效 |
| 图表增强 | 8 条曲线显示正常，底部信息栏更新，CSV 导出功能正常 |

### 8.3 P2 功能验收

| 验收项 | 标准 |
|--------|------|
| SQLite 持久化 | 数据写入成功，跨会话查询正常，自动清理生效 |
| 历史趋势窗口 | 日期范围查询正确，曲线渲染正常 |
| 充放电统计 | Block 0x30 数据正确解码展示 |
| 充电策略面板 | 5 个寄存器数据正确展示 |
| 电池信息面板 | Block 0x21/0x22 数据正确解码展示 |

### 8.4 代码质量

| 验收项 | 标准 |
|--------|------|
| 死代码清理 | 10 个废弃文件已删除 |
| 测试通过 | 所有现有测试通过，新增功能有对应测试 |
| 配置一致性 | yaml 与代码默认值一致 |
| 无重复实现 | 寿命预测算法单一实现 |

---

## 九、里程碑

| 里程碑 | 内容 | 优先级 |
|--------|------|--------|
| M1 | P0 Bug 修复 + 死代码清理 + 配置一致性 | P0 |
| M2 | 电芯电压面板 + 多通道温度 + 通信诊断 | P1 |
| M3 | 告警系统 + 图表增强 | P1 |
| M4 | SQLite 持久化 + 历史趋势窗口 | P2 |
| M5 | 充放电统计 + 充电策略 + 电池信息 + 状态字解码 | P2 |
| M6 | 测试补全 + 文档更新 | P3 |

---

## 十、风险与依赖

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Block 0x23 读取格式不确定 | 电芯电压解码错误 | 先在日志窗口验证格式，再接入主流程 |
| SQLite 写入影响采集性能 | 采样延迟增加 | 异步 buffer 批量写入，不阻塞采集线程 |
| 告警频繁触发影响体验 | 用户困扰 | 去抖机制 + 可配置阈值 + 一键静音 |
| 真实硬件不可用 | 无法验证部分功能 | Demo 模式覆盖所有新功能 |
| 窗口空间不足 | 面板拥挤 | 可滚动布局或 Tab 切换 |

---

## 附录 A：寄存器地址速查表

| 地址 | 名称 | 类型 | 当前状态 |
|------|------|------|----------|
| 0x08 | Temperature | Word | ✅ 已采集 |
| 0x09 | Voltage | Word | ✅ 已采集 |
| 0x0A | Current | Word | ✅ 已采集 |
| 0x0B | AverageCurrent | Word | ⚠️ 仅日志 |
| 0x0C | MaxError | Word | ⚠️ 仅日志 |
| 0x0D | RSOC | Word | ✅ 已采集 |
| 0x0E | AbsoluteStateOfCharge | Word | ⚠️ 仅日志 |
| 0x10 | RM | Word | ✅ 已采集 |
| 0x11 | RunTimeToEmpty | Word | ❌ V3.0 新增 |
| 0x12 | AverageTimeToEmpty | Word | ❌ V3.0 新增 |
| 0x13 | AverageTimeToFull | Word | ❌ V3.0 新增 |
| 0x14 | ChargingCurrent | Word | ❌ V3.0 新增 |
| 0x15 | ChargingVoltage | Word | ❌ V3.0 新增 |
| 0x16 | BatteryStatus | Word | ❌ V3.0 新增 |
| 0x17 | CycleCount | Word | ❌ P0 修复 |
| 0x18 | DC | Word | ✅ 已采集 |
| 0x1B | ManufacturerDate | Word | ❌ V3.0 新增 |
| 0x1C | ManufacturerData | Block | ⚠️ 仅日志 |
| 0x20 | FCC | Word | ✅ 已采集 |
| 0x21 | ManufacturerName | Block | ❌ V3.0 新增 |
| 0x22 | DeviceName | Block | ❌ V3.0 新增 |
| 0x23 | CellVoltage (1-4) | Block | ❌ V3.0 新增 |
| 0x26 | SmartChargeBit | Word | ✅ 已写入 |
| 0x2C | DesignVoltage(MSB) | Word | ✅ 已采集 |
| 0x30 | TotalCharged etc. | Block | ❌ V3.0 新增 |
| 0x3B | FETTemperature | Word | ❌ V3.0 新增 |
| 0x3F | OptCommand3F | Block | ✅ 已采集 |
| 0x50 | LightChargeBit | Word | ✅ 已写入 |
| 0x6A | BatteryLifeMonths | Word | ✅ 已采集 |
| 0x6B | BatteryLifeCycle | Word | ⚠️ 仅日志 |
| 0x6C | BatteryLifeSpan | Word | ⚠️ 仅日志 |
