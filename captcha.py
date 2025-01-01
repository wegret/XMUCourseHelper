'''
Author: wlaten
Date: 2024-12-31 08:25:34
LastEditTime: 2025-01-01 18:24:30
Discription: file content
'''
import base64
import requests
import time

import io
from PIL import Image
import yaml

with open('config/captcha.yaml', 'r', encoding='utf-8') as f:
    config = yaml.load(f, Loader=yaml.FullLoader)
captcha_token = config['captcha_token']

def verify(img_base64):
    url = "http://api.jfbym.com/api/YmServer/customApi"
    
    data = {
        "token": captcha_token,
        "type": 50100,
        "image": img_base64,
    }
    _headers = {
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, headers=_headers, json=data).json()
    print(response)
    return response['data']['data']
    
def request_with_retry(method, url, session, max_retries=3, **kwargs):
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

if __name__ == '__main__':
    
    url = 'https://xk.xmu.edu.cn/xsxkxmu/auth/captcha'
    try:
        # 创建一个会话对象
        session = requests.Session()
    
        response = request_with_retry('POST', url, session)
        data = response.json()
            
        if data['code'] == 200:
            captcha_base64 = data['data']['captcha'].split(',')[1]
            
            # 测试用, 保存验证码图片
            image_data = base64.b64decode(captcha_base64)
            image = Image.open(io.BytesIO(image_data))
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f'captcha_{timestamp}.png'
            image.save(f"cache/{filename}")
            print(f'验证码图片已保存为: {filename}')
            image.show()
            
            verify(captcha_base64)
            
                
    except Exception as e:
        print(f'请求验证码图片失败: {e}')