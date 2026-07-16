# Lenovo Battery Tool 重构项目需求文档 (PRD)

## 1. 项目背景

### 1.1 现状分析

当前版本（v2.0.0）是一个基于 PySide6 的联想电池监控桌面应用，存在以下架构问题：

| 问题类型 | 具体问题 | 严重程度 |
|----------|----------|----------|
| **架构耦合** | `MainWindow`直接依赖`DLLInterface`，缺少抽象层 | 高 |
| **代码臃肿** | `main_window.py`达845行，包含3个自定义Widget类 | 高 |
| **测试困难** | UI层与业务逻辑耦合，难以进行单元测试 | 高 |
| **扩展性差** | 数据源、导出器等硬编码，难以扩展 | 中 |
| **状态混乱** | 充电模式状态在多个地方维护 | 中 |

### 1.2 重构目标

基于企业级架构标准，对项目进行重构，实现：

- **解耦**：UI层与业务层、数据层完全分离
- **可测试**：核心逻辑100%可单元测试
- **可扩展**：插件化架构，支持动态扩展数据源、导出器等
- **可观测**：完善的日志、监控指标、异常追踪
- **高可用**：超时、重试、熔断、降级机制

---

## 2. 功能需求

### 2.1 核心功能（不变）

| 功能模块 | 功能描述 | 需求来源 |
|----------|----------|----------|
| 实时监控 | 实时显示电压、电流、温度、SOH、RSOC等指标 | 现有功能 |
| 寿命预测 | 根据寄存器0x6A预测电池剩余寿命（月） | 现有功能 |
| 充电模式 | 支持快充模式、夜间充电模式切换 | 现有功能 |
| 数据日志 | 显示完整SMBus寄存器数据 | 现有功能 |
| 图表展示 | 实时趋势图表（电压、电流、温度等） | 现有功能 |
| CSV导出 | 导出监控数据为CSV文件 | 现有功能 |

### 2.2 重构新增功能

| 功能模块 | 功能描述 | 优先级 |
|----------|----------|--------|
| **依赖注入** | 引入DI容器，支持服务解耦和Mock | P0 |
| **数据源抽象** | 抽象`BatteryDataSource`接口，支持多数据源 | P0 |
| **导出器抽象** | 抽象`DataExporter`接口，支持多格式导出 | P1 |
| **状态管理** | 统一状态管理，支持Observer模式分发 | P0 |
| **配置中心** | 集中化配置管理，支持动态重载 | P1 |
| **监控指标** | 添加采样延迟、处理耗时等性能指标 | P2 |
| **错误边界** | 全局异常处理，防止UI崩溃 | P1 |

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 目标值 | 说明 |
|------|--------|------|
| UI响应延迟 | ≤100ms | 数据更新到UI刷新的时间 |
| 采样周期 | 可配置（默认4s） | 通过配置文件调整 |
| 内存占用 | ≤100MB | 正常运行状态 |

### 3.2 可用性要求

| 要求 | 说明 |
|------|------|
| 容错降级 | DLL加载失败自动切换到模拟数据源 |
| 异常恢复 | 数据采集异常后自动重试 |
| 优雅关闭 | 关闭时正确清理资源、停止后台线程 |

### 3.3 可测试性要求

| 要求 | 目标 |
|------|------|
| 单元测试覆盖率 | ≥80% | 核心业务逻辑 |
| 集成测试 | 覆盖关键流程 |
| UI测试 | 关键交互可自动化测试 |

---

## 4. 技术架构

### 4.1 架构风格

采用 **分层架构 + 插件化设计**：

```
┌─────────────────────────────────────────────────────────────┐
│                      UI Layer (PySide6)                     │
│  MainWindow | ChartWindow | LogWindow | Widgets             │
├─────────────────────────────────────────────────────────────┤
│                     Presentation Layer                      │
│  ViewModels | Presenters | State Managers                   │
├─────────────────────────────────────────────────────────────┤
│                      Service Layer                          │
│  DataAcquisition | ChargeMode | LifePrediction | LogData    │
├─────────────────────────────────────────────────────────────┤
│                      Data Layer                             │
│  BatteryDataSource (Interface)                              │
│    ├── DLLDataSource (Real)                                 │
│    └── MockDataSource (Demo)                                │
├─────────────────────────────────────────────────────────────┤
│                     Infrastructure                          │
│  DI Container | Config | Logger | Exporters | Metrics       │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 关键设计

#### 4.2.1 依赖注入容器

```python
# 设计目标：支持构造函数注入、单例管理、Mock替换
class Container:
    def resolve(self, interface: Type[T]) -> T: ...
    def register(self, interface: Type[T], impl: Type[T]) -> None: ...
    def register_singleton(self, interface: Type[T], instance: T) -> None: ...
```

#### 4.2.2 数据源接口

```python
# 设计目标：抽象硬件访问层，支持真实/模拟数据源无缝切换
@protocol
class BatteryDataSource:
    def read_all_main_registers(self) -> dict[str, int | float]: ...
    def read_soh(self) -> int: ...
    def get_temperature(self, addr: int = 0x08) -> float: ...
    def get_first_usage_time(self, addr: int = 0x3F) -> str: ...
    def write_smbus(self, type_: int, addr: int, slave: int, mode_state: bool) -> None: ...
```

#### 4.2.3 导出器接口

```python
# 设计目标：支持CSV、JSON、Excel等多种格式导出
@protocol
class DataExporter:
    FORMAT: str  # "csv", "json", "xlsx"
    
    def export(self, snapshots: list[BatterySnapshot], path: Path) -> None: ...
```

#### 4.2.4 状态管理

```python
# 设计目标：统一状态管理，支持Observer模式
class BatteryStateManager(Observable):
    def update(self, snapshot: BatterySnapshot) -> None: ...
    def subscribe(self, observer: Observer) -> None: ...
    def unsubscribe(self, observer: Observer) -> None: ...
```

---

## 5. 数据模型

### 5.1 核心数据模型（保持不变）

| 模型 | 说明 | 位置 |
|------|------|------|
| `BatterySnapshot` | 电池数据快照（不可变） | `core/data_models.py` |
| `LogSnapshot` | 日志数据快照 | `core/data_models.py` |
| `ChargeMode` | 充电模式状态 | `core/data_models.py` |
| `AppConfig` | 应用配置 | `core/data_models.py` |

### 5.2 新增数据模型

| 模型 | 说明 | 字段 |
|------|------|------|
| `PerformanceMetrics` | 性能指标 | `sample_count: int`, `avg_latency_ms: float`, `max_latency_ms: float`, `error_count: int` |
| `DataSourceInfo` | 数据源信息 | `name: str`, `type: str`, `status: str`, `last_connect_time: datetime` |

---

## 6. API接口设计

### 6.1 服务层接口

| 接口 | 方法 | 参数 | 返回值 |
|------|------|------|--------|
| `DataAcquisitionService` | `fetch_snapshot()` | 无 | `BatterySnapshot` |
| `ChargeModeService` | `toggle(mode)` | `mode: ChargeModeType` | `bool` |
| `ChargeModeService` | `is_enabled(mode)` | `mode: ChargeModeType` | `bool` |
| `LifePredictionService` | `predict(raw_value)` | `raw_value: int` | `int`（月） |
| `LogDataService` | `fetch_log_snapshot()` | 无 | `LogSnapshot` |
| `MetricsService` | `record_latency(ms)` | `ms: float` | 无 |
| `MetricsService` | `record_error()` | 无 | 无 |
| `MetricsService` | `get_metrics()` | 无 | `PerformanceMetrics` |

### 6.2 基础设施接口

| 接口 | 方法 | 参数 | 返回值 |
|------|------|------|--------|
| `ConfigProvider` | `get(key, default)` | `key: str`, `default: Any` | `Any` |
| `ConfigProvider` | `reload()` | 无 | 无 |
| `ConfigProvider` | `watch(callback)` | `callback: Callable` | `int`（watch_id） |
| `LoggerProvider` | `get_logger(name)` | `name: str` | `logging.Logger` |
| `ExporterFactory` | `create(format)` | `format: str` | `DataExporter` |

---

## 7. UI设计

### 7.1 布局结构（保持不变）

- **左列**：仪表盘（寿命预测）+ 环形指标（RSOC/SOH/TEMP）+ 运行状态
- **中列**：电池图标 + 容量条 + 电芯电压 + 功率限制 + 会话统计
- **右列**：采样统计 + 寿命预测卡片 + 充电模式

### 7.2 新增UI组件

| 组件 | 说明 | 位置 |
|------|------|------|
| `StatusBarWidget` | 统一状态栏，显示数据源状态、采样延迟、错误计数 | `ui/widgets/status_bar.py` |
| `MetricsOverlay` | 可选的性能指标浮层（开发模式） | `ui/widgets/metrics_overlay.py` |

### 7.3 UI状态映射

| 状态 | 显示 | 触发条件 |
|------|------|----------|
| **正常** | 绿色指示灯 | 数据源连接正常，采样成功 |
| **警告** | 黄色指示灯 | 采样延迟超过阈值，温度过高 |
| **错误** | 红色指示灯 | 数据源连接失败，连续采样失败 |
| **演示** | "DEMO"标记 | 使用模拟数据源 |

---

## 8. 部署与集成

### 8.1 项目结构（重构后）

```
src/lenovo_tool/
├── __init__.py
├── main.py                      # 应用入口
├── core/                        # 核心层（数据模型、异常、接口定义）
│   ├── __init__.py
│   ├── data_models.py
│   ├── exceptions.py
│   ├── interfaces.py            # 新增：接口定义（DataSource, Exporter等）
│   ├── register_definitions.py
│   └── unit_definitions.py
├── data/                        # 新增：数据层（数据源实现）
│   ├── __init__.py
│   ├── dll_data_source.py       # 真实DLL数据源
│   ├── mock_data_source.py      # 模拟数据源（原DemoDLLInterface）
│   └── dll_interface.py         # 底层DLL访问（保留）
├── services/                    # 服务层（业务逻辑）
│   ├── __init__.py
│   ├── charge_mode.py
│   ├── csv_export.py
│   ├── data_acquisition.py
│   ├── life_prediction.py
│   ├── log_data_service.py
│   └── metrics_service.py       # 新增：性能指标服务
├── ui/                          # UI层
│   ├── __init__.py
│   ├── main_window.py           # 精简：仅负责UI组装
│   ├── chart_window.py
│   ├── log_window.py
│   ├── view_models/             # 新增：ViewModel层
│   │   ├── __init__.py
│   │   ├── main_view_model.py
│   │   └── chart_view_model.py
│   ├── widgets/                 # 扩充：抽取自定义Widget
│   │   ├── __init__.py
│   │   ├── half_gauge_widget.py
│   │   ├── battery_icon_widget.py
│   │   ├── life_prediction_widget.py
│   │   └── ...
│   ├── dialogs/
│   ├── styles/
│   └── workers/
└── utils/                       # 工具层（基础设施）
    ├── __init__.py
    ├── byte_utils.py
    ├── config_manager.py        # 增强：支持动态重载
    ├── constants.py
    ├── logger_setup.py
    ├── di_container.py          # 新增：依赖注入容器
    └── exporter_factory.py      # 新增：导出器工厂
```

### 8.2 依赖关系

```
UI Layer
  └── Presentation Layer (ViewModels)
        └── Service Layer
              └── Data Layer (DataSource)
                    └── Infrastructure (DLL, Config, Logger)
```

**关键约束**：
- UI层 **只能** 依赖Presentation层和基础设施
- Service层 **只能** 依赖Data层和基础设施
- 跨层依赖必须通过接口，禁止直接依赖具体实现

---

## 9. 测试策略

### 9.1 测试分层

| 测试层 | 范围 | 工具 |
|--------|------|------|
| **单元测试** | 核心服务、数据模型、工具函数 | `pytest` |
| **集成测试** | 服务间协作、数据源集成 | `pytest` + Mock |
| **UI测试** | 关键交互流程 | `pytest-qt` |
| **性能测试** | 采样延迟、内存占用 | `pytest-benchmark` |

### 9.2 测试覆盖率目标

| 模块 | 目标覆盖率 |
|------|------------|
| `core/` | ≥90% |
| `services/` | ≥85% |
| `data/` | ≥80% |
| `ui/view_models/` | ≥70% |

---

## 10. 实施计划

### 10.1 阶段划分

| 阶段 | 内容 | 周期 | 关键产出 |
|------|------|------|----------|
| **Phase 1** | 基础设施层重构（DI容器、配置中心、日志增强） | 1周 | `di_container.py`, `config_manager.py`优化 |
| **Phase 2** | 数据层抽象（DataSource接口、Mock数据源抽取） | 1周 | `interfaces.py`, `mock_data_source.py` |
| **Phase 3** | 服务层重构（Metrics服务、状态管理） | 1周 | `metrics_service.py`, `state_manager.py` |
| **Phase 4** | UI层重构（ViewModel抽取、Widget拆分） | 2周 | `view_models/`, 独立Widget文件 |
| **Phase 5** | 测试覆盖与集成验证 | 1周 | 完善测试套件，修复集成问题 |

### 10.2 里程碑

| 里程碑 | 完成条件 |
|--------|----------|
| **M1** | DI容器可用，核心服务可通过容器注入 |
| **M2** | 数据源抽象完成，真实/模拟数据源无缝切换 |
| **M3** | 服务层重构完成，所有核心逻辑可单元测试 |
| **M4** | UI层重构完成，主窗口代码量减少50%以上 |
| **M5** | 测试覆盖率达标，应用功能与原版本一致 |

---

## 11. 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| UI重构引入视觉回归 | 中 | 中 | 使用截图对比测试，保留原有样式 |
| 依赖注入引入复杂性 | 低 | 低 | 保持DI容器简洁，提供默认配置 |
| 数据源抽象影响性能 | 低 | 中 | 接口设计保持最小化，避免不必要的抽象层 |
| 测试覆盖不足 | 中 | 高 | 在每个阶段结束时强制执行测试 |

---

## 12. 验收标准

### 12.1 功能验收

- [ ] 所有原有功能正常工作（监控、预测、充电模式、日志、图表、导出）
- [ ] Demo模式可正常启动（无DLL环境）
- [ ] 配置文件修改后可动态生效（无需重启）
- [ ] 数据源切换不影响UI展示

### 12.2 架构验收

- [ ] 项目结构符合设计规范（分层清晰）
- [ ] 无循环依赖
- [ ] 核心服务可通过DI容器注入
- [ ] UI层无业务逻辑

### 12.3 质量验收

- [ ] 代码通过`mypy`类型检查
- [ ] 代码通过`ruff`风格检查
- [ ] 测试覆盖率≥80%
- [ ] 无新增的`print()`语句

---

**文档版本**: v1.0  
**创建日期**: 2026-07-16  
**适用版本**: Lenovo Battery Tool v3.0.0