'''
Author: wlaten
Date: 2025-12-27 00:52:30
LastEditTime: 2026-01-01 01:06:35
Discription: file content
'''
import requests
from utils.aes_util import AesUtil
import logging
import warnings
import urllib3
import time
from typing import Optional, Dict, Any, Tuple

from captcha import solve_captcha

warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)


class XMUClient:
    
    BASE_URL = "https://xk.xmu.edu.cn/xsxkxmu"
    
    def __init__(self,
                 username: str,
                 password: str,
                 campus: str,
                 config_captcha: dict):
        self.username = username
        self.password = password
        self.campus = campus
        self.aes = AesUtil("MWMqg2tPcDkxcm11")
        self.config_captcha = config_captcha
        
        self.session = self._create_session()
        self.token = None
        self.batch_id = None
        self.cookies = {}
        
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",    # todo 随机UA
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Origin": self.BASE_URL.rsplit("/", 1)[0],
            "Referer": f"{self.BASE_URL}/profile/index.html",
        })
        
        try:
            session.get(f"{self.BASE_URL}/profile/index.html", verify=False, timeout=10)
        except Exception as e:
            logging.warning(f"初始访问首页失败: {e}")
            
        return session
    
    def _request(self,
                 method: str,
                 endpoint: str, # 相对路径，如 "/auth/login"
                 max_retries: int = 3,
                 **kwargs) -> requests.Response:
        
        url = f"{self.BASE_URL}{endpoint}"
        
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("verify", False)
        
        last_exception = None
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_exception = e
                logging.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 递增等待
        raise last_exception

    def _get_captcha(self) -> Tuple[str, str]:
        resp = self._request("POST", "/auth/captcha")
        data = resp.json()
        if data.get("code") != 200:
            raise Exception(f"获取验证码失败: {data.get('message', '未知错误')}")
        
        uuid = data["data"]["uuid"]
        image_base64 = data["data"]["captcha"].split(",")[1]
        
        return uuid, image_base64
    
    def login(self) -> bool:
        uuid, image_base64 = self._get_captcha()
        
        success, captcha_code = solve_captcha(image_base64, self.config_captcha)
        if not success:
            raise Exception(f"验证码识别失败: {captcha_code}")
        logging.info(f"验证码识别结果: {captcha_code}")
        
        encrypted_password = self.aes.encrypt(self.password)
        
        payload = {
            "loginname": self.username,
            "password": encrypted_password,
            "captcha": str(captcha_code),
            "uuid": uuid
        }
        
        resp = self._request("POST", "/auth/login", data=payload)
        data = resp.json()
        # print(f"登录响应: {data}")
        
        if data.get("code") != 200:
            raise Exception(f"登录失败: {data.get('message', '未知错误')}")
        
        self.token = data["data"]["token"]
        self.session.headers["Authorization"] = self.token
        
        student = data["data"].get("student", {})
        batch_list = student.get("electiveBatchList", [])
        self.batch_id = batch_list[0]["code"] if batch_list else None
        
        logging.info(f"登录成功！用户: {student.get('XM', '未知')}, BatchID: {self.batch_id}")
        return True 

    @property
    def is_logged_in(self) -> bool:
        return self.token is not None and self.batch_id is not None
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    with open("config/user.yaml", "r", encoding="utf-8") as f:
        import yaml
        config = yaml.safe_load(f)
    
    client = XMUClient(
        username=config["username"],
        password=config["password"],
        campus=config.get("campus", "6"),
        config_captcha=config["captcha"]
    )
    
    try:
        resp = client._request("GET", f"/profile/index.html")
        print(f"请求成功，状态码: {resp.status_code}")
    except Exception as e:
        print(f"请求失败: {e}")
    
    if client.login():
        print("【登录成功】")
        print(f"   Token: {client.token[:20]}...")
        print(f"   BatchID: {client.batch_id}")
    else:
        print("【登录失败】")