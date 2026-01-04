from __future__ import annotations

"""
Author: wlaten
Date: 2025-01-01 18:06:37
LastEditTime: 2025-01-04 13:34:30
Discription: file content
"""

import websocket
import threading
import requests
import logging
import yaml
from urllib.parse import urlencode
from utils.aes_util import AesUtil
import time
from captcha import verify as captcha_verify
import json
from typing import Any, Optional, Dict, Callable
from watch import load_watch_list


class XMULogin:
    def __init__(self, config_path: str = "config/user.yaml"):
        self.session = requests.Session()
        self.token: str = ""
        self.aesutil = AesUtil("MWMqg2tPcDkxcm11")  # 固定密钥
        self.batch_id: str = ""
        self.cookies: Dict[str, str] = {}
        self.watch_list = load_watch_list()

        try:
            self.session.get(
                "https://xk.xmu.edu.cn/xsxkxmu/profile/index.html", verify=False
            )
        except Exception as e:
            logging.warning(f"初始访问首页失败: {str(e)}")

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Origin": "https://xk.xmu.edu.cn",
                "Referer": "https://xk.xmu.edu.cn/xsxkxmu/profile/index.html",
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )
        self.load_config(config_path)

    def load_config(self, config_path: str):
        """加载配置文件"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.username = config["username"]
                self.password = config["password"]
                self.campus = config.get("campus", "6")
                self.captcha_auto = config.get("captcha_auto", False)

                logging.info("配置文件加载成功")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    def request_with_retry(
        self, method: str, url: str, max_retries: int = 3, **kwargs: Any
    ) -> requests.Response:
        """带重试机制的请求方法"""
        for i in range(max_retries):
            try:
                response = self.session.request(method, url, verify=False, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logging.error(f"请求失败 (尝试 {i+1}/{max_retries}): {str(e)}")
                if i == max_retries - 1:
                    raise e
                time.sleep(1 * (i + 1))
        raise

    def get_captcha(self) -> Optional[Dict[str, Any]]:
        """获取验证码"""
        url = "https://xk.xmu.edu.cn/xsxkxmu/auth/captcha"
        logging.info("正在请求验证码")

        try:
            response = self.request_with_retry("POST", url)
            data = response.json()

            if data["code"] == 200:
                # 获取base64编码的验证码图片
                captcha_base64 = data["data"]["captcha"].split(",")[1]
                uuid = data["data"]["uuid"]

                if self.captcha_auto:
                    return {"uuid": uuid, "image_base64": captcha_base64}

                # 将base64转换为图片
                from PIL import Image
                import base64
                import io

                image_data = base64.b64decode(captcha_base64)
                image = Image.open(io.BytesIO(image_data))

                # 保存验证码图片
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"cache/captcha_{timestamp}.png"
                image.save(filename)
                logging.info(f"验证码图片已保存为: {filename}")

                image.show()

                return {
                    "uuid": uuid,
                    "image": image,
                    "image_path": filename,
                    "image_base64": captcha_base64,
                }
            else:
                logging.error(f"请求失败: {data['msg']}")
                return None

        except Exception as e:
            logging.error(f"获取验证码出错: {str(e)}")
            return None

    def login(self):
        """登录系统"""
        # 获取验证码
        captcha_result = self.get_captcha()
        if not captcha_result:
            logging.error("获取验证码失败")
            return False

        if self.captcha_auto:
            print("正在自动识别验证码...")
            try:
                captcha_code = captcha_verify(captcha_result["image_base64"])
            except Exception as e:
                logging.error(f"验证码识别出错: {str(e)}")
                return False
            print(f"验证码识别结果: {captcha_code}")
        else:
            captcha_code = input("请输入验证码: ")

        # 加密密码
        encrypted_password = self.aesutil.encrypt(self.password)
        logging.info("密码已加密")

        # 准备登录数据
        login_url = "https://xk.xmu.edu.cn/xsxkxmu/auth/login"
        login_data: Dict[str, Any] = {
            "loginname": self.username,
            "password": encrypted_password,
            "captcha": captcha_code,
            "uuid": captcha_result["uuid"],
        }

        try:
            response = self.request_with_retry(
                "POST", login_url, data=urlencode(login_data)
            )
            result = response.json()

            if result["code"] == 200:
                self.token = result["data"]["token"]
                # 设置token到header中
                self.session.headers["Authorization"] = self.token
                self.cookies = self.session.cookies.get_dict()
                self.cookies["Authorization"] = self.token
                logging.info("登录成功")
                logging.info(f'用户信息: {result["data"]["student"]["XM"]}')

                # 提取 batchId
                elective_batch_list = result["data"]["student"].get(
                    "electiveBatchList", []
                )
                if elective_batch_list:
                    self.batch_id = elective_batch_list[0]["code"]
                    logging.info(f"获取到 batchId: {self.batch_id}")
                else:
                    logging.error("未获取到 electiveBatchList 中的 batchId")
                    self.batch_id = ""

                def callback(msg: dict[str, Any]) -> None:
                    logging.info(f"[WS消息] {msg}")
                    if msg.get("code") == 200:
                        clazz_id = msg.get("data", {}).get("clazzId", "")
                        for course in self.watch_list[:]:
                            if course["JXBID"] == clazz_id:
                                logging.info(
                                    f"选课成功: {course['KCM']} ({course['JXBID']})"
                                )
                                self.watch_list.remove(course)

                self.websocket_client = XMUWebSocketClient(
                    url=f"wss://xk.xmu.edu.cn/xsxkxmu/websocket/{self.username}",
                    cookie="; ".join([f"{k}={v}" for k, v in self.cookies.items()]),
                    heartbeat_interval=10,
                    on_message_callback=callback,
                )

                return True
            else:
                logging.error(f"登录失败: {result['msg']}")
                return False

        except Exception as e:
            logging.error(f"登录过程出错: {str(e)}")
            return False


class XMUWebSocketClient:
    def __init__(
        self,
        url: str,
        cookie: str,
        heartbeat_interval: int = 30,
        on_message_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> None:
        """
        :param url: WebSocket 目标地址
        :param cookie: 完整的 Cookie 字符串
        :param heartbeat_interval: 自定义心跳间隔（秒）
        :param on_message_callback: 业务消息回调
        """
        self.url: str = url
        self.cookie: str = cookie
        self.heartbeat_interval: int = heartbeat_interval
        self.on_message_callback: Optional[Callable[[Any], None]] = on_message_callback

        self.ws: Optional[websocket.WebSocketApp] = None
        self.is_running: bool = False
        self._heartbeat_thread: Optional[threading.Thread] = None

    def _get_headers(self) -> list[str]:
        return [
            "Origin: https://xk.xmu.edu.cn",
            f"Cookie: {self.cookie}",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        ]

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        print(f"[WS] 连接已建立")
        self.is_running = True
        # 开启自定义心跳线程
        self._heartbeat_thread = threading.Thread(
            target=self._send_custom_heartbeat, daemon=True
        )
        self._heartbeat_thread.start()

    def _on_message(self, ws: websocket.WebSocketApp, message: Any) -> None:
        try:
            # 解析 JSON 响应
            data = json.loads(message)
            # 识别并拦截心跳返回包
            if data.get("data") == "heart" and data.get("code") == 200:
                # print("[WS] 心跳同步成功: pong") # 调试用
                return
        except (json.JSONDecodeError, TypeError):
            # 如果不是 JSON，按原始数据处理
            data = message

        # 传递给业务回调
        if self.on_message_callback:
            self.on_message_callback(data)

    def _send_custom_heartbeat(self) -> None:
        """自定义心跳线程逻辑"""
        print(f"[WS] 自定义心跳线程启动 (间隔: {self.heartbeat_interval}s)")
        while self.is_running:
            if self.ws and self.ws.sock and self.ws.sock.connected:
                try:
                    # 发送自定义心跳字符串
                    self.ws.send("hi")
                    # print("[WS] 发送心跳: hi") # 调试用
                except Exception as e:
                    print(f"[WS] 心跳发送失败: {e}")
            time.sleep(self.heartbeat_interval)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        print(f"[WS] 错误: {error}")

    def _on_close(self, ws: websocket.WebSocketApp, status: int, msg: str) -> None:
        print(f"[WS] 连接关闭: {status} - {msg}")
        self.is_running = False

    def connect(self) -> None:
        """启动客户端"""
        self.ws = websocket.WebSocketApp(
            self.url,
            header=self._get_headers(),  # type:ignore
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        # 运行 WebSocket 的 IO 循环
        t = threading.Thread(target=self.ws.run_forever)  # type:ignore
        t.daemon = True
        t.start()
