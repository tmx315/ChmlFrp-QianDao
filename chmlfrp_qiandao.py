#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium版 v4)
添加 GEETEST 检测和重试机制
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
from selenium.webdriver.common.action_chains import ActionChains
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
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 查找 Chrome
        chrome_binary = None
        for path in ["/opt/google/chrome/chrome", "/usr/bin/google-chrome"]:
            if os.path.exists(path):
                chrome_binary = path
                break
        
        chromedriver_path = "/usr/local/bin/chromedriver"
        
        if chrome_binary:
            chrome_options.binary_location = chrome_binary
        
        try:
            service = Service(chromedriver_path) if os.path.exists(chromedriver_path) else None
            if service:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome 启动失败: {e}")
            raise
        
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("Chrome 初始化成功")
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def safe_find(self, by, value, timeout=10):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except:
            return None
    
    def has_geetest(self) -> bool:
        """检查是否存在 GEETEST 验证框"""
        try:
            # 常见的 GEETEST 选择器
            selectors = [
                ".geetest_challenge",
                ".geetest_box",
                "iframe[name*='geetest']",
                "[class*='geetest']",
                "//div[contains(@class, 'geetest')]"
            ]
            for sel in selectors:
                try:
                    if sel.startswith("//"):
                        self.driver.find_element(By.XPATH, sel)
                    else:
                        self.driver.find_element(By.CSS_SELECTOR, sel)
                    return True
                except:
                    continue
            return False
        except:
            return False
    
    def click_at_coordinates(self, x, y):
        """在指定坐标点击（用于绕过某些检测）"""
        action = ActionChains(self.driver)
        action.move_by_offset(x, y).click().perform()
        action.move_by_offset(-x, -y).perform()  # 移回
    
    def login(self, username: str, password: str) -> bool:
        try:
            self.driver.get(self.LOGIN_URL)
            logger.info(f"[{username}] 打开登录页...")
            time.sleep(3)
            
            # 用户名
            user_input = self.safe_find(By.XPATH, "//input[@type='text']", 10)
            if not user_input:
                user_input = self.safe_find(By.CSS_SELECTOR, "input.el-input__inner", 5)
            
            if not user_input:
                logger.error(f"[{username}] 未找到用户名输入框")
                return False
            
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 密码
            pass_input = self.safe_find(By.XPATH, "//input[@type='password']", 10)
            if not pass_input:
                return False
            
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            # 登录按钮
            login_btn = None
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[contains(., '登录')]")
            except:
                try:
                    login_btn = self.driver.find_element(By.CSS_SELECTOR, "button.el-button--primary")
                except:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    if buttons:
                        login_btn = buttons[-1]
            
            if not login_btn:
                return False
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_btn)
            time.sleep(0.5)
            login_btn.click()
            
            time.sleep(5)
            
            current_url = self.driver.current_url
            logger.info(f"[{username}] 当前URL: {current_url}")
            
            if "home" in current_url:
                logger.info(f"[{username}] 登录成功!")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"[{username}] 登录异常: {str(e)}")
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        try:
            self.driver.get(self.HOME_URL)
            logger.info(f"[{username}] 进入用户中心...")
            time.sleep(3)
            
            # 截图看当前状态
            if os.environ.get("DEBUG") == "true":
                self.driver.save_screenshot(f"before_checkin_{username}.png")
            
            # 查找签到按钮
            checkin_btn = None
            try:
                # 先找包含"签到"文本的按钮
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    text = btn.text
                    if "签到" in text and "已" not in text:
                        checkin_btn = btn
                        logger.info(f"[{username}] 找到签到按钮: '{text}'")
                        break
                    elif "已签到" in text or "今日已签" in text:
                        return True, "今日已签到"
            except Exception as e:
                logger.error(f"查找按钮失败: {e}")
            
            if not checkin_btn:
                # 尝试其他选择器
                try:
                    checkin_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'el-button--primary')]")
                except:
                    pass
            
            if not checkin_btn:
                return False, "未找到签到按钮"
            
            # 点击前检查是否有 GEETEST
            if self.has_geetest():
                logger.warning(f"[{username}] 检测到 GEEST 验证，尝试处理...")
                # 这里可以添加滑块处理逻辑，但目前先返回失败
                return False, "遇到 GEETEST 验证，需要手动处理或等待 API 版本"
            
            # 点击签到
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkin_btn)
            time.sleep(0.5)
            
            # 使用 JavaScript 点击，有时比 Selenium 的 click 更稳定
            self.driver.execute_script("arguments[0].click();", checkin_btn)
            logger.info(f"[{username}] 已点击签到按钮")
            
            # 等待响应，检查是否有验证弹出
            time.sleep(3)
            
            # 检查是否出现 GEEST 验证
            if self.has_geetest():
                logger.warning(f"[{username}] 点击后弹出 GEEST 验证")
                # 保存截图
                self.driver.save_screenshot(f"geetest_{username}_{int(time.time())}.png")
                return False, "触发 GEETEST 滑块验证，无法自动完成"
            
            # 等待更长时间看结果
            time.sleep(3)
            
            # 检查结果提示
            try:
                msg_elem = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content")
                msg = msg_elem.text
                logger.info(f"[{username}] 提示信息: {msg}")
                
                if "成功" in msg:
                    return True, f"签到成功: {msg}"
                elif "已经" in msg or "已签到" in msg:
                    return True, "今日已签到"
                elif "积分" in msg:
                    return True, msg
                else:
                    return False, f"未知状态: {msg}"
            except:
                pass
            
            # 再次检查按钮状态
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "已签到" in btn.text or "今日已签" in btn.text:
                        return True, "签到成功（按钮状态已变）"
                    elif "签到" in btn.text:
                        # 按钮还在，说明可能没成功
                        return False, "点击后按钮未变化，可能未成功"
            except:
                pass
            
            return False, "无法确认签到状态"
            
        except Exception as e:
            logger.error(f"[{username}] 签到异常: {str(e)}")
            return False, str(e)

def get_accounts():
    users = os.environ.get("CHMLFRP_USER", "").replace("\\n", "\n").split("\n")
    passes = os.environ.get("CHMLFRP_PASS", "").replace("\\n", "\n").split("\n")
    
    user_list = [u.strip() for u in users if u.strip()]
    pass_list = [p.strip() for p in passes if p.strip()]
    
    if len(user_list) != len(pass_list):
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (Selenium v4)")
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
        
        # 上传截图作为 artifact（如果有的话）
        if os.environ.get("GITHUB_ACTIONS") == "true":
            import glob
            screenshots = glob.glob("*.png")
            if screenshots:
                logger.info(f"生成了 {len(screenshots)} 个截图文件")
        
        sys.exit(0 if success_count == len(results) else 1)
        
    finally:
        bot.close()

if __name__ == "__main__":
    main()