'''
Author: wlaten
Date: 2025-01-03 13:28:48
LastEditTime: 2025-01-03 14:48:30
Discription: file content
'''
import json 
import os
from utils.helpers import clear_screen, console, create_style
import questionary

def load_class_type_map():
    """
    从 info/clazzType.json 中读取并返回 {displayName: teachingClassType} 的映射字典
    """
    with open('info/clazzType.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {item['displayName']: item['teachingClassType'] for item in data}

def load_watch_list():
    """
    读取已有的监听列表
    """
    path = 'cache/watch_list.json'
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_watch_list(watch_list):
    """
    保存监听列表
    """
    os.makedirs('cache', exist_ok=True)
    path = 'cache/watch_list.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(watch_list, f, ensure_ascii=False, indent=2)
        
def watch_courses(xmu_login, course_controller, teaching_class_type, campus, keyword=None):
    """
    1. 根据给定的 teaching_class_type、campus、keyword 搜索课程
    2. 展示搜索结果，让用户选择想要监听的课程
    3. 将选定课程加入监听列表
    """
    style = create_style()
    page_number = 1

    while True:
        req = {
            "teachingClassType": teaching_class_type,  # 从命令行的 --type 映射得到
            "pageNumber": page_number,
            "pageSize": 10,
            "orderBy": "",
            "campus": campus   # 从 user.yaml 读出的用户校区
        }
        if keyword:
            req["KEY"] = keyword

        response_data = course_controller.search_courses(req)
        print(response_data)
        if not response_data:
            console.print("[red]未能获取到搜索结果。[/red]")
            break

        # 给用户展示并选择课程
        choices = []
        for idx, course in enumerate(response_data, start=1):
            course_name = course.get('KCM', '无名课程')
            teacher = course.get('SKJS', '未知教师')
            
            classlist = course['tcList']
            for c in classlist:
                teacher = c.get('SKJS', '未知教师')
                teaching_place = c.get('teachingPlace', '未知地点')
                title = f"{idx}. {course_name} | 教师: {teacher} | 地点: {teaching_place}"
                choices.append(questionary.Choice(title=title, value=c))

        # 加一个“下一页”或“退出”的选项
        if len(response_data) >= 10:
            choices.append(questionary.Choice(title="下一页", value="NEXT_PAGE"))
        choices.append(questionary.Choice(title="退出", value="EXIT"))

        selected = questionary.select(
            "请选择要加入监听列表的课程(或下一页/退出):",
            choices=choices,
            style=style
        ).ask()

        if selected == "EXIT":
            console.print("已退出查询。")
            break
        elif selected == "NEXT_PAGE":
            page_number += 1
            continue
        else:
            # 选中了某个实际课程
            console.print(f"\n您选择的课程: [cyan]{selected.get('courseName_zh', '无名课程')}[/cyan]")
            console.print(f"教师: {selected.get('SKJS', '未知教师')}")
            console.print(f"上课地点: {selected.get('teachingPlace', '未知地点')}")
            console.print(f"JXBID: {selected.get('JXBID', '未知')}")

            if questionary.confirm("是否将此课程加入监听列表？", style=style).ask():
                # 将课程信息存到 watch_list.json
                watch_list = load_watch_list()
                selected['clazzType'] = teaching_class_type
                watch_list.append(selected)
                save_watch_list(watch_list)

                console.print("[green]已将该课程加入监听列表。[/green]")
            else:
                console.print("[yellow]未加入监听列表。[/yellow]")

        # 是否继续翻页
        if len(response_data) < 10:
            # 当前页数不足10条，说明没有下一页了
            console.print("[yellow]已经没有更多结果。[/yellow]")
            continue
        # 如果用户刚才选了课程，不管是不是添加，都可以让他确认下一页
        if not questionary.confirm("是否查看下一页？", style=style).ask():
            break
