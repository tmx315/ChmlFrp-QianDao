#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium版 v3)
优化元素定位，适配 GitHub Actions
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

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
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--window-size=1920,1080")
        
        # 反检测和稳定性配置
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # 加速加载
        chrome_options.add_argument("--disable-javascript")  # 先禁用JS，登录后再启用
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 查找 Chrome 和 ChromeDriver
        chrome_binary = None
        for path in ["/opt/google/chrome/chrome", "/usr/bin/google-chrome", "/usr/bin/chromium-browser"]:
            if os.path.exists(path):
                chrome_binary = path
                break
        
        chromedriver_path = None
        for path in ["/usr/local/bin/chromedriver", "/usr/bin/chromedriver"]:
            if os.path.exists(path):
                chromedriver_path = path
                break
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
            logger.info(f"Chrome: {chrome_binary}")
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info(f"ChromeDriver: {chromedriver_path}")
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except WebDriverException as e:
            logger.error(f"Chrome 启动失败: {e}")
            raise
        
        # 隐藏 webdriver 属性
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                window.chrome = { runtime: {} };
            '''
        })
        
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("Chrome 初始化成功")
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def safe_find(self, by, value, timeout=10):
        """安全查找元素"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None
    
    def login(self, username: str, password: str) -> bool:
        try:
            self.driver.get(self.LOGIN_URL)
            logger.info(f"[{username}] 打开登录页...")
            
            # 等待页面加载
            time.sleep(3)
            
            # 截图调试（如果失败）
            debug_screenshot = lambda name: self.driver.save_screenshot(f"{name}_{int(time.time())}.png") if self.driver else None
            
            # 查找用户名输入框 - 使用更通用的选择器
            user_input = self.safe_find(By.XPATH, "//input[@type='text' or @name='username' or contains(@placeholder, '用户名') or contains(@placeholder, '邮箱')]", 10)
            if not user_input:
                # 尝试通过ID或class查找
                user_input = self.safe_find(By.CSS_SELECTOR, "input.el-input__inner, input[type='text'], input#username", 5)
            
            if not user_input:
                logger.error(f"[{username}] 未找到用户名输入框")
                debug_screenshot("no_user_input")
                return False
            
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 查找密码输入框
            pass_input = self.safe_find(By.XPATH, "//input[@type='password']", 10)
            if not pass_input:
                pass_input = self.safe_find(By.CSS_SELECTOR, "input[type='password'], input.el-input__inner[type='password']", 5)
            
            if not pass_input:
                logger.error(f"[{username}] 未找到密码输入框")
                return False
            
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 查找登录按钮 - 根据截图中的紫色按钮
            login_btn = None
            # 先尝试包含"登录"文本的按钮
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[contains(., '登录') or contains(., 'Sign')]")
            except:
                pass
            
            if not login_btn:
                # 尝试 primary 按钮
                login_btn = self.safe_find(By.CSS_SELECTOR, "button.el-button--primary, button[type='submit']", 5)
            
            if not login_btn:
                # 尝试最后一个按钮（通常是提交按钮）
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                if buttons:
                    login_btn = buttons[-1]
            
            if not login_btn:
                logger.error(f"[{username}] 未找到登录按钮")
                debug_screenshot("no_login_btn")
                return False
            
            logger.info(f"[{username}] 点击登录...")
            
            # 滚动到按钮可见并点击
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_btn)
            time.sleep(0.5)
            login_btn.click()
            
            # 等待跳转
            time.sleep(5)
            
            current_url = self.driver.current_url
            logger.info(f"[{username}] 当前URL: {current_url}")
            
            if "home" in current_url or "dashboard" in current_url:
                logger.info(f"[{username}] 登录成功!")
                return True
            
            # 检查是否有错误提示
            error_msgs = self.driver.find_elements(By.CSS_SELECTOR, ".el-message, .el-notification, .error-message")
            for msg in error_msgs:
                if msg.text:
                    logger.error(f"[{username}] 错误提示: {msg.text}")
            
            # 检查是否还在登录页
            if "sign" in current_url or "login" in current_url:
                logger.error(f"[{username}] 仍在登录页，可能登录失败")
                debug_screenshot("still_login_page")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"[{username}] 登录异常: {str(e)}")
            try:
                self.driver.save_screenshot(f"login_error_{username}_{int(time.time())}.png")
            except:
                pass
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        try:
            self.driver.get(self.HOME_URL)
            logger.info(f"[{username}] 进入用户中心...")
            time.sleep(3)
            
            # 查找签到按钮 - 根据截图，在右上角紫色按钮
            checkin_btn = None
            
            # 先尝试文本包含"签到"
            try:
                checkin_btn = self.driver.find_element(By.XPATH, "//button[contains(., '签到')]")
            except:
                pass
            
            if not checkin_btn:
                # 尝试所有按钮，找包含"签到"的
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "签到" in btn.text:
                        checkin_btn = btn
                        break
            
            if not checkin_btn:
                # 尝试第一个 primary 按钮（可能是签到）
                checkin_btn = self.safe_find(By.CSS_SELECTOR, "button.el-button--primary", 5)
            
            if not checkin_btn:
                return False, "未找到签到按钮"
            
            btn_text = checkin_btn.text
            logger.info(f"[{username}] 按钮文本: '{btn_text}'")
            
            if "已" in btn_text or "今日" in btn_text:
                return True, "今日已签到"
            
            # 点击
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkin_btn)
            time.sleep(0.5)
            checkin_btn.click()
            
            logger.info(f"[{username}] 已点击，等待响应...")
            time.sleep(4)
            
            # 检查结果
            try:
                msg_elem = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content")
                msg = msg_elem.text
                if "成功" in msg or "积分" in msg:
                    return True, f"签到成功: {msg}"
                elif "已经" in msg or "已签到" in msg:
                    return True, "今日已签到"
                else:
                    return True, msg
            except:
                pass
            
            # 检查按钮是否变成已签到
            try:
                new_text = checkin_btn.text
                if "已" in new_text:
                    return True, "签到成功"
            except:
                pass
            
            return True, "操作完成"
            
        except Exception as e:
            logger.error(f"[{username}] 签到异常: {str(e)}")
            return False, str(e)

def get_accounts():
    users = os.environ.get("CHMLFRP_USER", "").replace("\\n", "\n").split("\n")
    passes = os.environ.get("CHMLFRP_PASS", "").replace("\\n", "\n").split("\n")
    
    user_list = [u.strip() for u in users if u.strip()]
    pass_list = [p.strip() for p in passes if p.strip()]
    
    if len(user_list) != len(pass_list):
        logger.error(f"账户数量不匹配: {len(user_list)} vs {len(pass_list)}")
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (Selenium v3)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    accounts = get_accounts()
    if not accounts:
        logger.error("未配置账户，请设置 CHMLFRP_USER 和 CHMLFRP_PASS")
        sys.exit(1)
    
    logger.info(f"共 {len(accounts)} 个账户")
    
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