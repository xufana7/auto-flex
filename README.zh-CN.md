# Auto Flex 中文使用指南

`auto-flex` 用于把自然语言实验需求或已有的 Opentrons Python 协议转换成一套可追踪的 Flex 工作流程，包括硬件识别、实验说明、协议生成或导入、命令行仿真、错误修复以及可选的真机执行。

## 一、使用前检查

开始前确认以下条件：

- Codex 中能够看到 `$auto-flex` skill。
- `opentrons` MCP 服务已经启用。
- Opentrons 仿真器已经安装。
- 需要真机运行时，电脑能够访问 Flex 的 HTTP API 端口 `31950`。
- Skill 根目录存在 `.env`，默认内容包含：

  ```dotenv
  DEFAULT_IP=169.254.224.1
  HEARD_Flex=False
  ```

查看 MCP 状态：

```powershell
codex mcp get opentrons
```

查看硬件缓存状态：

```powershell
$skillRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills\auto-flex'
python (Join-Path $skillRoot 'scripts\flex_env.py') `
  --env (Join-Path $skillRoot '.env') status
```

## 二、第一次调用时会发生什么

第一次调用 `$auto-flex` 时，skill 会先读取 `.env`：

1. 发现 `HEARD_Flex=False`。
2. 使用 `DEFAULT_IP` 调用 Opentrons MCP 的 `robot_health`。
3. 获取机器人名称、型号、序列号、HTTP API 版本、固件版本和系统版本。
4. 把结果写入 `.env`。
5. 将 `HEARD_Flex` 设置为 `True`。
6. 后续调用直接使用缓存的硬件信息，不再重复查询。

如果用户在提示词中明确给出其他 IP，本次工作流使用用户给出的 IP；否则使用 `.env` 中的 `DEFAULT_IP=169.254.224.1`。

如果首次硬件查询失败，skill 不会把 `HEARD_Flex` 设置为 `True`，也不会继续生成实验方案或协议。此时应检查机器人电源、网络连接、IP 和端口 `31950`。

## 三、根据实验需求生成新协议

在 Codex 中输入类似内容：

```text
$auto-flex 使用 Flex 将源板 A1-A8 中的样品分别转移 100 µL 到目标板 A1-A8，
每孔混匀 3 次。使用 8 通道 1000 µL Flex 移液器。先仿真，仿真通过后准备真机执行。
```

执行流程如下：

1. 读取或发现 `.env` 中的 Flex 硬件信息。
2. 在当前工作区创建 `YYYY-MM-DD_expNN` 文件夹。
3. 生成 `exp_NN.md` 实验方案，其中包含：
   - 实验目的；
   - 已识别的 Flex 硬件信息；
   - 试剂、样品和液体体积；
   - 孔位对应关系；
   - Labware、移液器、吸头和模块；
   - Deck 布局；
   - 操作步骤、混匀和流速；
   - 安全检查和预期结果。
4. 弹出实验方案确认窗口。窗口提供：
   - “确认并继续”按钮；
   - 修改意见输入框；
   - 30 秒倒计时，超时自动确认方案。
5. 如果提交修改意见，skill 修改 `exp_NN.md` 后重新弹出确认窗口。
6. 方案确认后，skill 使用本地 Flex API RAG 文档和 `.env` 硬件信息生成 `protocol_NN.py`。
7. 使用 `opentrons_simulate` 仿真协议并保存日志。
8. 仿真发现错误时，结合日志和 RAG 文档修改工作协议，再次仿真。
9. 仿真通过后，进入真机执行确认。

方案的 30 秒自动确认只代表方案审核通过，不代表允许机器人开始运动。

## 四、使用已有的 Python 协议

可以附加 `.py` 文件，或者在提示词中提供绝对路径：

```text
$auto-flex 使用 D:\Lab\protocols\plate_transfer.py。
根据代码生成详细实验介绍，仿真并修复，然后在 169.254.224.1 的 Flex 上准备执行。
```

此模式会：

1. 读取 `.env` 硬件信息。
2. 检查文件是否为 Flex 协议，而不是 OT-2 协议或普通 Python 程序。
3. 记录原文件绝对路径和 SHA-256。
4. 保持原始文件不变，将其复制到实验目录并命名为 `protocol_NN.py`。
5. 根据用户说明、协议代码和 Flex 硬件信息生成详细的 `exp_NN.md`。
6. 跳过方案弹窗和新协议生成步骤。
7. 直接仿真工作副本，并根据错误修改工作副本。
8. 仿真成功后进入真机执行确认。

如果只想检查协议，不进行真机操作，请明确说明：

```text
$auto-flex 检查并仿真这个 protocol.py，只生成实验说明和仿真结果，不要上传或运行到真机。
```

## 五、仿真和自动修复

每次仿真都会生成独立日志，例如：

```text
simulation_01_attempt_01.log
simulation_01_attempt_02.log
```

Skill 会把非零退出码、Python traceback、协议分析错误、Labware 或模块冲突以及不支持的 API 调用视为失败。

为了防止无限修改，出现以下任一情况时会停止并请求人工处理：

- 已经尝试修复 5 次；
- 同一种实质性错误连续出现 2 次。

仿真通过只能证明协议能够通过软件分析，不能证明真实 Deck 布局、耗材安装、试剂身份、校准状态或机械运动绝对安全。

## 六、真机执行

仿真成功后，skill 会显示以下信息并要求明确确认：

- 最终使用的机器人 IP；
- 即将上传的 `protocol_NN.py`；
- 即将发生的物理机器人操作。

只有用户明确确认后，才会依次执行：

1. `upload_protocol`：上传协议；
2. `create_run`：创建运行；
3. `control_run`，动作 `play`：启动运行；
4. `get_run_status`：持续查询状态；
5. 将协议 ID、运行 ID、状态变化和错误写入 `live_run_NN.log`。

示例确认：

```text
确认在 169.254.224.1 上运行当前 protocol_01.py。
```

如果机器人报告故障，skill 不会自行尝试高风险恢复操作，而是记录状态并要求用户决定下一步。

## 七、输出文件

每次任务都会创建一个独立目录：

```text
2026-09-23_exp01/
  exp_01.md
  plan_confirmation_01_attempt_01.json
  protocol_01.py
  simulation_01_attempt_01.log
  live_run_01.log
```

其中：

- `exp_01.md`：实验方案或已有协议的详细实验介绍；
- `plan_confirmation_*.json`：新协议模式下的方案确认结果；
- `protocol_01.py`：生成的协议或已有协议的工作副本；
- `simulation_*.log`：每次仿真的完整日志；
- `live_run_01.log`：真机上传、运行和状态记录。

已有协议模式不会生成方案确认 JSON，因为该模式跳过方案确认窗口。

## 八、更换机器人或刷新硬件信息

更换 Flex、升级机器人软件或修改硬件配置后，重置缓存：

```powershell
$skillRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills\auto-flex'
python (Join-Path $skillRoot 'scripts\flex_env.py') `
  --env (Join-Path $skillRoot '.env') reset
```

重置后：

```dotenv
HEARD_Flex=False
```

下一次 `$auto-flex` 调用会重新通过 MCP 查询硬件。

如果只需修改默认 IP，可编辑 `.env`：

```dotenv
DEFAULT_IP=192.168.1.100
HEARD_Flex=False
```

## 九、常见问题

### 无法连接 Flex

- 确认机器人已开机；
- 确认电脑和机器人网络可达；
- 浏览器访问 `http://机器人IP:31950/health`；
- 确认 `.env` 中的 `DEFAULT_IP` 正确；
- 确认 `codex mcp get opentrons` 显示服务已启用。

### 找不到 `opentrons_simulate`

运行：

```powershell
$skillRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex\skills\auto-flex'
powershell -NoProfile -ExecutionPolicy Bypass -File `
  (Join-Path $skillRoot 'scripts\setup_simulator.ps1')
```

### Skill 没有出现

- 确认目录为 `%USERPROFILE%\.codex\skills\auto-flex`；
- 确认目录内存在 `SKILL.md`；
- 重启 Codex 并新建任务；
- 使用 `$auto-flex` 显式调用。

## 十、安全原则

- 每次真机运行前核对 IP、协议文件、Deck、Labware、移液器、吸头、模块和试剂位置。
- 方案超时自动确认不等于真机运行授权。
- 不要在公开仓库提交包含机器人序列号和网络信息的已填充 `.env`。
- 真机运行时保持人员在场，并确保能够使用 Flex 的停止或急停措施。

