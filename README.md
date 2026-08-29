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
- ChromeDriver（可选，速度更快，见下节）

---

## 查找 Chrome 版本与匹配的 ChromeDriver

Chrome 115 之后，ChromeDriver 的版本号与 Chrome 主版本号一一对应（例如 Chrome 131 ↔ ChromeDriver 131）。手动配置步骤如下：

1. **查看 Chrome 版本**（任选其一）：
   - 浏览器地址栏输入 `chrome://version/`，第一行「Google Chrome」即版本号（所有平台通用）
   - 命令行：
     - Linux：`google-chrome --version` 或 `chromium --version`
     - macOS：`"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --version`
2. **下载匹配的 ChromeDriver**：
   - 打开 [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/) 页面
   - 选择 **Stable** 渠道，找到与你的 Chrome **主版本号相同**的条目
   - 下载对应平台的 `chromedriver`（linux64 / mac-x64 / mac-arm64 / win32 / win64）
   - 解压后将 `chromedriver` 放到项目根目录（如 `chromedriver-linux64/chromedriver`）
3. 在 `config.json` 中设置 `chromedriver_path` 为驱动完整路径，脚本即使用本地驱动

> 提示：`chromedriver_path` 留空时，脚本会使用 `webdriver_manager` 自动下载与当前 Chrome 匹配的 ChromeDriver。手动配置只是为了让启动更快、避免每次联网下载。

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

---

## 配置文件说明

| 配置项 | 说明 |
| --- | --- |
| `user` | UCAS 登录用户名 |
| `password` | UCAS 登录密码 |
| `course_file` | 课程代码文件（`class.txt`）的绝对路径 |
| `chromedriver_path` | 本地 ChromeDriver 的绝对路径（留空则自动下载） |
| `headless` | 是否以无头模式运行（`true` / `false`） |
| `retry_per_course` | 每门课程的重试次数 |
| `always_continue` | 是否总是判定为成功继续 |
| `ocr_max_attempts` | 验证码 OCR 自动识别最大次数 |
| `manual_max_attempts` | 验证码人工输入最大次数 |
