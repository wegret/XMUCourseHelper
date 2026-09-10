'''
Discription: XMUCourseHelper GUI —— 基于 PySide6 的图形界面
'''

import sys
import os
import json
import logging
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSize, QObject
from PySide6.QtGui import QFont, QColor, QIcon, QAction, QTextCursor, QPalette
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QListWidget,
    QListWidgetItem, QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QCheckBox, QTextEdit, QStatusBar, QProgressBar, QGroupBox, QMessageBox,
    QFileDialog, QHeaderView, QSplitter, QFrame, QSizePolicy, QPlainTextEdit,
    QAbstractItemView, QMenu
)

# 复用现有客户端
from client import XMUClient


# ====================================================================
# 主题与样式
# ====================================================================

# 主色调 + 配色板
COLORS = {
    "primary":      "#94070A", 
    "primary_hover":"#B30A0E",
    "primary_light":"#FBE9EA",
    "accent":       "#C8A951",   
    "bg":           "#F4F4F6",
    "surface":      "#FFFFFF",
    "border":       "#E3E3E8",
    "text":         "#1F1F23",
    "text_sub":     "#6B6B73",
    "success":      "#1E8E3E",
    "warning":      "#D97706",
    "danger":       "#C2410C",
    "sidebar_bg":   "#1B1B1F",
    "sidebar_text":"#E6E6E8",
    "sidebar_active":"#94070A",
}

# QSS 样式表
QSS = f"""
* {{
    font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif;
    font-size: 13px;
    color: {COLORS['text']};
}}
QMainWindow, QWidget {{ background: {COLORS['bg']}; }}

/* 侧边栏 */
#Sidebar {{
    background: {COLORS['sidebar_bg']};
    border: none;
}}
#Sidebar QLabel {{
    color: {COLORS['sidebar_text']};
    background: transparent;
}}
#SidebarTitle {{
    font-size: 18px;
    font-weight: 700;
    color: #FFFFFF;
    padding: 18px 20px 8px 20px;
}}
#SidebarSubtitle {{
    color: #8A8A92;
    font-size: 11px;
    padding: 0 20px 14px 20px;
}}
QListWidget#NavList {{
    background: {COLORS['sidebar_bg']};
    border: none;
    outline: none;
    padding: 6px;
    font-size: 14px;
}}
QListWidget#NavList::item {{
    color: {COLORS['sidebar_text']};
    padding: 10px 14px;
    margin: 2px 6px;
    border-radius: 8px;
}}
QListWidget#NavList::item:hover {{
    background: rgba(255,255,255,0.06);
}}
QListWidget#NavList::item:selected {{
    background: {COLORS['primary']};
    color: #FFFFFF;
    font-weight: 600;
}}

/* 卡片 */
QFrame#Card {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
}}
QLabel#CardTitle {{
    font-size: 16px;
    font-weight: 700;
    color: {COLORS['text']};
}}
QLabel#CardHint {{
    color: {COLORS['text_sub']};
    font-size: 12px;
}}
QLabel#SectionLabel {{
    font-size: 13px;
    font-weight: 600;
    color: {COLORS['text']};
}}

/* 输入控件 */
QLineEdit, QSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {COLORS['primary']};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLORS['primary']};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    selection-background-color: {COLORS['primary']};
    selection-color: #FFFFFF;
    outline: none;
}}

/* 按钮 */
QPushButton {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 7px 16px;
    color: {COLORS['text']};
}}
QPushButton:hover {{ background: {COLORS['primary_light']}; border-color: {COLORS['primary']}; }}
QPushButton:disabled {{ color: #A0A0A8; background: #F0F0F2; border-color: {COLORS['border']}; }}

QPushButton#Primary {{
    background: {COLORS['primary']};
    color: #FFFFFF;
    border: none;
    font-weight: 600;
    padding: 8px 18px;
}}
QPushButton#Primary:hover {{ background: {COLORS['primary_hover']}; }}
QPushButton#Primary:disabled {{ background: #D8D8DC; color: #FFFFFF; }}

QPushButton#Danger {{
    background: transparent;
    color: {COLORS['danger']};
    border: 1px solid {COLORS['danger']};
}}
QPushButton#Danger:hover {{ background: {COLORS['danger']}; color: #FFFFFF; }}

QPushButton#Ghost {{
    background: transparent;
    border: none;
    color: {COLORS['text_sub']};
}}
QPushButton#Ghost:hover {{ color: {COLORS['primary']}; }}

/* 表格 */
QTableWidget {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    gridline-color: {COLORS['border']};
    outline: 0;
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['text']};
}}
QHeaderView::section {{
    background: #FAFAFC;
    color: {COLORS['text_sub']};
    padding: 8px 10px;
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
}}
QTableWidget::item {{ padding: 8px 10px; }}
QTableWidget::item:selected {{ background: {COLORS['primary_light']}; }}

/* 日志 */
QPlainTextEdit#LogView {{
    background: #1E1E22;
    color: #E6E6E8;
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    font-family: "Consolas", "Cascadia Mono", monospace;
    font-size: 12px;
    padding: 8px;
}}

/* 状态栏 */
QStatusBar {{ background: {COLORS['surface']}; border-top: 1px solid {COLORS['border']}; }}
QStatusBar QLabel {{ color: {COLORS['text_sub']}; padding: 0 8px; }}

/* 状态徽章 */
QLabel#Badge {{
    padding: 2px 10px;
    border-radius: 10px;
    color: #FFFFFF;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#BadgeSuccess {{ background: {COLORS['success']}; }}
QLabel#BadgeWarning {{ background: {COLORS['warning']}; }}
QLabel#BadgeDanger  {{ background: {COLORS['danger']}; }}
QLabel#BadgeMuted  {{ background: #C0C0C6; color: #4B4B53; }}

/* 进度条 */
QProgressBar {{
    background: #ECECEF;
    border: none;
    border-radius: 4px;
    text-align: center;
    height: 8px;
}}
QProgressBar::chunk {{ background: {COLORS['primary']}; border-radius: 4px; }}

QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    background: {COLORS['surface']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['text_sub']};
}}

/* 复选框：放大指示器，勾选状态用主色填充 */
QCheckBox {{
    spacing: 8px;
    outline: none;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1.5px solid #B0B0B8;
    border-radius: 4px;
    background: {COLORS['surface']};
}}
QCheckBox::indicator:hover {{
    border-color: {COLORS['primary']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['primary']};
    border-color: {COLORS['primary']};
    image: none;
}}
"""


# ====================================================================
# 工具：状态徽章
# ====================================================================

def make_badge(text: str, level: str = "Muted") -> QLabel:
    """生成一个圆角状态徽章"""
    lbl = QLabel(text)
    lbl.setObjectName(f"Badge{level}")
    lbl.setAlignment(Qt.AlignCenter)
    return lbl


# ====================================================================
# Qt 信号桥：把 logging 输出转发到 UI
# ====================================================================

class _QtLogHandler(logging.Handler):
    """logging.Handler 子类，把日志通过 Qt 信号转发到主线程"""
    def __init__(self, sink):
        super().__init__()
        self._sink = sink
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                             datefmt="%H:%M:%S"))

    def emit(self, record):
        try:
            msg = self.format(record)
            # 用信号保证线程安全地推送到 UI
            self._sink.log_signal.emit(msg, record.levelname)
        except Exception:
            pass


# ====================================================================
# 工作线程：登录 / 搜索 / 监控循环
# ====================================================================

class LoginWorker(QThread):
    """后台登录"""
    success = Signal(bool, str)   # (是否成功, 消息)

    def __init__(self, client: XMUClient):
        super().__init__()
        self.client = client

    def run(self):
        try:
            ok = self.client.login()
            if ok:
                self.client.save()
                self.success.emit(True, "登录成功")
            else:
                self.success.emit(False, "登录失败")
        except Exception as e:
            self.success.emit(False, f"登录异常: {e}")


class SearchWorker(QThread):
    """后台搜索课程"""
    finished_result = Signal(list)   # 课程列表
    failed = Signal(str)

    def __init__(self, client: XMUClient, keyword: str, class_type: str = "ALLKC"):
        super().__init__()
        self.client = client
        self.keyword = keyword
        self.class_type = class_type

    def run(self):
        try:
            rows = self.client.search_courses(self.class_type, keyword=self.keyword)
            self.finished_result.emit(rows or [])
        except Exception as e:
            self.failed.emit(str(e))


class AddWatchWorker(QThread):
    """后台加入监控"""
    done = Signal(bool, str, str, str)   # (success, msg, KCH, JXBID)

    def __init__(self, client: XMUClient, kch: str, jxbid: str):
        super().__init__()
        self.client = client
        self.kch = kch
        self.jxbid = jxbid

    def run(self):
        try:
            ok, msg = self.client.add_watch(self.kch, self.jxbid)
            self.client.save()
            self.done.emit(ok, msg, self.kch, self.jxbid)
        except Exception as e:
            self.done.emit(False, f"添加监控异常: {e}", self.kch, self.jxbid)


class MonitorWorker(QThread):
    """后台监控循环，受 stop() 控制"""
    change_signal = Signal(dict)               # 变更
    vacancy_signal = Signal(dict, bool, str)   # (change, success, msg)
    round_signal = Signal(int, int)           # (round_num, changes_count)
    log_signal = Signal(str, str)             # (msg, level)
    status_signal = Signal(str)               # 状态文本

    def __init__(self, client: XMUClient):
        super().__init__()
        self.client = client
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        self.status_signal.emit("监控运行中")
        round_num = 0
        while not self._stop_flag:
            round_num += 1
            self.log_signal.emit(
                f"[第 {round_num} 轮] 开始检查 {len(self.client.watch_list)} 门课程",
                "INFO"
            )
            try:
                if not self.client.is_logged_in:
                    self.log_signal.emit("登录已过期，正在重新登录...", "WARNING")
                    self.client.login()
                    self.client.save()
                    self.log_signal.emit("重新登录成功", "INFO")

                changes = self.client.check_once()
                self.round_signal.emit(round_num, len(changes))

                if not changes:
                    self.log_signal.emit(f"[第 {round_num} 轮] 无变化", "INFO")
                else:
                    self.log_signal.emit(
                        f"[第 {round_num} 轮] 发现 {len(changes)} 个变化", "INFO"
                    )

                for change in changes:
                    # 变更本身由 _on_change 处理并打印
                    self.change_signal.emit(change)
                    if self.client.auto_add_enable and change.get("has_vacancy"):
                        self.log_signal.emit(
                            f"检测到空位，尝试自动选课: {change['info'].get('KCM', '')}",
                            "WARNING"
                        )
                        ok, msg = self.client.add_course(
                            KCH=change["KCH"],
                            clazzId=change["JXBID"],
                            clazzType=change["info"]["clazzType"]
                        )
                        # vacancy_signal 会在 _on_vacancy 里继续打印成功/失败
                        self.vacancy_signal.emit(change, ok, msg)

                self.client.save()
            except Exception as e:
                self.log_signal.emit(f"监控循环异常: {e}", "ERROR")
                self.log_signal.emit(traceback.format_exc(), "ERROR")

            # 分段 sleep，便于快速响应 stop
            interval = max(1, int(self.client.check_interval))
            slept = 0
            self.log_signal.emit(f"等待 {interval} 秒后进入下一轮...", "INFO")
            while slept < interval and not self._stop_flag:
                QThread.msleep(200)
                slept += 0.2

        self.status_signal.emit("已停止")


# ====================================================================
# 面板：配置
# ====================================================================

class ConfigPanel(QWidget):
    """账号与验证码配置"""

    config_saved = Signal()   # 配置保存后通知主窗口

    CAMPUS_OPTIONS = [
        ("6", "翔安校区"),
        ("1", "思明校区"),
        ("9", "漳州校区"),
    ]
    CAPTCHA_OPTIONS = [
        ("llm",    "LLM 多模态识别"),
        ("vcode",  "本地 vcode 网络"),
        ("manual", "手动输入"),
    ]

    def __init__(self, config_path: str, parent=None):
        super().__init__(parent)
        self.config_path = Path(config_path)
        self._build_ui()
        self._load_config()

    # ---------- UI 构建 ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("账号与配置")
        title.setObjectName("CardTitle")
        hint = QLabel("配置会保存到 config/user.yaml，登录前请先填写完整。")
        hint.setObjectName("CardHint")
        root.addWidget(title)
        root.addWidget(hint)

        # —— 账号区 ——
        acct_box = QGroupBox("账号信息")
        grid = QGridLayout(acct_box)
        grid.setContentsMargins(14, 18, 14, 14)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("学号")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("密码")
        self.password_edit.setEchoMode(QLineEdit.Password)

        self.campus_combo = QComboBox()
        for code, name in self.CAMPUS_OPTIONS:
            self.campus_combo.addItem(name, code)

        self.auto_add_check = QCheckBox("自动选课（有空位时自动提交）")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 3600)
        self.interval_spin.setSuffix(" 秒")

        grid.addWidget(QLabel("学号"), 0, 0)
        grid.addWidget(self.username_edit, 0, 1, 1, 3)
        grid.addWidget(QLabel("密码"), 1, 0)
        grid.addWidget(self.password_edit, 1, 1, 1, 3)
        grid.addWidget(QLabel("校区"), 2, 0)
        grid.addWidget(self.campus_combo, 2, 1)
        grid.addWidget(QLabel("检查间隔"), 3, 0)
        grid.addWidget(self.interval_spin, 3, 1)
        grid.addWidget(self.auto_add_check, 4, 1, 1, 3)

        root.addWidget(acct_box)

        # —— 验证码区 ——
        cap_box = QGroupBox("验证码识别方式")
        cap_layout = QVBoxLayout(cap_box)
        cap_layout.setContentsMargins(14, 18, 14, 14)
        cap_layout.setSpacing(10)

        cap_row = QHBoxLayout()
        cap_row.addWidget(QLabel("方式"))
        self.captcha_type_combo = QComboBox()
        for code, name in self.CAPTCHA_OPTIONS:
            self.captcha_type_combo.addItem(name, code)
        cap_row.addWidget(self.captcha_type_combo, 1)
        cap_layout.addLayout(cap_row)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://ark.cn-beijing.volces.com/api/v3/chat/completions")
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("API Key（豆包、Qwen 等模型）")
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("doubao-seed-1-6-thinking-250615")

        cap_layout.addWidget(QLabel("Base URL"))
        cap_layout.addWidget(self.base_url_edit)
        cap_layout.addWidget(QLabel("API Key"))
        cap_layout.addWidget(self.api_key_edit)
        cap_layout.addWidget(QLabel("模型名称"))
        cap_layout.addWidget(self.model_edit)

        self.captcha_type_combo.currentIndexChanged.connect(self._refresh_captcha_visibility)
        root.addWidget(cap_box)

        # —— 按钮区 ——
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.save_btn = QPushButton("保存配置")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(self.save_btn)
        root.addLayout(btn_row)
        root.addStretch(1)

        self._refresh_captcha_visibility()

    def _refresh_captcha_visibility(self):
        need_llm = self.captcha_type_combo.currentData() == "llm"
        for w in (self.base_url_edit, self.api_key_edit, self.model_edit):
            w.setEnabled(need_llm)

    # ---------- 配置 IO ----------

    def _load_config(self):
        if not self.config_path.exists():
            return
        try:
            import yaml
            with open(self.config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"读取配置失败: {e}")
            return

        self.username_edit.setText(cfg.get("username", "") or "")
        self.password_edit.setText(cfg.get("password", "") or "")

        campus = str(cfg.get("campus", "6"))
        for i in range(self.campus_combo.count()):
            if self.campus_combo.itemData(i) == campus:
                self.campus_combo.setCurrentIndex(i)
                break

        self.auto_add_check.setChecked(bool(cfg.get("auto_add_enable", False)))
        self.interval_spin.setValue(int(cfg.get("check_interval", 120)))

        cap = cfg.get("captcha", {}) or {}
        ctype = str(cap.get("type", "llm")).lower()
        for i in range(self.captcha_type_combo.count()):
            if self.captcha_type_combo.itemData(i) == ctype:
                self.captcha_type_combo.setCurrentIndex(i)
                break
        self.base_url_edit.setText(cap.get("base_url", "") or "")
        self.api_key_edit.setText(cap.get("api_key", "") or "")
        self.model_edit.setText(cap.get("model", "") or "")

    def _save_config(self):
        cfg = {
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "campus": self.campus_combo.currentData(),
            "auto_add_enable": self.auto_add_check.isChecked(),
            "check_interval": self.interval_spin.value(),
            "captcha": {
                "type": self.captcha_type_combo.currentData(),
                "base_url": self.base_url_edit.text().strip(),
                "api_key": self.api_key_edit.text().strip(),
                "model": self.model_edit.text().strip(),
            }
        }
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            import yaml
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"写入配置失败: {e}")
            return
        self.config_saved.emit()
        QMessageBox.information(self, "已保存", "配置已保存到 config/user.yaml")

    def current_config_dict(self) -> dict:
        """供主窗口构造 XMUClient 时使用"""
        return {
            "username": self.username_edit.text().strip(),
            "password": self.password_edit.text(),
            "campus": self.campus_combo.currentData(),
            "auto_add_enable": self.auto_add_check.isChecked(),
            "check_interval": self.interval_spin.value(),
            "captcha": {
                "type": self.captcha_type_combo.currentData(),
                "base_url": self.base_url_edit.text().strip(),
                "api_key": self.api_key_edit.text().strip(),
                "model": self.model_edit.text().strip(),
            }
        }


# ====================================================================
# 面板：课程搜索
# ====================================================================

class SearchPanel(QWidget):
    """关键词搜索 + 加入监控"""

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("课程搜索")
        title.setObjectName("CardTitle")
        hint = QLabel("输入课程号或关键词，从结果中勾选要监控的教学班。")
        hint.setObjectName("CardHint")
        root.addWidget(title)
        root.addWidget(hint)

        # —— 搜索条 ——
        bar = QHBoxLayout()
        bar.addWidget(QLabel("关键词"))
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("课程号或课程名称关键词")
        self.keyword_edit.returnPressed.connect(self._on_search)
        bar.addWidget(self.keyword_edit, 1)
        self.search_btn = QPushButton("搜索")
        self.search_btn.setObjectName("Primary")
        self.search_btn.clicked.connect(self._on_search)
        bar.addWidget(self.search_btn)
        root.addLayout(bar)

        # —— 结果表 ——
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["选", "课程号", "课程名", "教师", "上课地点", "已选/容量"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 160)
        self.table.setColumnWidth(5, 110)
        root.addWidget(self.table, 1)

        # —— 加入监控 ——
        action_row = QHBoxLayout()
        action_row.addWidget(QLabel("可勾选多行后批量加入监控"))
        action_row.addStretch(1)
        self.add_btn = QPushButton("加入监控")
        self.add_btn.setObjectName("Primary")
        self.add_btn.clicked.connect(self._on_add_watch)
        action_row.addWidget(self.add_btn)
        root.addLayout(action_row)

    # ---------- 交互 ----------

    def _on_search(self):
        kw = self.keyword_edit.text().strip()
        if not kw:
            QMessageBox.information(self, "提示", "请输入关键词")
            return
        client = self.parent_window.get_client()
        if client is None:
            QMessageBox.warning(self, "未就绪", "请先在「配置」面板登录")
            return

        self.search_btn.setEnabled(False)
        self.table.setRowCount(0)

        self._worker = SearchWorker(client, kw)
        self._worker.finished_result.connect(self._on_search_done)
        self._worker.failed.connect(self._on_search_fail)
        self.parent_window.register_worker(self._worker)
        self._worker.start()

    def _on_search_done(self, rows: list):
        self.search_btn.setEnabled(True)
        self.table.setRowCount(len(rows))
        for r, clazz in enumerate(rows):
            check = QCheckBox()
            check_widget = QWidget()
            cw = QHBoxLayout(check_widget)
            cw.addWidget(check)
            cw.setAlignment(Qt.AlignCenter)
            cw.setContentsMargins(6, 0, 6, 0)
            self.table.setCellWidget(r, 0, check_widget)

            self._set_cell(r, 1, str(clazz.get("KCH", "")))
            self._set_cell(r, 2, str(clazz.get("KCM", "")))
            self._set_cell(r, 3, str(clazz.get("SKJS", "")))
            self._set_cell(r, 4, str(clazz.get("teachingPlaceHide", "未知")))
            sel = int(clazz.get("numberOfSelected", 0))
            cap = int(clazz.get("classCapacity", 0))
            cell = QTableWidgetItem(f"{sel} / {cap}")
            if sel < cap:
                cell.setForeground(QColor(COLORS["success"]))
            else:
                cell.setForeground(QColor(COLORS["danger"]))
            self.table.setItem(r, 5, cell)

            # 缓存到行 item 的 data，便于取 KCH/JXBID
            data = {
                "KCH":   str(clazz.get("KCH", "")),
                "JXBID": str(clazz.get("JXBID", "")),
                "KCM":   str(clazz.get("KCM", "")),
            }
            check.setProperty("course_data", data)

    def _set_cell(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        self.table.setItem(row, col, item)

    def _on_search_fail(self, msg: str):
        self.search_btn.setEnabled(True)
        QMessageBox.critical(self, "搜索失败", msg)

    def _on_add_watch(self):
        client = self.parent_window.get_client()
        if client is None:
            QMessageBox.warning(self, "未就绪", "请先登录")
            return
        picked = []
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            if w is None:
                continue
            cb = w.findChild(QCheckBox)
            if cb and cb.isChecked():
                data = cb.property("course_data")
                if data:
                    picked.append(data)
        if not picked:
            QMessageBox.information(self, "提示", "请先勾选要监控的课程")
            return

        # 串行发起 add_watch（共享同一 client，避免并发请求）
        self.add_btn.setEnabled(False)
        self._pending = list(picked)
        self._run_next_add(client)

    def _run_next_add(self, client):
        if not self._pending:
            self.add_btn.setEnabled(True)
            return
        data = self._pending.pop(0)
        worker = AddWatchWorker(client, data["KCH"], data["JXBID"])
        worker.done.connect(lambda ok, msg, k, j: self.parent_window.log(
            f"添加监控 {data['KCM']}（{k}-{j}）: {msg}",
            "INFO" if ok else "WARNING"
        ))
        worker.done.connect(lambda *args: self._run_next_add(client))
        self.parent_window.register_worker(worker)
        worker.start()


# ====================================================================
# 面板：监控列表
# ====================================================================

class WatchListPanel(QWidget):
    """查看 / 删除监控课程"""

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("监控列表")
        title.setObjectName("CardTitle")
        hint = QLabel("右键或勾选复选框删除监控项。")
        hint.setObjectName("CardHint")
        root.addWidget(title)
        root.addWidget(hint)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["选", "课程号", "课程名", "教师", "已选/容量", "空位状态"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_context_menu)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 110)
        self.table.setColumnWidth(5, 110)
        root.addWidget(self.table, 1)

        # 操作栏
        row = QHBoxLayout()
        row.addStretch(1)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh)
        row.addWidget(self.refresh_btn)
        self.delete_btn = QPushButton("删除勾选项")
        self.delete_btn.setObjectName("Danger")
        self.delete_btn.clicked.connect(self._delete_checked)
        row.addWidget(self.delete_btn)
        root.addLayout(row)

    # ---------- 数据 ----------

    def refresh(self):
        client = self.parent_window.get_client()
        if client is None:
            return
        self.table.setRowCount(0)
        idx = 0
        for KCH, jxb_dict in client.watch_list.items():
            for JXBID, info in jxb_dict.items():
                self.table.insertRow(idx)
                # 复选框
                cw = QWidget()
                lay = QHBoxLayout(cw)
                lay.setContentsMargins(0, 0, 0, 0)
                cb = QCheckBox()
                lay.addWidget(cb, alignment=Qt.AlignCenter)
                self.table.setCellWidget(idx, 0, cw)

                meta = info.get("info", {})
                self._set_cell(idx, 1, str(KCH))
                self._set_cell(idx, 2, str(meta.get("KCM", "")))
                self._set_cell(idx, 3, str(meta.get("SKJS", "")))

                sel = info.get("last_selected", 0)
                cap = info.get("capacity", 0)
                item = QTableWidgetItem(f"{sel} / {cap}")
                if sel < cap:
                    item.setForeground(QColor(COLORS["success"]))
                else:
                    item.setForeground(QColor(COLORS["danger"]))
                self.table.setItem(idx, 4, item)

                # 空位徽章
                badge = make_badge(
                    "有空位" if sel < cap else "已满",
                    "Success" if sel < cap else "Danger"
                )
                badge.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(idx, 5, badge)

                idx += 1

    def _set_cell(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setToolTip(text)
        self.table.setItem(row, col, item)

    def _on_context_menu(self, pos):
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu(self)
        act_del = QAction("删除此监控", self)
        act_del.triggered.connect(lambda: self._delete_rows([idx.row()]))
        menu.addAction(act_del)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _delete_checked(self):
        client = self.parent_window.get_client()
        if client is None:
            return
        rows_to_delete = []
        for r in range(self.table.rowCount()):
            w = self.table.cellWidget(r, 0)
            if w is None:
                continue
            cb = w.findChild(QCheckBox)
            if cb and cb.isChecked():
                rows_to_delete.append(r)
        if not rows_to_delete:
            QMessageBox.information(self, "提示", "请先勾选要删除的项")
            return
        self._delete_rows(rows_to_delete)

    def _delete_rows(self, rows: list):
        client = self.parent_window.get_client()
        if client is None:
            return
        # 通过 (KCH, JXBID) 定位
        targets = []
        for r in rows:
            kch_item = self.table.item(r, 1)
            if not kch_item:
                continue
            kch = kch_item.text()
            # 从 client 里找对应 JXBID
            for KCH, jxb_dict in client.watch_list.items():
                if KCH == kch:
                    # 这里 r 对应表里第几行也是这个 JXBID，需要按顺序匹配
                    pass
            # 因为一个 KCH 可能有多个 JXBID，需要按表行顺序对应到 JXBID
            # 简化：把当前行第 3 列的教师作为参考，遍历 client 找对应 JXBID
        # 用更简单方法：根据选中的行号按 client 中的顺序取
        all_keys = []  # [(KCH, JXBID), ...]
        for KCH, jxb_dict in client.watch_list.items():
            for JXBID in jxb_dict.keys():
                all_keys.append((KCH, JXBID))
        for r in sorted(rows, reverse=True):
            if 0 <= r < len(all_keys):
                KCH, JXBID = all_keys[r]
                jxb_dict = client.watch_list.get(KCH, {})
                if JXBID in jxb_dict:
                    course_name = jxb_dict[JXBID]['info']['KCM']
                    del jxb_dict[JXBID]
                    if not jxb_dict:
                        del client.watch_list[KCH]
                    self.parent_window.log(
                        f"已删除监控: {course_name}（{KCH}-{JXBID}）", "INFO"
                    )
        client.save()
        self.refresh()


# ====================================================================
# 面板：运行监控
# ====================================================================

class MonitorPanel(QWidget):
    """启动 / 停止 监控 + 实时日志"""

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.worker: Optional[MonitorWorker] = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        title = QLabel("监控运行")
        title.setObjectName("CardTitle")
        hint = QLabel("点击开始后，后台会按检查间隔轮询空位。可随时停止。")
        hint.setObjectName("CardHint")
        root.addWidget(title)
        root.addWidget(hint)

        # —— 控制条 ——
        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("开始监控")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn = QPushButton("停止")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        ctrl.addWidget(self.start_btn)
        ctrl.addWidget(self.stop_btn)
        ctrl.addSpacing(20)
        self.status_badge = make_badge("未启动", "Muted")
        ctrl.addWidget(self.status_badge)
        ctrl.addStretch(1)
        self.round_label = QLabel("第 0 轮")
        ctrl.addWidget(self.round_label)
        root.addLayout(ctrl)

        # —— 日志 ——
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        root.addWidget(self.log_view, 1)

        # —— 变更提示 ——
        self.event_label = QLabel("最近变更：—")
        self.event_label.setObjectName("CardHint")
        root.addWidget(self.event_label)

    # ---------- 交互 ----------

    def _on_start(self):
        client = self.parent_window.get_client()
        if client is None:
            QMessageBox.warning(self, "未就绪", "请先登录")
            return
        if not client.watch_list:
            QMessageBox.information(self, "提示", "监控列表为空，请先在「课程搜索」加入监控")
            return
        if self.worker and self.worker.isRunning():
            return

        self.worker = MonitorWorker(client)
        self.worker.log_signal.connect(self.parent_window.log)
        self.worker.round_signal.connect(self._on_round)
        self.worker.change_signal.connect(self._on_change)
        self.worker.vacancy_signal.connect(self._on_vacancy)
        self.worker.status_signal.connect(self._on_status)
        self.parent_window.register_worker(self.worker)
        self.worker.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _on_stop(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)

    def _on_status(self, text: str):
        level = "Success" if "运行" in text else ("Danger" if "停止" in text else "Muted")
        self.status_badge.setText(text)
        self.status_badge.setObjectName(f"Badge{level}")
        self.status_badge.style().unpolish(self.status_badge)
        self.status_badge.style().polish(self.status_badge)
        if "停止" in text:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _on_round(self, round_num: int, change_count: int):
        self.round_label.setText(f"第 {round_num} 轮 · {change_count} 个变化")

    def _on_change(self, c: dict):
        direction = "减少" if c["new"] < c["old"] else "增加"
        msg = (f"变更 {c['info']['KCM']}（{c['KCH']}）：{c['old']}→{c['new']} / {c['capacity']}"
               f"（{direction}）")
        self.event_label.setText(f"最近变更：{msg}")
        self.parent_window.log(msg, "WARNING" if c.get("has_vacancy") else "INFO")

    def _on_vacancy(self, c: dict, ok: bool, msg: str):
        if ok:
            self.parent_window.log(f"【自动选课成功】{c['info']['KCM']}", "INFO")
        else:
            self.parent_window.log(f"【自动选课失败】{c['info']['KCM']} 原因: {msg}", "ERROR")


# ====================================================================
# 主窗口
# ====================================================================

class MainWindow(QMainWindow):
    """主窗口：侧边栏导航 + 堆栈内容"""

    NAV_CONFIG   = 0
    NAV_SEARCH   = 1
    NAV_WATCH    = 2
    NAV_MONITOR  = 3

    def __init__(self):
        super().__init__()
        self.setWindowTitle("XMU 选课助手")
        self.resize(1080, 720)
        self.setMinimumSize(900, 600)

        # 客户端与工作线程
        self.client: Optional[XMUClient] = None
        self._workers = []

        # 日志 sink：Qt 信号转发
        class _Sink(QObject):
            log_signal = Signal(str, str)
        self._log_sink = _Sink()
        self._log_sink.log_signal.connect(self._append_log)

        # 安装 Qt 日志桥
        self._qt_handler = _QtLogHandler(self._log_sink)
        self._qt_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(self._qt_handler)

        self._build_ui()
        self._build_statusbar()
        self._apply_theme()

        # 状态轮询：每隔 1 秒刷新登录状态徽章
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_login_status)
        self._poll_timer.start()

    # ---------- UI ----------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 侧边栏
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        title = QLabel("XMU 选课助手")
        title.setObjectName("SidebarTitle")
        subtitle = QLabel("Xiamen University Course Helper")
        subtitle.setObjectName("SidebarSubtitle")
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        for icon, name in [
            ("⚙", "配置"), ("🔍", "课程搜索"), ("📋", "监控列表"), ("▶", "运行监控")
        ]:
            item = QListWidgetItem(f"  {icon}  {name}")
            item.setSizeHint(QSize(0, 40))
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(self.NAV_CONFIG)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        side_layout.addWidget(self.nav_list, 1)

        # 登录状态徽章
        self.login_badge = make_badge("● 未登录", "Danger")
        self.login_badge.setContentsMargins(20, 8, 20, 8)
        sb_row = QHBoxLayout()
        sb_row.setContentsMargins(20, 8, 20, 12)
        sb_row.addWidget(self.login_badge)
        side_layout.addLayout(sb_row)

        layout.addWidget(sidebar)

        # 内容区
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.config_panel = ConfigPanel("config/user.yaml")
        self.config_panel.config_saved.connect(self._on_config_saved)
        self.search_panel = SearchPanel(self)
        self.watch_panel  = WatchListPanel(self)
        self.monitor_panel = MonitorPanel(self)

        self.stack.addWidget(self.config_panel)
        self.stack.addWidget(self.search_panel)
        self.stack.addWidget(self.watch_panel)
        self.stack.addWidget(self.monitor_panel)

    def _build_statusbar(self):
        bar = self.statusBar()
        self.status_msg = QLabel("准备就绪")
        bar.addWidget(self.status_msg, 1)
        self.worker_count = QLabel("0")
        bar.addPermanentWidget(QLabel("活动任务:"))
        bar.addPermanentWidget(self.worker_count)

    def _apply_theme(self):
        self.setStyleSheet(QSS)

    # ---------- 导航 ----------

    def _on_nav_changed(self, row: int):
        self.stack.setCurrentIndex(row)
        if row == self.NAV_WATCH:
            self.watch_panel.refresh()

    # ---------- 客户端管理 ----------

    def _on_config_saved(self):
        """配置保存后构造/重建客户端，并尝试自动登录"""
        cfg = self.config_panel.current_config_dict()
        try:
            self.client = XMUClient(
                username=cfg["username"],
                password=cfg["password"],
                campus=cfg["campus"],
                config_captcha=cfg["captcha"],
                auto_add_enable=cfg["auto_add_enable"],
                check_interval=cfg["check_interval"],
            )
            # 尝试从缓存载入登录态
            self.client.load()
            self.status_msg.setText("配置已加载，尝试恢复登录态...")
            self._login_worker = LoginWorker(self.client)
            self._login_worker.success.connect(self._on_login_done)
            self.register_worker(self._login_worker)
            self._login_worker.start()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"构造客户端失败: {e}")

    def _on_login_done(self, ok: bool, msg: str):
        self.log(f"登录结果：{msg}", "INFO" if ok else "ERROR")
        self.status_msg.setText(msg)

    def get_client(self) -> Optional[XMUClient]:
        if self.client is None:
            # 尝试自动从配置文件构造
            cfg_path = Path("config/user.yaml")
            if cfg_path.exists():
                try:
                    import yaml
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    self.client = XMUClient(
                        username=cfg["username"],
                        password=cfg["password"],
                        campus=cfg.get("campus", "6"),
                        config_captcha=cfg.get("captcha", {}),
                        auto_add_enable=cfg.get("auto_add_enable", False),
                        check_interval=cfg.get("check_interval", 120),
                    )
                    self.client.load()
                except Exception:
                    return None
        return self.client

    # ---------- 工作线程管理 ----------

    def register_worker(self, worker: QThread):
        self._workers.append(worker)
        worker.finished.connect(lambda: self._on_worker_finished(worker))
        self.worker_count.setText(str(sum(1 for w in self._workers if w.isRunning())))

    def _on_worker_finished(self, worker: QThread):
        if worker in self._workers:
            self._workers.remove(worker)
        self.worker_count.setText(str(sum(1 for w in self._workers if w.isRunning())))

    # ---------- 日志 ----------

    def log(self, msg: str, level: str = "INFO"):
        """主线程接口：直接写入日志区"""
        color = {
            "INFO":     "#E6E6E8",
            "WARNING":  "#FFD27A",
            "ERROR":    "#FF8080",
            "DEBUG":    "#9AA0A6",
        }.get(level, "#E6E6E8")
        # 转义 <>&
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.monitor_panel.log_view.appendHtml(
            f'<span style="color:#9AA0A6">[{ts}]</span> '
            f'<span style="color:{color}">[{level}]</span> {safe}'
        )
        self.monitor_panel.log_view.verticalScrollBar().setValue(
            self.monitor_panel.log_view.verticalScrollBar().maximum()
        )

    def _append_log(self, msg: str, level: str):
        """logging.Handler 转发入口"""
        self.log(msg, level)

    # ---------- 状态轮询 ----------

    def _poll_login_status(self):
        """轻量地根据 client.token 刷新徽章，不发起网络请求"""
        if self.client and self.client.token and self.client.batch_id:
            self.login_badge.setText("已登录")
            self.login_badge.setObjectName("BadgeSuccess")
        else:
            self.login_badge.setText("未登录")
            self.login_badge.setObjectName("BadgeDanger")
        # 重新应用样式
        self.login_badge.style().unpolish(self.login_badge)
        self.login_badge.style().polish(self.login_badge)

    # ---------- 关闭事件 ----------

    def closeEvent(self, event):
        # 停止监控线程
        if self.monitor_panel.worker:
            self.monitor_panel.worker.stop()
            self.monitor_panel.worker.wait(2000)
        # 关闭客户端 session
        if self.client:
            try:
                self.client.session.close()
            except Exception:
                pass
        event.accept()


# ====================================================================
# 入口
# ====================================================================

def main():
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("XMUCourseHelper")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
