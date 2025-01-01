'''
Author: wlaten
Date: 2024-12-31 07:23:59
LastEditTime: 2025-01-01 18:36:57
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

import warnings
import urllib3
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

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
        
        style = create_style()
        
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
                            break
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
                        
                        # 可选择是否继续翻页或退出
                        if not questionary.confirm("是否继续查看下一页课程?", style=style).ask():
                            break
                        page_number += 1
                        
                else:
                    print("未获取到 Batch ID，请检查登录响应。")
            else:
                print("登录失败！")
        except Exception as e:
            print(f"发生错误: {str(e)}")
            logging.error(f"程序运行出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
