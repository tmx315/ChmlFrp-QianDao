#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (单Canvas GEETEST破解版)
"""

import os
import sys
import time
import random
import logging
import base64
import io
from datetime import datetime
from typing import List, Tuple, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    class Image:
        class Image:
            pass

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
        
        try:
            if chromedriver_path:
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome 启动失败: {e}")
            raise
        
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 20)
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
        try:
            selectors = [
                ".geetest_challenge",
                ".geetest_box",
                ".geetest_popup_box",
                "iframe[src*='geetest']",
                "[class*='geetest']"
            ]
            for sel in selectors:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, sel)
                    return True
                except:
                    continue
            return False
        except:
            return False
    
    def get_geetest_info(self):
        """获取 GEETEST 的详细信息"""
        try:
            # 保存截图
            self.driver.save_screenshot(f"geetest_debug_{int(time.time())}.png")
            logger.info("已保存调试截图")
            
            # 检查所有图片
            images = self.driver.find_elements(By.TAG_NAME, "img")
            logger.info(f"img标签数量: {len(images)}")
            
            # 检查canvas
            canvases = self.driver.find_elements(By.TAG_NAME, "canvas")
            logger.info(f"canvas数量: {len(canvases)}")
            
            # 检查滑块
            try:
                slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button")
                logger.info(f"滑块位置: {slider.location}, 大小: {slider.size}")
            except:
                logger.warning("未找到滑块")
            
            return True
        except Exception as e:
            logger.error(f"获取信息失败: {e}")
            return False
    
    def brute_force_slide(self) -> bool:
        """暴力尝试各种滑动距离（针对单canvas）"""
        try:
            # 常见滑块距离
            distances = [150, 180, 200, 220, 250, 170, 190, 210, 230]
            
            for dist in distances:
                logger.info(f"暴力尝试滑动: {dist}px")
                
                # 尝试刷新（获取新验证）
                if dist != distances[0]:
                    try:
                        refresh = self.driver.find_element(By.CSS_SELECTOR, ".geetest_refresh")
                        refresh.click()
                        logger.info("已刷新验证")
                        time.sleep(3)
                    except:
                        logger.warning("无法刷新，继续尝试")
                
                # 检查是否还有验证框
                if not self.has_geetest():
                    logger.info("验证框已消失，可能已自动通过")
                    return True
                
                # 获取滑块
                try:
                    slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button")
                except:
                    logger.info("滑块不存在，验证可能已通过")
                    return True
                
                # 执行滑动
                action = ActionChains(self.driver)
                action.click_and_hold(slider).perform()
                time.sleep(0.3)
                
                # 分步移动，模拟人类
                steps = random.randint(3, 6)
                step_dist = dist // steps
                for i in range(steps):
                    # 添加随机抖动
                    y_off = random.randint(-3, 3)
                    action.move_by_offset(step_dist, y_off).perform()
                    time.sleep(random.uniform(0.05, 0.15))
                
                # 最后微调
                remaining = dist - (step_dist * steps)
                if remaining > 0:
                    action.move_by_offset(remaining, random.randint(-2, 2)).perform()
                
                time.sleep(0.3)
                action.release().perform()
                
                # 等待验证结果
                time.sleep(3)
                
                # 检查是否成功
                if not self.has_geetest():
                    logger.info(f"✓ 暴力破解成功! 距离: {dist}px")
                    return True
                
                logger.warning(f"✗ 距离 {dist}px 失败")
            
            return False
            
        except Exception as e:
            logger.error(f"暴力破解异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def solve_geetest(self) -> bool:
        """破解 GEETEST"""
        logger.info("=" * 40)
        logger.info("开始破解 GEETEST")
        
        # 获取信息
        self.get_geetest_info()
        
        # 直接暴力破解（针对单canvas情况最有效）
        logger.info("执行暴力破解方案...")
        if self.brute_force_slide():
            return True
        
        logger.error("所有破解方案均失败")
        return False
    
    def login(self, username: str, password: str) -> bool:
        try:
            self.driver.get(self.LOGIN_URL)
            logger.info(f"[{username}] 打开登录页...")
            time.sleep(3)
            
            user_input = self.safe_find(By.XPATH, "//input[@type='text']", 10)
            if not user_input:
                user_input = self.safe_find(By.CSS_SELECTOR, "input.el-input__inner", 5)
            
            if not user_input:
                return False
            
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
            pass_input = self.safe_find(By.XPATH, "//input[@type='password']", 10)
            if not pass_input:
                return False
            
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))
            
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
            
            checkin_btn = None
            try:
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
                return False, "未找到签到按钮"
            
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkin_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", checkin_btn)
            logger.info(f"[{username}] 已点击签到")
            
            time.sleep(3)
            
            if self.has_geetest():
                logger.info(f"[{username}] 检测到 GEETEST")
                
                if self.solve_geetest():
                    time.sleep(2)
                else:
                    return False, "GEETEST 验证失败"
            
            try:
                msg_elem = self.driver.find_element(By.CSS_SELECTOR, ".el-message__content")
                msg = msg_elem.text
                if "成功" in msg or "积分" in msg:
                    return True, f"签到成功: {msg}"
                elif "已经" in msg or "已签" in msg:
                    return True, "今日已签到"
                else:
                    return True, msg
            except:
                pass
            
            try:
                buttons = self.driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "已签到" in btn.text:
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
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (暴力破解版)")
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
