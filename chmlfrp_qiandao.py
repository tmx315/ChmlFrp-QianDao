#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium版 v2)
修复元素定位，支持缓存 Chrome
"""

import os
import sys
import time
import random
import logging
from datetime import datetime
from typing import List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ChmlFrpSelenium:
    LOGIN_URL = "https://panel.chmlfrp.net/sign"
    HOME_URL = "https://panel.chmlfrp.net/home"
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.headless = os.environ.get("HEADLESS", "true").lower() == "true"
        
    def init_driver(self):
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")  # 新版 headless
            chrome_options.add_argument("--window-size=1920,1080")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 尝试多种方式启动
        driver_path = None
        chrome_binary = None
        
        # 检查环境变量
        if os.path.exists("/usr/local/bin/chromedriver"):
            driver_path = "/usr/local/bin/chromedriver"
        elif os.path.exists("/usr/bin/chromedriver"):
            driver_path = "/usr/bin/chromedriver"
            
        if os.path.exists("/opt/google/chrome/chrome"):
            chrome_binary = "/opt/google/chrome/chrome"
        elif os.path.exists("/usr/bin/google-chrome"):
            chrome_binary = "/usr/bin/google-chrome"
        elif os.path.exists("/usr/bin/chromium-browser"):
            chrome_binary = "/usr/bin/chromium-browser"
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
            logger.info(f"使用 Chrome: {chrome_binary}")
        
        try:
            if driver_path:
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome 启动失败: {e}")
            raise
        
        # 隐藏 webdriver 属性
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("Chrome 驱动初始化成功")
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def find_element_with_retry(self, selectors, timeout=10):
        """多选择器重试查找元素"""
        wait = WebDriverWait(self.driver, timeout)
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    elem = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                else:
                    elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                return elem
            except:
                continue
        raise NoSuchElementException(f"无法找到元素: {selectors}")
    
    def login(self, username: str, password: str) -> bool:
        try:
            self.driver.get(self.LOGIN_URL)
            logger.info(f"[{username}] 打开登录页...")
            time.sleep(2)
            
            # 填写用户名 - 多种选择器尝试
            user_selectors = [
                "//input[@type='text']",
                "//input[@name='username']",
                "//input[@placeholder='用户名' or @placeholder='邮箱' or contains(@placeholder, '用户')]",
                "input.el-input__inner[type='text']",
                "input[placeholder*='用户名'], input[placeholder*='邮箱'], input[placeholder*='user']"
            ]
            user_input = self.find_element_with_retry(user_selectors, 10)
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 填写密码
            pass_selectors = [
                "//input[@type='password']",
                "input.el-input__inner[type='password']",
                "input[type='password']"
            ]
            pass_input = self.find_element_with_retry(pass_selectors, 5)
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 点击登录按钮 - 基于截图的紫色按钮
            login_btn_selectors = [
                "//button[contains(@class, 'el-button--primary')]",
                "//button[.//span[contains(text(), '登录')]]",
                "//span[contains(text(), '登录')]/parent::button",
                "button.el-button.el-button--primary",
                "button[type='submit']",
                "//button[contains(text(), '登录')]",
                "//div[@class='login-form']//button"
            ]
            
            logger.info(f"[{username}] 查找登录按钮...")
            login_btn = self.find_element_with_retry(login_btn_selectors, 5)
            
            # 滚动到按钮可见
            self.driver.execute_script("arguments[0].scrollIntoView(true);", login_btn)
            time.sleep(0.5)
            
            logger.info(f"[{username}] 点击登录...")
            login_btn.click()
            
            # 等待跳转
            time.sleep(5)
            
            # 检查登录结果
            current_url = self.driver.current_url
            logger.info(f"[{username}] 当前URL: {current_url}")
            
            if "home" in current_url or "panel" in current_url:
                logger.info(f"[{username}] 登录成功!")
                return True
            
            # 检查错误提示
            try:
                error_selectors = [
                    ".el-message__content",
                    ".el-notification__content",
                    ".error-message",
                    "[class*='error']",
                    "//div[contains(@class, 'el-message')]"
                ]
                for sel in error_selectors:
                    try:
                        if sel.startswith("//"):
                            err = self.driver.find_element(By.XPATH, sel).text
                        else:
                            err = self.driver.find_element(By.CSS_SELECTOR, sel).text
                        if err:
                            logger.error(f"[{username}] 登录错误: {err}")
                            break
                    except:
                        continue
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"[{username}] 登录异常: {str(e)}")
            # 保存截图调试
            try:
                self.driver.save_screenshot(f"login_error_{int(time.time())}.png")
                logger.info("已保存错误截图")
            except:
                pass
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        try:
            self.driver.get(self.HOME_URL)
            logger.info(f"[{username}] 进入用户中心...")
            time.sleep(3)
            
            # 查找签到按钮 - 基于截图中的紫色按钮在右上角
            checkin_selectors = [
                "//button[contains(@class, 'el-button--primary') and contains(., '签到')]",
                "//span[contains(text(), '签到')]/ancestor::button",
                "//button[.//span[contains(text(), '签到')]]",
                "button.checkin-btn",
                "[class*='checkin'] button",
                "//div[contains(@class, 'header')]//button[contains(@class, 'el-button--primary')]",
                "//div[contains(@class, 'nav')]//button[contains(@class, 'primary')]"
            ]
            
            btn = None
            for sel in checkin_selectors:
                try:
                    if sel.startswith("//"):
                        btn = self.driver.find_element(By.XPATH, sel)
                    else:
                        btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if btn:
                        break
                except:
                    continue
            
            if not btn:
                # 尝试查找所有按钮
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for b in buttons:
                    if "签到" in b.text:
                        btn = b
                        break
            
            if not btn:
                return False, "未找到签到按钮"
            
            btn_text = btn.text
            logger.info(f"[{username}] 按钮文本: {btn_text}")
            
            if "已签到" in btn_text or "今日" in btn_text:
                return True, "今日已签到"
            
            # 点击签到
            btn.click()
            logger.info(f"[{username}] 已点击签到，等待响应...")
            time.sleep(3)
            
            # 处理可能的滑块验证（简化版）
            # 实际可能需要更复杂的逻辑
            
            # 检查结果
            try:
                msg_elem = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content")
                msg = msg_elem.text
                if "成功" in msg:
                    return True, f"签到成功: {msg}"
                else:
                    return True, msg
            except:
                pass
            
            # 再次检查按钮状态
            try:
                new_text = btn.text
                if "已签到" in new_text:
                    return True, "签到成功"
            except:
                pass
            
            return True, "签到操作完成"
            
        except Exception as e:
            logger.error(f"[{username}] 签到异常: {str(e)}")
            return False, str(e)

def get_accounts():
    users = os.environ.get("CHMLFRP_USER", "").replace("\\n", "\n").split("\n")
    passes = os.environ.get("CHMLFRP_PASS", "").replace("\\n", "\n").split("\n")
    
    user_list = [u.strip() for u in users if u.strip()]
    pass_list = [p.strip() for p in passes if p.strip()]
    
    if len(user_list) != len(pass_list):
        logger.error("账户数量不匹配")
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (Selenium v2)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    accounts = get_accounts()
    if not accounts:
        logger.error("未配置账户")
        sys.exit(1)
    
    bot = ChmlFrpSelenium()
    
    try:
        bot.init_driver()
        
        results = []
        for idx, (user, pwd) in enumerate(accounts, 1):
            logger.info(f"\n[{idx}/{len(accounts)}] 处理: {user}")
            
            if bot.login(user, pwd):
                success, msg = bot.checkin(user)
                results.append((user, success, msg))
            else:
                results.append((user, False, "登录失败"))
            
            if idx < len(accounts):
                time.sleep(random.uniform(5, 10))
        
        logger.info("\n" + "=" * 60)
        logger.info("结果汇总")
        for user, success, msg in results:
            logger.info(f"{'✅' if success else '❌'} {user}: {msg}")
        
        success_count = sum(1 for _, s, _ in results if s)
        logger.info(f"统计: 成功 {success_count}/{len(results)}")
        
        sys.exit(0 if success_count == len(results) else 1)
        
    finally:
        bot.close()

if __name__ == "__main__":
    main()