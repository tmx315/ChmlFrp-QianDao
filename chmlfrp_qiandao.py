#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (修复版 v2)
修复：token 字段名改为 usertoken
"""

import os
import sys
import json
import time
import random
import logging
import requests
from datetime import datetime
from typing import List, Dict, Tuple, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ChmlFrpAPI:
    BASE_URL = "https://cf-v2.uapis.cn"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://panel.chmlfrp.net",
            "Referer": "https://panel.chmlfrp.net/"
        })
        self.token: Optional[str] = None
        self.debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    def log_debug(self, title: str, data):
        if self.debug:
            logger.info(f"[DEBUG] {title}: {json.dumps(data, ensure_ascii=False, indent=2)[:500] if isinstance(data, dict) else str(data)[:500]}")
    
    def login(self, username: str, password: str) -> bool:
        try:
            url = f"{self.BASE_URL}/login"
            payload = {"username": username, "password": password}
            
            delay = random.uniform(2, 5)
            logger.info(f"[{username}] 登录前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            response = self.session.post(url, json=payload, timeout=15)
            
            try:
                result = response.json()
            except:
                logger.error(f"[{username}] JSON解析失败: {response.text[:200]}")
                return False
            
            self.log_debug("登录响应", result)
            
            if result.get("code") != 200:
                msg = result.get("msg", "未知错误")
                logger.error(f"[{username}] 登录失败: {msg}")
                return False
            
            # 修复：CHMLFRP 使用 usertoken 字段
            data = result.get("data", {})
            if isinstance(data, dict):
                token = data.get("usertoken")  # 关键修复：字段名是 usertoken
                if token:
                    self.token = token
                    self.user_info = data
                    self.session.headers["Authorization"] = f"Bearer {token}"
                    logger.info(f"[{username}] 登录成功! Token: {token[:20]}...")
                    return True
            
            logger.error(f"[{username}] 未找到 usertoken，data字段: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return False
            
        except Exception as e:
            logger.error(f"[{username}] 登录异常: {str(e)}")
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        if not self.token:
            return False, "未登录"
        
        try:
            url = f"{self.BASE_URL}/user/checkin"
            
            delay = random.uniform(5, 15)
            logger.info(f"[{username}] 签到前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            response = self.session.post(url, timeout=15)
            
            try:
                result = response.json()
            except:
                return False, f"响应解析失败: {response.text[:200]}"
            
            self.log_debug("签到响应", result)
            
            code = result.get("code")
            msg = result.get("msg", "")
            
            if code == 200:
                data = result.get("data", {})
                pts = data.get("points", "?") if isinstance(data, dict) else "?"
                days = data.get("consecutive_days", "?") if isinstance(data, dict) else "?"
                return True, f"签到成功! +{pts}积分, 连续{days}天"
            elif code == 400 and ("已签到" in msg or "已经" in msg):
                return True, f"今日已签到"
            else:
                return False, f"失败: {msg}"
                
        except Exception as e:
            return False, f"异常: {str(e)}"

def get_accounts():
    users = os.environ.get("CHMLFRP_USER", "").replace("\\n", "\n").split("\n")
    passes = os.environ.get("CHMLFRP_PASS", "").replace("\\n", "\n").split("\n")
    
    user_list = [u.strip() for u in users if u.strip()]
    pass_list = [p.strip() for p in passes if p.strip()]
    
    if len(user_list) != len(pass_list):
        logger.error(f"账户数量不匹配")
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (修复版 v2)")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    accounts = get_accounts()
    if not accounts:
        logger.error("未配置账户")
        sys.exit(1)
    
    results = []
    for idx, (user, pwd) in enumerate(accounts, 1):
        logger.info(f"\n[{idx}/{len(accounts)}] 处理: {user}")
        
        api = ChmlFrpAPI()
        if not api.login(user, pwd):
            results.append((user, False, "登录失败"))
            continue
        
        success, msg = api.checkin(user)
        results.append((user, success, msg))
        
        if idx < len(accounts):
            time.sleep(random.uniform(3, 6))
    
    logger.info("\n" + "=" * 60)
    logger.info("结果汇总")
    for user, success, msg in results:
        logger.info(f"{'✅' if success else '❌'} {user}: {msg}")
    
    success_count = sum(1 for _, s, _ in results if s)
    logger.info(f"统计: 成功 {success_count}/{len(results)}")
    
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"summary=成功 {success_count}/{len(results)}\n")
    
    sys.exit(0 if success_count == len(results) else 1)

if __name__ == "__main__":
    main()