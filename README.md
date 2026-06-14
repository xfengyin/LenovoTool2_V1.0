# Lenovo Battery Tool v2.0

Lenovo 笔记本电池监控、诊断与预测平台。  
Sunwoda 集团内部工具，仅供内部使用。

## 项目结构

```
LenovoTool2_V1.0/
├── src/lenovo_tool/
│   ├── core/                       # 核心层
│   │   ├── data_models.py          # 不可变数据模型
│   │   ├── dll_interface.py        # DLL 硬件通信线程安全封装
│   │   ├── dll_loader.py           # DLL 路径解析与验证
│   │   ├── exceptions.py           # 异常层次
│   │   ├── register_definitions.py # SMBus 寄存器目录
│   │   └── unit_definitions.py     # 寄存器单位定义
│   ├── services/                   # 业务服务层
│   │   ├── charge_mode.py          # 充电模式切换
│   │   ├── csv_export.py           # CSV 导出
│   │   ├── data_acquisition.py     # 实时数据采集
│   │   ├── life_prediction.py      # 电池寿命预测
│   │   └── log_data_service.py     # 全寄存器日志扫描
│   ├── ui/                         # PySide6 GUI
│   │   ├── main_window.py          # 主窗口
│   │   ├── log_window.py           # 日志数据窗口
│   │   ├── dialogs/                # 对话框
│   │   ├── styles/                 # QSS 样式
│   │   ├── widgets/                # 自定义控件
│   │   └── workers/                # 后台工作线程
│   ├── utils/                      # 工具模块
│   │   ├── byte_utils.py           # 字节操作工具
│   │   ├── config_manager.py       # YAML 配置管理
│   │   ├── constants.py            # 常量定义
│   │   └── logger_setup.py         # 日志配置
│   └── main.py                     # 应用入口
├── tests/                          # 单元测试
├── config/                         # 配置文件目录
├── Dockerfile                      # Docker 镜像
├── docker-compose.yml              # Docker Compose
└── pyproject.toml                  # 项目配置与依赖
```

## 快速开始

### 安装依赖

```bash
pip install -e ".[dev]"
```

### 运行应用

**GUI 模式（真实硬件）：**
```bash
python -m lenovo_tool.main
```

**Demo 模式（模拟数据，无需 DLL）：**
```bash
python -m lenovo_tool.main --demo
```

### Docker 运行

```bash
docker-compose up -d
```

## 核心模块说明

### 1. 硬件通信层

- **DLLInterface**: 线程安全的 SWD_EC.dll / Sunwoda.dll 封装
- **DLLLoader**: DLL 路径解析，支持多搜索路径
- **DemoDLLInterface**: 无硬件环境下的模拟数据接口

### 2. 数据采集与预测

- **DataAcquisitionService**: 原子性读取所有电池寄存器
- **LifePredictionService**: 基于寄存器 0x6A 位域的寿命预测
- **LogDataService**: 全量 SMBus 寄存器扫描

### 3. GUI 控件

- **ChartWidget**: pyqtgraph 实时滚动图表
- **GaugeWidget**: 自绘圆形仪表盘（寿命预测）
- **LCDDisplay**: LCD 数字显示 + 单位标签
- **BatteryDataPanel**: 温度/RSOC/SOH 进度条面板
- **PerformanceLimitsWidget**: PL1/PL2/PL4 功率限制显示

## 技术栈

| 组件 | 技术选型 | 用途 |
|------|---------|------|
| GUI Framework | PySide6 | 桌面应用程序 |
| Charts | pyqtgraph | 实时数据图表 |
| Config | PyYAML | YAML 配置管理 |
| Testing | pytest | 单元测试 |
| Linting | Ruff + mypy | 代码质量检查 |

## 开发规范

- 遵循 PEP 8 编码规范
- 使用 Black 格式化，Ruff 代码检查，MyPy 类型检查
- 所有公共模块必须包含 Google 风格 docstrings 和完整类型注解

## 测试

```bash
pytest tests/ --cov=lenovo_tool --cov-report=term-missing
```

覆盖率目标：>= 80%