#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (API版本)
基于 ChmlFrp API V2 直接调用，无需浏览器
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
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ChmlFrpAPI:
    """CHMLFRP API 封装"""
    
    BASE_URL = "https://cf-v2.uapis.cn"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.token: Optional[str] = None
        self.user_info: Dict = {}
    
    def login(self, username: str, password: str) -> bool:
        """
        用户登录
        :return: 是否登录成功
        """
        try:
            url = f"{self.BASE_URL}/login"
            data = {
                "username": username,
                "password": password
            }
            
            # 随机延时，模拟人工操作
            delay = random.uniform(1, 3)
            logger.info(f"[{username}] 登录前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            response = self.session.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("code") == 200:
                self.token = result.get("data", {}).get("token")
                self.user_info = result.get("data", {})
                if self.token:
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    logger.info(f"[{username}] 登录成功！用户ID: {self.user_info.get('userid')}")
                    return True
                else:
                    logger.error(f"[{username}] 登录成功但未获取到 token")
                    return False
            else:
                logger.error(f"[{username}] 登录失败: {result.get('msg', '未知错误')}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"[{username}] 登录请求异常: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[{username}] 登录过程出错: {str(e)}")
            return False
    
    def checkin(self) -> Tuple[bool, str]:
        """
        执行签到
        :return: (是否成功, 消息)
        """
        if not self.token:
            return False, "未登录或登录已过期"
        
        try:
            url = f"{self.BASE_URL}/user/checkin"
            
            # 随机延时 5-20 秒，避免被识别为自动化
            delay = random.uniform(5, 20)
            logger.info(f"签到前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            response = self.session.post(url, timeout=10)
            result = response.json()
            
            code = result.get("code")
            msg = result.get("msg", "")
            
            if code == 200:
                # 签到成功
                data = result.get("data", {})
                return True, f"签到成功！获得 {data.get('points', 0)} 积分，连续签到 {data.get('consecutive_days', 0)} 天"
            elif code == 400 and "已经签到" in msg:
                # 今日已签到
                return True, f"今日已签到: {msg}"
            else:
                return False, f"签到失败: {msg}"
                
        except requests.RequestException as e:
            return False, f"请求异常: {str(e)}"
        except Exception as e:
            return False, f"签到过程出错: {str(e)}"
    
    def get_user_info(self) -> Dict:
        """获取用户信息"""
        if not self.token:
            return {}
        
        try:
            url = f"{self.BASE_URL}/user/info"
            response = self.session.get(url, timeout=10)
            result = response.json()
            if result.get("code") == 200:
                return result.get("data", {})
            return {}
        except:
            return {}

def get_accounts_from_env() -> List[Tuple[str, str]]:
    """
    从环境变量获取账户信息
    支持多账户，使用换行符分隔
    """
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
    logger.info("CHMLFRP 自动签到工具启动")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # 获取账户信息
    accounts = get_accounts_from_env()
    
    if not accounts:
        # 尝试从硬编码配置读取（仅用于本地测试）
        logger.warning("未从环境变量读取到账户信息，尝试读取本地配置...")
        # 在此添加本地测试账户（生产环境请注释掉）
        # accounts = [("your_username", "your_password")]
        if not accounts:
            logger.error("未配置任何账户，请设置 CHMLFRP_USER 和 CHMLFRP_PASS 环境变量")
            sys.exit(1)
    
    results = []
    total = len(accounts)
    
    for idx, (username, password) in enumerate(accounts, 1):
        logger.info(f"\n[{idx}/{total}] 正在处理账户: {username}")
        logger.info("-" * 40)
        
        api = ChmlFrpAPI()
        
        # 登录
        if not api.login(username, password):
            results.append({
                "username": username,
                "success": False,
                "message": "登录失败"
            })
            continue
        
        # 获取用户信息（可选）
        user_info = api.get_user_info()
        if user_info:
            logger.info(f"当前积分: {user_info.get('points', 'N/A')}")
        
        # 执行签到
        success, message = api.checkin()
        results.append({
            "username": username,
            "success": success,
            "message": message
        })
        
        # 账户间随机延时，避免并发请求
        if idx < total:
            delay = random.uniform(3, 8)
            logger.info(f"等待 {delay:.1f} 秒后处理下一个账户...")
            time.sleep(delay)
    
    # 汇总结果
    logger.info("\n" + "=" * 50)
    logger.info("签到结果汇总")
    logger.info("=" * 50)
    
    success_count = sum(1 for r in results if r["success"])
    for r in results:
        status = "✅ 成功" if r["success"] else "❌ 失败"
        logger.info(f"{status} | {r['username']}: {r['message']}")
    
    logger.info("-" * 50)
    logger.info(f"总计: {total} 个账户，成功 {success_count} 个，失败 {total - success_count} 个")
    
    # 设置 GitHub Actions 输出（如果在 Actions 环境中）
    if os.environ.get("GITHUB_ACTIONS") == "true":
        summary = "\n".join([f"{'✅' if r['success'] else '❌'} {r['username']}: {r['message']}" for r in results])
        print(f"::set-output name=result::{summary}")
    
    return success_count == total

if __name__ == "__main__":
    try:
        success = run_checkin()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序异常: {str(e)}")
        sys.exit(1)