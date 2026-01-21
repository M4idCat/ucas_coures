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
1. Python 3.8+
2. 安装依赖：
   ```bash
   pip install selenium webdriver-manager ddddocr
