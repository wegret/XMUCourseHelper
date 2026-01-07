"""
Author: wlaten
Date: 2025-01-01 18:06:37
LastEditTime: 2025-01-04 13:34:30
Discription: file content
"""

import requests
import logging
import yaml
import os
from urllib.parse import urlencode
from utils.aes_util import AesUtil
import time
from captcha import verify as captcha_verify
from typing import Any, Optional, Dict


class XMULogin:
    def __init__(self, config_path: str = "config/user.yaml"):
        self.session = requests.Session()
        self.token: str = ""
        self.aesutil = AesUtil("MWMqg2tPcDkxcm11")  # 固定密钥
        self.batch_id: str = ""
        self.cookies: Dict[str, str] = {}

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

    def save_captcha_image(self, image_base64: str) -> Optional[str]:
        """保存验证码图片到本地（仅手动验证时使用）"""
        try:
            from PIL import Image
            import base64
            import io

            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"cache/captcha_{timestamp}.png"
            image.save(filename)
            logging.info(f"验证码图片已保存为: {filename}")

            image.show()
            return filename
        except Exception as e:
            logging.error(f"保存验证码图片出错: {str(e)}")
            return None

    def delete_captcha_image(self, image_path: Optional[str]) -> None:
        """删除验证码图片"""
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                logging.info(f"验证码图片已删除: {image_path}")
            except Exception as e:
                logging.warning(f"删除验证码图片失败: {str(e)}")

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
                    # 自动验证模式，不保存图片
                    return {"uuid": uuid, "image_base64": captcha_base64}

                # 手动验证模式，保存图片并显示
                image_path = self.save_captcha_image(captcha_base64)

                return {
                    "uuid": uuid,
                    "image_path": image_path,
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
        else:
            captcha_code = input("请输入验证码: ")
            # 用户输入完成后删除验证码图片
            self.delete_captcha_image(captcha_result.get("image_path"))

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

                return True
            else:
                logging.error(f"登录失败: {result['msg']}")
                return False

        except Exception as e:
            logging.error(f"登录过程出错: {str(e)}")
            return False
