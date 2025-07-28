"""
Author: wlaten
Date: 2025-01-01 18:07:52
LastEditTime: 2025-01-01 18:10:22
Discription: file content
"""

import json
import questionary
from utils.helpers import clear_screen, chunk_choices, console, create_style
from utils.config_handler import load_last_selection, save_last_selection
from questionary import Choice
from typing import List


def select_KKDW():
    """选择开课单位"""
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

    style = create_style()

    while True:
        clear_screen()

        start_index = current_page * 10

        choices: List[Choice] = []
        for idx, item in enumerate(pages[current_page]):
            title = f"{start_index + idx + 1}. {item.get('name', '无名')}"
            if item.get("name") == last_selected_name:
                title += " [上次选择]"
            choices.append(Choice(title=title, value=item))

        if total_pages > 1:
            if current_page < total_pages - 1:
                choices.append(Choice(title="↓ 下一页", value="NEXT"))
            if current_page > 0:
                choices.append(Choice(title="↑ 上一页", value="PREV"))

        console.print(
            f"\n[page_info]第 {current_page + 1}/{total_pages} 页[/page_info]"
        )

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
            save_last_selection(
                {"last_kkdw_name": result.get("name"), "last_kkdw_id": result.get("id")}
            )
            return result
