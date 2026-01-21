#!/usr/bin/env python3
# save_session.py
import os
import time
import re
import json
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager

# -------------------- 站点配置 --------------------
SEP_HOME   = "https://sep.ucas.ac.cn/"
COURSE_URL = "https://sep.ucas.ac.cn/portal/site/524/2412"
USE_LOCAL_DRIVER = True  # 若为 False 则使用 webdriver_manager 自动下载
# 登录页元素
XPATH_USERNAME = '//*[@id="userName1"]'
XPATH_PASSWORD = '//*[@id="pwd1"]'
XPATH_LOGINBTN = '//*[@id="sb1"]'
VERIFY_XPATHS = [
    '//*[@id="certCode1"]',
    "//input[contains(@placeholder,'验证码')]",
    "//input[contains(@id,'cert') or contains(@name,'cert')]",
]

# 抢课页元素
XPATH_ADD_COURSE_BTN   = '//*[@id="regfrm2"]/div/button'
XPATH_COURSE_CODE      = '//*[@id="courseCode"]'
XPATH_SUBMIT_QUERY     = '//*[@id="submitBtn"]'
XPATH_RESULT_TABLE     = '//*[@id="courseinfo"]'
XPATH_SELECT_CHECKBOX  = '//*[@id="courseinfo"]/tr/td[1]/input'

# 验证码与提交
XPATH_CAPTCHA_IMG      = '//*[@id="adminValidateImg"]'
XPATH_CAPTCHA_INPUT    = '//*[@id="vcode"]'
XPATH_SUBMIT_COURSE    = '//*[@id="submitCourse"]'
XPATH_LOGIN_ERROR      = '//*[@id="loginError"]'
XPATH_LOGIN_SUCCESS    = '//*[@id="loginSuccess"]'

# 弹窗确认
XPATH_CONFIRM_MODAL_BTN= '//*[@id="jbox-state-state0"]/div[2]/button[1]'

# -------------------- 运行参数（由 JSON 覆盖） --------------------
HEADLESS             = True
RETRY_PER_COURSE     = 2
ALWAYS_CONTINUE      = False
OCR_MAX_ATTEMPTS     = 6
MANUAL_MAX_ATTEMPTS  = 3
DRIVER_PATH          = ""

# -------------------- 文本模式 --------------------
SUCCESS_PATTERNS     = re.compile(r"(提交成功|选课成功|添加成功|保存成功|success|已加入|已提交)", re.I)
ERROR_PATTERNS       = re.compile(r"(失败|错误|不允许|无效|请重试)", re.I)
CONFLICT_PATTERNS    = re.compile(r"(时间冲突|上课时间冲突|冲突)", re.I)
CAPTCHA_BAD_PAT      = re.compile(r"(验证码|校验码).*(错误|不正确|有误)", re.I)
RATE_LIMIT_PATTERNS  = re.compile(r"(提交选课过于频繁|操作过于频繁|稍后再试)", re.I)

# -------------------- 配置读取 --------------------
def load_config() -> dict:
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    cfg_path = os.environ.get("CONFIG_JSON", default_path)
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(
            f"未找到配置文件：{cfg_path}\n"
            "请在脚本同目录创建 config.json 或通过环境变量 CONFIG_JSON 指定路径。"
        )
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for key in ["user", "password", "course_file"]:
        if key not in cfg or not str(cfg[key]).strip():
            raise ValueError(f"配置文件缺少必填字段: '{key}'")
    return cfg

def apply_config(cfg: dict):
    global HEADLESS, RETRY_PER_COURSE, ALWAYS_CONTINUE
    global OCR_MAX_ATTEMPTS, MANUAL_MAX_ATTEMPTS, DRIVER_PATH
    HEADLESS             = bool(cfg.get("headless", HEADLESS))
    RETRY_PER_COURSE     = int(cfg.get("retry_per_course", RETRY_PER_COURSE))
    ALWAYS_CONTINUE      = bool(cfg.get("always_continue", ALWAYS_CONTINUE))
    OCR_MAX_ATTEMPTS     = int(cfg.get("ocr_max_attempts", OCR_MAX_ATTEMPTS))
    MANUAL_MAX_ATTEMPTS  = int(cfg.get("manual_max_attempts", MANUAL_MAX_ATTEMPTS))
    DRIVER_PATH          = str(cfg.get("chromedriver_path",  DRIVER_PATH))


# -------------------- 工具函数 --------------------
def start_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--start-maximized")
    if HEADLESS:
        opts.add_argument("--headless=new")
        opts.add_argument("--window-size=1920,1080")
    if USE_LOCAL_DRIVER:
        driver_path = DRIVER_PATH if 'DRIVER_PATH' in globals() else None
        service = Service(driver_path)
    else:
        service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

def wait_click(driver, locator, timeout=15):
    wait = WebDriverWait(driver, timeout)
    el = wait.until(EC.element_to_be_clickable((By.XPATH, locator)))
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    return el

def switch_into_frame_holding(driver, xpath, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        driver.switch_to.default_content()
        try:
            driver.find_element(By.XPATH, xpath)
            return True
        except NoSuchElementException:
            pass
        for frame in driver.find_elements(By.TAG_NAME, "iframe"):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                driver.find_element(By.XPATH, xpath)
                return True
            except NoSuchElementException:
                continue
    driver.switch_to.default_content()
    return False

def find_verify_input(driver):
    for vx in VERIFY_XPATHS:
        try:
            return driver.find_element(By.XPATH, vx)
        except Exception:
            continue
    return None

def ocr_digits_from_element(driver, img_el, prefer_len=5):
    try:
        import ddddocr
    except ImportError as e:
        raise ImportError("请先安装 ddddocr: pip install ddddocr") from e
    img_bytes = img_el.screenshot_as_png
    ocr = ddddocr.DdddOcr(show_ad=False)
    res = ocr.classification(img_bytes)
    digits = "".join(ch for ch in res if ch.isdigit())
    return digits[:prefer_len] if digits else ""

def refresh_captcha(driver, img_el):
    try:
        img_el.click()
    except Exception:
        try:
            driver.execute_script(
                "arguments[0].src = arguments[0].src.split('?')[0] + '?t=' + Date.now();", img_el
            )
        except Exception:
            pass

def get_elem_text(driver, xpath: str, timeout: float) -> str:
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return (el.text or "").strip()
    except TimeoutException:
        return ""

def try_solve_and_submit_captcha(driver, expect_len=5) -> bool:
    """
    OCR 多次 ->（不行）人工输入多次。
    仅在触发频率限制时等待 1 秒；其余不做固定 sleep。
    """
    if not switch_into_frame_holding(driver, XPATH_CAPTCHA_IMG, timeout=8):
        print("[warn] 未能定位到验证码 frame，尝试在当前文档继续。")

    wait = WebDriverWait(driver, 12)
    try:
        img_el   = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_CAPTCHA_IMG)))
        input_el = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_CAPTCHA_INPUT)))
        submit_el= wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_SUBMIT_COURSE)))
    except TimeoutException:
        print("[WARN] 未能找到验证码元素，请检查 XPath。")
        return False

    # ---------- 1) OCR 自动识别阶段 ----------
    for _ in range(OCR_MAX_ATTEMPTS):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", img_el)
            code = ocr_digits_from_element(driver, img_el, prefer_len=expect_len)
            if not code or len(code) < expect_len:
                refresh_captcha(driver, img_el)
                continue

            input_el.clear()
            input_el.send_keys(code)

            try:
                submit_el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", submit_el)

            # 成功/错误判断
            success_txt = get_elem_text(driver, XPATH_LOGIN_SUCCESS, timeout=1.2)
            if success_txt:
                return True

            err = get_elem_text(driver, XPATH_LOGIN_ERROR, timeout=1.2)
            if err:
                if CAPTCHA_BAD_PAT.search(err):
                    refresh_captcha(driver, img_el)
                    continue
                # 其他错误（含冲突/频率限制）由上层处理
                return False

            # 既无成功也无错误，通常会弹确认框
            return True

        except Exception:
            refresh_captcha(driver, img_el)

    print("[info] OCR 阶段未通过，进入人工输入。")

    # ---------- 2) 人工输入兜底 ----------
    for _ in range(MANUAL_MAX_ATTEMPTS):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", img_el)
            manual = input("请输入图片验证码（留空=刷新）：").strip()
            if not manual:
                refresh_captcha(driver, img_el)
                continue

            input_el.clear()
            input_el.send_keys(manual)
            try:
                submit_el.click()
            except Exception:
                driver.execute_script("arguments[0].click();", submit_el)

            success_txt = get_elem_text(driver, XPATH_LOGIN_SUCCESS, timeout=1.2)
            if success_txt:
                return True

            err = get_elem_text(driver, XPATH_LOGIN_ERROR, timeout=1.2)
            if err:
                if CAPTCHA_BAD_PAT.search(err):
                    refresh_captcha(driver, img_el)
                    continue
                return False

            return True

        except Exception:
            refresh_captcha(driver, img_el)

    print("[WARN] 人工输入阶段仍未通过。")
    return False

def confirm_submit_modal(driver, timeout=10):
    driver.switch_to.default_content()
    try:
        btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_CONFIRM_MODAL_BTN))
        )
    except TimeoutException:
        print("[WARN] 未检测到确认提交弹窗。")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)

    print("[ok] 已点击弹窗‘确认提交’。")
    return True

def outcome_after_submit(driver) -> str:
    """
    success / conflict / rate_limit / error / unknown
    """
    driver.switch_to.default_content()
    s_txt = get_elem_text(driver, XPATH_LOGIN_SUCCESS, timeout=1.0)
    if s_txt:
        return "success"
    e_txt = get_elem_text(driver, XPATH_LOGIN_ERROR, timeout=1.0)
    if e_txt:
        if CONFLICT_PATTERNS.search(e_txt):
            return "conflict"
        if RATE_LIMIT_PATTERNS.search(e_txt):
            return "rate_limit"
        return "error"
    return "unknown"

# -------------------- 业务步骤 --------------------
def open_add_course(driver):
    if not switch_into_frame_holding(driver, XPATH_ADD_COURSE_BTN, timeout=6):
        print("[info] 直接尝试在当前文档点击新增课程。")
    wait_click(driver, XPATH_ADD_COURSE_BTN, timeout=12)

def search_course(driver, code: str):
    if not switch_into_frame_holding(driver, XPATH_COURSE_CODE, timeout=6):
        print("[warn] 未能定位到课程编码输入框所在 frame，尝试当前文档。")
    code_input = WebDriverWait(driver, 12).until(
        EC.presence_of_element_located((By.XPATH, XPATH_COURSE_CODE))
    )
    code_input.clear()
    code_input.send_keys(code)
    wait_click(driver, XPATH_SUBMIT_QUERY, timeout=8)

    if not switch_into_frame_holding(driver, XPATH_RESULT_TABLE, timeout=6):
        print("[warn] 未能定位到结果表格 frame，尝试当前文档。")
    WebDriverWait(driver, 12).until(
        EC.presence_of_element_located((By.XPATH, XPATH_RESULT_TABLE))
    )

def select_first_checkbox(driver) -> Tuple[bool, bool]:
    checkboxes = driver.find_elements(By.XPATH, XPATH_SELECT_CHECKBOX)
    if not checkboxes:
        return (False, True)

    any_enabled = False
    for cb in checkboxes:
        try:
            is_disabled = cb.get_attribute("disabled") is not None
            if is_disabled:
                continue
            any_enabled = True

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
            checked  = cb.get_attribute("checked")
            if not checked:
                try:
                    cb.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", cb)
            return (True, False)

        except (StaleElementReferenceException, ElementClickInterceptedException):
            continue

    if not any_enabled:
        return (False, True)

    return (False, False)

def take_course_once(driver, course_code: str) -> Tuple[bool, bool]:
    open_add_course(driver)
    search_course(driver, course_code)
    selected, full_or_none = select_first_checkbox(driver)

    if not selected:
        if full_or_none:
            return (False, True)
        else:
            return (False, False)

    if not try_solve_and_submit_captcha(driver, expect_len=5):
        return (False, False)

    _ = confirm_submit_modal(driver, timeout=10)

    out = outcome_after_submit(driver)
    if out == "success":
        return (True, False)
    if out == "conflict":
        return (False, True)
    if out == "rate_limit":
        print("[info] 提交过于频繁，等待 1 秒后重试当前课程。")
        time.sleep(1.0)
        return (False, False)
    if out == "error":
        return (False, False)

    # 宽松兜底
    blob_success = get_elem_text(driver, XPATH_LOGIN_SUCCESS, timeout=0.5)
    blob_error   = get_elem_text(driver, XPATH_LOGIN_ERROR, timeout=0.5)
    if blob_success or SUCCESS_PATTERNS.search((blob_success or "")):
        return (True, False)
    if blob_error:
        if CONFLICT_PATTERNS.search(blob_error):
            return (False, True)
        if RATE_LIMIT_PATTERNS.search(blob_error):
            print("[info] 提交过于频繁（兜底识别），等待 1 秒后重试当前课程。")
            time.sleep(1.0)
            return (False, False)
        return (False, False)

    if ALWAYS_CONTINUE:
        return (True, False)
    return (False, False)

# -------------------- 入口 --------------------
def read_course_codes(path: str) -> List[str]:
    codes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            codes.append(s)
    if not codes:
        raise RuntimeError("课程文件为空或仅包含空行/注释。")
    return codes

def login(driver, user: str, pwd: str):
    driver.get(SEP_HOME)
    wait = WebDriverWait(driver, 15)
    user_el = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_USERNAME)))
    pwd_el  = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_PASSWORD)))
    login_btn = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_LOGINBTN)))

    user_el.clear(); user_el.send_keys(user)
    pwd_el.clear();  pwd_el.send_keys(pwd)
    print("[info] 已填写用户名与密码，若有验证码请手动输入。")

    verify_el = find_verify_input(driver)
    if verify_el:
        input("请输入登录页验证码后按回车继续...")
    login_btn.click()

    try:
        WebDriverWait(driver, 30).until(lambda d: "登录" not in d.title)
        print("[ok] 登录成功（标题变化）")
    except TimeoutException:
        print("[warn] 30s 内标题未变化，继续尝试后续步骤。")

def main():
    cfg = load_config()
    apply_config(cfg)

    user = cfg["user"]
    pwd  = cfg["password"]
    course_file = cfg["course_file"]

    codes = read_course_codes(course_file)
    print(f"[info] 共读取到 {len(codes)} 门课程。")

    driver = start_driver()
    try:
        login(driver, user, pwd)
        driver.get(COURSE_URL)

        for idx, code in enumerate(codes, 1):
            print(f"\n===== 开始第 {idx}/{len(codes)} 门课程：{code} =====")
            success = False
            attempts = 0
            skip_course = False
            while attempts <= RETRY_PER_COURSE and not success and not skip_course:
                attempts += 1
                print(f"[info] 尝试 {attempts}/{RETRY_PER_COURSE + 1}")
                try:
                    success, skip_course = take_course_once(driver, code)
                except Exception as e:
                    print(f"[warn] 处理课程 {code} 异常：{e}")
                    success = False
                    skip_course = False

                # 返回课程页，立即进入下一轮/下一门（无固定 sleep）
                try:
                    driver.switch_to.default_content()
                    driver.get(COURSE_URL)
                except Exception:
                    pass

            if skip_course:
                print(f"[SKIP] 课程 {code} 已满/时间冲突/无可选项，跳过。")
            elif success:
                print(f"[OK] 课程 {code} 判定成功。进入下一门。")
            else:
                print(f"[FAIL] 课程 {code} 未判定成功（已达最大重试次数 {RETRY_PER_COURSE}）。")

        print("\n[ALL DONE] 已按文件顺序完成所有课程的尝试。")
        if not HEADLESS:
            input("按回车关闭浏览器...")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    main()
