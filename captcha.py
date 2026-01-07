"""
Author: wlaten
Date: 2024-12-31 08:25:34
LastEditTime: 2025-01-01 18:24:30
Discription: file content
"""

import base64
import requests
import time
from typing import Any

import io
from PIL import Image
import yaml

with open("config/captcha.yaml", "r", encoding="utf-8") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)

# 大模型 API 配置
llm_base_url: str = config["base_url"]
llm_api_key: str = config["api_key"]
llm_model: str = config["model"]


def verify(img_base64: str) -> str:
    """使用大模型 API 识别验证码（数学计算题）"""
    url = f"{llm_base_url.rstrip('/')}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {llm_api_key}",
    }

    prompt = (
        "Analyze the uploaded image and extract any visible mathematical expression "
        "involving only addition, subtraction, multiplication, or division. "
        "Solve the calculation and return the final integer result as a single Arabic numeral, "
        "without any additional text, symbols, or formatting."
    )

    data: dict[str, Any] = {
        "model": llm_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 16,
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    answer = result["choices"][0]["message"]["content"].strip()
    print(f"验证码识别结果: {answer}")
    return answer


def request_with_retry(
    method: str,
    url: str,
    session: requests.Session,
    max_retries: int = 3,
    **kwargs: Any,
) -> requests.Response:
    """带重试机制的请求方法"""
    for i in range(max_retries):
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if i == max_retries - 1:
                raise e
            time.sleep(1 * (i + 1))
    raise


if __name__ == "__main__":

    url = "https://xk.xmu.edu.cn/xsxkxmu/auth/captcha"
    try:
        # 创建一个会话对象
        session = requests.Session()

        response = request_with_retry("POST", url, session)
        data = response.json()

        if data["code"] == 200:
            captcha_base64 = data["data"]["captcha"].split(",")[1]

            # 测试用, 保存验证码图片
            image_data = base64.b64decode(captcha_base64)
            image = Image.open(io.BytesIO(image_data))
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"captcha_{timestamp}.png"
            image.save(f"cache/{filename}")
            print(f"验证码图片已保存为: {filename}")
            image.show()

            verify(captcha_base64)

    except Exception as e:
        print(f"请求验证码图片失败: {e}")
