#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (修复版)
基于 ChmlFrp API V2
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class ChmlFrpAPI:
    """CHMLFRP API V2 封装"""
    
    BASE_URL = "https://cf-v2.uapis.cn"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": "https://panel.chmlfrp.net",
            "Referer": "https://panel.chmlfrp.net/"
        })
        self.token: Optional[str] = None
        self.debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    def log_debug(self, title: str, data):
        if self.debug:
            logger.info(f"[DEBUG] {title}")
            try:
                if isinstance(data, dict):
                    logger.info(json.dumps(data, ensure_ascii=False, indent=2)[:800])
                else:
                    logger.info(str(data)[:800])
            except:
                logger.info(str(data)[:800])
    
    def login(self, username: str, password: str) -> bool:
        try:
            url = f"{self.BASE_URL}/login"
            payload = {"username": username, "password": password}
            
            delay = random.uniform(2, 5)
            logger.info(f"[{username}] 登录前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            logger.info(f"[{username}] 正在登录...")
            response = self.session.post(url, json=payload, timeout=15)
            
            self.log_debug("登录响应状态", {
                "status_code": response.status_code,
                "headers": dict(response.headers)
            })
            
            try:
                result = response.json()
            except:
                logger.error(f"[{username}] 响应解析失败: {response.text[:200]}")
                return False
            
            self.log_debug("登录响应体", result)
            
            if response.status_code != 200:
                logger.error(f"[{username}] HTTP错误: {response.status_code}")
                return False
            
            # API V2 返回格式处理
            code = result.get("code")
            if code != 200:
                msg = result.get("msg", "未知错误")
                logger.error(f"[{username}] 登录失败: {msg} (code: {code})")
                return False
            
            # 提取 token - 适配多种格式
            data = result.get("data", {})
            token = None
            
            if isinstance(data, dict):
                token = data.get("token") or data.get("Token") or data.get("access_token")
                if token:
                    self.user_info = data
            elif isinstance(data, str) and len(data) > 20:
                token = data
            
            if not token:
                logger.error(f"[{username}] 未找到token，响应字段: {list(result.keys())}")
                if isinstance(data, dict):
                    logger.error(f"data字段: {list(data.keys())}")
                return False
            
            self.token = token
            self.session.headers["Authorization"] = f"Bearer {token}"
            logger.info(f"[{username}] 登录成功! Token: {token[:15]}...")
            return True
            
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
            
            logger.info(f"[{username}] 正在签到...")
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
                if isinstance(data, dict):
                    pts = data.get("points", "?")
                    days = data.get("consecutive_days", "?")
                    return True, f"签到成功! +{pts}积分, 连续{days}天"
                return True, "签到成功!"
            elif code == 400 and ("已签到" in msg or "已经签到" in msg):
                return True, f"今日已签到: {msg}"
            else:
                return False, f"签到失败: {msg} (code: {code})"
                
        except Exception as e:
            return False, f"请求异常: {str(e)}"

def get_accounts() -> List[Tuple[str, str]]:
    """获取账户列表"""
    users = os.environ.get("CHMLFRP_USER", "")
    passes = os.environ.get("CHMLFRP_PASS", "")
    
    if not users or not passes:
        return []
    
    # 处理换行符（支持真实换行和\n转义）
    user_list = [u.strip() for u in users.replace("\\n", "\n").split("\n") if u.strip()]
    pass_list = [p.strip() for p in passes.replace("\\n", "\n").split("\n") if p.strip()]
    
    if len(user_list) != len(pass_list):
        logger.error(f"账户数量不匹配: {len(user_list)} 用户名 vs {len(pass_list)} 密码")
        return []
    
    return list(zip(user_list, pass_list))

def main():
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    if os.environ.get("DEBUG") == "true":
        logger.info("调试模式: 开启")
    
    accounts = get_accounts()
    if not accounts:
        logger.error("未找到账户配置，请设置 CHMLFRP_USER 和 CHMLFRP_PASS")
        sys.exit(1)
    
    logger.info(f"共发现 {len(accounts)} 个账户")
    
    results = []
    for idx, (user, pwd) in enumerate(accounts, 1):
        logger.info(f"\n[{idx}/{len(accounts)}] 处理账户: {user}")
        logger.info("-" * 40)
        
        api = ChmlFrpAPI()
        
        if not api.login(user, pwd):
            results.append((user, False, "登录失败"))
            continue
        
        success, msg = api.checkin(user)
        results.append((user, success, msg))
        
        if idx < len(accounts):
            time.sleep(random.uniform(3, 6))
    
    # 汇总
    logger.info("\n" + "=" * 60)
    logger.info("签到结果汇总")
    logger.info("-" * 60)
    
    success_count = sum(1 for _, s, _ in results if s)
    for user, success, msg in results:
        icon = "✅" if success else "❌"
        logger.info(f"{icon} {user}: {msg}")
    
    logger.info("-" * 60)
    logger.info(f"统计: 成功 {success_count}/{len(results)}")
    logger.info("=" * 60)
    
    # GitHub Actions 输出
    if os.environ.get("GITHUB_ACTIONS") == "true":
        summary = f"成功 {success_count}/{len(results)}"
        # 新方式写入环境文件
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"summary={summary}\n")
    
    sys.exit(0 if success_count == len(results) else 1)

if __name__ == "__main__":
    main()