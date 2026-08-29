# UCAS 抢课脚本

本项目是一个使用 **Python + Selenium** 编写的自动化脚本，用于在 **中国科学院大学 (UCAS)** 教务系统进行抢课操作。  
支持自动登录、课程查询、自动勾选、验证码 OCR 识别（支持人工兜底输入），并处理课程已满/时间冲突/提交过于频繁等情况。

---

## 功能特性
- 自动登录 UCAS SEP 教务系统
- 从文件读取课程代码，一行一个
- 自动跳转到新增课程界面并查询课程
- 自动识别验证码（基于 [ddddocr](https://github.com/sml2h3/ddddocr)）
- 验证码识别失败时可人工输入兜底
- 检测课程是否已满（`checkbox` disabled）
- 处理“时间冲突”课程自动跳过
- 处理“提交过于频繁”提示，自动延迟后重试
- 配置灵活（支持 JSON 配置文件）

---

## 环境依赖

- Python 3.8+
- Chrome 浏览器（建议使用最新版本）
- ChromeDriver（可选，速度更快）
  - 前往 [ChromeDriver 下载页面](https://googlechromelabs.github.io/chrome-for-testing/#stable) 下载与 Chrome 版本匹配的 ChromeDriver，并放置在项目根目录下
  - 将 `main.py` 第 25 行的 `USE_LOCAL_DRIVER` 设置为 `True`

---

## 安装依赖

### 方式一：使用 uv（推荐）

本项目使用 [uv](https://docs.astral.sh/uv/) 管理虚拟环境与依赖，配置位于 `pyproject.toml`。

1. 安装 uv（如未安装）：
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. 创建虚拟环境并安装依赖（`uv` 会读取 `pyproject.toml` 并自动生成/更新 `uv.lock`）：
   ```bash
   uv sync
   ```

3. 运行脚本：
   ```bash
   uv run python main.py
   ```
   或先激活虚拟环境再运行：
   ```bash
   source .venv/bin/activate
   python main.py
   ```

4. 添加/更新依赖：
   ```bash
   uv add selenium webdriver-manager ddddocr
   ```

### 方式二：使用 pip

```bash
pip install selenium webdriver-manager ddddocr
```

---

## 使用说明

1. 准备课程文件：复制 `class.txt.example` 为 `class.txt`，一行一个课程代码
2. 准备配置文件：复制 `config.json.example` 为 `config.json`，修改用户名、密码、课程文件路径等配置项
3. 运行脚本：
   ```bash
   uv run python main.py
   ```

### 配置文件说明

| 配置项 | 说明 |
| --- | --- |
| `user` | UCAS 登录用户名 |
| `password` | UCAS 登录密码 |
| `course_file` | 课程代码文件（`class.txt`）的绝对路径 |
| `chromedriver_path` | 本地 ChromeDriver 的绝对路径（使用本地驱动时填写） |
| `headless` | 是否以无头模式运行（`true` / `false`） |
| `retry_per_course` | 每门课程的重试次数 |
| `always_continue` | 是否总是判定为成功继续 |
| `ocr_max_attempts` | 验证码 OCR 自动识别最大次数 |
| `manual_max_attempts` | 验证码人工输入最大次数 |
