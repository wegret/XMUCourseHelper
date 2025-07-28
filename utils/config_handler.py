"""
Author: wlaten
Date: 2025-01-01 18:07:27
LastEditTime: 2025-01-01 18:09:44
Discription: file content
"""

import json
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path("config/last_selection.json")


def load_last_selection() -> Dict[Any, Any]:
    """加载上次选择的配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_last_selection(selection: Dict[Any, Any]):
    """保存当前选择到配置文件"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(selection, f, ensure_ascii=False, indent=2)
