# Opentrons Flex Python Protocol API 完整说明文档

> **目标读者**：使用 Opentrons Flex 机器人编写自动化生物实验协议的开发者
> **API 版本**：基于 Python Protocol API **v2.29**（最新版本）
> **来源**：Opentrons 官方文档 [docs.opentrons.com/python-api](https://docs.opentrons.com/python-api/)

---

## 目录

1. [Flex 协议基础](#1-flex-协议基础)
2. [协议上下文 ProtocolContext](#2-协议上下文-protocolcontext)
3. [甲板与槽位](#3-甲板与槽位)
4. [耗材 Labware 与适配器](#4-耗材-labware-与适配器)
5. [移液器 Pipettes](#5-移液器-pipettes)
6. [液体类 Liquid Classes](#6-液体类-liquid-classes)
7. [模块 Modules](#7-模块-modules)
   - 7.1 [Temperature Module（温度模块）](#71-temperature-module温度模块)
   - 7.2 [Thermocycler Module（热循环模块）](#72-thermocycler-module热循环模块)
   - 7.3 [Heater-Shaker Module（加热震荡器）](#73-heater-shaker-module加热震荡器)
   - 7.4 [Magnetic Block（磁力块，仅 Flex）](#74-magnetic-block磁力块仅-flex)
   - 7.5 [Absorbance Plate Reader（吸光度读卡器，仅 Flex）](#75-absorbance-plate-reader吸光度读卡器仅-flex)
   - 7.6 [Flex Stacker Module（Flex 堆栈模块，仅 Flex）](#76-flex-stacker-moduleflex-堆栈模块仅-flex)
8. [机器人控制 RobotContext](#8-机器人控制-robotcontext)
9. [抓手移动耗材](#9-抓手移动耗材)
10. [垃圾处理：TrashBin 与 WasteChute](#10-垃圾处理trashbin-与-wastechute)
11. [相机 capture_image](#11-相机-capture_image)
12. [并发任务、计时器与步骤分组](#12-并发任务计时器与步骤分组)
13. [运行时参数 Runtime Parameters](#13-运行时参数-runtime-parameters)
14. [完整 Flex 示例协议](#14-完整-flex-示例协议)
15. [协议仿真 Protocol Simulation](#15-协议仿真-protocol-simulation)
    - 15.1 [为什么需要仿真](#151-为什么需要仿真)
    - 15.2 [`opentrons.simulate` 模块](#152-opentronssimulate-模块)
    - 15.3 [`opentrons.execute` 模块 vs `opentrons.simulate`](#153-opentronsexecute-模块-vs-opentronssimulate)
    - 15.4 [`get_protocol_api()`：交互式仿真](#154-get_protocol_api交互式仿真)
    - 15.5 [Jupyter Notebook 仿真](#155-jupyter-notebook-仿真)
    - 15.6 [命令行工具 `opentrons_simulate`](#156-命令行工具-opentrons_simulate)
    - 15.7 [`is_simulating()`：运行时检测](#157-is_simulating运行时检测)
    - 15.8 [仿真中的 Labware 偏移](#158-仿真中的-labware-偏移)
    - 15.9 [仿真限制与差异](#159-仿真限制与差异)

---

## 1. Flex 协议基础

### 1.1 什么是 Opentrons Flex？

Opentrons Flex 是一台自动化液体处理机器人。Python Protocol API 是一个 Python 框架，让你通过 Python 代码控制 Flex 机器人、它的移液器、可选的硬件模块和抓手。

### 1.2 协议文件结构

```python
from opentrons import protocol_api

# metadata —— 协议元信息
metadata = {
    "protocolName": "My Flex Protocol",
    "author": "Name <opentrons@example.com>",
    "description": "示例协议",
}

# requirements —— 声明机器人类型与 API 版本
requirements = {"robotType": "Flex", "apiLevel": "2.29"}

# run 函数 —— 协议主体
def run(protocol: protocol_api.ProtocolContext):
    # 在这里编写 Flex 控制逻辑
    ...
```

### 1.3 Flex 与 OT-2 的关键差异

| 维度 | Flex | OT-2 |
|------|------|------|
| 甲板槽位 | A1-D4 坐标制（共 16 个） | 1-11 数字制（共 11 个） |
| 抓手 | ✅ Flex Gripper 标配 | ❌ 无 |
| 移液器 | 1/8/96 通道 Flex 系列 | 1/8 通道 GEN1/GEN2 |
| 96 通道移液器 | ✅ 支持 | ❌ 不支持 |
| 液体存在检测 | ✅ 基于压力传感器 | ❌ |
| 垃圾桶 | 可加载多个，最多可达第 1/3 列 | 仅槽位 12 固定垃圾桶 |
| 废液槽 | ✅ WasteChute（D3） | ❌ |
| 工作 + 暂存区 | 列 1-3 工作区；列 4 暂存区 | 无暂存区 |
| 液体类 v2.24 | ✅ 完整支持 | ⚠️ 受限 |
| `robot` 属性 v2.22 | ✅ RobotContext | ❌ |
| `capture_image` v2.27 | ✅ 相机 | ❌ |
| Absorbance Plate Reader | ✅ 仅 Flex | ❌ |
| Flex Stacker | ✅ 仅 Flex | ❌ |
| Magnetic Block | ✅ 仅 Flex | 改用 Magnetic Module |

> **API 自 v2.15 起**，Flex 协议中也支持 OT-2 数字格式（"10" / 10），反之亦然，但**不推荐混用**。

---

## 2. 协议上下文 ProtocolContext

`ProtocolContext` 是协议执行时的核心对象。所有顶层操作都通过它进行。

### 2.1 关键属性

| 属性 | 类型 | 引入版本 | 说明 |
|------|------|---------|------|
| `api_version` | `APIVersion` | v2.0 | 当前 API 版本 |
| `bundled_data` | `dict[str, bytes]` | v2.0 | 协议打包数据文件 |
| `deck` | `Deck` | v2.0 | 已加载甲板对象的视图 |
| `door_closed` | `bool` | v2.5 | Flex 前门是否关闭 |
| `fixed_trash` | `Labware \| TrashBin` | v2.0 | OT-2 槽 12 固定垃圾桶（Flex 默认 `None`） |
| `loaded_instruments` | `dict` | v2.0 | 已加载移液器字典 |
| `loaded_labwares` | `dict` | v2.0 | 已加载耗材字典 |
| `loaded_modules` | `dict` | v2.0 | 已加载模块字典 |
| `params` | `ParameterContext` | v2.18 | 运行时参数值 |
| `rail_lights_on` | `bool` | v2.5 | 环境灯是否开启 |
| `robot` | `RobotContext` | **v2.22** | Flex 运动系统上下文 |

### 2.2 协议级方法总览

| 方法 | 引入版本 | Flex 相关性 | 说明 |
|------|---------|------------|------|
| `load_labware()` | v2.0 | ✅ | 加载耗材 |
| `load_labware_from_definition()` | v2.0 | ✅ | 用自定义定义加载 |
| `load_adapter()` | v2.15 | ✅ | 加载适配器 |
| `load_adapter_from_definition()` | v2.15 | ✅ | 用自定义定义加载适配器 |
| `load_instrument()` | v2.0 | ✅ | 加载移液器 |
| `load_module()` | v2.0 | ✅ | 加载硬件模块 |
| `load_trash_bin()` | **v2.16** | ✅ Flex 专属 | 加载可移动垃圾桶 |
| `load_waste_chute()` | **v2.16** | ✅ Flex 专属 | 加载废液槽 |
| `load_lid_stack()` | **v2.23** | ✅ Flex 专属 | 加载 Opentrons 耐用自动密封盖堆叠 |
| `move_labware()` | v2.15 | ✅ Flex 推荐 | 移动耗材（支持抓手） |
| `move_lid()` | **v2.23** | ✅ Flex 专属 | 移动盖子（支持抓手） |
| `define_liquid()` | v2.14 | ✅ | 在协议中注册液体 |
| `define_liquid_class()` | **v2.24** | ✅ Flex 完整 | 定义自定义液体类 |
| `get_liquid_class()` | **v2.24** | ✅ Flex 完整 | 加载 Opentrons 验证的液体类 |
| `comment(msg)` | v2.0 | ✅ | 在运行日志中写一条说明 |
| `pause()` | v2.0 | ✅ | 暂停协议 |
| `resume()` | v2.0 ⚠️ v2.12+ 已弃用 | – | 推荐用 `pause()` + `comment()` |
| `delay()` | v2.0 | ✅ | 协议内同步延迟 |
| `home()` | v2.0 | ✅ | 归位 |
| `set_rail_lights(on)` | v2.5 | ✅ Flex 推荐 | 控制环境灯 |
| `is_simulating()` | v2.0 | ✅ | 是否正在模拟 |
| `commands` | v2.0 | ✅ | 协议运行日志 |
| `capture_image()` | **v2.27** | ✅ **Flex 专属** | 用 Flex 相机拍照 |
| `create_timer(seconds)` | **v2.27** | ✅ | 创建后台运行的 `Task` 定时器 |
| `wait_for_tasks()` | **v2.27** | ✅ | 等待一组任务完成 |
| `create_and_start_step_group()` | **v2.29** | ✅ | 启动一个步骤组 |
| `group_steps()` | **v2.29** | ✅ | `with` 风格的步骤组 |

### 2.3 v2.27 起的后台任务系统

```python
cool_task = module.start_set_temperature(celsius=4)
pipette.aspirate(50, plate["A1"])  # 同时等待
protocol.wait_for_tasks([cool_task])
```

返回的 `Task` 对象包含属性：
- `created_at` (property, v2.27) — 任务创建时间戳
- `started` (property, v2.27) — 是否已开始
- `done` (property, v2.27) — 是否完成
- `finished_at` (property, v2.27) — 完成时间戳

### 2.4 v2.29 起的步骤分组

```python
# 方式 1: with 语句
with protocol.group_steps("培养细胞"):
    pipette.aspirate(100, source_plate["A1"])
    pipette.dispense(100, dest_plate["A1"])

# 方式 2: 显式开始/结束
group = protocol.create_and_start_step_group("清洗步骤")
pipette.aspirate(200, wash_buffer["A1"])
pipette.dispense(200, plate["A1"])
group.end_group()
```

---

## 3. 甲板与槽位

### 3.1 甲板布局

```
        左                       右
   ┌──────────────────────────────┐
后 │  A1   A2   A3  │  A4 (暂存) │
   │  B1   B2   B3  │  B4 (暂存) │
   │  C1   C2   C3  │  C4 (暂存) │
前 │  D1   D2   D3  │  D4 (暂存) │
   └──────────────────────────────┘
```

- **工作区**：A1–C3（移液器和抓手均可到达）
- **暂存区**：A4–D4（仅抓手可到达，用于耗材/模块的存储或放置）

### 3.2 甲板装饰物与槽位限制

| 装饰物 | 允许槽位 | 说明 |
|--------|---------|------|
| Staging Area（暂存区槽） | A3–D3 | 每个 staging 槽占用第 4 列物理空间 |
| Trash Bin | A1–D1、A3–D3 | 一个或多个垃圾桶 |
| Waste Chute | 仅 D3 | 唯一支持位置 |

### 3.3 加载垃圾桶 `load_trash_bin()` v2.16

```python
default_trash = protocol.load_trash_bin(location="A3")

# 可加载多个：
left_trash = protocol.load_trash_bin("A3")
right_trash = protocol.load_trash_bin("B3")
left_pipette.trash_container = left_trash
right_pipette.trash_container = right_trash
```

> **注意**：Flex 协议 v2.15 中垃圾桶是隐式的；从 v2.16 开始必须在协议中显式加载。

### 3.4 加载废液槽 `load_waste_chute()` v2.16

```python
chute = protocol.load_waste_chute()
```

- **唯一位置**：D3
- **4 种甲板配置**：标准、带盖、带 staging slot、带 staging slot 和盖
- **何时需要移除盖子**：
  - 96 通道移液器要在废液槽上 `dispense()`、`blow_out()` 或 `drop_tip()`
  - `move_labware()` 用 `use_gripper=True` 移入废液槽

### 3.5 槽位冲突检查

Flex ≥ 7.1.0：协议运行前，App 和触摸屏会检查 **deck conflict**。例如：
- 在 C3 已加载模块时尝试加载 C4 staging slot → 冲突
- 加载 Stacker 到 A4 时不能再在 A3 加载垃圾桶

---

## 4. 耗材 Labware 与适配器

### 4.1 加载耗材 `load_labware()`

```python
plate = protocol.load_labware(
    load_name="corning_96_wellplate_360ul_flat",
    location="D1",
    label="Sample Plate",               # 可选人类可读标签
    lid="opentrons_flex_tiprack_lid"   # v2.23+ 可附带盖子
)
```

### 4.2 加载适配器 `load_adapter()` v2.15+

```python
hs_adapter = hs_mod.load_adapter("opentrons_96_flat_bottom_adapter")
hs_plate = hs_adapter.load_labware("nest_96_wellplate_200ul_flat")
```

适配器也可以加载到甲板槽位上：
```python
riser = protocol.load_adapter(
    load_name="opentrons_flex_deck_riser", location="A2"
)
```

### 4.3 加载盖子栈 `load_lid_stack()` v2.23+

```python
lid_stack = protocol.load_lid_stack(
    load_name="opentrons_tough_pcr_auto_sealing_lid",
    location="B2",
    quantity=4   # 最多 5
)
```

支持的 `load_name`：
- `opentrons_tough_pcr_auto_sealing_lid` — 耐用 PCR 自动密封盖（与 Thermocycler 配合）
- `opentrons_flex_tiprack_lid` — Flex tip rack 盖
- `opentrons_tough_universal_lid` — 通用 Opentrons 盖（v2.23+）

### 4.4 OFF_DECK：甲板外位置

```python
from opentrons import protocol_api

off_deck_plate = protocol.load_labware(
    "nest_96_wellplate_200ul_flat", location=protocol_api.OFF_DECK
)
```

`OFF_DECK` 也可作为 `move_labware()` 的 `new_location`。注意：**将耗材移至甲板外必须**手动（`use_gripper=False`），否则 API 会报错。

### 4.5 获取耗材中的内容

```python
plate["A1"]              # Well 对象
plate.wells()            # 所有孔
plate.wells_by_name()    # 名字→孔映射
plate.rows()             # 行的列表
plate.columns()          # 列的列表
plate.rows_by_name()["A"]# A 行
plate.columns_by_name()["1"]  # 第 1 列
```

### 4.6 井位坐标定位

```python
well.top()                    # 井口中心
well.top(z=-1)                # 井口下方 1mm
well.bottom()                 # 井底中心
well.bottom(z=2)              # 井底上方 2mm
well.center()                 # 中心
```

---

## 5. 移液器 Pipettes

### 5.1 Flex 移液器型号与 API 加载名

| 移液器 | 容量范围 | API load name |
|--------|---------|---------------|
| Flex 1-Channel | 1–50 µL | `flex_1channel_50` |
| Flex 1-Channel | 5–1000 µL | `flex_1channel_1000` |
| Flex 8-Channel | 1–50 µL | `flex_8channel_50` |
| Flex 8-Channel | 5–1000 µL | `flex_8channel_1000` |
| Flex 96-Channel | 1–200 µL | `flex_96channel_200` |
| Flex 96-Channel | 5–1000 µL | `flex_96channel_1000` |

> ⚠️ **96 通道移液器占两个挂载位**：`mount` 参数可不传（v2.16+），且不能与其他移液器共存。

### 5.2 加载移液器 `load_instrument()` v2.0+

```python
left = protocol.load_instrument(
    instrument_name="flex_1channel_1000",
    mount="left",
    tip_racks=[tiprack_1],
    liquid_presence_detection=True   # v2.20+，仅 Flex
)
```

参数说明：
- `instrument_name`: 上述 6 个 load name 之一
- `mount`: `"left"` 或 `"right"`（96 通道时可选）
- `tip_racks`: 可用吸头盒列表
- `liquid_presence_detection` (v2.20+)：是否全局开启液体检测，**仅 Flex**

### 5.3 移液器属性

| 属性 | 类型 | 引入版本 | 说明 |
|------|------|---------|------|
| `channels` | `int` | v2.0 | 1、8 或 96 |
| `active_channels` | `int` | v2.16 | 当前布局使用的通道数 |
| `mount` | `str` | v2.0 | `"left"` / `"right"` |
| `name` | `str` | v2.0 | v2.23+ 返回 API load name |
| `model` | `str` | v2.0 | 内部型号字符串 |
| `current_volume` | `float` | v2.0 | 当前吸头内的液体量（µL） |
| `max_volume` | `float` | v2.0 | 最大容积 |
| `min_volume` | `float` | v2.0 | 最小容积（随体积模式变化） |
| `flow_rate` | `FlowRates` | v2.0 | 含 `aspirate`、`dispense`、`blow_out` 三个字段 |
| `default_speed` | `float` | v2.0 | 龙门架移动速度（mm/s） |
| `has_tip` | `bool` | v2.7 | 是否装有吸头 |
| `tip_racks` | `list` | v2.0 | 关联吸头盒 |
| `starting_tip` | `Well \| None` | v2.0 | 自动选吸头的起始位置 |
| `current_tip_source_well` | `Optional[Well]` | v2.25 | 当前吸头来自哪个井 |
| `liquid_presence_detection` | `bool` | v2.20 | Flex 独占，是否全局启用液体检测 |
| `trash_container` | `TrashBin \| WasteChute` | v2.16 | 该移液器丢弃吸头的目标 |

### 5.4 移液器：液体处理方法

#### `aspirate()` v2.0
```python
pipette.aspirate(
    volume=None,                # 体积（µL），None = 吸满
    location=None,             # Well/Location，None = 当前位置
    rate=1.0,                   # 流速乘数
    flow_rate=None,             # 绝对流速 µL/s（v2.24+）
    end_location=None,          # v2.27+ 吸液中移动到的终点
    movement_delay=None,        # v2.27+ 吸液开始后延迟（秒）
)
```
> 仅传一个未命名参数会按 `volume` 解释；仅传位置需使用关键字。

#### `dispense()` v2.0
```python
pipette.dispense(
    volume=None,
    location=None,             # Well / Location / TrashBin / WasteChute / None
    rate=1.0,
    push_out=None,             # 分液后继续推出（µL），v2.15+
    flow_rate=None,            # v2.24+
    end_location=None,         # v2.27+
    movement_delay=None,       # v2.27+
)
```
> v2.17 起 `volume=0` 等于不分配；v2.16 及以前等同全部分配。
> v2.17 起超出当前液体量会报错。

#### `blow_out()` v2.0
```python
pipette.blow_out(location=None, flow_rate=None)  # flow_rate v2.28+
```
v2.16+ 起 `location` 可为 `TrashBin` / `WasteChute`。

#### `mix()` v2.0
```python
pipette.mix(
    repetitions=1,
    volume=None,
    location=None,
    rate=1.0,
    aspirate_flow_rate=None,   # v2.24+
    dispense_flow_rate=None,   # v2.24+
    aspirate_delay=None,       # v2.24+
    dispense_delay=None,       # v2.24+
    final_push_out=None,       # v2.24+
)
```

#### `air_gap()` v2.0
```python
pipette.air_gap(volume=None, height=None, in_place=None, rate=None, flow_rate=None)
```
v2.24+ 支持 `in_place=True` 在当前位置形成气垫。

#### `dynamic_mix()` v2.27
```python
pipette.dynamic_mix(
    aspirate_start_location=...,  # 必填
    dispense_start_location=...,  # 必填
    repetitions=1,
    volume=None,
    aspirate_end_location=None,
    dispense_end_location=None,
    rate=1.0,
    ...
)
```

#### `prepare_to_aspirate()` v2.16+
在吸液前将柱塞置于底部，必须在吹出/排空后调用。

### 5.5 移液器：吸头管理

#### `pick_up_tip()` v2.0
```python
pipette.pick_up_tip(
    location=None,            # Well / Labware / Location / None
    presses=None,             # v2.14 已弃用
    increment=None,           # v2.14 已弃用
    prep_after=None,          # v2.13+
)
```

#### `drop_tip()` v2.0
```python
pipette.drop_tip(
    location=None,            # Well / Location / TrashBin / WasteChute / None
    home_after=None,          # OT-2 默认 True
    alternate_drop_location=None,  # v2.28+
)
```

#### `return_tip()` v2.0
将当前吸头放回原位，不重置吸头跟踪（`Well.has_tip` 仍为 False）。

### 5.6 移液器：运动与位置

#### `move_to()` v2.0
```python
pipette.move_to(
    location,                 # Location / TrashBin / WasteChute
    force_direct=False,
    minimum_z_height=None,
    speed=None,
    publish=True,
)
```

> `force_direct=True` 会直线移动，**可能造成碰撞**，慎用。

#### `touch_tip()` v2.0
```python
pipette.touch_tip(
    location=None,
    radius=1.0,               # 距中心的比例
    v_offset=-1.0,            # 高度偏移（mm）
    speed=60.0,
    mm_from_edge=_Unset,      # v2.24+ 与 radius 互斥
)
```

#### `home()` / `home_plunger()`
- `pipette.home()`：归位机器人
- `pipette.home_plunger()`：仅归位该安装位柱塞（v2.0）

### 5.7 移液器：液体检测（**仅 Flex**）v2.20+

| 方法 | 引入版本 | 说明 |
|------|---------|------|
| `detect_liquid_presence(well)` | v2.20 | 返回 `bool` |
| `require_liquid_presence(well)` | v2.20 | 未检测到液体则报错 |
| `measure_liquid_height(well)` | v2.20 | 返回液体高度（mm） |
| `get_minimum_liquid_sense_height()` | v2.21 | 返回最低液面检测高度 |

> **传感器位置**：8 通道移液器仅通道 1（A1）和 8（H1）有传感器；96 通道仅通道 1（A1）和 96（H12）有传感器。

### 5.8 移液器：配置

#### `configure_for_volume()` v2.15
```python
pipette.configure_for_volume(volume=50)  # 例如 50 µL 进入低体积模式
```
> Flex `flex_1channel_50` / `flex_8channel_50` 必须设置低体积模式才能精准处理小体积。

#### `configure_nozzle_layout()` v2.16+
```python
pipette.configure_nozzle_layout(
    style=NozzleLayout,        # 必须
    start="A1",                # NozzleLayout 字符串
    end=None,                  # 仅 PARTIAL_COLUMN 需要
    tip_racks=None,            # 覆盖默认 tip_racks
)
```

支持的 `NozzleLayout` 枚举：

| 常量 | 适用移液器 | 引入版本 | 含义 |
|------|-----------|---------|------|
| `ALL` | 8/96 | v2.16 | 使用全部喷嘴（默认） |
| `COLUMN` | 96 | v2.16 | 8 个喷嘴，对应一列 |
| `ROW` | 96 | v2.20 | 12 个喷嘴，对应一行 |
| `PARTIAL_COLUMN` | 8 | v2.20 | 2–7 个连续喷嘴 |
| `SINGLE` | 8/96 | v2.20 | 单喷嘴 |

> **重要规则**：在 PARTIAL_COLUMN 模式下，不要将移液器移至耗材的 A 行（最前端喷嘴会悬空）。

#### 阶段吸头吸取最佳实践
- 进行 COL/ROW/SINGLE 配置时 **不要** 将吸头盒放在 tip-rack adapter 上
- 进行 ALL 配置时 **必须** 使用 tip-rack adapter

### 5.9 复杂液体命令（Complex Commands）

| 方法 | 引入版本 | 说明 |
|------|---------|------|
| `transfer()` | v2.0 | 多对一/一对多 transfer |
| `distribute()` | v2.0 | 一对多分发 |
| `consolidate()` | v2.0 | 多对一合并 |
| `distribute_with_liquid_class()` | **v2.24** | 按液体类分发（**仅 Flex**） |
| `consolidate_with_liquid_class()` | **v2.24** | 按液体类合并（**仅 Flex**） |

`new_tip` 选项：`"once"`（默认）、`"always"`、`"never"`。

---

## 6. 液体类 Liquid Classes（**Flex 完整支持**）

> **API v2.24** 引入液体类系统。OT-2 仅在受限形式下支持，**Flex 协议完整支持**。

### 6.1 内置液体类

通过 `protocol.get_liquid_class()` 获取：
- `water` — 水
- `glycerol_50` — 50% 甘油
- `ethanol_80` — 80% 乙醇

```python
water_class = protocol.get_liquid_class("water")
ethanol_class = protocol.get_liquid_class("ethanol_80")
```

### 6.2 自定义液体类 `define_liquid_class()` v2.24

为非 Opentrons 验证液体在协议内自定义类：
```python
my_liquid = protocol.define_liquid_class(
    name="custom_buffer",
    display_name="Custom Buffer",
    # 详细内容参考官方文档
)
```

### 6.3 定义液体信息 `define_liquid()` v2.14

```python
my_liquid = protocol.define_liquid(
    name="sample_buffer",
    description="Tris-HCl buffer",
    display_color="#FF00FF",
)
plate["A1"].load_liquid(liquid=my_liquid, volume=200)
```

### 6.4 使用液体类的转移

```python
water_class = protocol.get_liquid_class("water")
pipette.distribute_with_liquid_class(
    liquid_class=water_class,
    volume=100,
    source=reservoir["A1"],
    dest=[plate["A1"], plate["A2"], plate["A3"]],
    new_tip="once",
)
```

---

## 7. 模块 Modules

### 7.1 Temperature Module（温度模块）

```python
temp_mod = protocol.load_module(
    module_name="temperature module gen2",
    location="D3"
)
```

支持的模块名：
- `"temperature module gen1"` (v2.0)
- `"temperature module gen2"` (v2.3+)

#### 加载耗材

```python
# 加载适配器（推荐，v2.15+）
adapter = temp_mod.load_adapter("opentrons_96_well_aluminum_block")
plate = adapter.load_labware("nest_96_wellplate_100ul_pcr_full_skirt")

# 或加载 combination labware（v2.0+ 兼容旧版本）
combo = temp_mod.load_labware("opentrons_96_aluminumblock_nest_wellplate_100uL")
```

#### 温度控制

| 方法 | 引入版本 | 类型 | 说明 |
|------|---------|------|------|
| `set_temperature(celsius)` | v2.0 | **阻塞** | 等待达到目标温度 |
| `start_set_temperature(celsius)` | v2.3 (v2.27 起并发语义) | **并发** | 不等待，可与其他任务并行 |
| `deactivate()` | v2.0 | 阻塞 | 关闭加热/制冷和风扇 |
| `status` (property) | v2.3 | – | 返回 `"holding at target"` / `"cooling"` / `"heating"` / `"idle"` |
| `current_temperature` (property) | v2.0 | – | 当前温度（°C） |

阻塞示例：
```python
temp_mod.set_temperature(celsius=4)
pipette.aspirate(50, plate["A1"])
```

并发示例（v2.27+）：
```python
task = temp_mod.start_set_temperature(celsius=4)
pipette.aspirate(50, plate["A1"])  # 同时进行
pipette.dispense(50, plate["A1"])
protocol.wait_for_tasks([task])
```

### 7.2 Thermocycler Module（热循环模块）

```python
tc_mod = protocol.load_module(module_name="thermocyclerModuleV2")
plate = tc_mod.load_labware(name="opentrons_96_wellplate_200ul_pcr_full_skirt")
```

支持的模块名：
- `"thermocyclerModuleV1"` — GEN1
- `"thermocyclerModuleV2"` — v2.13+，GEN2

> **槽位**：唯一位置为 A1+B1（占用甲板左后两个工作区槽位，但不需要指定）

#### 盖子控制

| 方法 | 引入版本 | 类型 |
|------|---------|------|
| `open_lid()` | v2.0 | 阻塞 |
| `close_lid()` | v2.0 | 阻塞 |
| `set_lid_temperature(temperature)` | v2.0 | 阻塞 |
| `start_set_lid_temperature(temperature)` | **v2.27** | 并发 |
| `deactivate_lid()` | v2.0 | 阻塞 |

盖子温度范围：37–110 °C。

#### 温控块控制

| 方法 | 引入版本 | 类型 |
|------|---------|------|
| `set_block_temperature(temperature, hold_time_minutes, hold_time_seconds, ramp_rate, block_max_volume)` | v2.0 | 阻塞 |
| `start_set_block_temperature(temperature, ramp_rate, block_max_volume)` | **v2.27** | 并发 |
| `deactivate_block()` | v2.0 | 阻塞 |

温控块范围：4–99 °C。
`hold_time_minutes` / `hold_time_seconds`：可同时使用，时间相加。
`ramp_rate`（v2.28+）：°C/秒。
`block_max_volume`：用于准确控温的默认 25 µL。

#### Profile（温度循环）

Profile 由字典列表定义：
```python
profile = [
    {"temperature": 95, "hold_time_seconds": 30},
    {"temperature": 57, "hold_time_seconds": 30},
    {"temperature": 72, "hold_time_seconds": 60},
]
```

| 方法 | 引入版本 | 类型 |
|------|---------|------|
| `execute_profile(steps, repetitions, block_max_volume)` | v2.0 | 阻塞 |
| `start_execute_profile(steps, repetitions, block_max_volume)` | **v2.27** | 并发 |

完整 PCR 示例：
```python
tc_mod.set_lid_temperature(105)
tc_mod.execute_profile(
    steps=[
        {"temperature": 95, "hold_time_seconds": 30},
        {"temperature": 57, "hold_time_seconds": 30},
        {"temperature": 72, "hold_time_seconds": 60},
    ],
    repetitions=20,
    block_max_volume=32,
)
```

#### Auto-sealing lids（自动封膜）v2.16+ / v2.23+

```python
# 加载 riser
riser = protocol.load_adapter("opentrons_flex_deck_riser", "A2")

# 加载 lid 栈
lid_stack = riser.load_lid_stack(
    load_name="opentrons_tough_pcr_auto_sealing_lid",
    quantity=3
)

# 用抓手将 lid 移到板上
tc_mod.open_lid()
protocol.move_lid(
    source_location=lid_stack,
    new_location=plate,
    use_gripper=True
)
tc_mod.close_lid()
```

> GEN2 Thermocycler 自带 plate lift：可在打开盖子时长按 3 秒抬起板，便于取出。

### 7.3 Heater-Shaker Module（加热震荡器）

```python
hs_mod = protocol.load_module(
    module_name="heaterShakerModuleV1",
    location="D1"
)
```

> **Flex 槽位**：仅 1 列和 3 列（A3、C3 等）。在 A3 时需要先移动垃圾桶。

#### 闩锁与耗材加载

```python
hs_mod.open_labware_latch()
hs_mod.close_labware_latch()  # 摇晃前必须关闭

# v2.15+ 推荐先加载适配器
hs_adapter = hs_mod.load_adapter("opentrons_96_flat_bottom_adapter")
hs_plate = hs_adapter.load_labware("nest_96_wellplate_200ul_flat")
```

#### 温度控制

```python
# 阻塞
hs_mod.set_and_wait_for_temperature(celsius=75)
# 并发 (v2.27 起返回 Task)
task = hs_mod.set_target_temperature(celsius=75)
protocol.wait_for_tasks([task])
# 停用
hs_mod.deactivate_heater()
```

#### 摇晃

```python
hs_mod.set_and_wait_for_shake_speed(500)   # 阻塞
task = hs_mod.set_shake_speed(500)         # 并发，v2.27+
hs_mod.deactivate_shaker()
```

> 加热范围：37–95 °C；摇晃范围：200–3000 rpm。
> 协议结束后模块不会自动停用，需在 App 中手动停用。

### 7.4 Magnetic Block（磁力块，**仅 Flex**）

无源模块，仅靠永久磁铁吸住 beads。

```python
magnetic_block = protocol.load_module(
    module_name="magneticBlockV1",
    location="D1"
)
mag_plate = magnetic_block.load_labware(
    name="biorad_96_wellplate_200ul_pcr"
)

# 用抓手在模块和甲板之间移动
protocol.move_labware(mag_plate, new_location="B2", use_gripper=True)
```

> v2.15+ 引入。不支持 OT-2（OT-2 用 Magnetic Module）。

### 7.5 Absorbance Plate Reader（吸光度读卡器，**仅 Flex**）

```python
pr_mod = protocol.load_module(
    module_name="absorbanceReaderV1",
    location="D3"
)
```

> **槽位限制**：仅 A3–D3。模块 caddy 占据第 3 + 第 4 列；第 4 列不能有其他耗材。

#### 方法

| 方法 | 引入版本 | 说明 |
|------|---------|------|
| `open_lid()` | v2.21 | 移到第 4 列打开位置 |
| `close_lid()` | v2.21 | 移到第 3 列关闭位置 |
| `is_lid_on()` | v2.21 | 当前盖子是否在检测位 |
| `initialize(mode, wavelengths, reference_wavelength)` | v2.21 | 初始化读取参数 |
| `read(export_filename=None)` | v2.21 | 执行读取，返回 dict 或保存 CSV |

#### 完整工作流

```python
pr_mod = protocol.load_module("absorbanceReaderV1", "D3")
pr_mod.close_lid()                            # 1. 空载关闭
pr_mod.initialize(mode="single", wavelengths=[450])  # 2. 初始化
pr_mod.open_lid()                             # 3. 开盖

plate = some_labware                         # 已加载的孔板
protocol.move_labware(plate, pr_mod, use_gripper=True)  # 4. 放入板
pr_mod.close_lid()
pr_data = pr_mod.read()                      # 5. 读取
```

`mode` 选项：
- `"single"`：单波长，可指定 `reference_wavelength`
- `"multi"`：多波长（wavelengths 最多 6 项；不可指定 `reference_wavelength`）

读取结果数据结构（嵌套字典）：
```python
pr_data[450]["A1"]     # A1 在 450 nm 的 OD 值
pr_data[600]["H12"]    # H12 在 600 nm 的 OD 值
pr_data[450]           # 整板 450 nm 读数
```

### 7.6 Flex Stacker Module（Flex 堆栈模块，**仅 Flex**）

在 Flex 右侧（column 4）连接多达 4 个 Stacker，提供自动的吸头盒/孔板存储与分发。

```python
stacker_1 = protocol.load_module(
    module_name="flexStackerModuleV1", location="A4"
)
```

#### 配置存储内容

```python
stacker_1.set_stored_labware(
    load_name="opentrons_flex_96_tiprack_200ul",
    count=5,
    lid="opentrons_flex_tiprack_lid"
)
```

最大存储量：
- 7 个 Flex tip rack（栈中 6 个 + shuttle 上 1 个）
- 48 个 PCR 板
- 16 个深孔板

#### 取放与移动

```python
# 从 stacker 取一个到甲板
protocol.move_labware(
    labware=stacker_1.retrieve(),
    new_location="B2",
    use_gripper=True
)

# 将甲板上的板放回 stacker
protocol.move_labware(plate, stacker_1, use_gripper=True)
stacker_1.store()
```

#### Stacker 操作

| 方法 | 引入版本 | 说明 |
|------|---------|------|
| `set_stored_labware(load_name, count, lid)` | v2.25 | 配置种类与数量 |
| `set_stored_labware_items(labware)` | v2.25 | 直接列出要存的耗材 |
| `load_labware()` | v2.25 | 用 stacker/shuttle 作为常规槽位 |
| `retrieve()` | v2.25 | 取出一个到 shuttle |
| `store()` | v2.25 | 将 shuttle 上的耗材存入栈 |
| `fill(count, message)` | v2.25 | 暂停协议，让用户补足耗材 |
| `empty()` | v2.25 | 暂停协议，让用户清空 stacker |
| `get_max_storable_labware()` | v2.25 | 计算最多能存多少 |
| `get_current_storable_labware()` | v2.25 | 当前条件下能存多少 |
| `get_stored_labware()` | v2.25 | 当前栈内耗材列表 |

> **注意**：column 4 会被 stacker shuttle 占用，**该行的 column 3 不能加载模块或垃圾桶**。

---

## 8. 机器人控制 RobotContext（**仅 Flex**） v2.22+

通过 `protocol.robot` 访问 `RobotContext`，可单独控制 Flex 的运动系统。

```python
robot = protocol.robot
```

### 8.1 方法

| 方法 | 引入版本 | 说明 |
|------|---------|------|
| `close_gripper_jaw(force=None)` | v2.22 | 闭合抓手，force 单位牛顿 |
| `open_gripper_jaw()` | v2.22 | 完全打开抓手 |
| `move_to(mount, destination, speed=None)` | v2.22 | 移动指定 mount |
| `move_axes_to(axis_map, critical_point=None, speed=None)` | v2.22 | 绝对位置移动 |
| `move_axes_relative(axis_map, speed=None)` | v2.22 | 相对位置移动 |
| `axis_coordinates_for(mount, location)` | v2.22 | 由 location 构建轴坐标 |
| `build_axis_map(axis_map)` | v2.22 | 把字符串轴映射转字典 |
| `plunger_coordinates_for_named_position(mount, position_name)` | v2.22 | 柱塞命名位置（top/bottom/blowout/drop） |
| `plunger_coordinates_for_volume(mount, volume, action)` | v2.22 | 柱塞按体积与动作（aspirate/dispense） |

### 8.2 可控轴

`axis_map` 字典支持的键：`"x"`、`"y"`、`"z_l"`、`"z_r"`、`"z_g"`、`"q"`。大小写不敏感。

### 8.3 `mount` 参数

支持字符串或 `Mount` 枚举：
- `"left"` / `"right"` — 移液器
- `"extension"` / `"gripper"` — 抓手（两个字符串都指向同一挂载位）

### 8.4 使用示例

#### 通过位置构建轴坐标并移动
```python
from opentrons import protocol_api
from opentrons.types import Mount

requirements = {"robotType": "Flex", "apiLevel": "2.22"}

def run(protocol: protocol_api.ProtocolContext):
    robot = protocol.robot
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D1")
    left = protocol.load_instrument("flex_1channel_1000", mount="left")

    # 计算到 plate["A1"] 顶部的轴坐标
    coords = robot.axis_coordinates_for(Mount.LEFT, plate["A1"].top())
    robot.move_axes_to(coords)
```

#### 相对移动
```python
robot.move_axes_relative({"x": 5, "y": -5})   # 相对当前位置移动
```

#### 抓手控制
```python
robot.open_gripper_jaw()
robot.close_gripper_jaw(force=10)   # 10 N
```

#### 柱塞精确控制
```python
top_pos = robot.plunger_coordinates_for_named_position(
    "left", "top"
)
robot.move_axes_to(top_pos)
```

---

## 9. 抓手移动耗材

### 9.1 `move_labware()` v2.15

```python
protocol.move_labware(
    labware=plate,
    new_location="D2",
    use_gripper=False,        # True = 抓手；False/None = 手动（暂停等用户）
    pick_up_offset=None,      # 可选微调
    drop_offset=None,
    grip_force=None,
)
```

- `use_gripper=True`：Flex 抓手自动移动。**OT-2 协议中会报错**。
- `use_gripper=False` 或缺省：暂停协议，等待用户在触摸屏上确认手动移动后继续。

### 9.2 抓手支持的耗材类型

- 全裙 PCR 板（armadillo、opentrons）
- NEST 96 孔 200 µL 平板 / 2 mL 深孔板
- Opentrons Flex 96 tip rack 及带滤芯版本
- Opentrons 耐用 PCR 自动密封盖 / Flex tip rack 盖

### 9.3 与模块一起移动耗材

将耗材放到模块上时，`new_location` 必须是**最顶层未占用对象**：

```python
hs_adapter = hs_mod.load_adapter("opentrons_96_flat_bottom_adapter")
hs_mod.open_labware_latch()
protocol.move_labware(plate, hs_adapter, use_gripper=True)
```

### 9.4 移入废液槽

```python
chute = protocol.load_waste_chute()
protocol.move_labware(plate, chute, use_gripper=True)   # 必须是 True
```

### 9.5 `move_lid()` v2.23+

```python
protocol.move_lid(
    source_location=lid_stack,    # lid 栈 / 板 / 适配器
    new_location=plate,           # 目标板
    use_gripper=True
)
```

> 已用完的 lid 可用 `move_lid()` 移到 trash bin 或 waste chute 处置。

### 9.6 移至甲板外

```python
protocol.move_labware(plate, protocol_api.OFF_DECK)   # 不允许 use_gripper=True
```

---

## 10. 垃圾处理：TrashBin 与 WasteChute

### 10.1 Trash Bin（可移动垃圾桶）v2.16+

- **可加载多个**，每个 Flex 推荐放 1 或 3 列槽
- 不加载垃圾桶而使用相关功能将报错
- 通过 `pipette.trash_container` 可为不同移液器指定不同的垃圾桶

```python
chute = protocol.load_waste_chute()
trash = protocol.load_trash_bin("A3")
left_pipette.trash_container = trash   # 覆盖默认
```

### 10.2 Waste Chute（废液槽）v2.16+

- **唯一位置：D3**
- 1/8 通道移液器可以透过盖口分液、吹出或丢弃吸头
- 96 通道移液器需移除盖子才能分液/吹出/丢吸头
- 移入耗材时必须 `use_gripper=True`

### 10.3 通用规则

- `pipette.drop_tip(location=trash_or_chute, ...)`
- `pipette.blow_out(location=trash_or_chute)`
- 1 通道和 8 通道移液器可以在 chute 盖子开口处分液
- Chute 与 staging area slot（D3 + D4）可共存（需特殊 deck plate adapter 配置）

---

## 11. 相机 capture_image（**仅 Flex**） v2.27+

Flex 配备顶部相机；可以在协议中拍照（例如记录板状态）。

```python
protocol.capture_image(
    filename="step1_after_mixing",
    resolution=(1920, 1080),       # 默认
    zoom=2.0,                      # 缩放倍数
    contrast=0.0,                  # -1.0 至 1.0
    brightness=0.0,
    saturation=0.0,
    home_before=True,              # 拍照前是否归位
)
```

- 返回类型：根据实现可能是图像数据 / 文件句柄 / 标签
- `home_before=False` 可避免归位时延
- 常配合 `pause()` 记录关键步骤

---

## 12. 并发任务、计时器与步骤分组

### 12.1 Task 类 v2.27+

在协议后台运行的对象。`aspirate/dispense` 之外，许多模块方法在 v2.27 后返回 `Task`，让您并行做其他事情。

| 属性 | 说明 |
|------|------|
| `created_at` (property) | 任务创建时间 |
| `started` (property) | 是否已开始执行 |
| `done` (property) | 是否已完成 |
| `finished_at` (property) | 完成时间戳（None = 还没完） |

### 12.2 `create_timer()` v2.27+

创建独立的后台计时器：

```python
timer = protocol.create_timer(seconds=300)  # 5 分钟
# ... 同时做别的
protocol.wait_for_tasks([timer])
```

### 12.3 `wait_for_tasks()` v2.27+

```python
cool = module.start_set_temperature(celsius=4)
pipette.aspirate(50, plate["A1"])
pipette.dispense(50, plate["A1"])
pipette.drop_tip()
protocol.wait_for_tasks([cool])   # 等到温度到
```

### 12.4 Step Grouping（步骤分组）v2.29+

用于在 App 端产生清晰的步骤折叠：

```python
# with 风格
with protocol.group_steps("细胞培养加样"):
    pipette.aspirate(100, source["A1"])
    pipette.dispense(100, dest["A1"])

# 显式风格
group = protocol.create_and_start_step_group("PCR 体系配制")
# ... 一系列 pipette / 模块操作
group.end_group()
```

---

## 13. 运行时参数 Runtime Parameters

API v2.18 引入。在 Opentrons App 端可以由用户在协议运行前配置变量，例如样本数、处理的孔等。

```python
def add_parameters(parameters):
    parameters.int(
        name="sample_count",
        display_name="Samples to process",
        default=24,
        minimum=1,
        maximum=96,
    )
    parameters.str(
        name="diluent",
        display_name="Diluent type",
        choices=[{"display_name": "Water", "value": "water"},
                 {"display_name": "Buffer", "value": "buffer"}],
        default="water",
    )

def run(protocol):
    sample_count = protocol.params.sample_count
    diluent = protocol.params.diluent
    # ...
```

常用参数类型：
- `parameters.int(...)`：整数
- `parameters.str(...)`：字符串
- `parameters.float(...)`：浮点
- `parameters.bool(...)`：布尔
- `parameters.csv(...)`：CSV 文件，运行时作为 CSVParameter 注入

---

## 14. 完整 Flex 示例协议

下面是一个综合示例，展示本说明文档中提到的核心能力：

```python
from opentrons import protocol_api

requirements = {"robotType": "Flex", "apiLevel": "2.29"}

def run(protocol: protocol_api.ProtocolContext):
    # ---------- 1. 加载耗材与适配器 ----------
    tip_rack = protocol.load_labware(
        "opentrons_flex_96_tiprack_200ul", location="B2"
    )
    reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml", location="A2"
    )
    sample_plate = protocol.load_labware(
        "corning_96_wellplate_360ul_flat", location="C2"
    )

    # ---------- 2. 加载模块 ----------
    temp_mod = protocol.load_module("temperature module gen2", location="D1")
    temp_adapter = temp_mod.load_adapter("opentrons_96_well_aluminum_block")
    temp_plate = temp_adapter.load_labware(
        "opentrons_96_wellplate_100ul_pcr_full_skirt"
    )

    hs_mod = protocol.load_module("heaterShakerModuleV1", location="C1")
    hs_adapter = hs_mod.load_adapter("opentrons_96_flat_bottom_adapter")
    hs_plate = hs_adapter.load_labware("nest_96_wellplate_200ul_flat")

    # 吸光度读卡器（仅 Flex）
    plate_reader = protocol.load_module("absorbanceReaderV1", location="D3")
    plate_reader.close_lid()
    plate_reader.initialize(mode="single", wavelengths=[450])

    # ---------- 3. 加载 Flex Stacker ----------
    stacker = protocol.load_module("flexStackerModuleV1", location="A4")
    stacker.set_stored_labware(
        load_name="opentrons_flex_96_tiprack_200ul",
        count=5,
        lid="opentrons_flex_tiprack_lid",
    )

    # ---------- 4. 加载垃圾处理 ----------
    trash = protocol.load_trash_bin("A3")

    # ---------- 5. 加载移液器 ----------
    left = protocol.load_instrument(
        "flex_1channel_1000", mount="left", tip_racks=[tip_rack]
    )
    right = protocol.load_instrument(
        "flex_8channel_1000", mount="right", tip_racks=[tip_rack]
    )

    # ---------- 6. 准备温度模块（并发） ----------
    cool_task = temp_mod.start_set_temperature(celsius=4)

    # ---------- 7. Heater-Shaker 加热 ----------
    heat_task = hs_mod.set_target_temperature(celsius=37)
    protocol.wait_for_tasks([heat_task])

    # ---------- 8. 步骤分组 ----------
    with protocol.group_steps("向 Heater-Shaker 加样"):
        left.pick_up_tip()
        left.aspirate(50, reservoir["A1"])
        left.dispense(50, hs_plate["A1"])
        left.drop_tip()

    # ---------- 9. 使用液体类分发 ----------
    water = protocol.get_liquid_class("water")
    right.distribute_with_liquid_class(
        liquid_class=water,
        volume=20,
        source=reservoir["A2"],
        dest=sample_plate.wells(),
        new_tip="once",
    )

    # ---------- 10. 用抓手把完成的板移至 reader ----------
    plate_reader.open_lid()
    protocol.move_labware(sample_plate, plate_reader, use_gripper=True)
    plate_reader.close_lid()
    od_data = plate_reader.read(export_filename="od_results")
    plate_reader.open_lid()
    protocol.move_labware(sample_plate, protocol_api.OFF_DECK)

    # ---------- 11. 拍照记录 ----------
    protocol.comment("Final state recorded.")
    protocol.capture_image(
        filename="final_state",
        zoom=1.0,
    )

    # ---------- 12. 收尾 ----------
    protocol.wait_for_tasks([cool_task])
    temp_mod.deactivate()
    hs_mod.deactivate_heater()
    hs_mod.deactivate_shaker()
    rail_lights = True
    protocol.set_rail_lights(False)
    protocol.comment("Protocol complete.")
```

---

## 15. 协议仿真 Protocol Simulation

Opentrons Python Protocol API 提供两套入口，可以在**不接触真实机器人**的情况下运行 Flex 协议：

1. **`opentrons.simulate`** — 完全离线的协议仿真库
2. **`opentrons.execute`** — 在真实机器人上运行协议的入口（也可走仿真路径）

外加三个常用仿真渠道：
- **Jupyter Notebook** — 在 Flex 自带的 Jupyter 中以单元(cell)粒度交互式仿真
- **命令行工具 `opentrons_simulate`** — 终端一键仿真
- **`is_simulating()`** — 在协议内部检测当前是否处于仿真环境

> ⚠️ 本文只覆盖 **Flex** 协议下的仿真行为。

### 15.1 为什么需要仿真

- 离线开发：在没有 Flex 机器人的环境下，验证协议逻辑
- 单元/集成测试：CI 流水线中检查协议能否完成
- 调参：反复尝试移液体积、混合次数、液体类参数等
- 错误排查：协议运行前的早期错误捕获

### 15.2 `opentrons.simulate` 模块

主入口：构建一个连接到**虚拟硬件**的 `ProtocolContext`，或从外部文件仿真整段协议。

#### `get_protocol_api()` — 拿到仿真用的 ProtocolContext

```python
get_protocol_api(
    version: str | APIVersion,
    bundled_labware: dict[str, LabwareDefinition] | None = None,
    bundled_data:  dict[str, bytes] | None = None,
    extra_labware: dict[str, LabwareDefinition] | None = None,
    hardware_simulator: ThreadManagedHardware | None = None,
    *,
    robot_type: str | None = None,                # 关键！Flex 还是 OT-2
    use_virtual_hardware: bool = True,            # 内部使用
) -> protocol_api.ProtocolContext
```

参数说明：

| 参数 | 说明 |
|------|------|
| `version` | API 版本字符串（如 `"2.29"`）或 `APIVersion(2, 29)` |
| `bundled_data` | 注入协议可通过 `protocol.bundled_data` 访问的文件映射 |
| `extra_labware` | 自定义耗材定义目录 |
| `robot_type` | **`"Flex"` 或 `"OT-2"`**。在真实机器人上调用时默认为该机器人；离线调用时为 **向后兼容默认 OT-2**，因此 Flex 协议必须显式传 `"Flex"` |
| `use_virtual_hardware` | 内部使用，控制是否走 Protocol Engine 虚拟硬件 |
| `hardware_simulator` | 内部使用，复用已有硬件模拟器实例 |

#### `simulate()` — 一站式仿真协议文件

```python
from opentrons.simulate import simulate, format_runlog

with open("my_protocol.py", "rb") as f:
    runlog, bundle = simulate(f, file_name="my_protocol.py")

print(format_runlog(runlog))
```

参数：

| 参数 | 说明 |
|------|------|
| `protocol_file` | 类文件对象 |
| `file_name` | 文件名（用于解析器） |
| `custom_labware_paths` | 自定义耗材搜索目录列表 |
| `custom_data_paths` | 自定义 data 文件目录或文件列表 |
| `propagate_logs` | 是否把日志传到根记录器 |
| `log_level` | `"debug" / "info" / "warning" / "error"`（默认 `warning`） |
| `hardware_simulator_file_path` | **仅内部使用**，仿真时无需传 |
| `duration_estimator` | **仅内部使用** |

返回 `_SimulateResult`，包含：
1. **运行日志**（run log）—— 命令字典列表，每条命令形如：
   ```python
   {
       "level": 1,                          # 嵌套深度（aspirate 嵌在 transfer 嵌在 mix 中则 depth=3）
       "payload": {"text": "...", ...},    # 命令内容，文本在 payload["text"]
       "logs": [<LogRecord>, ...]           # 该命令产生的 Python 日志
   }
   ```
2. **打包数据**（仅在为 `PythonProtocol` 且 `allow_bundle()` 为 True 时返回）

> ⚠️ 在新版本中 `payload["text"]` **不是 format string**，不要 `.format()` 它（包含 `{` `}` 会抛 `KeyError`）。

#### `format_runlog()` 与 `bundle_from_sim()`

```python
from opentrons.simulate import format_runlog, bundle_from_sim

# 把运行日志渲染成人类可读字符串
text = format_runlog(runlog)

# 把已仿真完毕的 Protocol + Context 转成打包数据
bundle = bundle_from_sim(protocol_obj, context)
```

#### `allow_bundle()` / `get_arguments()` / `main()`

- `allow_bundle()`：返回是否允许打包（受环境变量 `OT_API_FF_allowBundleCreation=1` 控制）
- `get_arguments(parser)`：给现有 argparse 解析器添加 simulate 的 CLI 参数
- `main()`：命令行入口，返回 shell 返回码

### 15.3 `opentrons.execute` 模块 vs `opentrons.simulate`

| 维度 | `opentrons.execute` | `opentrons.simulate` |
|------|--------------------|---------------------|
| 用途 | 在 Flex/OT-2 上真实执行 | 完全离线仿真 |
| `execute()` / `simulate()` 返回 | `None`（或抛错） | `(runlog, bundle)` 元组 |
| 是否需要 `protocol_name` | ✅ 需要 | ❌ 用 `file_name` |
| `emit_runlog` 回调 | ✅ 提供，实时打印每条命令 | ❌ 不提供（返回完整 runlog） |
| `robot_type` 参数 | ❌ 不存在 | ✅ 存在 |
| `hardware_simulator_file_path` | ❌ | ✅ 内部使用 |
| `duration_estimator` | ❌ | ✅ 内部使用 |
| `use_virtual_hardware` | ❌ | ✅ 内部使用 |

`opentrons.execute.get_protocol_api()` 是 Jupyter/SSH 路径上用的版本，没有仿真专用参数。

### 15.4 `get_protocol_api()`：交互式仿真

```python
from opentrons.simulate import get_protocol_api

protocol = get_protocol_api("2.29", robot_type="Flex")
protocol.home()

tiprack = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "B2")
plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "C2")
right = protocol.load_instrument("flex_1channel_1000", "right", tip_racks=[tiprack])
protocol.comment("Connected to simulated Flex.")
```

> **Flex 必填**：`robot_type="Flex"`，否则按 OT-2 处理，将无法加载 Flex-only 的 load name（如 `flex_96channel_1000`、Magnetic Block 等）。

### 15.5 Jupyter Notebook 仿真

Flex 自带 Jupyter Notebook 服务，端口 **48888**，访问方式：
- Robot Settings → Advanced → Launch Jupyter Notebook
- 或直接 `http://<robot-ip>:48888`

在 Jupyter 中打开并以 cell 为单位逐段仿真：

```python
import opentrons.execute
protocol = opentrons.execute.get_protocol_api("2.29")
protocol.home()
```

> 第一个命令必须 `home()`，否则会抛 `MustHomeError`（App 自动 home，但 Jupyter/SSH 下不会）。

#### 运行已写好的协议

```python
import opentrons.execute
from opentrons import protocol_api

def run(protocol: protocol_api.ProtocolContext):
    # 已写好的协议主体（仅定义不调用）
    tiprack = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "B2")
    left = protocol.load_instrument("flex_1channel_1000", "left", tip_racks=[tiprack])

# 在新 cell 中启动仿真
protocol = opentrons.execute.get_protocol_api("2.29")
run(protocol)   # 此时才会真正移动
```

#### Flex 协议的特殊注意

- `set_offset()` 在 Flex 上**跨槽位依旧生效**（同 labware type 即可，参考 §15.8）
- 不要让 Jupyter 在 robot server 运行期间给模块发命令，会冲突；用 Terminal 运行 `systemctl stop opentrons-robot-server`，结束再用 `systemctl start opentrons-robot-server`
- 自定义 labware 放在 Jupyter 的 `labware/` 子目录即可被自动发现

### 15.6 命令行工具 `opentrons_simulate`

终端一键仿真：

```bash
# 最简单：
opentrons_simulate my_protocol.py

# 设置日志级别：
opentrons_simulate --log-level=info my_protocol.py

# 把日志一并打到 stderr：
opentrons_simulate --propagate-log my_protocol.py

# 或直接走 Python：
python -m opentrons.simulate my_protocol.py
```

命令会自动调用 `simulate()` 并默认打印 stdout 中的运行日志。

### 15.7 `is_simulating()`：运行时检测

在 `ProtocolContext` 上调用 `is_simulating()` 判断当前是否处于仿真环境（v2.0+）：

```python
def run(protocol):
    if protocol.is_simulating():
        protocol.comment("Running in simulation — skipping camera.")
    else:
        protocol.capture_image(filename="start")
```

用途：
- 跳过只能在真实机器人执行的命令（如相机拍照、液体检测）
- 决定是否发出网络请求、文件 I/O 等副作用操作
- 为仿真/真实运行走不同代码路径

### 15.8 仿真中的 Labware 偏移

Flex 协议在 App 中运行时会跑 **Labware Position Check** 自动产生偏移；但在 Jupyter / SSH / `opentrons_execute` / `opentrons_simulate` 中**不会**自动产生——你需要用 `set_offset()` 手动写入偏移（v2.12+）。

#### 推荐的"哑协议"流程

1. **写一个最小协议** —— 只加载你需要测偏移的 labware 与最小量程的 pipette，并 `pick_up_tip()` 一次（OT-2 上不做这步将无法运行 LPC）
   ```python
   metadata = {"apiLevel": "2.29"}
   def run(protocol):
       tiprack = protocol.load_labware(
           "opentrons_flex_96_tiprack_1000ul", "B2")
       reservoir = protocol.load_labware(
           "nest_12_reservoir_15ml", "A2")
       plate = protocol.load_labware(
           "nest_96_wellplate_200ul_flat", "C2")
       p1000 = protocol.load_instrument(
           "flex_1channel_1000", "left", tip_racks=[tiprack])
       p1000.pick_up_tip()
       p1000.return_tip()
   ```
2. 上传到 App，做 Labware Position Check，复制自动生成的 `set_offset()` 代码
3. 把它们加到你的 Jupyter/仿真脚本中：
   ```python
   tiprack.set_offset(x=0.00, y=0.00, z=0.00)
   reservoir.set_offset(x=0.10, y=0.20, z=0.30)
   plate.set_offset(x=0.10, y=0.20, z=0.30)
   ```

#### Flex vs OT-2 的偏移行为差异

| 维度 | Flex | OT-2 |
|------|------|------|
| 跨槽位复用 | ✅ 同一 labware type 在 Flex 甲板任意位置都继承同一偏移 | ❌ 同一 labware type 必须在同一槽位 |
| 移出再移回 | 离开甲板（`OFF_DECK`）时偏移"剥离" | 跨槽位移动后偏移丢失，需重新调用 `set_offset()` |

例（Flex）：
```python
tiprack.set_offset(x=0.1, y=0.1, z=0.1)
protocol.move_labware(tiprack, protocol_api.OFF_DECK)        # 离开甲板，偏移被剥离
protocol.move_labware(tiprack2, "B3")                       # tiprack2 自动继承同偏移
```

例（OT-2）：
```python
plate.set_offset(x=-0.1, y=-0.2, z=-0.3)
protocol.move_labware(plate, "3")                            # 偏移归零
plate.set_offset(x=-0.1, y=-0.2, z=-0.3)                    # 必须重设
```

> ⚠️ 偏移不要跨协议混用，可能导致碰撞。如果不确定请重新跑 Labware Position Check。

### 15.9 仿真限制与差异

仿真和真实执行 **不完全等同**，下面是常见的差异点：

| 行为 | 仿真中 | 真实机器人 |
|------|--------|-----------|
| `capture_image()` | 立即成功（不生成图像） | 真实拍照，写入运行日志 |
| `liquid_presence_detection` / `detect_liquid_presence()` | 始终返回 `True` | 真实压力传感器判断 |
| `measure_liquid_height()` | 返回合理值（虚拟液面） | 真实测量 |
| `create_timer()` / `start_set_*()` | 任务几乎瞬时完成 | 真实耗时 |
| `capture_image(zoom/resolution)` 等相机参数 | 不生效 | 真实生效 |
| `pause()` | 立即继续 | 等待用户在 App/触摸屏 Resume |
| `move_labware(use_gripper=True)` | 走虚拟抓手 | 真实抓手 |
| 液体处理体积、混合次数 | 严格按指定 | 真实世界误差 |
| 自动 Labware Position Check | ❌ 跳过，需手动 `set_offset()` | ✅ App 自动跑 |
| 模块错误（温度超范围、盖未关好等） | 多数不会被仿真触发 | 真实报错 |

> 💡 **经验法则**：通过 `protocol.is_simulating()` 把不可仿真副作用（相机、IO、网络请求等）分支处理；让协议代码尽可能"在两个世界都安全"。

#### 一个完整的仿真示例

```python
# 终端或 IDE 内运行
from opentrons.simulate import get_protocol_api, simulate, format_runlog

# 路径 1：交互式
protocol = get_protocol_api("2.29", robot_type="Flex")
protocol.home()
plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "C2")
tiprack = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "B2")
right = protocol.load_instrument("flex_1channel_1000", "right", tip_racks=[tiprack])

assert protocol.is_simulating()       # True
right.pick_up_tip()
right.aspirate(100, plate["A1"])
right.dispense(100, plate["A2"])
right.drop_tip()
print(format_runlog(protocol.commands()))

# 路径 2：直接对协议文件做整体仿真
with open("my_protocol.py", "rb") as f:
    runlog, _ = simulate(f, file_name="my_protocol.py")
print(format_runlog(runlog))
```

---

## 附录：API 版本里程碑（仅 Flex 相关能力）

| 版本 | 重要 Flex 能力 |
|------|---------------|
| v2.0 | Flex 基本协议架构；移液器基础方法；模块基础 |
| v2.5 | `door_closed`、`rail_lights_on`、`set_rail_lights()` |
| v2.13 | Heater-Shaker 支持；Thermocycler GEN2 |
| v2.14 | `define_liquid()`；`max_speeds` 标记弃用 |
| v2.15 | `use_gripper` 自动移动；`MagneticBlockV1`；`flex_96channel_1000`；`configure_for_volume()` |
| v2.16 | `load_trash_bin()`、`load_waste_chute()`；TrashBin/WasteChute 在移液器命令中支持；`configure_nozzle_layout()`；`prepare_to_aspirate()` |
| v2.18 | 运行时参数 |
| v2.20 | 液体存在检测；Partial nozzle layouts（Row/Single/Partial Column） |
| v2.21 | `AbsorbanceReaderV1` 模块；`get_minimum_liquid_sense_height()` |
| v2.22 | `protocol.robot` (`RobotContext`)；单轴控制 |
| v2.23 | `load_lid_stack()`；`move_lid()` |
| v2.24 | 液体类系统（`define_liquid_class()`、`get_liquid_class()`） |
| v2.25 | `FlexStackerModuleV1` |
| v2.27 | `capture_image()`；`create_timer()`；`wait_for_tasks()`；并发模块操作 |
| v2.28 | `alternate_drop_location`；20 µL tip-rack 支持；`ramp_rate` for Thermocycler |
| **v2.29** | `group_steps()`、`create_and_start_step_group()`；`ThermocyclerContext` 中的 `current_cycle` 等 |

---

## 关键链接速查

- 教程：https://docs.opentrons.com/python-api/tutorial/
- Protocol API Reference：https://docs.opentrons.com/python-api/reference/protocols/
- 移液器参考：https://docs.opentrons.com/python-api/reference/instruments/
- 模块：
  - Temperature: https://docs.opentrons.com/python-api/reference/temperature-module/
  - Thermocycler: https://docs.opentrons.com/python-api/reference/thermocycler/
  - Heater-Shaker: https://docs.opentrons.com/python-api/reference/heater-shaker/
  - Magnetic Block: https://docs.opentrons.com/python-api/reference/magnetic-block/
  - Absorbance Reader: https://docs.opentrons.com/python-api/reference/absorbance-plate-reader/
  - Flex Stacker: https://docs.opentrons.com/python-api/reference/flex-stacker/
- 机器人电机：https://docs.opentrons.com/python-api/reference/robot-motors/
- Labware 库：https://labware.opentrons.com/
- 运行时参数：https://docs.opentrons.com/python-api/runtime-parameters/using-values/
- 移动耗材：https://docs.opentrons.com/python-api/moving-labware/
- 部分吸头吸取：https://docs.opentrons.com/python-api/pipettes/partial-tip-pickup/
- 液体类：https://docs.opentrons.com/python-api/liquids/
- **仿真与执行：https://docs.opentrons.com/python-api/reference/execute-simulate/**
- **高级控制：https://docs.opentrons.com/python-api/advanced-control/**
  - Jupyter Notebook：https://docs.opentrons.com/python-api/advanced-control/jupyter/
  - 命令行：https://docs.opentrons.com/python-api/advanced-control/command-line/

- 教程：https://docs.opentrons.com/python-api/tutorial/
- Protocol API Reference：https://docs.opentrons.com/python-api/reference/protocols/
- 移液器参考：https://docs.opentrons.com/python-api/reference/instruments/
- 模块：
  - Temperature: https://docs.opentrons.com/python-api/reference/temperature-module/
  - Thermocycler: https://docs.opentrons.com/python-api/reference/thermocycler/
  - Heater-Shaker: https://docs.opentrons.com/python-api/reference/heater-shaker/
  - Magnetic Block: https://docs.opentrons.com/python-api/reference/magnetic-block/
  - Absorbance Reader: https://docs.opentrons.com/python-api/reference/absorbance-plate-reader/
  - Flex Stacker: https://docs.opentrons.com/python-api/reference/flex-stacker/
- 机器人电机：https://docs.opentrons.com/python-api/reference/robot-motors/
- Labware 库：https://labware.opentrons.com/
- 运行时参数：https://docs.opentrons.com/python-api/runtime-parameters/using-values/
- 移动耗材：https://docs.opentrons.com/python-api/moving-labware/
- 部分吸头吸取：https://docs.opentrons.com/python-api/pipettes/partial-tip-pickup/
- 液体类：https://docs.opentrons.com/python-api/liquids/
- **仿真与执行：https://docs.opentrons.com/python-api/reference/execute-simulate/**
- **高级控制：https://docs.opentrons.com/python-api/advanced-control/**
  - Jupyter Notebook：https://docs.opentrons.com/python-api/advanced-control/jupyter/
  - 命令行：https://docs.opentrons.com/python-api/advanced-control/command-line/

---

_文档版本：1.0，基于 Opentrons Python Protocol API v2.29_