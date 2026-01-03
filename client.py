'''
Author: wlaten
Date: 2025-12-27 00:52:30
LastEditTime: 2026-01-04 00:31:42
Discription: file content
'''
import requests
from utils.aes_util import AesUtil
import logging
import warnings
import urllib3
import time, os, json
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
        
        self.watch_list = {}  # KCH -> {JXBID: { last_selected: int, capacity: int, subscribers: list }}
        
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
            print(data)
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
        if self.batch_id is None:
            return False
        payload = {
            "batchId": self.batch_id
        }
        resp = self._request("POST", "/elective/user", allow_redirects=False, data=payload)
        try:
            data = resp.json()
        except Exception:
            # logging.debug(f"is_logged_in parse json fail, status={resp.status_code}, text={resp.text}")
            return False
        # logging.debug(
        #     f"is_logged_in status={resp.status_code}, url={resp.url}, "
        #     f"history={[r.status_code for r in resp.history]}, data={data}, "
        #     f"token_set={self.token is not None}, batch_set={self.batch_id is not None}"
        # )
        return data.get("code") == 200 and self.token is not None and self.batch_id is not None
        # return self.token is not None and self.batch_id is not None
    
    def search_courses(self, 
                   teaching_class_type: str,
                   keyword: Optional[str] = None,
                   **extra_params) -> Optional[list]:
        """
        搜索课程（会返回所有课程）
        
        Args:
            teaching_class_type: 课程类型（如 "ALLKC", "BXKC" 等， 见 info/clazzType.json ）
            keyword: 搜索关键词
            **extra_params: 其他参数（如 KKDW 等）
        
        Returns:
            Optional[list]: 课程列表或None
        """
        
        payload = {
            "teachingClassType": teaching_class_type,
            "pageNumber": 1,    
            "pageSize": 10,
            "orderBy": "",
            "campus": self.campus
        }
        if keyword:
            payload["KEY"] = keyword
        
        payload.update(extra_params)
        
        courses = []
        
        error_cnt = 0
        while True:
            try:
                resp = self._request("POST", "/elective/xmu/clazz/list", json=payload)
                data = resp.json()
                
                if data.get("code") != 200:
                    logging.error(f"搜索课程失败: {data.get('message', '未知错误')}")
                    return None
                
                courses.extend(data["data"].get("rows", []))
                
                if len(courses) >= data["data"].get("total", 0):
                    return courses
                
                payload["pageNumber"] += 1
                error_cnt = 0
                
            except Exception as e:
                logging.error(f"搜索课程异常: {e}")
                error_cnt += 1            
                if error_cnt >= 3:
                    return None
            time.sleep(0.2)
    
    def query_class_number(self, KCH, JXBID) -> Tuple[int, int]:
        """
        查询课程剩余名额
        Args:
            KCH: 课程号
            JXBID: 教学班ID
        Returns:
            (int, int): (已选人数, 总名额)
        """
        classes = self.search_courses("ALLKC", keyword=str(KCH))
        for clazz in classes:
            if str(clazz.get("JXBID")) == str(JXBID):
                return (int(clazz.get("numberOfSelected")), int(clazz.get("classCapacity")))
        raise Exception(f"未找到课程 {KCH} 的教学班 {JXBID}")
    
    def add_watch(self, KCH, JXBID, info, subscriber=(-1, -1)):
        """
        把课程加入监控列表
        Args:
            KCH: 课程号
            JXBID: 教学班ID
            subscriber: 订阅者标识，后续引入qq bot用，(qq号, 群号)，如果是私聊则群号为-1
        Returns:
            str: 结果信息
        """
        number_of_selected, capacity = self.query_class_number(KCH, JXBID)
        if KCH not in self.watch_list:
            self.watch_list[KCH] = {}
        if JXBID not in self.watch_list[KCH]:
            self.watch_list[KCH][JXBID] = {
                "last_selected": number_of_selected,
                "capacity": capacity,
                "info": info,
                "subscribers": []
            }
        if subscriber not in self.watch_list[KCH][JXBID]["subscribers"]:
            self.watch_list[KCH][JXBID]["subscribers"].append(subscriber)
        else:
            return "您已订阅该课程的监控"
        return "已成功将课程加入监控列表"
    
    def save(self, filepath = "cache/XMUClient.json"):
        """
        保存客户端状态到文件
        Args:
            filepath: 文件路径
        """
        import json
        data = {
            "token": self.token,
            "batch_id": self.batch_id,
            "cookies": self.session.cookies.get_dict(),
            "watch_list": self.watch_list
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, filepath = "cache/XMUClient.json"):
        """
        从文件加载客户端状态
        Args:
            filepath: 文件路径
        """
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.token = data.get("token")
        self.batch_id = data.get("batch_id")
        cookies = data.get("cookies", {})
        self.session.cookies.update(cookies)
        self.watch_list = data.get("watch_list", {})
        if self.token:  # 补回鉴权头
            self.session.headers["Authorization"] = self.token
    
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    with open("config/user.yaml", "r", encoding="utf-8") as f:
        import yaml
        config = yaml.safe_load(f)
    
    client = XMUClient(
        username=config["username"],
        password=config["password"],
        campus=config.get("campus", "6"),
        config_captcha=config["captcha"]
    )
    
        
    # courses = client.search_courses("ALLKC", keyword="130220000051")
    
    # print(f"搜索到 {len(courses)} 门课程")
    # with open("cache/courses.json", "w", encoding="utf-8") as f:
    #     import json
    #     json.dump(courses, f, ensure_ascii=False, indent=2)
    
    # selected, capacity = client.query_class_number("130220000051", "20252026213022000005104")
    # print(f"已选人数: {selected}, 总名额: {capacity}")
    
    while True:
        client.load()
        if client.is_logged_in == False:
            if client.login():
                print("【登录成功】")
                print(f"   Token: {client.token[:20]}...")
                print(f"   BatchID: {client.batch_id}")
            else:
                print("【登录失败】")
                time.sleep(2)
                continue
            client.save()
            print("已保存登录状态到缓存文件")
        else:
            print("【已登录】")
        
        print("【请选择操作】")
        print("1. 添加课程监控")
        print("2. 查看/删除监控列表")
        print("3. 开始循环监控")
        
        choice = input("请输入操作编号: ").strip()
        if choice == "1":
            keyword = input("请输入关键词（可以是课程号，更推荐）: ").strip()
            classes = client.search_courses("ALLKC", keyword=keyword)
            if not classes:
                print("未找到相关课程")
                continue
            print(f"找到 {len(classes)} 门相关课程:")
            
            for idx, clazz in enumerate(classes):
                print(f"{idx + 1}. {clazz['KCM']}（{clazz['SKJS']}） {clazz.get('teachingPlaceHide', '未知')}, 已选/总名额: {clazz['numberOfSelected']}/{clazz['classCapacity']}")
            
            sel = input("请输入要监控的课程编号（多个用逗号分隔，可以用-，例如，“1-4,5,7”）: ").strip()
            indices = []
            for part in sel.split(","):
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    indices.extend(range(start, end + 1))
                else:
                    indices.append(int(part))
            
            for idx in indices:
                if 1 <= idx <= len(classes):
                    clazz = classes[idx - 1]
                    KCH = clazz["KCH"]
                    JXBID = clazz["JXBID"]
                    result = client.add_watch(KCH, JXBID, {
                        "KCM": clazz["KCM"],
                        "SKJS": clazz["SKJS"],
                        "teachingPlaceHide": clazz["teachingPlaceHide"]
                    })
                    print(f"添加监控课程 {clazz['KCM']}（{KCH} - {JXBID}）: {result}")
                else:
                    print(f"无效的课程编号: {idx}")
            
            client.save()
            print("已保存监控列表到缓存文件")
    
        elif choice == "2":
            if not client.watch_list:
                print("当前监控列表为空")
                continue
            print("当前监控列表:")
            
            idx = 1
            for KCH, jxb_dict in client.watch_list.items():
                for JXBID, info in jxb_dict.items():
                    print(f"{idx}. {info['info']['KCM']}（{KCH} - {JXBID}） 已选/总名额: {info['last_selected']}/{info['capacity']}")
                    idx += 1
            
            choice = input("是否要删除某个监控？(y/n): ").strip().lower()
            if choice == "y":
                sel = input("请输入要删除的监控编号（多个用逗号分隔，可以用-，例如，“1-4,5,7”）: ").strip()
                indices = []
                for part in sel.split(","):
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        indices.extend(range(start, end + 1))
                    else:
                        indices.append(int(part))
                
                to_delete = []
                idx = 1
                for KCH, jxb_dict in client.watch_list.items():
                    for JXBID in jxb_dict.keys():
                        if idx in indices:
                            to_delete.append((KCH, JXBID))
                        idx += 1
                
                for KCH, JXBID in to_delete:
                    del client.watch_list[KCH][JXBID]
                    if not client.watch_list[KCH]:
                        del client.watch_list[KCH]
                    print(f"已删除监控课程 {KCH} - {JXBID}")
                
                client.save()
                print("已保存监控列表到缓存文件")
            
        elif choice == "3":
            print("开始循环监控课程名额变化，按 Ctrl+C 停止")
            try:
                while True:
                    for KCH, jxb_dict in client.watch_list.items():
                        for JXBID, info in jxb_dict.items():
                            try:
                                selected, capacity = client.query_class_number(KCH, JXBID)
                                if selected != info["last_selected"]:
                                    print(f"课程 {info['info']['KCM']}（{KCH} - {JXBID}）名额变化: {info['last_selected']} -> {selected} / {capacity}")
                                    info["last_selected"] = selected
                                    info["capacity"] = capacity
                                    client.save()
                                else:
                                    print(f"课程 {info['info']['KCM']}（{KCH} - {JXBID}）名额无变化: {selected} / {capacity}")
                            except Exception as e:
                                print(f"查询课程 {KCH} - {JXBID} 名额失败: {e}")
                    time.sleep(30)  # 每30秒检查一次
            except KeyboardInterrupt:
                print("已停止课程监控循环")
                
        else:
            print("无效的操作编号，请重试")