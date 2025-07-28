"""
Author: wlaten
Date: 2025-01-01 18:07:20
LastEditTime: 2025-01-01 18:09:14
Discription: file content
"""

import base64
from Crypto.Cipher import AES


class AesUtil:
    """AES加密工具类，用于加密密码"""

    def __init__(self, key: str):
        self.key = key.encode("utf-8")  # 密钥需要为16, 24或32字节
        self.block_size = 16

    def pkcs7_pad(self, data: str):
        """PKCS7 填充"""
        pad_length = self.block_size - (len(data) % self.block_size)
        padding = chr(pad_length) * pad_length
        return data + padding

    def encrypt(self, data: str):
        """AES ECB 加密并进行Base64编码"""
        padded_data = self.pkcs7_pad(data)
        cipher = AES.new(self.key, AES.MODE_ECB)  # type:ignore
        encrypted = cipher.encrypt(padded_data.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")
