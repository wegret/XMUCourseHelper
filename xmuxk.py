'''
Author: wlaten
Date: 2024-12-31 07:23:59
LastEditTime: 2024-12-31 09:43:41
Discription: file content
'''
import json
import questionary
import argparse
from typing import List, Dict
import os
from pathlib import Path
from rich.console import Console
from rich.theme import Theme
import requests
import base64
from PIL import Image
import io
import time
import logging
import yaml
from urllib.parse import urlencode
from Crypto.Cipher import AES
import urllib3

# Windows和Unix系统的清屏命令
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

custom_theme = Theme({
    "page_info": "yellow",
})
console = Console(theme=custom_theme)

CONFIG_FILE = Path("config/last_selection.json")

def load_last_selection() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_last_selection(selection: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)

def chunk_choices(items: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def select_KKDW():
    with open("info/KKDW.json", "r", encoding="utf-8") as f:
        KKDW = json.load(f)
    
    last_selection = load_last_selection()
    last_selected_name = last_selection.get("last_kkdw_name")
    
    start_page = 0
    if last_selected_name:
        for idx, item in enumerate(KKDW):
            if item.get("name") == last_selected_name:
                start_page = idx // 10
                break
    
    pages = chunk_choices(KKDW)
    current_page = start_page
    total_pages = len(pages)
    
    while True:
        clear_screen()
        
        start_index = current_page * 10
        
        choices = []
        for idx, item in enumerate(pages[current_page]):
            title = f"{start_index + idx + 1}. {item.get('name', '无名')}"
            if item.get("name") == last_selected_name:
                title += " [上次选择]"
            choices.append(questionary.Choice(title=title, value=item))
        
        if total_pages > 1:
            choices.append(questionary.Choice(title="↓ 下一页", value="NEXT"))
            choices.append(questionary.Choice(title="↑ 上一页", value="PREV"))
        
        console.print(f"\n[page_info]第 {current_page + 1}/{total_pages} 页[/page_info]")
        
        style = questionary.Style([
            ('question', ''),  
            ('selected', 'reverse bold'), 
            ('pointer', ''), 
            ('instruction', ''),
            ('highlighted', 'noreverse bold'),
            ('answer', 'cyan bold'),
        ])
        
        result = questionary.select(
            "",
            choices=choices,
            style=style,
            use_indicator=True,
            instruction=None,
        ).ask()
        
        if result == "NEXT":
            current_page = (current_page + 1) % total_pages
        elif result == "PREV":
            current_page = (current_page - 1) % total_pages
        else:
            save_last_selection({
                "last_kkdw_name": result.get("name"),
                "last_kkdw_id": result.get("id")
            })
            return result

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xmu_login.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AesUtil:
    '''AES加密工具类，用于加密密码'''
    def __init__(self, key):
        self.key = key.encode('utf-8')  # 密钥需要为16, 24或32字节
        self.block_size = 16

    def pkcs7_pad(self, data):
        """PKCS7 填充"""
        pad_length = self.block_size - (len(data) % self.block_size)
        padding = chr(pad_length) * pad_length
        return data + padding

    def encrypt(self, data):
        """AES ECB 加密并进行Base64编码"""
        padded_data = self.pkcs7_pad(data)
        cipher = AES.new(self.key, AES.MODE_ECB)
        encrypted = cipher.encrypt(padded_data.encode('utf-8'))
        return base64.b64encode(encrypted).decode('utf-8')

class XMULogin:
    def __init__(self, config_path='config/user.yaml'):
        self.session = requests.Session()
        self.token = None
        self.aesutil = AesUtil('MWMqg2tPcDkxcm11')  # 固定密钥
        self.batch_id = None

        try:
            self.session.get('https://xk.xmu.edu.cn/xsxkxmu/profile/index.html', verify=False)
        except Exception as e:
            logging.warning(f"初始访问首页失败: {str(e)}")

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Origin': 'https://xk.xmu.edu.cn',
            'Referer': 'https://xk.xmu.edu.cn/xsxkxmu/profile/index.html',
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        self.load_config(config_path)

    def load_config(self, config_path):
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.username = config['username']
                self.password = config['password']
                self.captcha_auto = config['captcha_auto'] 
                
                logging.info('配置文件加载成功')
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    def request_with_retry(self, method, url, max_retries=3, **kwargs):
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

    def get_captcha(self):
        """获取验证码"""
        url = 'https://xk.xmu.edu.cn/xsxkxmu/auth/captcha'
        logging.info('正在请求验证码')
        
        try:
            response = self.request_with_retry('POST', url)
            data = response.json()
            
            if data['code'] == 200:
                # 获取base64编码的验证码图片
                captcha_base64 = data['data']['captcha'].split(',')[1]
                uuid = data['data']['uuid']
                
                if self.captcha_auto:
                    return {
                        'uuid': uuid,
                        'image_base64': captcha_base64
                    }
                
                # 将base64转换为图片
                image_data = base64.b64decode(captcha_base64)
                image = Image.open(io.BytesIO(image_data))
                
                # 保存验证码图片
                timestamp = time.strftime('%Y%m%d_%H%M%S')
                filename = f'cache/captcha_{timestamp}.png'
                image.save(filename)
                logging.info(f'验证码图片已保存为: {filename}')
                
                image.show()
                
                return {
                    'uuid': uuid,
                    'image': image,
                    'image_path': filename,
                    'image_base64': captcha_base64
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
            raise Exception("获取验证码失败")

        if self.captcha_auto:
            from captcha import verify as captcha_verify
            print('正在自动识别验证码...')
            captcha_code = captcha_verify(captcha_result['image_base64'])
            print(f'验证码识别结果: {captcha_code}')
        else:
            captcha_code = input('请输入验证码: ')

        # 加密密码
        encrypted_password = self.aesutil.encrypt(self.password)
        logging.info('密码已加密')

        # 准备登录数据
        login_url = 'https://xk.xmu.edu.cn/xsxkxmu/auth/login'
        login_data = {
            'loginname': self.username,
            'password': encrypted_password,
            'captcha': captcha_code,
            'uuid': captcha_result['uuid']
        }

        try:
            response = self.request_with_retry('POST', login_url, data=urlencode(login_data))
            result = response.json()

            if result['code'] == 200:
                self.token = result['data']['token']
                # 设置token到header中
                self.session.headers['Authorization'] = self.token
                logging.info('登录成功')
                logging.info(f'用户信息: {result["data"]["student"]["XM"]}')
                
                # 提取 batchId
                elective_batch_list = result['data']['student'].get('electiveBatchList', [])
                if elective_batch_list:
                    self.batch_id = elective_batch_list[0]['code']
                    logging.info(f'获取到 batchId: {self.batch_id}')
                else:
                    logging.error("未获取到 electiveBatchList 中的 batchId")
                    self.batch_id = None

                return True
            else:
                logging.error(f"登录失败: {result['msg']}")
                return False

        except Exception as e:
            logging.error(f"登录过程出错: {str(e)}")
            return False

class XMUCourseController:
    def __init__(self, session, token, batch_id):
        self.session = session
        self.token = token
        self.batch_id = batch_id
        self.session.headers.update({
            'Authorization': self.token,
            'Content-Type': 'application/json;charset=UTF-8',  # 修改为 JSON 类型
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://xk.xmu.edu.cn',
            'Referer': f'https://xk.xmu.edu.cn/xsxkxmu/elective/grablessons?batchId={self.batch_id}'
        })

    def search_courses(self, params):
        """
        搜索课程

        Args:
            params (dict): 搜索参数，包括 KKDW 和 KEY 等。

        Returns:
            dict: 搜索结果
        """
        url = 'https://xk.xmu.edu.cn/xsxkxmu/elective/xmu/clazz/list'
        
        try:
            response = self.session.post(url, json=params, verify=False)
            response.raise_for_status()
            result = response.json()
            if result['code'] == 200:
                logging.info("课程搜索成功")
                return result['data']['rows']
            else:
                logging.error(f"课程搜索失败: {result['msg']}")
                return None
        except Exception as e:
            logging.error(f"搜索课程出错: {str(e)}")
            return None

    def add_course(self, clazz_type, clazz_id, secret_val, need_book='', choose_volunteer='1'):
        """
        选课

        Args:
            clazz_type (str): 课程类型
            clazz_id (str): 课程ID
            secret_val (str): 加密值
            need_book (str): 是否需要教材，默认空字符串
            choose_volunteer (str): 志愿值，默认'1'
            
        Returns:
            dict: 选课结果
        """
        url = 'https://xk.xmu.edu.cn/xsxkxmu/elective/clazz/add'
        
        # 构造选课数据
        data = {
            'clazzType': clazz_type,
            'clazzId': clazz_id,
            'secretVal': secret_val,
            'needBook': need_book,
            'chooseVolunteer': choose_volunteer
        }
        
        # 更新请求头
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'batchId': self.batch_id
        }
        self.session.headers.update(headers)
        
        try:
            # 添加verify=False来禁用SSL验证
            response = self.session.post(url, data=data, verify=False)
            response.raise_for_status()
            
            result = response.json()
            if result['code'] == 200:
                logging.info(f"选课成功: {clazz_id}")
            else:
                logging.warning(f"选课失败: {result['msg']}")
            return result
        except Exception as e:
            logging.error(f"选课过程出错: {str(e)}")
            return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", help="输入课程名关键词")
    args = parser.parse_args()
    
    if args.search:
        req = {
            "teachingClassType": "ALLKC",
            "pageNumber": 1,
            "pageSize": 10,
            "orderBy": "",
            "KEY": args.search
        }
        
        clear_screen()
        console.print(f"课程名关键词为: [cyan]{args.search}[/cyan]")
        
        style = questionary.Style([
            ('selected', 'reverse bold'),
            ('answer', 'cyan bold'),
        ])
        
        if questionary.confirm("是否需要选择开课单位?", style=style).ask():
            selected_kkdw = select_KKDW()
            if selected_kkdw:
                req["KKDW"] = selected_kkdw.get("code", "")
        
        clear_screen()
        console.print("\n最终请求参数:")
        console.print(json.dumps(req, ensure_ascii=False, indent=2))
        
        try:
            print("正在登录...")
            xmu = XMULogin()
            
            # 登录
            if xmu.login():
                print("登录成功！")
                
                if xmu.batch_id:
                    print(f"Batch ID: {xmu.batch_id}")
                    
                    # 初始化课程控制器
                    course_controller = XMUCourseController(xmu.session, xmu.token, xmu.batch_id)
                    
                    # 开始搜索课程
                    page_number = 1
                    while True:
                        req["pageNumber"] = page_number
                        response_data = course_controller.search_courses(req)
                        
                        if not response_data:
                            console.print("[red]未能获取到搜索结果。[/red]")
                            break
                        
                        # 构造选择项
                        choices = []
                        for idx, course in enumerate(response_data, start=1):
                            course_name = course.get('courseName_zh', '无名课程')
                            teacher = course.get('SKJS', '未知教师')
                            campus = course.get('campus', '未知校区')
                            teaching_place = course.get('teachingPlace', '未知地点')
                            limit_kind = ', '.join([lk.get('limitDesc_zh', '') for lk in course.get('limitKindList', [])])
                            
                            title = f"{idx}. {course_name} | 教师: {teacher} | 校区: {campus} | 地点: {teaching_place}"
                            if limit_kind:
                                title += f" | 限制: {limit_kind}"
                            
                            choices.append(questionary.Choice(title=title, value=course))
                        
                        # 添加退出选项
                        choices.append(questionary.Choice(title="退出", value="EXIT"))
                        
                        # 让用户选择课程
                        selected_course = questionary.select(
                            "请选择一个课程进行选课:",
                            choices=choices,
                            style=style
                        ).ask()
                        
                        if selected_course == "EXIT":
                            console.print("退出程序。")
                        else:
                            # 显示选中的课程信息
                            console.print(f"\n您选择的课程: [cyan]{selected_course.get('courseName_zh', '无名课程')}[/cyan]")
                            console.print(f"教师: {selected_course.get('SKJS', '未知教师')}")
                            console.print(f"校区: {selected_course.get('campus', '未知校区')}")
                            console.print(f"地点: {selected_course.get('teachingPlace', '未知地点')}")
                            
                            if questionary.confirm("是否要选取此课程?", style=style).ask():
                                clazz_type = selected_course.get('courseType', '')
                                clazz_id = selected_course.get('courseGroupCode', '')
                                secret_val = selected_course.get('secretVal', '')
                                
                                add_result = course_controller.add_course(
                                    clazz_type=clazz_type,
                                    clazz_id=clazz_id,
                                    secret_val=secret_val
                                )
                                
                                if add_result and add_result.get('code') == 200:
                                    console.print(f"[green]选课成功: {selected_course.get('courseName_zh', '无名课程')}[/green]")
                                else:
                                    error_msg = add_result.get('msg', '未知错误') if add_result else '未知错误'
                                    console.print(f"[red]选课失败: {error_msg}[/red]")
                            else:
                                console.print("未进行选课操作。")
                        
                        
                else:
                    print("未获取到 Batch ID，请检查登录响应。")
            else:
                print("登录失败！")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            logging.error(f"程序运行出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
