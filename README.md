# 致远高考志愿预测系统

基于 2023-2025 三年真实专业录取数据，冲稳保三档智能推荐，让每一分都有价值。

## 快速开始

### 1. 环境要求

- Python 3.10+
- pip

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量（可选）

```bash
# Windows
set SECRET_KEY=your-secret-key
set DEEPSEEK_KEY=sk-your-api-key

# Linux/Mac
export SECRET_KEY=your-secret-key
export DEEPSEEK_KEY=sk-your-api-key
```

不设置则使用默认值（AI 问答需要 DeepSeek API Key）。

### 4. 导入数据

准备以下 Excel 数据文件，放到桌面 `高考河北数据` 文件夹：

| 数据 | 文件关键词 |
|------|-----------|
| 2024 本科专业录取 | `专业录取数据-本科` |
| 2024 专科专业录取 | `专业录取数据-专科` |
| 2023 专业录取 | `2023河北专业` |
| 2025 全国专业录取 | `25年全国高校` |
| 2025 专科录取 | `2025年` (放 D:\高考数据\) |
| 一分一段表 | `一分一段` |
| 招生计划 (2023) | `河北-2023-招生计划` |
| 招生计划 (2024) | `河北省2024年高考招生计划` |
| 招生计划 (2025) | `2025年河北省招生计划` |

修改 `data_loader.py` 中的 `DESKTOP` 和 `D_DRIVE` 路径，然后运行：

```bash
python data_loader.py
```

### 5. 启动服务

```bash
python app.py
```

打开浏览器访问 `http://localhost:5000`

## 功能

- **志愿模拟**：输入分数和位次，自动推荐冲/稳/保三档志愿
- **名师解惑**：AI 即时解答专业选择、就业前景等问题
- **一键导出**：勾选心仪专业，导出 Excel 表格
- **邀请系统**：分享邀请码，双方各得 3 次免费模拟

## 技术栈

Python Flask + SQLAlchemy + Bootstrap 5 + SQLite
