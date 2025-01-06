'''
Author: wlaten
Date: 2024-12-31 07:23:59
LastEditTime: 2025-01-04 20:35:16
Discription: file content
'''

import json
import argparse
from utils.helpers import clear_screen, console, create_style
from selection import select_KKDW
from login import XMULogin
from course_controller import XMUCourseController
import logging
import time
import questionary
import random
from collections import defaultdict

import warnings
import urllib3
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

from watch import load_class_type_map, load_watch_list, save_watch_list, watch_courses

import sys

def alert_user(course_name, number_of_selected, class_capacity):
    """
    播放提示音并显示提示框
    """
    
    if sys.platform.startswith('win'):
        import tkinter as tk
        from tkinter import messagebox
        
        print('\a')  

        def show_message():
            root = tk.Tk()
            root.withdraw() 
            messagebox.showinfo(
                "课程有空位啦！",
                f"课程: {course_name}\n已选人数: {number_of_selected}/{class_capacity}"
            )
            root.destroy()

        show_message()
    else:
        import requests
        
        data = {
            "msg_type": "course_alert",
            "course_name": course_name,
            "selected": number_of_selected,
            "capacity": class_capacity
        }
        
        try:
            # TODO 这里路由应该在config里配置
            r = requests.post("http://127.0.0.1:8080/alert", json=data, timeout=5)
            if r.status_code != 200:
                console.print(f"[red]发送提示失败: {r.text}[/red]")
            else:
                console.print("[green]已发送提示。[/green]")
        except Exception as e:
            console.print(f"[red]发送提示失败: {str(e)}[/red]")
        
    
    
def listen_loop(xmu, course_controller, interval, autoadd_enabled=False, random_adjustment=False):
    """
    持续监听 watch_list.json 中的课程，定时查询更新 secretVal、选课人数、容量并判断是否有空位
    autoadd_enabled: 是否启用自动添加监听课程
    random_adjustment: 是否启用随机调整查询间隔
    """
    while True:
        watch_list = load_watch_list()
        if not watch_list:
            console.print("[yellow]当前监听列表为空，请先添加监听课程。[/yellow]")
        else:
            watch_list_typed = defaultdict(list)
            for course_info in watch_list:
                watch_list_typed[course_info.get('clazzType')].append(course_info)
                
            tykc_dict = {}
            if 'TYKC' in watch_list_typed:
                req_tykc = {
                    "teachingClassType": "TYKC",
                    "pageNumber": 1,
                    "pageSize": 10,
                    "orderBy": "",
                    "campus": xmu.campus
                }
                
                response_data_tykc = []
                while True:
                    response_data = course_controller.search_courses(req_tykc)
                    if not response_data:
                        console.print("[red]未能获取到课程。[/red]")
                        return
                    
                    response_data_tykc.extend(response_data)
                    
                    if len(response_data) < 10:
                        break
                    req_tykc["pageNumber"] += 1
                
                for course in response_data_tykc:
                    for c in course.get('tcList', []):
                        tykc_dict[c.get('JXBID')] = c
                
            
            for course_info in watch_list[:]:       # 做副本，避免迭代时删除元素
                jxbid = course_info.get('JXBID')
                course_name = course_info.get('courseName_zh', '未知课程')
                teaching_class_type = course_info.get('clazzType')
                if not jxbid or not teaching_class_type:
                    console.print(f"[red]监听列表中缺少 JXBID 或 clazzType，跳过此条课程。[/red]")
                    continue
                
                if teaching_class_type == 'TYKC':
                    found_course = tykc_dict.get(jxbid)
                
                else:
                    req = {
                        "teachingClassType": teaching_class_type,
                        "pageNumber": 1,
                        "pageSize": 10,
                        "orderBy": "",
                        "campus": xmu.campus
                    }
                    req["KEY"] = course_name

                    response_data = course_controller.search_courses(req)

                    found_course = None
                    if response_data:
                        for c in response_data:
                            for sub_course in c.get('tcList', []):
                                if sub_course.get('JXBID') == jxbid:
                                    found_course = sub_course
                                    break
                            if found_course:
                                break

                # 如果找到了对应 JXBID 的课程
                if found_course:
                    secret_val = found_course.get('secretVal', '未知')
                    number_of_selected = found_course.get('numberOfSelected', 0)
                    class_capacity = found_course.get('classCapacity', 0)

                    # 输出课程现况
                    console.print(f"\n[bold]课程[/bold]: [cyan]{course_name}[/cyan]")
                    console.print(f"[bold]JXBID[/bold]: {jxbid}")
                    # console.print(f"[bold]secretVal[/bold]: {secret_val}")
                    console.print(f"[bold]已选人数[/bold]: {number_of_selected} / [bold]容量[/bold]: {class_capacity}")

                    # 判断是否有空位
                    if number_of_selected < class_capacity:
                        console.print(f"[green]{course_name} 有空位！[/green]")
                        
                        if not sys.platform.startswith('win'):  # Linux下，特判一下，删掉这个课程
                            watch_list.remove(course_info)
                            save_watch_list(watch_list) # TODO：这是不对的，应该在数据库中判断变化，而不是直接删除
                        
                        if autoadd_enabled:
                            add_result = course_controller.add_course(
                                clazz_type=teaching_class_type,
                                clazz_id=jxbid,
                                secret_val=secret_val
                            )
                            if add_result and add_result.get('code') == 200:
                                console.print(f"[green]选课成功: {course_name}[/green]")
                                
                                # 选课成功后从 watch_list 中移除
                                watch_list.remove(course_info)
                                save_watch_list(watch_list)
                            else:
                                error_msg = add_result.get('msg', '未知错误') if add_result else '未知错误'
                                console.print(f"[red]选课失败: {error_msg}[/red]")
                        alert_user(course_name, number_of_selected, class_capacity)
                        print("继续执行....")
                    else:
                        console.print(f"[yellow]{course_name} 暂无空位[/yellow]")
                else:
                    console.print(f"[red]未找到课程 {course_name} (JXBID={jxbid})，可能已下架或查询条件有误。[/red]")
                    return 
        
        next_interval = interval
        if random_adjustment:
            adjust_fac = 0.5
            min_interval = int(interval * (1 - adjust_fac))
            max_interval = int(interval * (1 + adjust_fac))
            next_interval = int(random.uniform(min_interval, max_interval))
        
        console.print(f"\n等待 [cyan]{next_interval}[/cyan] 秒后再次查询...\n")
        time.sleep(next_interval)
        

def alert_error(msg):
    if sys.platform.startswith('win'):
        import ctypes
        MessageBox = ctypes.windll.user32.MessageBoxW
        MessageBox(None, msg, "Error", 0)
    else:
        import requests
        
        data = {
            "msg_type": "error_alert",
            "msg": msg
        }
        
        try:
            # TODO 这里路由应该在config里配置
            r = requests.post("http://127.0.0.1:8080/alert", json=data, timeout=5)
            if r.status_code != 200:
                console.print(f"[red]发送提示失败: {r.text}[/red]")
            else:
                console.print("[green]已发送提示。[/green]")
        except Exception as e:
            console.print(f"[red]发送提示失败: {str(e)}[/red]")
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", help="输入课程名关键词")
    parser.add_argument("--watch", action="store_true", help="监听模式（交互式添加监听课程）")
    parser.add_argument("--listen", action="store_true", help="是否进入持续监听循环（自动查询）")
    parser.add_argument("--interval", type=int, default=60, help="监听模式下的查询间隔秒数，默认 60 秒")
    parser.add_argument("--type", help="选课类型的显示名称，例如：本专业计划课程")
    parser.add_argument("--key", help="搜索关键词")
    parser.add_argument("--autoadd", action="store_true", help="是否启用自动添加监听课程")
    parser.add_argument("--random", action="store_true", help="是否启用随机调整查询间隔")
    parser.add_argument("--all", action="store_true", help="自动选中所有搜索到的课程")
    args = parser.parse_args()
    
    failure_cnt = 0
    
    while True:
        if failure_cnt >= 5:
            alert_error("xk.xmu.edu.cn出错，或网络中断")
        
        console.print("[bold][red]正在登录...[/red][/bold]")
        xmu = XMULogin()
        if not xmu.login():
            console.print("[red]登录失败！[/red]")
            failure_cnt += 1
            continue

        if not xmu.batch_id:
            print("未获取到 Batch ID，请检查登录响应。")
            failure_cnt += 1
            continue
        
        failure_cnt = 0

        course_controller = XMUCourseController(xmu.session, xmu.token, xmu.batch_id)

        if args.watch:
            class_type_map = load_class_type_map()
            if not args.type or args.type not in class_type_map:
                console.print("[red]无效或缺少 --type，请检查输入。[/red]")
                return

            campus = xmu.campus

            teaching_class_type = class_type_map[args.type]
            keyword = args.key if args.key else None

            # 查课 & 添加监听
            ret = watch_courses(
                xmu_login=xmu,
                course_controller=course_controller,
                teaching_class_type=teaching_class_type,
                campus=campus,
                keyword=keyword,
                add_all=args.all
            )
            if ret == False:
                return 

        if args.listen:
            listen_loop(xmu, course_controller, args.interval, autoadd_enabled=args.autoadd, random_adjustment=args.random)
    
    # if args.search:
    #     req = {
    #         "teachingClassType": "ALLKC",
    #         "pageNumber": 1,
    #         "pageSize": 10,
    #         "orderBy": "",
    #         "KEY": args.search
    #     }
        
    #     clear_screen()
    #     console.print(f"课程名关键词为: [cyan]{args.search}[/cyan]")
        
    #     style = create_style()
        
    #     if questionary.confirm("是否需要选择开课单位?", style=style).ask():
    #         selected_kkdw = select_KKDW()
    #         if selected_kkdw:
    #             req["KKDW"] = selected_kkdw.get("code", "")
        
    #     clear_screen()
    #     console.print("\n最终请求参数:")
    #     console.print(json.dumps(req, ensure_ascii=False, indent=2))
        
    #     try:
    #         print("正在登录...")
    #         xmu = XMULogin()
            
    #         if xmu.login():
    #             print("登录成功！")
                
    #             if xmu.batch_id:
    #                 print(f"Batch ID: {xmu.batch_id}")
                    
    #                 course_controller = XMUCourseController(xmu.session, xmu.token, xmu.batch_id)
                    
    #                 page_number = 1
    #                 while True:
    #                     req["pageNumber"] = page_number
    #                     response_data = course_controller.search_courses(req)
                        
    #                     if not response_data:
    #                         console.print("[red]未能获取到搜索结果。[/red]")
    #                         break
                        
    #                     # 构造选择项
    #                     choices = []
    #                     for idx, course in enumerate(response_data, start=1):
    #                         course_name = course.get('courseName_zh', '无名课程')
    #                         teacher = course.get('SKJS', '未知教师')
    #                         campus = course.get('campus', '未知校区')
    #                         teaching_place = course.get('teachingPlace', '未知地点')
    #                         limit_kind = ', '.join([lk.get('limitDesc_zh', '') for lk in course.get('limitKindList', [])])
                            
    #                         title = f"{idx}. {course_name} | 教师: {teacher} | 校区: {campus} | 地点: {teaching_place}"
    #                         if limit_kind:
    #                             title += f" | 限制: {limit_kind}"
                            
    #                         choices.append(questionary.Choice(title=title, value=course))
                        
    #                     choices.append(questionary.Choice(title="退出", value="EXIT"))
                        
    #                     selected_course = questionary.select(
    #                         "请选择一个课程进行选课:",
    #                         choices=choices,
    #                         style=style
    #                     ).ask()
                        
    #                     if selected_course == "EXIT":
    #                         console.print("退出程序。")
    #                         break
    #                     else:
    #                         # 显示选中的课程信息
    #                         console.print(f"\n您选择的课程: [cyan]{selected_course.get('courseName_zh', '无名课程')}[/cyan]")
    #                         console.print(f"教师: {selected_course.get('SKJS', '未知教师')}")
    #                         console.print(f"校区: {selected_course.get('campus', '未知校区')}")
    #                         console.print(f"地点: {selected_course.get('teachingPlace', '未知地点')}")
                            
    #                         if questionary.confirm("是否要选取此课程?", style=style).ask():
    #                             clazz_type = selected_course.get('courseType', '')
    #                             clazz_id = selected_course.get('courseGroupCode', '')
    #                             secret_val = selected_course.get('secretVal', '')
                                
    #                             add_result = course_controller.add_course(
    #                                 clazz_type=clazz_type,
    #                                 clazz_id=clazz_id,
    #                                 secret_val=secret_val
    #                             )
                                
    #                             if add_result and add_result.get('code') == 200:
    #                                 console.print(f"[green]选课成功: {selected_course.get('courseName_zh', '无名课程')}[/green]")
    #                             else:
    #                                 error_msg = add_result.get('msg', '未知错误') if add_result else '未知错误'
    #                                 console.print(f"[red]选课失败: {error_msg}[/red]")
    #                         else:
    #                             console.print("未进行选课操作。")
                        
    #                     if not questionary.confirm("是否继续查看下一页课程?", style=style).ask():
    #                         break
    #                     page_number += 1
                        
    #             else:
    #                 print("未获取到 Batch ID，请检查登录响应。")
    #         else:
    #             print("登录失败！")
    #     except Exception as e:
    #         print(f"发生错误: {str(e)}")
    #         logging.error(f"程序运行出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
