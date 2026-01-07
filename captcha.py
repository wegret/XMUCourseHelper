'''
Author: wlaten
Date: 2025-12-27 01:44:41
LastEditTime: 2026-01-03 22:29:51
Discription: file content
'''

import base64
import time
from pathlib import Path
from PIL import Image
import io
import requests
from requests.exceptions import ReadTimeout
import re


def solve_captcha(image_base64: str, config: dict, input_func=None) -> str:
    """
    识别验证码
    
    Args:
        image_base64: base64编码的图片
        config: 配置字典
        input_func: 自定义输入函数（用于QQ bot等场景），默认用input
    
    Returns:
        (bool, str): 识别状态和结果
    """
    method = config.get("type", "manual")
    
    if method == "manual":
        return _solve_manual(image_base64, input_func or input)

    elif method == "api":
        token = config["token"]
        return _solve_api(image_base64, token)
    
    elif method == "llm":
        return _solve_llm(
            image_base64,
            config["base_url"],
            config["api_key"],
            config["model"]
        )

def _solve_manual(image_base64: str, input_func) -> str:
    """手动输入"""
    image_data = base64.b64decode(image_base64)
    image = Image.open(io.BytesIO(image_data))
    
    Path("cache").mkdir(exist_ok=True)
    filename = f"cache/captcha_{time.strftime('%Y%m%d_%H%M%S')}.png"
    image.save(filename)
    
    try:
        image.show()
    except:
        pass
    
    print(f"验证码已保存: {filename}")
    return True, input_func("请输入验证码: ")


def _solve_api(image_base64: str, token: str) -> str:
    """打码平台"""
    resp = requests.post(
        "http://api.jfbym.com/api/YmServer/customApi",
        json={"token": token, "type": 50100, "image": image_base64},
        headers={"Content-Type": "application/json"}
    ).json()
    
    if resp.get("code") != 10000:
        return False, f"打码平台请求失败: {resp.get('message', '未知错误')}"
    return True, resp["data"]["data"]


def _process_image(image_base64: str,
                   scale_factor: float = 3.0
                   ) -> str:
    """ 预处理图片 """
    try:
        image_data = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_data))
        
        new_width = int(image.width * scale_factor)
        new_height = int(image.height * scale_factor)
        
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        
        resized_image.save(buffered, format="PNG")
        new_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        return new_base64
        
    except Exception as e:
        print(f"图片预处理（放大）失败: {e}，将使用原图。")
        return image_base64

def _solve_llm(image_base64: str, base_url: str, api_key: str, model: str) -> str:
    """使用大模型识别验证码"""
    
    image_base64 = _process_image(image_base64)
    
    try:
        resp = requests.post(
            base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze the uploaded image and extract any visible mathematical expression involving only addition, subtraction, multiplication, or division. Solve the calculation and return the final integer result as a single Arabic numeral, without any additional text, symbols, or formatting."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                    ]
                }]
            },
            timeout=(5, 30)
        )
    except ReadTimeout:
        return False, "LLM 接口超时"
    except requests.RequestException as e:
        return False, f"LLM 请求错误: {e}"
    
    if not resp.ok:
        return False, f"LLM请求失败: {resp.status_code} {resp.text}"
    
    try:
        data = resp.json()
    except Exception as e:
        return False, f"LLM响应解析失败: {e}"

    content = data["choices"][0]["message"]["content"].strip()
    matches = re.findall(r"【([^【】]+)】", content)
    if not matches:
        return False, f"未能从LLM响应中提取验证码: {content}"
    
    return True, matches[-1]

if __name__ == "__main__":
    with open("cache/captcha_20251227_002336.png", "rb") as f:
        image_data = f.read()
    
    image_base64 = base64.b64encode(image_data).decode()
    
    with open("config/user.yaml", "r", encoding="utf-8") as f:
        import yaml
        config = yaml.safe_load(f)
    
    state, code = solve_captcha(image_base64, config['captcha'])
    print(f"识别结果: {code}")