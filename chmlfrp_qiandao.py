#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium版)
支持 GeeTest 滑块验证码
"""

import os
import sys
import json
import time
import random
import logging
import base64
from datetime import datetime
from typing import List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ChmlFrpSelenium:
    """CHMLFRP Selenium 自动化（支持 GeeTest 滑块验证）"""
    
    LOGIN_URL = "https://panel.chmlfrp.net/sign"
    HOME_URL = "https://panel.chmlfrp.net/home"
    
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.headless = os.environ.get("HEADLESS", "true").lower() == "true"
        self.debug = os.environ.get("DEBUG", "false").lower() == "true"
        
    def init_driver(self):
        """初始化 Chrome 驱动"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            # 无头模式下需要更大的窗口，有些验证会检测
            chrome_options.add_argument("--window-size=1920,1080")
        
        # 反检测设置
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 尝试初始化
        try:
            # GitHub Actions 环境
            if os.environ.get("GITHUB_ACTIONS") == "true":
                # 使用系统安装的 chromium
                chrome_options.binary_location = "/usr/bin/chromium-browser"
                service = Service("/usr/bin/chromedriver")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 本地环境使用 webdriver-manager
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except:
                    self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome 驱动初始化失败: {e}")
            raise
        
        # 执行 CDP 命令隐藏 webdriver 属性
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 20)
        logger.info("Chrome 驱动初始化成功")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def login(self, username: str, password: str) -> bool:
        """登录"""
        try:
            self.driver.get(self.LOGIN_URL)
            logger.info(f"[{username}] 打开登录页...")
            time.sleep(3)
            
            # 填写用户名
            user_input = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, "input[type='text'], input[name='username'], input[placeholder*='用户名'], input[placeholder*='邮箱']"
            )))
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            
            # 填写密码
            pass_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))
            
            # 点击登录按钮
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .el-button--primary")
            login_btn.click()
            
            logger.info(f"[{username}] 已点击登录，等待跳转...")
            time.sleep(5)
            
            # 检查是否登录成功（URL 变化或出现用户中心元素）
            if "home" in self.driver.current_url or "panel" in self.driver.current_url:
                logger.info(f"[{username}] 登录成功!")
                return True
            else:
                # 检查是否有错误提示
                try:
                    error = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content, .error-message").text
                    logger.error(f"[{username}] 登录失败: {error}")
                except:
                    logger.error(f"[{username}] 登录失败，当前URL: {self.driver.current_url}")
                return False
                
        except Exception as e:
            logger.error(f"[{username}] 登录异常: {str(e)}")
            if self.debug:
                self.save_screenshot(f"login_error_{username}")
            return False
    
    def solve_geetest(self) -> bool:
        """
        尝试处理 GeeTest 滑块验证
        注意：这只是一个基础实现，实际可能需要更复杂的逻辑
        """
        try:
            # 检查是否存在 GeeTest 验证框
            geetest_selector = ".geetest_challenge, .geetest_box, iframe[name*='geetest']"
            try:
                geetest = self.driver.find_element(By.CSS_SELECTOR, geetest_selector)
                logger.info("检测到 GeeTest 验证...")
            except NoSuchElementException:
                return True  # 没有验证框，直接通过
            
            # 等待滑块出现
            slider = self.wait.until(EC.presence_of_element_located((
                By.CSS_SELECTOR, ".geetest_slider, .geetest_slider_button, .geetest_btn"
            )))
            
            logger.info("开始处理滑块验证...")
            
            # 获取滑块位置
            slider_location = slider.location
            slider_size = slider.size
            
            # 简单的拖动逻辑（实际可能需要根据缺口位置计算）
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.5)
            
            # 随机拖动（实际应该解析图片找到缺口位置）
            # 这里使用随机距离，成功率可能不高
            distance = random.randint(100, 200)
            action.move_by_offset(distance, 0).perform()
            time.sleep(0.5)
            
            # 释放
            action.release().perform()
            time.sleep(3)
            
            # 检查是否验证成功（验证框消失）
            try:
                self.driver.find_element(By.CSS_SELECTOR, geetest_selector)
                logger.warning("验证可能未通过，验证框仍存在")
                return False
            except NoSuchElementException:
                logger.info("滑块验证通过!")
                return True
                
        except Exception as e:
            logger.error(f"滑块验证处理失败: {e}")
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        """执行签到"""
        try:
            # 进入用户中心
            self.driver.get(self.HOME_URL)
            logger.info(f"[{username}] 进入用户中心...")
            time.sleep(3)
            
            # 查找签到按钮
            # 根据截图，签到按钮应该在右上角，紫色/蓝色按钮
            checkin_selectors = [
                "//button[contains(text(), '签到')]",
                "//span[contains(text(), '签到')]/parent::button",
                ".el-button--primary span:contains('签到')",
                "[class*='checkin']",
                "[class*='qiandao']"
            ]
            
            checkin_btn = None
            for selector in checkin_selectors:
                try:
                    if selector.startswith("//"):
                        checkin_btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        checkin_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if checkin_btn:
                        break
                except:
                    continue
            
            if not checkin_btn:
                # 尝试通过文本内容查找
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "签到" in btn.text:
                        checkin_btn = btn
                        break
            
            if not checkin_btn:
                return False, "未找到签到按钮"
            
            # 检查是否已经签到
            btn_text = checkin_btn.text
            if "已签到" in btn_text or "今日已签" in btn_text:
                return True, "今日已签到"
            
            logger.info(f"[{username}] 点击签到按钮...")
            checkin_btn.click()
            time.sleep(2)
            
            # 处理可能出现的 GeeTest 验证
            if not self.solve_geetest():
                return False, "滑块验证失败"
            
            # 等待签到结果
            time.sleep(3)
            
            # 查找成功提示
            try:
                msg = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content").text
                if "成功" in msg or "积分" in msg:
                    return True, f"签到成功: {msg}"
                else:
                    return True, msg
            except:
                # 检查按钮状态变化
                try:
                    new_text = checkin_btn.text
                    if "已签到" in new_text:
                        return True, "签到成功（按钮状态变化）"
                except:
                    pass
                return True, "签到操作完成"
                
        except Exception as e:
            logger.error(f"[{username}] 签到异常: {str(e)}")
            if self.debug:
                self.save_screenshot(f"checkin_error_{username}")
            return False, str(e)
    
    def save_screenshot(self, name: str):
        """保存截图用于调试"""
        try:
            filename = f"{name}_{int(time.time())}.png"
            self.driver.save_screenshot(filename)
            logger.info(f"已保存截图: {filename}")
        except:
            pass

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
    logger.info("CHMLFRP 自动签到工具 (Selenium版)")
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