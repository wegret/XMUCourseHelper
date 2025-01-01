'''
Author: wlaten
Date: 2025-01-01 18:07:14
LastEditTime: 2025-01-01 18:08:49
Discription: file content
'''

import os
from typing import List, Dict
from questionary import Choice
from utils.config_handler import load_last_selection, save_last_selection
from utils.config_handler import CONFIG_FILE
from rich.console import Console
from rich.theme import Theme
import questionary

def clear_screen():
    """清屏函数，支持Windows和Unix系统"""
    os.system('cls' if os.name == 'nt' else 'clear')

def chunk_choices(items: List[Dict], chunk_size: int = 10) -> List[List[Dict]]:
    """将列表分块"""
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

custom_theme = Theme({
    "page_info": "yellow",
})
console = Console(theme=custom_theme)

def create_style():
    """创建questionary的样式"""
    return questionary.Style([
        ('question', ''),  
        ('selected', 'reverse bold'), 
        ('pointer', ''), 
        ('instruction', ''),
        ('highlighted', 'noreverse bold'),
        ('answer', 'cyan bold'),
    ])
