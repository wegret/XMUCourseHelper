'''
Author: wlaten
Date: 2025-01-01 18:06:46
LastEditTime: 2025-01-03 22:10:15
Discription: file content
'''

import requests
import logging
from typing import Dict
import time
import urllib.parse

class XMUCourseController:
    def __init__(self, session, token, batch_id):
        self.session = session
        self.token = token
        self.batch_id = batch_id
        self.session.headers.update({
            'Authorization': self.token,
            'Content-Type': 'application/json;charset=UTF-8', 
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://xk.xmu.edu.cn',
            'Referer': f'https://xk.xmu.edu.cn/xsxkxmu/elective/grablessons?batchId={self.batch_id}',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            # TODO  cookie(route 和 Authorization)
        })

    def search_courses(self, params: Dict) -> Dict:
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

    def add_course(self, clazz_type: str, clazz_id: str, secret_val: str, need_book: str = '', choose_volunteer: str = '1'):
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
        
        # 对 secret_val 进行 URL 编码
        encoded_secret_val = urllib.parse.quote_plus(secret_val)
        
        data = {
            'clazzType': clazz_type,
            'clazzId': clazz_id,
            'secretVal': encoded_secret_val,
            # 'needBook': need_book,    # ! 这个在第三轮自由选课里不需要吧
            # 'chooseVolunteer': choose_volunteer
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'batchId': self.batch_id,
            # TODO 这里有cookie，不知道有没有影响
        }
        self.session.headers.update(headers)
        
        try:
            logging.debug(f"发送选课请求数据: {data}")
            response = self.session.post(url, data=data, verify=False)
            logging.debug(f"收到响应: {response.text}")
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