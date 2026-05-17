# Print Shop Automation Workflow

这个项目来自一次打印店照片订单自动化实践：店员把订单文件夹放进监控目录，系统识别尺寸和模式，预处理图片，匹配打印机预设，再把任务派发到打印队列。

它不是一个单点脚本，而是一套围绕真实门店动作拆出来的 Windows 工作流。对我来说，最有价值的地方不是调用打印机本身，而是把线下操作里的重复判断变成了可检查、可恢复、可交接的流程。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/platform-Windows-0078D4?logo=windows&logoColor=white)
![Workflow](https://img.shields.io/badge/workflow-folder%20watcher%20%2B%20print%20queue-0F766E)
![License](https://img.shields.io/badge/license-MIT-green)

```mermaid
flowchart LR
    A[订单文件夹] --> B[解析尺寸 / 模式 / 张数 / 订单号]
    B --> C[图片格式检查]
    C --> D[拍立得预处理]
    D --> E[匹配纸张和打印预设]
    E --> F[进入打印任务队列]
    F --> G[执行打印]
    G --> H[完成归档 / 异常处理 / 语音提示]
```

关键词：打印店自动化、照片打印、文件夹监控、批量打印、Windows Print API、Tkinter、Pillow、watchdog、print queue。

## 🚀 先跑核心测试

这个项目依赖 Windows 打印能力。没有真实打印机时，也可以先跑解析和配置测试：

```bash
git clone https://github.com/Ce-Legend/print-shop-automation-workflow.git
cd print-shop-automation-workflow
python -m pip install -e .[dev]
python -m pytest -q
```

要启动完整界面，需要在 Windows 上安装依赖并配置打印机：

```powershell
python -m pip install -r requirements.txt
Copy-Item config.example.json config.json
python main.py
```

## 📁 文件夹就是任务单

这个项目没有让店员在系统里反复填表，而是把任务信息放进文件夹名称。

```text
【拍立得】5寸,10张 250701-123456789012345
【全景】6寸,8张 250702-123456789012346
3T_拍立得_5张250703-123456789012347
```

系统会从名称里解析：

- 尺寸：3寸、4寸、5寸、6寸，也兼容 3T、5T 这类叫法。
- 模式：拍立得、全景。
- 张数：用于核对订单数量。
- 订单号：用于日志、异常追踪和归档。

更多样例见 [examples/order-folder-names.md](examples/order-folder-names.md)。

## 🧭 我想重点留下来的实践

### 1. 先让店员动作变少

线下打印店最怕的是每单都要点一遍设置：纸张、边距、色彩、尺寸、方向。系统的入口被设计成监控文件夹，是因为这个动作最贴近日常工作。店员只需要把订单放进去，后面的识别、预处理、排队和提示都由程序接住。

### 2. 文件夹命名比表单更适合这个场景

表单当然更规范，但会增加操作负担。打印店订单本来就以文件夹流转，直接从文件夹名解析任务信息，反而更自然。这里的 `FolderNameParser` 支持中文尺寸、数字别名、张数和订单号，就是为了降低一线使用门槛。

### 3. 打印机预设要承认边界

Windows 标准打印 API 能控制一部分基础参数，但很难完整接管厂商驱动里的高级色彩预设。这个项目没有硬绕过去，而是采用一次人工配置、后续自动复用的办法。技术上不完美，但对门店交付更务实。

### 4. 异常不能只写进日志

线下系统出错时，没人会一直盯控制台。所以项目里同时做了日志、异常文件夹、界面状态和语音提示。照片格式不支持、文件夹命名不完整、打印机不可用，都应该变成店员能理解的状态。

### 5. 真实交付需要用户引导工具

除了主程序，我还做了预设配置引导和配置状态检查工具。原因很简单：如果第一次配置失败，自动化系统就会被认为不好用。引导工具比一段说明文更能减少交付后的沟通成本。

## 📦 代码结构

```text
.
├── main.py                         # 程序入口、依赖检查、日志初始化
├── ui_main.py                      # Tkinter 主界面
├── folder_monitor.py               # 监控文件夹、解析订单文件夹名
├── task_manager.py                 # 打印任务对象、队列和状态
├── task_dispatcher.py              # 任务分发和调度
├── image_preprocessor.py           # 拍立得图片预处理入口
├── print_executor.py               # 打印执行器
├── printer_manager.py              # 打印机发现和基础管理
├── printer_preset_manager.py       # 打印预设配置
├── config_manager.py               # 配置读写和预设映射
├── voice_announcer.py              # 语音播报
├── log_manager.py                  # 日志管理
├── examples/                       # 订单命名样例
└── tests/                          # 不依赖真实打印机的轻量测试
```

## 🔧 可以复用到哪些场景

- 照片打印店：按订单文件夹自动分发照片打印任务。
- 证件照/拍立得业务：根据尺寸和模式套用不同预处理脚本。
- 小型门店自动化：把文件夹、命名规则和状态提示组合成轻量工作流。
- Windows 本地工具：Tkinter + watchdog + pywin32 的桌面自动化实践。

## ⚙️ 配置思路

公开版提供的是 [config.example.json](config.example.json)。实际运行时复制为 `config.json`，再在本机配置监控目录和打印机。

核心配置分三块：

- `monitor_path`：订单文件夹进入的位置。
- `printers`：可用打印机、纸张规格和启用状态。
- `presets`：尺寸和模式到打印预设名称的映射。

预设映射示例：

```json
{
  "5寸": {
    "全景": "5寸全景",
    "拍立得": "5寸拍立得",
    "default": "5寸拍立得"
  }
}
```

## ✅ 测试

```bash
python -m pytest -q
```

当前测试只覆盖不依赖真实打印机的部分：

- 文件夹名称解析。
- 尺寸别名识别。
- 拍立得 / 全景模式识别。
- 默认预设映射。

真实打印链路需要在 Windows + 实体打印机环境里验证。

## License

MIT
