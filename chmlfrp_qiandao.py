#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium + GEETEST破解版)
"""

import os
import sys
import time
import random
import logging
import base64
import io
from datetime import datetime
from typing import List, Tuple, Optional, TYPE_CHECKING

# 尝试导入 Pillow
try:
    from PIL import Image, ImageChops
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    # 创建假类避免类型注解错误
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
        
        # 查找 Chrome
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
                from selenium.webdriver.chrome.service import Service
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
        
        from selenium.webdriver.support.ui import WebDriverWait
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
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except:
            return None
    
    def has_geetest(self) -> bool:
        """检查是否存在 GEETEST 验证框"""
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
    
    def get_geetest_images(self):
        """获取 GEETEST 的两张图片"""
        if not HAS_PIL:
            return None, None
            
        try:
            time.sleep(2)
            
            # 获取带缺口的背景图
            bg_js = "return document.querySelector('.geetest_canvas_bg') ? document.querySelector('.geetest_canvas_bg').toDataURL('image/png') : null"
            bg_data = self.driver.execute_script(bg_js)
            
            # 获取完整背景图
            show_full_js = """
                var el = document.querySelector('.geetest_canvas_fullbg');
                if(el) el.style.opacity = 1;
                return document.querySelector('.geetest_canvas_fullbg') ? document.querySelector('.geetest_canvas_fullbg').toDataURL('image/png') : null;
            """
            full_data = self.driver.execute_script(show_full_js)
            
            if not bg_data or not full_data:
                return None, None
            
            # 解码 base64
            bg_img = Image.open(io.BytesIO(base64.b64decode(bg_data.split(',')[1])))
            full_img = Image.open(io.BytesIO(base64.b64decode(full_data.split(',')[1])))
            
            return bg_img, full_img
        except Exception as e:
            logger.error(f"获取GEETEST图片失败: {e}")
            return None, None
    
    def calculate_gap(self, bg_img, full_img) -> int:
        """计算缺口位置"""
        if not HAS_PIL:
            return 100  # 默认值
            
        try:
            bg = bg_img.convert('RGB')
            full = full_img.convert('RGB')
            
            width, height = bg.size
            threshold = 60
            
            for x in range(60, width - 60, 2):  # 从60开始，避免左边干扰
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
        """生成人类-like的滑动轨迹"""
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
        
        # 修正误差
        total = sum(tracks)
        if total > distance:
            tracks[-1] -= (total - distance)
        elif total < distance:
            tracks.append(distance - total)
        
        return tracks
    
    def solve_geetest(self) -> bool:
        """破解 GEETEST 滑块验证"""
        if not HAS_PIL:
            logger.error("没有 Pillow，无法破解 GEETEST")
            return False
        
        try:
            logger.info("开始破解 GEETEST...")
            time.sleep(2)
            
            # 获取图片
            bg_img, full_img = self.get_geetest_images()
            if not bg_img or not full_img:
                logger.error("无法获取验证图片")
                return False
            
            # 保存调试
            if os.environ.get("DEBUG") == "true":
                bg_img.save(f"geetest_bg_{int(time.time())}.png")
                full_img.save(f"geetest_full_{int(time.time())}.png")
            
            # 计算缺口
            gap_x = self.calculate_gap(bg_img, full_img)
            logger.info(f"检测到缺口位置: {gap_x}")
            
            # 获取滑块
            slider = None
            try:
                slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button")
            except:
                try:
                    slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider")
                except:
                    pass
            
            if not slider:
                logger.error("未找到滑块")
                return False
            
            # 计算滑动距离
            slider_x = slider.location['x']
            distance = gap_x - slider_x - 10
            
            if distance < 50 or distance > 400:
                distance = gap_x  # 如果计算异常，直接用缺口位置
            
            logger.info(f"需要滑动距离: {distance}")
            
            # 生成轨迹
            tracks = self.get_slide_tracks(int(distance))
            logger.info(f"生成轨迹点数: {len(tracks)}")
            
            # 执行滑动
            from selenium.webdriver.common.action_chains import ActionChains
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.5)
            
            # 分步移动
            for track in tracks:
                action.move_by_offset(track, random.randint(-2, 2)).perform()
                time.sleep(random.uniform(0.01, 0.03))
            
            time.sleep(0.5)
            action.release().perform()
            
            # 等待结果
            time.sleep(3)
            
            if not self.has_geetest():
                logger.info("GEETEST 验证通过!")
                return True
            else:
                logger.warning("验证可能失败，验证框仍在")
                return False
                
        except Exception as e:
            logger.error(f"破解 GEETEST 异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def simple_slide_attempt(self) -> bool:
        """简化的滑块尝试（无Pillow时使用）"""
        try:
            logger.info("尝试简化版滑动...")
            slider = self.driver.find_element(By.CSS_SELECTOR, ".geetest_slider_button, .geetest_slider")
            
            # 简单拖动到中间偏右
            from selenium.webdriver.common.action_chains import ActionChains
            action = ActionChains(self.driver)
            action.click_and_hold(slider).perform()
            time.sleep(0.3)
            
            # 分三段移动
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
            
            # 查找签到按钮
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
            
            # 点击签到
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkin_btn)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", checkin_btn)
            logger.info(f"[{username}] 已点击签到")
            
            # 等待看是否弹出 GEETEST
            time.sleep(3)
            
            # 检查并处理 GEETEST
            if self.has_geetest():
                logger.info(f"[{username}] 检测到 GEETEST 验证")
                
                # 先尝试完整破解（需要Pillow）
                if HAS_PIL:
                    success = self.solve_geetest()
                else:
                    success = self.simple_slide_attempt()
                
                if not success:
                    return False, "GEETEST 验证失败"
                time.sleep(3)
            
            # 检查结果
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
            
            # 再次检查按钮状态
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
    logger.info("CHMLFRP 自动签到工具 (GEETEST破解版)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Pillow可用: {HAS_PIL}")
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