#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (Selenium版本)
适用于需要浏览器模拟的场景，或API无法使用的情况
"""

import os
import sys
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    import ddddocr
    OCR_ENABLED = True
except ImportError:
    OCR_ENABLED = False
    logging.warning("ddddocr 未安装，如遇到验证码将跳过")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ChmlFrpSelenium:
    """CHMLFRP Selenium 自动化"""
    
    LOGIN_URL = "https://panel.chmlfrp.net/login"
    USER_URL = "https://panel.chmlfrp.net/user"
    
    def __init__(self, headless: bool = None, debug: bool = False):
        self.driver: Optional[webdriver.Chrome] = None
        self.wait: Optional[WebDriverWait] = None
        self.headless = headless if headless is not None else os.environ.get("HEADLESS", "false").lower() == "true"
        self.debug = debug or os.environ.get("DEBUG", "false").lower() == "true"
        self.ocr = ddddocr.DdddOcr() if OCR_ENABLED else None
        
    def init_driver(self):
        """初始化 Chrome 驱动"""
        chrome_options = Options()
        
        if self.headless or os.environ.get("GITHUB_ACTIONS") == "true":
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 尝试初始化
        try:
            # 尝试使用 webdriver-manager
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            except:
                # 回退到系统路径
                self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome 驱动初始化失败: {e}")
            raise
        
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
        })
        
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("Chrome 驱动初始化成功")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def solve_captcha(self) -> Optional[str]:
        """识别验证码（如有）"""
        if not self.ocr:
            return None
        
        try:
            # 查找验证码图片
            captcha_img = self.driver.find_element(By.XPATH, "//img[contains(@src,'captcha') or contains(@class,'captcha')]")
            img_base64 = captcha_img.get_attribute("src")
            
            if "base64" in img_base64:
                img_data = base64.b64decode(img_base64.split(",")[1])
                result = self.ocr.classification(img_data)
                logger.info(f"验证码识别结果: {result}")
                return result
        except NoSuchElementException:
            pass
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
        
        return None
    
    def login(self, username: str, password: str) -> bool:
        """登录账户"""
        try:
            self.driver.get(self.LOGIN_URL)
            delay = random.uniform(2, 5)
            logger.info(f"[{username}] 页面加载，延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            # 填写用户名
            user_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            user_input.clear()
            for char in username:
                user_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            # 填写密码
            pass_input = self.driver.find_element(By.NAME, "password")
            pass_input.clear()
            for char in password:
                pass_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
            
            # 检查验证码
            captcha_code = self.solve_captcha()
            if captcha_code:
                captcha_input = self.driver.find_element(By.NAME, "captcha")
                captcha_input.send_keys(captcha_code)
            
            # 点击登录
            login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'登录') or @type='submit']")
            login_btn.click()
            
            # 等待登录成功跳转
            time.sleep(3)
            
            # 检查是否登录成功
            if "user" in self.driver.current_url or "panel" in self.driver.current_url:
                logger.info(f"[{username}] 登录成功！")
                return True
            else:
                # 检查错误信息
                try:
                    error_msg = self.driver.find_element(By.CLASS_NAME, "el-message__content").text
                    logger.error(f"[{username}] 登录失败: {error_msg}")
                except:
                    logger.error(f"[{username}] 登录失败: 未知错误")
                return False
                
        except TimeoutException:
            logger.error(f"[{username}] 登录超时")
            return False
        except Exception as e:
            logger.error(f"[{username}] 登录过程出错: {e}")
            return False
    
    def checkin(self) -> Tuple[bool, str]:
        """执行签到"""
        try:
            # 进入用户中心
            self.driver.get(self.USER_URL)
            time.sleep(3)
            
            # 查找签到按钮
            try:
                checkin_btn = self.driver.find_element(By.XPATH, "//button[contains(text(),'签到') or contains(@class,'checkin')]")
                
                if "已签到" in checkin_btn.text or "disabled" in checkin_btn.get_attribute("class"):
                    return True, "今日已签到"
                
                # 点击签到
                checkin_btn.click()
                time.sleep(2)
                
                # 查找结果提示
                try:
                    msg = self.driver.find_element(By.CLASS_NAME, "el-message__content").text
                    return True, msg
                except:
                    return True, "签到操作已执行"
                    
            except NoSuchElementException:
                # 可能已签到或页面结构不同
                page_source = self.driver.page_source
                if "已签到" in page_source or "今日已签" in page_source:
                    return True, "今日已签到（页面检测）"
                return False, "未找到签到按钮"
                
        except Exception as e:
            return False, f"签到过程出错: {str(e)}"

def get_accounts_from_env() -> List[Tuple[str, str]]:
    """从环境变量获取账户"""
    users_str = os.environ.get("CHMLFRP_USER", "")
    passes_str = os.environ.get("CHMLFRP_PASS", "")
    
    if not users_str or not passes_str:
        return []
    
    users = [u.strip() for u in users_str.split("\n") if u.strip()]
    passes = [p.strip() for p in passes_str.split("\n") if p.strip()]
    
    if len(users) != len(passes):
        logger.error("用户名和密码数量不匹配！")
        return []
    
    return list(zip(users, passes))

def run_checkin():
    """主运行函数"""
    logger.info("=" * 50)
    logger.info("CHMLFRP Selenium 自动签到工具启动")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    accounts = get_accounts_from_env()
    
    if not accounts:
        logger.error("未配置账户，请设置 CHMLFRP_USER 和 CHMLFRP_PASS 环境变量")
        sys.exit(1)
    
    bot = ChmlFrpSelenium()
    bot.init_driver()
    
    results = []
    
    try:
        for idx, (username, password) in enumerate(accounts, 1):
            logger.info(f"\n[{idx}/{len(accounts)}] 处理账户: {username}")
            
            if bot.login(username, password):
                success, msg = bot.checkin()
                results.append({"username": username, "success": success, "message": msg})
            else:
                results.append({"username": username, "success": False, "message": "登录失败"})
            
            if idx < len(accounts):
                time.sleep(random.uniform(5, 10))
    finally:
        bot.close()
    
    # 汇总
    logger.info("\n" + "=" * 50)
    logger.info("签到结果汇总")
    logger.info("=" * 50)
    for r in results:
        status = "✅" if r["success"] else "❌"
        logger.info(f"{status} {r['username']}: {r['message']}")
    
    return all(r["success"] for r in results)

if __name__ == "__main__":
    try:
        success = run_checkin()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"程序异常: {e}")
        sys.exit(1)