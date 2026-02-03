#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CHMLFRP 自动签到工具 (修复版)
修复了 token 提取逻辑，添加了调试模式
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
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ChmlFrpAPI:
    """CHMLFRP API V2 封装"""
    
    BASE_URL = "https://cf-v2.uapis.cn"
    
    def __init__(self):
        self.session = requests.Session()
        # 模拟真实浏览器请求头
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://panel.chmlfrp.net",
            "Referer": "https://panel.chmlfrp.net/",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site"
        })
        self.token: Optional[str] = None
        self.user_info: Dict = {}
        self.debug = os.environ.get("DEBUG", "false").lower() == "true"
    
    def log_debug(self, message: str, data=None):
        """打印调试信息"""
        if self.debug:
            logger.info(f"[DEBUG] {message}")
            if data:
                logger.info(f"[DEBUG DATA] {json.dumps(data, ensure_ascii=False, indent=2)[:500]}...")
    
    def login(self, username: str, password: str) -> bool:
        """
        用户登录 - 修复版，适配实际 API 返回结构
        """
        try:
            url = f"{self.BASE_URL}/login"
            data = {
                "username": username,
                "password": password
            }
            
            # 随机延时
            delay = random.uniform(2, 5)
            logger.info(f"[{username}] 登录前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            logger.info(f"[{username}] 正在发送登录请求...")
            response = self.session.post(url, json=data, timeout=15)
            
            # 打印原始响应用于调试
            self.log_debug(f"登录响应状态码: {response.status_code}")
            self.log_debug(f"登录响应头: {dict(response.headers)}")
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                logger.error(f"[{username}] 响应不是有效 JSON: {response.text[:200]}")
                return False
            
            self.log_debug("登录响应内容", result)
            
            # 检查 HTTP 状态码
            if response.status_code != 200:
                logger.error(f"[{username}] 登录失败，HTTP状态码: {response.status_code}")
                logger.error(f"响应: {result}")
                return False
            
            # 检查业务状态码 - API V2 可能返回 200 但 code 字段不同
            code = result.get("code", -1)
            if code != 200:
                msg = result.get("msg", "未知错误")
                logger.error(f"[{username}] 登录失败，业务码: {code}, 消息: {msg}")
                return False
            
            # 提取 token - 适配多种可能的字段名
            data_obj = result.get("data", {})
            if isinstance(data_obj, dict):
                # 可能的 token 字段名
                self.token = (data_obj.get("token") or 
                             data_obj.get("access_token") or 
                             data_obj.get("Token") or
                             data_obj.get("Authorization"))
                
                if self.token:
                    self.user_info = data_obj
                    # 更新请求头
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    logger.info(f"[{username}] 登录成功！获取到 token: {self.token[:20]}...")
                    return True
                else:
                    logger.error(f"[{username}] 登录成功但未找到 token 字段")
                    logger.error(f"可用字段: {list(data_obj.keys())}")
                    return False
            else:
                # 有些 API 可能直接返回 token 字符串
                if isinstance(data_obj, str) and len(data_obj) > 10:
                    self.token = data_obj
                    self.session.headers["Authorization"] = f"Bearer {self.token}"
                    logger.info(f"[{username}] 登录成功！(token 在 data 字符串中)")
                    return True
                logger.error(f"[{username}] 登录响应 data 字段格式异常: {type(data_obj)}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"[{username}] 登录请求异常: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"[{username}] 登录过程出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def checkin(self, username: str) -> Tuple[bool, str]:
        """
        执行签到 - 修复版
        """
        if not self.token:
            return False, "未登录或登录已过期"
        
        try:
            url = f"{self.BASE_URL}/user/checkin"
            
            # 随机延时 5-20 秒
            delay = random.uniform(5, 20)
            logger.info(f"[{username}] 签到前延时 {delay:.1f} 秒...")
            time.sleep(delay)
            
            logger.info(f"[{username}] 正在发送签到请求...")
            
            # 注意：有些签到接口可能需要特定的请求体或查询参数
            # 根据 CHMLFRP 文档，签到可能是 GET 或 POST
            response = self.session.post(url, timeout=15)
            
            self.log_debug(f"签到响应状态码: {response.status_code}")
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                return False, f"签到响应不是有效 JSON: {response.text[:200]}"
            
            self.log_debug("签到响应内容", result)
            
            # 处理响应
            code = result.get("code", -1)
            msg = result.get("msg", "")
            
            if code == 200:
                data = result.get("data", {})
                if isinstance(data, dict):
                    points = data.get("points", 0)
                    days = data.get("consecutive_days", 0)
                    return True, f"签到成功！获得 {points} 积分，连续签到 {days} 天"
                return True, "签到成功！"
            elif code == 400:
                # 可能已经签到
                if "已经签到" in msg or "已签到" in msg:
                    return True, f"今日已签到: {msg}"
                return False, f"签到失败: {msg}"
            elif code == 401 or code == 403:
                return False, f"认证失败，token 可能过期: {msg}"
            else:
                return False, f"签到失败(代码{code}): {msg}"
                
        except requests.RequestException as e:
            return False, f"请求异常: {str(e)}"
        except Exception as e:
            return False, f"签到过程出错: {str(e)}"
    
    def get_user_info(self) -> Dict:
        """获取用户信息 - 用于验证 token 是否有效"""
        if not self.token:
            return {}
        
        try:
            url = f"{self.BASE_URL}/user/info"
            response = self.session.get(url, timeout=10)
            result = response.json()
            
            self.log_debug("用户信息响应", result)
            
            if result.get("code") == 200:
                return result.get("data", {})
            return {}
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return {}

def get_accounts_from_env() -> List[Tuple[str, str]]:
    """从环境变量获取账户信息"""
    users_str = os.environ.get("CHMLFRP_USER", "")
    passes_str = os.environ.get("CHMLFRP_PASS", "")
    
    if not users_str or not passes_str:
        return []
    
    # 支持多种分隔符：换行、逗号
    if "\\n" in users_str:
        users = [u.strip() for u in users_str.split("\\n") if u.strip()]
        passes = [p.strip() for p in passes_str.split("\\n") if p.strip()]
    elif "," in users_str:
        users = [u.strip() for u in users_str.split(",") if u.strip()]
        passes = [p.strip() for p in passes_str.split(",") if p.strip()]
    else:
        users = [users_str.strip()]
        passes = [passes_str.strip()]
    
    if len(users) != len(passes):
        logger.error(f"用户名和密码数量不匹配！用户: {len(users)}, 密码: {len(passes)}")
        return []
    
    return list(zip(users, passes))

def run_checkin():
    """主运行函数"""
    logger.info("=" * 60)
    logger.info("CHMLFRP 自动签到工具 (修复版) 启动")
    logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"API 地址: https://cf-v2.uapis.cn")
    logger.info("=" * 60)
    
    # 检查调试模式
    if os.environ.get("DEBUG", "false").lower() == "true":
        logger.info("调试模式已启用")
    
    # 获取账户信息
    accounts = get_accounts_from_env()
    
    if not accounts:
        # 尝试从硬编码配置读取（仅用于本地测试）
        logger.warning("未从环境变量读取到账户信息")
        logger.info("请设置环境变量: CHMLFRP_USER 和 CHMLFRP_PASS")
        logger.info("支持多账户，使用换行符或逗号分隔")
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
        
        # 可选：获取用户信息验证 token
        user_info = api.get_user_info()
        if user_info:
            logger.info(f"当前用户: {user_info.get('username', 'N/A')}, 积分: {user_info.get('points', 'N/A')}")
        
        # 执行签到
        success, message = api.checkin(username)
        results.append({
            "username": username,
            "success": success,
            "message": message
        })
        
        # 账户间随机延时
        if idx < total:
            delay = random.uniform(3, 8)
            logger.info(f"等待 {delay:.1f} 秒后处理下一个账户...")
            time.sleep(delay)
    
    # 汇总结果
    logger.info("\n" + "=" * 60)
    logger.info("签到结果汇总")
    logger.info("=" * 60)
    
    success_count = sum(1 for r in results if r["success"])
    for r in results:
        status = "✅ 成功" if r["success"] else "❌ 失败"
        logger.info(f"{status} | {r['username']}: {r['message']}")
    
    logger.info("-" * 60)
    logger.info(f"总计: {total} 个账户，成功 {success_count} 个，失败 {total - success_count} 个")
    logger.info("=" * 60)
    
    # 设置 GitHub Actions 输出（新方式）
    if os.environ.get("GITHUB_ACTIONS") == "true":
        summary = f"成功 {success_count}/{total}"
        details = "\n".join([f"{'✅' if r['success'] else '❌'} {r['username']}: {r['message']}" for r in results])
        
        # 使用环境文件（新方式）
        github_output = os.environ.get("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"summary={summary}\n")
                f.write(f"details<<EOF\n{details}\nEOF\n")
        else:
            # 旧方式（兼容）
            print(f"::set-output name=summary::{summary}")
    
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
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)