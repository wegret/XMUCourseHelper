'''
Author: wlaten
Date: 2025-12-27 00:52:30
LastEditTime: 2026-01-04 19:46:53
Discription: file content
'''
import requests
from utils.aes_util import AesUtil
import logging
import warnings
import urllib3
import time, os, json
from typing import Optional, Dict, Any, Tuple
import urllib.parse

from captcha import solve_captcha

warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

os.makedirs("cache", exist_ok=True)

min_request_interval = 1.1  # 最小请求间隔，防止被封

class XMUClient:
    
    BASE_URL = "https://xk.xmu.edu.cn/xsxkxmu"
    
    def __init__(self,
                 username: str,
                 password: str,
                 campus: str,
                 config_captcha: dict,
                 auto_add_enable: bool = False,
                 check_interval: int = 60):  
        self.username = username
        self.password = password
        self.campus = campus
        self.aes = AesUtil("MWMqg2tPcDkxcm11")
        self.config_captcha = config_captcha
        self.auto_add_enable = auto_add_enable
        self.check_interval = check_interval
        
        self.session = self._create_session()
        self.token = None
        self.batch_id = None
        self.cookies = {}
        
        self.watch_list = {}  # KCH -> {JXBID: { last_selected: int, capacity: int, subscribers: list }}
        
        self.last_request_time = 0
        
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
            logging.warning(f"初始访问首页失败: {e}")   # todo 这是网络波动
            
        return session
    
    def _reset_session(self):
        """重建 session，相当于重启浏览器"""
        logging.info("重建 Session...")
        self.session.close()
        self.token = None
        self.batch_id = None
        self.session = self._create_session()
    
    def _request(self,
                 method: str,
                 endpoint: str, # 相对路径，如 "/auth/login"
                 max_retries: int = 3,
                 retry_forever: bool = False,
                 backoff_base: float = 1.0,
                 backoff_cap: int = 60,
                 **kwargs) -> requests.Response:
        
        url = f"{self.BASE_URL}{endpoint}"
        
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("verify", False)
        
        last_exception = None
        attempt = 0
        # retry_forever 会在服务不可用时持续重试，防止程序直接崩溃
        while True:
            attempt += 1
            
            if time.time() - self.last_request_time < min_request_interval:
                sleep_time = min_request_interval - (time.time() - self.last_request_time)
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()
            
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                last_exception = e
                attempt_info = f"{attempt}/{max_retries}" if not retry_forever else f"{attempt}/∞"
                logging.warning(f"请求失败 (尝试 {attempt_info}): {e}")
                if not retry_forever and attempt >= max_retries:
                    raise last_exception
                sleep_seconds = min(backoff_cap, backoff_base * attempt)
                logging.info(f"等待 {sleep_seconds:.0f} 秒后重试...")
                time.sleep(sleep_seconds)

    def _get_captcha(self) -> Tuple[str, str]:
        resp = self._request("POST", "/auth/captcha", retry_forever=True)
        data = resp.json()
        if data.get("code") != 200:
            raise Exception(f"获取验证码失败: {data.get('message', '未知错误')}")
        
        uuid = data["data"]["uuid"]
        image_base64 = data["data"]["captcha"].split(",")[1]
        
        return uuid, image_base64
    
    def login(self) -> bool:
        
        error_cnt = 0
        while True:
            if error_cnt >= 5:
                logging.error("连续多次登录失败，正在重建 Session...")
                self._reset_session()
                error_cnt = 0
            
            uuid, image_base64 = self._get_captcha()
            
            success, captcha_code = solve_captcha(image_base64, self.config_captcha)
            if not success:
                logging.warning(f"验证码识别失败: {captcha_code}")
                continue
            
            logging.info(f"验证码识别结果: {captcha_code}")
            
            encrypted_password = self.aes.encrypt(self.password)
            
            payload = {
                "loginname": self.username,
                "password": encrypted_password,
                "captcha": str(captcha_code),
                "uuid": uuid
            }
            
            try:
                resp = self._request("POST", "/auth/login", data=payload, retry_forever=True)
                data = resp.json()
                # print(f"登录响应: {data}")
                
                if data.get("code") != 200:
                    logging.warning(f"登录失败: {data.get('msg') or data.get('message', '未知错误')}，正在重试...")
                    error_cnt += 1
                    continue
                
                self.token = data["data"]["token"]
                self.session.headers["Authorization"] = self.token
                self.session.cookies.set("Authorization", self.token)
                
                student = data["data"].get("student", {})
                batch_list = student.get("electiveBatchList", [])
                self.batch_id = batch_list[0]["code"] if batch_list else None
                if self.batch_id:   # API 选课接口需要 batchId 头才能视为有效轮次
                    self.session.headers["batchId"] = self.batch_id
                
                logging.info(f"登录成功！用户: {student.get('XM', '未知')}, BatchID: {self.batch_id}")
                return True 
            
            except Exception as e:
                logging.error(f"登录请求异常: {e}，正在重试...")
                error_cnt += 1

    @property
    def is_logged_in(self) -> bool:
        if self.batch_id is None:
            return False
        payload = {
            "batchId": self.batch_id
        }
        resp = self._request("POST", "/elective/user", allow_redirects=False, data=payload, retry_forever=True)
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
                resp = self._request("POST", "/elective/xmu/clazz/list", json=payload,
                                     timeout=5)
                data = resp.json()
                
                if data.get("code") != 200:
                    logging.error(f"搜索课程失败: {data.get('message', '未知错误')}")
                    return None
                
                courses.extend(data["data"].get("rows", []))
                
                if len(courses) >= data["data"].get("total", 0):
                    courses_clean = []
                    for course in courses:
                        if "tcList" in course:
                            for clazz in course["tcList"]:
                                if str(clazz.get("campus")) == str(self.campus):
                                    courses_clean.append(clazz)
                        else:
                            if str(course.get("campus")) == str(self.campus):
                                courses_clean.append(course)
                    return courses_clean
                
                payload["pageNumber"] += 1
                error_cnt = 0
                
            except Exception as e:
                logging.error(f"搜索课程异常: {e}")
                error_cnt += 1            
                if error_cnt >= 3:
                    return None
    
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
    
    def add_watch(self, KCH, JXBID, subscriber=(-1, -1)):
        """
        把课程加入监控列表
        Args:
            KCH: 课程号
            JXBID: 教学班ID
            subscriber: 订阅者标识，后续引入qq bot用，(qq号, 群号)，如果是私聊则群号为-1
        Returns:
            bool: 是否成功
            str: 结果信息
        """
        # number_of_selected, capacity = self.query_class_number(KCH, JXBID)
        if KCH not in self.watch_list:
            self.watch_list[KCH] = {}
        if JXBID not in self.watch_list[KCH]:
            
            info = {}
            class_type = ["TJKC", "FANKC", "FAWKC", "TYKC", "XGKC"]
            
            for t in class_type:
                classes = self.search_courses(t, keyword=str(KCH))
                # print(f"搜索课程类型 {t}，找到 {len(classes)} 门相关课程")
                if len(classes) > 0:
                    # 这个就说明是了
                
                    for clazz in classes:
                        if str(clazz.get("JXBID")) == str(JXBID):
                            # todo 这里没有检查是否可选，默认选的一定可选
                            info = {
                                "KCM": clazz["KCM"],
                                "SKJS": clazz["SKJS"],
                                "secretVal": clazz["secretVal"],
                                "teachPlaceHide": clazz.get("teachingPlaceHide", "未知"),
                                "clazzType": t
                            }
                            number_of_selected, capacity = int(clazz.get("numberOfSelected")), int(clazz.get("classCapacity"))
                    
                    if info:
                        break
                
            if info == {}:
                logging.info("这门课你无法选择！")
                return False, "这门课你无法选择！是给你选的吗你就选？"
            
            self.watch_list[KCH][JXBID] = {
                "last_selected": number_of_selected,
                "capacity": capacity,
                "info": info,
                "subscribers": [],
                "had_vacancy": False  # 强制首轮检测一次空位
            }
            
        if subscriber not in self.watch_list[KCH][JXBID]["subscribers"]:
            self.watch_list[KCH][JXBID]["subscribers"].append(subscriber)
        else:
            return True, "您已订阅该课程的监控"
        return True, "已成功将课程加入监控列表"
    
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
            self.session.cookies.set("Authorization", self.token)
        if self.batch_id:
            self.session.headers["batchId"] = self.batch_id
    
    def add_course(self, KCH, clazzId, clazzType):
        
        print(f"尝试选课: KCH={KCH}, clazzId={clazzId}, clazzType={clazzType}")
        classes = self.search_courses(clazzType, keyword=KCH)
        if not classes:
            return False, "未找到课程列表，无法选课"

        secretVal = None
        for clazz in classes:
            if str(clazz.get("JXBID")) == str(clazzId):
                secretVal = clazz.get("secretVal")
                break
        if not secretVal:
            return False, "未找到对应课程信息，无法选课"
        
        headers = {
            "Referer": f"{self.BASE_URL}/elective/grablessons?batchId={self.batch_id}"
        }
        try:
            resp = self._request("POST", "/elective/clazz/add", data={
                "clazzType": clazzType,
                "clazzId": clazzId,
                "secretVal": secretVal
            }, headers=headers)
            data = resp.json()
            if data.get("code") == 200:
                return True, f"【选课成功】"
            else:
                return False, f"选课失败: {data.get('msg', '未知错误')}"
        except Exception as e:
            return False, f"选课请求异常: {e}"
    
    def check_once(self) -> list:
        """
        单次检查所有监控课程，返回变化列表
        Returns:
            list[dict]: [{"KCH": ..., "JXBID": ..., "info": ..., "old": int, "new": int, "capacity": int, "has_vacancy": bool}, ...]
        """
        changes = []
        for KCH, jxb_dict in self.watch_list.items():
            classes = self.search_courses("ALLKC", keyword=str(KCH))
            if not classes:
                continue
            for clazz in classes:
                JXBID = str(clazz.get("JXBID"))
                if JXBID not in jxb_dict:
                    continue
                
                number_of_selected = int(clazz.get("numberOfSelected"))
                capacity = int(clazz.get("classCapacity"))
                watch_info = jxb_dict[JXBID]
                last_selected = watch_info["last_selected"]
                prev_has_vacancy = watch_info.get("had_vacancy", False)
                has_vacancy = number_of_selected < capacity
                
                if number_of_selected != last_selected or (has_vacancy and not prev_has_vacancy):
                    changes.append({
                        "KCH": KCH,
                        "JXBID": JXBID,
                        "info": watch_info["info"],
                        "old": last_selected,
                        "new": number_of_selected,
                        "capacity": capacity,
                        "has_vacancy": has_vacancy,
                        "secretVal": clazz.get("secretVal")
                    })
                
                watch_info["last_selected"] = number_of_selected
                watch_info["capacity"] = capacity
                watch_info["info"]["secretVal"] = clazz.get("secretVal")
                watch_info["had_vacancy"] = has_vacancy

        return changes
    
    def start_monitoring(self, on_change=None, on_vacancy=None):
        """
        开始监控循环
        Args:
            on_change: 回调函数，签名 (change_dict) -> None，任何变化时调用
            on_vacancy: 回调函数，签名 (change_dict, success, msg) -> None，有空位时调用
        """
        logging.info(f"开始监控，间隔 {self.check_interval} 秒")
        round_num = 0
        
        while True:
            round_num += 1
            logging.info(f"[第 {round_num} 轮检查] 开始检查 {len(self.watch_list)} 门课程...")
            
            if not self.is_logged_in:
                logging.warning("登录已过期，尝试重新登录...")
                self.login()
                self.save()
            
            changes = self.check_once()
            
            if changes:
                logging.info(f"[第 {round_num} 轮检查] 发现 {len(changes)} 个变化")
            else:
                logging.info(f"[第 {round_num} 轮检查] 无变化")
            
            for change in changes:
                if on_change:
                    on_change(change)
                
                if self.auto_add_enable and change["has_vacancy"]:
                    logging.info(f"检测到空位，尝试自动选课: {change['info']['KCM']}")
                    success, msg = self.add_course(
                        KCH=change["KCH"],
                        clazzId=change["JXBID"],
                        clazzType=change["info"]["clazzType"]
                    )
                    if on_vacancy:
                        on_vacancy(change, success, msg)
            
            self.save()
            logging.info(f"[第 {round_num} 轮检查] 完成，等待 {self.check_interval} 秒...")
            time.sleep(self.check_interval) 
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    with open("config/user.yaml", "r", encoding="utf-8") as f:
        import yaml
        config = yaml.safe_load(f)
    
    client = XMUClient(
        username=config["username"],
        password=config["password"],
        campus=config.get("campus", "6"),
        config_captcha=config["captcha"],
        auto_add_enable=config.get("auto_add_enable", False),
        check_interval=config.get("check_interval")
    )
    
    while True:
        print("正在检查客户端状态...")
        client.load()
        if client.is_logged_in == False:
            print("未登录或登录过期，正在登录...")
            if client.login():
                print("【登录成功】")
                print(f"   Token: {client.token[:20]}...")
                print(f"   BatchID: {client.batch_id}")
            else:
                print("【登录失败】")
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
                    success, result = client.add_watch(KCH, JXBID)
                    if success:
                        print(f"添加监控课程 {clazz['KCM']}（{KCH} - {JXBID}）: {result}")
                    else:
                        print(f"添加监控课程 {clazz['KCM']}（{KCH} - {JXBID}）失败: {result}")
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
            
            sel = input("请输入要删除的监控编号（多个用逗号分隔，可以用-，例如 1-4,5,7；直接回车跳过）: ").strip()
            if sel:
                try:
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
                        course_name = client.watch_list[KCH][JXBID]['info']['KCM']
                        del client.watch_list[KCH][JXBID]
                        if not client.watch_list[KCH]:
                            del client.watch_list[KCH]
                        print(f"已删除监控课程: {course_name} ({KCH} - {JXBID})")
                    
                    client.save()
                    print("已保存监控列表到缓存文件")
                except ValueError:
                    print("输入格式错误，请输入有效的数字编号")
            
        elif choice == "3":
            print(f"开始循环监控，间隔 {client.check_interval} 秒，按 Ctrl+C 停止")
            
            def on_change(c):
                direction = "减少" if c["new"] < c["old"] else "增加"
                print(f"课程 {c['info']['KCM']}（{c['KCH']}）选课人数{direction}！{c['old']} -> {c['new']}/{c['capacity']}")
            
            def on_vacancy(c, success, msg):
                if success:
                    print(f"【自动选课成功！】 {c['info']['KCM']}")
                else:
                    print(f"【自动选课失败！】{c['info']['KCM']}，原因: {msg}")
            
            try:
                client.start_monitoring(on_change=on_change, on_vacancy=on_vacancy)
            except KeyboardInterrupt:
                print("已停止监控")
                
        else:
            print("无效的操作编号，请重试")