#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium + GEETEST破解重试版)
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
    
    def get_geetest_images_with_retry(self, max_retries=3):
        """带重试的获取 GEETEST 图片"""
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试获取图片 ({attempt + 1}/{max_retries})...")
                time.sleep(2)
                
                # 首先检查页面上的所有 canvas
                all_canvas = self.driver.find_elements(By.TAG_NAME, "canvas")
                logger.info(f"页面上共有 {len(all_canvas)} 个 canvas")
                
                if len(all_canvas) >= 2:
                    # 尝试获取前两个 canvas 的数据
                    try:
                        bg_data = self.driver.execute_script(
                            "return document.querySelectorAll('canvas')[0].toDataURL('image/png');"
                        )
                        full_data = self.driver.execute_script(
                            "return document.querySelectorAll('canvas')[1].toDataURL('image/png');"
                        )
                        
                        if bg_data and full_data:
                            bg_img = Image.open(io.BytesIO(base64.b64decode(bg_data.split(',')[1])))
                            full_img = Image.open(io.BytesIO(base64.b64decode(full_data.split(',')[1])))
                            
                            if os.environ.get("DEBUG") == "true":
                                timestamp = int(time.time())
                                bg_img.save(f"geetest_bg_{timestamp}.png")
                                full_img.save(f"geetest_full_{timestamp}.png")
                            
                            return bg_img, full_img
                    except Exception as e:
                        logger.warning(f"通过索引获取 canvas 失败: {e}")
                
                # 备用：尝试 class 选择器
                canvas_selectors = [
                    (".geetest_canvas_bg", ".geetest_canvas_fullbg"),
                    ("canvas.geetest_canvas_slice", "canvas.geetest_canvas_bg"),
                    ("[class*='slice'] canvas", "[class*='bg'] canvas"),
                ]
                
                for bg_sel, full_sel in canvas_selectors:
                    try:
                        bg_elem = self.driver.find_element(By.CSS_SELECTOR, bg_sel)
                        full_elem = self.driver.find_element(By.CSS_SELECTOR, full_sel)
                        
                        bg_data = self.driver.execute_script(
                            "return arguments[0].toDataURL('image/png');", bg_elem
                        )
                        full_data = self.driver.execute_script(
                            "return arguments[0].toDataURL('image/png');", full_elem
                        )
                        
                        if bg_data and full_data:
                            bg_img = Image.open(io.BytesIO(base64.b64decode(bg_data.split(',')[1])))
                            full_img = Image.open(io.BytesIO(base64.b64decode(full_data.split(',')[1])))
                            return bg_img, full_img
                    except:
                        continue
                
                logger.error(f"第 {attempt + 1} 次尝试无法获取图片")
                if attempt < max_retries - 1:
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"获取图片异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        return None, None
    
    def calculate_gap(self, bg_img, full_img) -> int:
        if not HAS_PIL:
            return 100
            
        try:
            bg = bg_img.convert('RGB')
            full = full_img.convert('RGB')
            
            width, height = bg.size
            threshold = 60
            
            # 从左边 60px 开始扫描，避免边框干扰
            for x in range(60, width - 60, 2):
                for y in range(0, height, 5):
                    bg_pixel = bg.getpixel((x, y))
                    full_pixel = full.getpixel((x, y))
                    
                    diff = sum(abs(a - b) for a, b in zip(bg_pixel, full_pixel))
                    if diff > threshold:
                        return x
            
            return width // 2
        except Exception as e:
            logger.error(f"计算缺口失败: {e}")
            return 100
    
    def get_slide_tracks(self, distance: int) -> List[int]:
        tracks = []
        current = 0
        mid = distance * 3 / 4
        t = 0.2
        v = 0
        
        while current < distance:
            if current < mid:
                a = 2
            else:
                a = -3
            
            v0 = v
            v = v0 + a * t
            move = v0 * t + 0.5 * a * t * t
            current += move
            tracks.append(round(move))
        
        total = sum(tracks)
        if total > distance:
            tracks[-1] -= (total - distance)
        elif total < distance:
            tracks.append(distance - total)
        
        return tracks
    
    def perform_slide(self, gap_x: int) -> bool:
        """执行滑动"""
        try:
            slider = None
            for sel in [".geetest_slider_button", ".geetest_slider", "[class*='slider']"]:
                try:
                    slider = self.driver.find_element(By.CSS_SELECTOR, sel)
                    logger.info(f"找到滑块: {sel}")
                    break
                except:
                    continue
            
            if not slider:
                logger.error("未找到滑块")
                return False
            
            # 计算距离
            try:
                slider_x = slider.location['x']
                distance = gap_x - slider_x - 10
            except:
                distance = gap_x
            
            if distance < 50:
                distance = 100
            elif distance > 400:
                distance = 300
            
            logger.info(f"滑动距离: {distance}")
            
            tracks = self.get_slide_tracks(int(distance))
            
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.5)
            
            for i, track in enumerate(tracks):
                y_offset = random.randint(-3, 3) if i % 3 == 0 else 0
                action.move_by_offset(track, y_offset).perform()
                time.sleep(random.uniform(0.01, 0.04))
            
            time.sleep(random.uniform(0.2, 0.5))
            action.release().perform()
            
            time.sleep(3)
            
            if not self.has_geetest():
                logger.info("GEETEST 验证通过!")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"滑动失败: {e}")
            return False
    
    def random_slide_attempt(self) -> bool:
        """随机滑动"""
        try:
            slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button, .geetest_slider")
            distance = random.randint(150, 250)
            
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.3)
            action.move_by_offset(distance, random.randint(-5, 5)).perform()
            time.sleep(0.3)
            action.release().perform()
            
            time.sleep(3)
            return not self.has_geetest()
        except:
            return False
    
    def simple_slide_attempt(self) -> bool:
        """简化滑动"""
        try:
            slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button, .geetest_slider")
            
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.3)
            
            action.move_by_offset(80, 0).perform()
            time.sleep(0.2)
            action.move_by_offset(100, 0).perform()
            time.sleep(0.2)
            action.move_by_offset(60, 0).perform()
            time.sleep(0.3)
            action.release().perform()
            
            time.sleep(3)
            return not self.has_geetest()
        except:
            return False
    
    def solve_geetest(self) -> bool:
        """破解 GEETEST，带多种备用方案"""
        if not HAS_PIL:
            logger.warning("无 Pillow，使用简化方案")
            return self.simple_slide_attempt()
        
        # 尝试1：图像识别
        logger.info("方案1: 图像识别...")
        bg_img, full_img = self.get_geetest_images_with_retry(3)
        
        if bg_img and full_img:
            try:
                gap_x = self.calculate_gap(bg_img, full_img)
                logger.info(f"缺口位置: {gap_x}")
                
                if self.perform_slide(gap_x):
                    return True
                logger.warning("图像滑动失败")
            except Exception as e:
                logger.error(f"图像识别失败: {e}")
        
        # 尝试2：随机滑动
        logger.info("方案2: 随机滑动...")
        if self.random_slide_attempt():
            return True
        
        # 尝试3：简化滑动
        logger.info("方案3: 简化滑动...")
        if self.simple_slide_attempt():
            return True
        
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
                logger.info(f"[{username}] 检测到 GEETEST，开始破解...")
                
                if self.solve_geetest():
                    time.sleep(2)
                else:
                    return False, "GEETEST 验证失败（所有方案都失败）"
            
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
    logger.info("CHMLFRP 自动签到工具 (重试版)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Pillow: {HAS_PIL}")
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