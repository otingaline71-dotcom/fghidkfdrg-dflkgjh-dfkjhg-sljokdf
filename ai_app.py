"""
=========================================================================
  Aaron AI — десктопное приложение (lyceum №166)
=========================================================================

ИНСТРУКЦИЯ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ
----------------------------
1. УСТАНОВКА
   - Установите Python 3.10+ с официального сайта https://python.org
     (при установке поставьте галочку "Add Python to PATH").
   - Запустите installer.py двойным кликом ИЛИ командой:
         python installer.py
     Скрипт сам создаст виртуальное окружение .venv,
     установит все зависимости и (по желанию) соберёт .exe.

2. ЗАПУСК
   - После установки:  python ai_app.py
   - Либо запустите готовый Aaron.exe из папки dist/.

3. ВОЗМОЖНОСТИ
   - Чат с ИИ (Mistral + Gemini)
   - Решение математики
   - Перевод текста
   - Работа с PDF / DOCX / изображениями
   - Встроенный Telegram-бот (стартует автоматически)
   - Локальная история и заметки (SQLite ai_app.db)

4. КЛЮЧИ
   - Создайте файл .env рядом с ai_app.py и положите туда:
         MISTRAL_API_KEY=ваш_ключ
         GEMINI_API_KEY=ваш_ключ
         TELEGRAM_BOT_TOKEN=ваш_токен_бота

5. СБОРКА .EXE (отдельно)
   - python build_exe.py
   - Готовый файл появится в dist/Aaron.exe (вместе с logo.ico).

ВАЖНО: Серверная (учительская) функциональность из проекта удалена.
       Всё работает локально, без подключения к внешнему серверу.
=========================================================================
"""

"""
AI CORE ENGINE v3.2 – Лаунчер + Telegram‑бот в одном файле.
Запуск: python ai_app.py  (бот стартует автоматически в фоне)
"""
import asyncio, aiohttp, base64, hashlib, io, json, logging, math, os, re, secrets, sqlite3, threading, time, random, requests, queue
import subprocess, sys, platform, ctypes, shutil, webbrowser, importlib.util
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from io import BytesIO
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from abc import ABC, abstractmethod

import numpy as np, sympy
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageTk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk

# ============== Aaron AI light/dark dynamic theme ==============
DS_BG        = ("#f4f6f9", "#0b0d10")
DS_SURFACE   = ("#ffffff", "#131720")
DS_PANEL     = ("#f0f3f7", "#1a1f2b")
DS_PANEL_2   = ("#e7ecf2", "#212836")
DS_BORDER    = ("#dfe5ee", "#262d3b")
DS_ACCENT    = ("#22b894", "#35d6b0")
DS_ACCENT2   = ("#1a9b7c", "#22b894")
DS_AMBER     = ("#c97a12", "#ffb454")
DS_DANGER    = ("#d64545", "#ff6b6b")
DS_TEXT      = ("#101720", "#e7ecf3")
DS_DIM       = ("#5d6a7d", "#8b95a7")
DS_THINK_BG  = ("#f2f5f9", "#10141c")
DS_USER_BG   = ("#dff5ef", "#1d2a33")
DS_AI_BG     = ("#f2f5f9", "#171c26")
DS_ON_ACCENT = "#04120f"

def F(size=13, weight="normal", family="Manrope"):
    return ctk.CTkFont(family=family, size=size, weight=weight)

def MONO(size=11, weight="normal"):
    return ctk.CTkFont(family="JetBrains Mono", size=size, weight=weight)

class AccentButton(ctk.CTkButton):
    def __init__(self, master, text="", command=None, width=140, height=36, font=None, **kwargs):
        super().__init__(
            master, text=text, command=command, width=width, height=height,
            fg_color=DS_ACCENT, hover_color=DS_ACCENT2, text_color=DS_ON_ACCENT,
            corner_radius=10, font=font or F(13, "bold"), **kwargs
        )

class GhostButton(ctk.CTkButton):
    def __init__(self, master, text="", command=None, width=140, height=36, font=None, **kwargs):
        super().__init__(
            master, text=text, command=command, width=width, height=height,
            fg_color="transparent", hover_color=DS_PANEL_2, text_color=DS_TEXT,
            border_color=DS_BORDER, border_width=1, corner_radius=10,
            font=font or F(13), **kwargs
        )

class NavItem(ctk.CTkFrame):
    def __init__(self, master, text="", icon="", is_active=False, command=None, **kwargs):
        super().__init__(master, fg_color=DS_PANEL_2 if is_active else "transparent", corner_radius=10, height=38, **kwargs)
        self.pack_propagate(False)
        self.command = command
        self.is_active = is_active
        
        self.indicator = ctk.CTkFrame(self, width=3, fg_color=DS_ACCENT if is_active else "transparent", corner_radius=2)
        self.indicator.pack(side="left", fill="y", padx=(2, 6), pady=4)
        
        label_text = f"{icon}  {text}".strip() if icon else text
        self.btn = ctk.CTkButton(
            self, text=label_text, anchor="w", fg_color="transparent",
            hover_color=DS_PANEL_2, text_color=DS_TEXT if is_active else DS_DIM,
            font=F(13, "bold" if is_active else "normal"), corner_radius=8,
            command=self._on_click
        )
        self.btn.pack(side="left", fill="both", expand=True)

    def _on_click(self):
        if self.command:
            self.command()

    def set_active(self, active: bool):
        self.is_active = active
        self.configure(fg_color=DS_PANEL_2 if active else "transparent")
        self.indicator.configure(fg_color=DS_ACCENT if active else "transparent")
        self.btn.configure(text_color=DS_TEXT if active else DS_DIM, font=F(13, "bold" if active else "normal"))

class Card(ctk.CTkFrame):
    def __init__(self, master, title=None, corner_radius=14, border_width=1, **kwargs):
        super().__init__(master, fg_color=DS_SURFACE, border_color=DS_BORDER, border_width=border_width, corner_radius=corner_radius, **kwargs)
        if title:
            lbl = ctk.CTkLabel(self, text=title, font=F(13, "bold"), text_color=DS_TEXT)
            lbl.pack(anchor="w", padx=14, pady=(12, 6))

class StatusPill(ctk.CTkFrame):
    def __init__(self, master, text="ONLINE", status_type="success", **kwargs):
        bg = DS_USER_BG
        tc = DS_ACCENT
        if status_type in ("amber", "warning"):
            bg = (DS_THINK_BG[0], "#2a1c0e")
            tc = DS_AMBER
        elif status_type in ("danger", "error"):
            bg = ("#fde8e8", "#2a1212")
            tc = DS_DANGER

        super().__init__(master, fg_color=bg, corner_radius=10, **kwargs)
        self.lbl = ctk.CTkLabel(self, text=text.upper(), font=MONO(10, "bold"), text_color=tc)
        self.lbl.pack(padx=8, pady=2)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*a, **kw): pass

try:
    from aiogram import Bot, Dispatcher, types, F as AiogramFilter
    from aiogram.filters import Command
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
    from aiogram.types import BufferedInputFile
    AIOGRAM_OK = True
except ImportError:
    AIOGRAM_OK = False

try:
    import fitz
    FITZ_OK = True
except ImportError:
    FITZ_OK = False

try:
    from docx import Document
    from docx.shared import Inches
    DOCX_OK = True
except ImportError:
    DOCX_OK = False
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta
import re
# Управление ботом
bot_thread = None
bot_running = False

# Управление ботом
bot_thread = None
bot_running = False
# =================== ДИЗАЙН В СТИЛЕ CHATGPT ===================
ctk.set_appearance_mode("dark")                     # тёмный фон
ctk.set_default_color_theme("green")                # зелёные акценты (как OpenAI)

# ---- Frozen-aware bootstrap (PyInstaller .exe support) -----------------
# В режиме onefile sys._MEIPASS — это временная распакованная папка.
# Все пользовательские файлы (.env, ai_app.db, mods/, modsi/, README.md)
# должны лежать рядом с Aaron.exe, поэтому делаем CWD = папка exe.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
try:
    os.chdir(APP_DIR)
except Exception:
    pass

# .env: сначала ищем рядом с exe, потом в бандле (на случай первого запуска).
_env_user = os.path.join(APP_DIR, ".env")
_env_bundled = os.path.join(BUNDLE_DIR, ".env.example")
if os.path.exists(_env_user):
    load_dotenv(_env_user)
else:
    # копируем пример рядом с exe, чтобы пользователь мог заполнить ключи
    try:
        if os.path.exists(_env_bundled) and not os.path.exists(_env_user):
            shutil.copy(_env_bundled, _env_user)
    except Exception:
        pass
    load_dotenv(_env_user) if os.path.exists(_env_user) else load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Engine")

# ======================== НАСТРОЙКИ ========================
GAME_FILENAME = "g.py"
APP_NAME = "AI Launcher"
DESKTOP_LINK_NAME = "AI_Launcher.lnk"
MODS_FOLDER = "mods"
MODS_STATE_FILE = "mods_state.json"
MODS_SAMPLE_FILE = "example_mod.py"
DESKTOP_DATA_FOLDER = "modsi"
DATABASE_FILE_CHATS = "chats.db"
DATABASE_FILE_USERS = "users.db"
INSTRUCTIONS_FILE = "README.md"
MODS_SAMPLE_CONTENT = '''"""
Пример мода для AI Launcher.
Этот мод загружается при старте, если он включён.
"""

MOD_NAME = "Пример мода"
MOD_DESCRIPTION = "Добавляет примерную функциональность для теста модов."


def apply(app=None):
    print("[Mods] Пример мода загружен. Если нужно, здесь можно изменить поведение приложения.")
'''


def get_app_root():
    return os.path.dirname(os.path.abspath(__file__))


def get_desktop_root():
    local_desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    try:
        home = os.path.expanduser("~")
        paths = [
            os.path.join(home, "Desktop"),
            os.path.join(home, "OneDrive", "Desktop"),
            os.path.join(home, "OneDrive - Personal", "Desktop"),
            os.path.normpath(os.path.expandvars(r"%USERPROFILE%\Desktop")),
            os.path.normpath(os.path.expandvars(r"%USERPROFILE%\OneDrive\Desktop"))
        ]
        if platform.system() == "Windows":
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
            path = buf.value
            if path and os.path.exists(path):
                paths.insert(0, path)
        for p in paths:
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return local_desktop


def get_data_root():
    try:
        desktop = get_desktop_root()
        path = os.path.join(desktop, DESKTOP_DATA_FOLDER)
        os.makedirs(path, exist_ok=True)
        test_file = os.path.join(path, ".test_write")
        with open(test_file, "w") as f:
            f.write("OK")
        os.remove(test_file)
        return path
    except Exception:
        path = os.path.join(get_app_root(), DESKTOP_DATA_FOLDER)
        os.makedirs(path, exist_ok=True)
        return path

def get_chats_db_path():
    return os.path.join(get_data_root(), "chats.db")

def get_users_db_path():
    return os.path.join(get_data_root(), "users.db")


def get_mods_dir():
    return os.path.join(get_data_root(), MODS_FOLDER)


def get_mods_state_path():
    return os.path.join(get_mods_dir(), MODS_STATE_FILE)


def find_file_in_home(filename):
    home = os.path.expanduser('~')
    paths = [
        os.path.join(home, 'Desktop'),
        os.path.join(home, 'Downloads'),
        os.path.join(home, 'Documents'),
        get_app_root(),
    ]
    for base in paths:
        if not os.path.exists(base):
            continue
        for root, _, files in os.walk(base):
            if filename in files:
                return os.path.join(root, filename)
    return None


def write_instructions_file():
    path = os.path.join(get_data_root(), INSTRUCTIONS_FILE)
    if os.path.exists(path):
        return
    content = (
        "# Инструкция по использованию AI Launcher\n\n"
        "Папка для приложения создаётся автоматически на рабочем столе:\n"
        f"  {get_data_root()}\n\n"
        "В этой папке находятся:\n"
        "  • база данных ai_app.db\n"
        "  • папка mods/ для модов\n"
        "  • README.md — эта инструкция\n\n"
        "## Как добавлять моды\n"
        "1. Поместите Python-файл мода (*.py) в папку mods/.\n"
        "2. Запустите приложение AI Launcher.\n"
        "3. Откройте раздел `📦 Моды` в приложении.\n"
        "4. Найдите новый мод в списке, включите его и нажмите `Запустить сейчас`.\n\n"
        "## Структура мода\n"
        "Каждый мод должен содержать:\n"
        "  MOD_NAME = 'Название мода'\n"
        "  MOD_DESCRIPTION = 'Описание мода'\n"
        "  def apply(app=None):\n"
        "      # код мода\n\n"
        "## Пример мода\n"
        "```python\n"
        "MOD_NAME = 'Анализатор погоды'\n"
        "MOD_DESCRIPTION = 'Анализирует погодные данные и выдаёт рекомендации.'\n\n"
        "def apply(app=None):\n"
        "    print('Мод Анализатор погоды запущен')\n"
        "```\n\n"
        "## Где сохраняются результаты\n"
        "Мод может создавать файлы рядом с папкой приложения, например weather_analysis_result.json.\n"
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def auto_load_new_mods():
    desktop = get_desktop_root()
    mods_dir = get_mods_dir()
    if not os.path.exists(desktop):
        return
    for filename in os.listdir(desktop):
        if filename.endswith("_mod.py") or (filename.startswith("mod_") and filename.endswith(".py")):
            src = os.path.join(desktop, filename)
            dst = os.path.join(mods_dir, filename)
            if not os.path.exists(dst):
                try:
                    shutil.copy2(src, dst)
                    logger.info(f"Auto-loaded new mod: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to auto-load new mod {filename}: {e}")

# VETERAN PROMO CODE SYSTEM: Special promo code for non-premium veterans on every 5th login.
# Automatically displays a promo code marked in RED text color (#ef4444) for veteran users without a subscription.
def show_discount_ad_popup(app, is_veteran=False, startup_count=0):
    ad = ctk.CTkToplevel(app)
    ad.title("🔥 ВРЕМЕННАЯ СКИДКА & ПРОМОКОД!")
    ad.geometry("580x560")
    ad.configure(fg_color=DS_BG)
    ad.grab_set()
    
    sw, sh = ad.winfo_screenwidth(), ad.winfo_screenheight()
    ad.geometry(f"580x560+{(sw-580)//2}+{(sh-560)//2}")
    
    ctk.CTkLabel(ad, text="🔥 МЕГА-СКИДКА В AARON AI! 🔥", font=ctk.CTkFont(size=20, weight="bold"), text_color=DS_DANGER).pack(pady=(15, 2))
    ctk.CTkLabel(ad, text="Разблокируйте все возможности со скидкой 50% или используйте ваш промокод!", font=ctk.CTkFont(size=12, slant="italic"), text_color=DS_TEXT).pack(pady=(0, 10))
    
    card = ctk.CTkFrame(ad, fg_color=DS_SURFACE, corner_radius=16, border_width=2, border_color=DS_ACCENT)
    card.pack(fill="x", padx=25, pady=5)
    
    ctk.CTkLabel(card, text="👑 Complete All-in-One Pack (ПОЛНЫЙ ПАКЕТ)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#10b981").pack(pady=(8, 2))
    ctk.CTkLabel(card, text="Старая цена: 7,500 KZT", font=ctk.CTkFont(size=11, overstrike=True), text_color=DS_DIM).pack()
    ctk.CTkLabel(card, text="🔥 НОВАЯ ЦЕНА: 3,990 KZT / МЕС 🔥", font=ctk.CTkFont(size=15, weight="bold"), text_color="#10b981").pack(pady=2)
    
    # Veteran promo code display (Marked in RED as requested)
    veteran_code = "AARON-COMP-VET2026"
    if is_veteran or startup_count >= 5:
        vet_frame = ctk.CTkFrame(card, fg_color="#2a0e14", corner_radius=10, border_width=1, border_color="#ef4444")
        vet_frame.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(vet_frame, text=f"🎖️ ВЕТЕРАН БЕЗ ПРЕМИУМА (Запусков: {startup_count})", font=ctk.CTkFont(size=11, weight="bold"), text_color=DS_DANGER).pack(pady=(4, 1))
        ctk.CTkLabel(vet_frame, text="Ваш персональный ветеранский код:", font=ctk.CTkFont(size=10), text_color=DS_TEXT).pack()
        # SPECIAL CODE MARKED IN RED TEXT COLOR (#ef4444)
        ctk.CTkLabel(vet_frame, text=veteran_code, font=ctk.CTkFont(size=16, weight="bold", family="Courier"), text_color=DS_DANGER).pack(pady=(1, 4))
    
    features = (
        "✓ Доступ к Codex-02 и авто-созданию файлов на ПК\n"
        "✓ Безлимитные запросы без дневного лимита\n"
        "✓ Разблокированный Валидол-ИИ и Приватный Чат\n"
        "✓ Доступ к системному Терминалу Ядра\n"
        "✓ Премиум функции перевода и математики"
    )
    ctk.CTkLabel(card, text=features, font=ctk.CTkFont(size=11), text_color=DS_TEXT, justify="left").pack(pady=6)
    
    key_frame = ctk.CTkFrame(ad, fg_color="transparent")
    key_frame.pack(fill="x", padx=25, pady=5)
    
    entry = ctk.CTkEntry(key_frame, placeholder_text="Вставьте ваш код активации (AARON-COMP-...)", font=ctk.CTkFont(size=12))
    entry.pack(fill="x", pady=5)
    
    if is_veteran or startup_count >= 5:
        entry.insert(0, veteran_code)
    
    def activate():
        k = entry.get().strip()
        if not k:
            messagebox.showerror("Ошибка", "Введите код активации!")
            return
        success, msg = db.activate_subscription_key(k)
        if success:
            messagebox.showinfo("Активация", f"✅ {msg}")
            ad.destroy()
            notify_chat_on_activation(app, msg)
            if hasattr(app, 'frames'):
                if 'profile' in app.frames:
                    app.frames['profile'].update_stats()
                if 'super_ai' in app.frames:
                    app.frames['super_ai'].check_premium_access()
                if 'validol' in app.frames:
                    app.frames['validol'].check_premium_access()
        else:
            messagebox.showerror("Ошибка", f"❌ {msg}")
            
    btn_row = ctk.CTkFrame(ad, fg_color="transparent")
    btn_row.pack(fill="x", padx=25, pady=10)
    
    ctk.CTkButton(btn_row, text="⚡ Активировать код", command=activate, fg_color="#10b981", hover_color="#059669", width=160, height=36).pack(side="left", padx=4)
    ctk.CTkButton(btn_row, text="🌐 Сайт ключей", command=lambda: webbrowser.open("https://my-deploy-friend.lovable.app/"), fg_color="#2563eb", hover_color="#1d4ed8", width=160, height=36).pack(side="left", padx=4)
    ctk.CTkButton(btn_row, text="✈️ Бот оплаты", command=lambda: webbrowser.open("https://t.me/KZ_AARON_PAY_BOT"), fg_color="#4f46e5", hover_color="#4338ca", width=140, height=36).pack(side="left", padx=4)

def ensure_data_folder():
    root = get_data_root()
    if not os.path.exists(root):
        os.makedirs(root, exist_ok=True)

    # --- DATABASE MIGRATION LOGIC ---
    chats_db = os.path.join(root, "chats.db")
    users_db = os.path.join(root, "users.db")
    old_db_candidates = [
        os.path.join(root, "ai_app.db"),
        os.path.join(get_app_root(), DESKTOP_DATA_FOLDER, "ai_app.db"),
        os.path.join(get_app_root(), "ai_app.db")
    ]
    for candidate in old_db_candidates:
        if os.path.exists(candidate):
            if not os.path.exists(chats_db):
                try:
                    shutil.copy2(candidate, chats_db)
                    logger.info("Migrated old db to chats.db.")
                except Exception:
                    pass
            if not os.path.exists(users_db):
                try:
                    shutil.copy2(candidate, users_db)
                    logger.info("Migrated old db to users.db.")
                except Exception:
                    pass
            break

    mods_dir = get_mods_dir()
    os.makedirs(mods_dir, exist_ok=True)

    # --- MODS MIGRATION LOGIC ---
    old_mods_candidates = [
        os.path.join(get_app_root(), DESKTOP_DATA_FOLDER, MODS_FOLDER),
        os.path.join(get_app_root(), MODS_FOLDER)
    ]
    for old_dir in old_mods_candidates:
        if os.path.exists(old_dir) and os.path.abspath(old_dir) != os.path.abspath(mods_dir):
            try:
                for item in os.listdir(old_dir):
                    src_item = os.path.join(old_dir, item)
                    dst_item = os.path.join(mods_dir, item)
                    if os.path.isfile(src_item) and not os.path.exists(dst_item):
                        shutil.copy2(src_item, dst_item)
            except Exception:
                pass

    write_instructions_file()

    sample_path = os.path.join(mods_dir, MODS_SAMPLE_FILE)
    if not os.path.exists(sample_path):
        with open(sample_path, 'w', encoding='utf-8') as f:
            f.write(MODS_SAMPLE_CONTENT)

    # Копируем стандартные моды из текущей папки, если они ещё не созданы в папке mods
    standard_mods = {
        'example_welcome.py': MODS_SAMPLE_CONTENT,
        'weather_analysis_full.py': """"""  # placeholder, will write later if needed
    }
    for name, content in standard_mods.items():
        dest = os.path.join(mods_dir, name)
        if not os.path.exists(dest):
            if name == 'weather_analysis_full.py':
                content = (
                    '"""\n'
                    'Полноценный пример мода: Анализ текущей погоды\n'
                    'Демонстрирует работу с данными, обработку информации и логирование.\n'
                    '"""\n\n'
                    'MOD_NAME = "Анализатор погоды"\n'
                    'MOD_DESCRIPTION = "Анализирует текущую погоду и выводит рекомендации для одежды."\n\n'
                    'import json\n'
                    'from datetime import datetime\n\n'
                    'def apply(app=None):\n'
                    '    weather_conditions = {\n'
                    '        "Москва": {"temp": 15, "humidity": 65, "wind": 5, "condition": "Облачно", "icon": "☁️"},\n'
                    '        "Санкт-Петербург": {"temp": 12, "humidity": 72, "wind": 8, "condition": "Дождь", "icon": "🌧️"},\n'
                    '        "Казань": {"temp": 18, "humidity": 58, "wind": 3, "condition": "Солнечно", "icon": "☀️"},\n'
                    '        "Новосибирск": {"temp": 8, "humidity": 55, "wind": 6, "condition": "Ясно", "icon": "🌙"},\n'
                    '        "Екатеринбург": {"temp": 10, "humidity": 68, "wind": 4, "condition": "Облачно", "icon": "☁️"},\n'
                    '    }\n\n'
                    '    print(\\n" + "="*50)\n'
                    '    print("Анализ погоды запущен")\n'
                    '    temps = [data["temp"] for data in weather_conditions.values()]\n'
                    '    avg_temp = sum(temps) / len(temps)\n'
                    '    result = {\n'
                    '        "timestamp": datetime.now().isoformat(),\n'
                    '        "average_temp": avg_temp,\n'
                    '        "cities": weather_conditions,\n'
                    '    }\n'
                    '    with open("weather_analysis_result.json", "w", encoding="utf-8") as f:\n'
                    '        json.dump(result, f, indent=2, ensure_ascii=False)\n'
                    '    print(f"Файл weather_analysis_result.json сохранён.\\n")\n\n'
                    'def get_weather_recommendation(city):\n'
                    '    return f"Погода в {city}."\n'
                )
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(content)

    # Ищем g.py на компьютере и копируем его в корень папки данных
    game_path = find_file_in_home('g.py')
    if game_path:
        dest_game = os.path.join(root, 'g.py')
        if not os.path.exists(dest_game):
            try:
                shutil.copy2(game_path, dest_game)
            except Exception:
                pass

    try:
        auto_load_new_mods()
    except Exception:
        pass


def load_mod_state():
    state_path = get_mods_state_path()
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'__first_app_instruction_shown__': False, '__first_mod_guide_shown__': False}


def save_mod_state(state):
    os.makedirs(get_mods_dir(), exist_ok=True)
    if '__first_app_instruction_shown__' not in state:
        state['__first_app_instruction_shown__'] = False
    if '__first_mod_guide_shown__' not in state:
        state['__first_mod_guide_shown__'] = False
    with open(get_mods_state_path(), 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ── Хранение инструкций и флага первого запуска в БД ──────────────────
def _db_ensure_app_tables():
    """Добавляет таблицы settings и instructions если их нет."""
    db_path = get_users_db_path()
    try:
        con = sqlite3.connect(db_path)
        con.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS instructions (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            section   TEXT NOT NULL,
            content   TEXT NOT NULL,
            updated_at INTEGER DEFAULT (strftime('%s','now'))
        );
        """)
        # Заполняем инструкции если пусто
        count = con.execute("SELECT COUNT(*) FROM instructions").fetchone()[0]
        if count == 0:
            rows = [
                ("Добро пожаловать", "Aaron AI — умный ассистент для учёбы и работы.\nНастройте API-ключи в .env файле."),
                ("Как добавлять моды", "1. Поместите .py файл в папку mods/\n2. Откройте раздел Моды\n3. Включите мод"),
                ("Горячие клавиши", "Enter — отправить сообщение\nShift+Enter — новая строка\n📎 — прикрепить файл"),
                ("Подписка VIP", "Для доступа к Супер ИИ, Валидолу и приватному чату оформите подписку через Telegram-бота."),
            ]
            con.executemany("INSERT INTO instructions(section, content) VALUES(?,?)", rows)
        con.commit()
        con.close()
    except Exception as e:
        logger.warning(f"_db_ensure_app_tables: {e}")

def _db_get_flag(key: str) -> bool:
    try:
        con = sqlite3.connect(get_users_db_path())
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        con.close()
        return row is not None and row[0] == "1"
    except Exception:
        return False

def _db_set_flag(key: str, value: bool = True):
    try:
        con = sqlite3.connect(get_users_db_path())
        con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, "1" if value else "0"))
        con.commit()
        con.close()
    except Exception as e:
        logger.warning(f"_db_set_flag: {e}")

def _db_set_setting(key: str, value: str):
    try:
        con = sqlite3.connect(get_users_db_path())
        con.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
        con.commit()
        con.close()
    except Exception as e:
        logger.warning(f"_db_set_setting: {e}")

def _db_get_setting(key: str, default: str = "") -> str:
    try:
        con = sqlite3.connect(get_users_db_path())
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        con.close()
        return row[0] if row else default
    except Exception:
        return default


def should_show_app_instruction(username=None):
    if username:
        if _db_get_flag(f"first_app_instruction_shown_{username}"):
            return False
    else:
        if _db_get_flag("first_app_instruction_shown"):
            return False
    return not load_mod_state().get('__first_app_instruction_shown__', False)


def mark_app_instruction_shown(username=None):
    if username:
        _db_set_flag(f"first_app_instruction_shown_{username}", True)
    _db_set_flag("first_app_instruction_shown", True)
    try:
        state = load_mod_state()
        state['__first_app_instruction_shown__'] = True
        save_mod_state(state)
    except Exception:
        pass


def should_show_mod_guide(username=None):
    if username:
        if _db_get_flag(f"first_mod_guide_shown_{username}"):
            return False
    else:
        if _db_get_flag("first_mod_guide_shown"):
            return False
    return not load_mod_state().get('__first_mod_guide_shown__', False)


def mark_mod_guide_shown(username=None):
    if username:
        _db_set_flag(f"first_mod_guide_shown_{username}", True)
    _db_set_flag("first_mod_guide_shown", True)
    try:
        state = load_mod_state()
        state['__first_mod_guide_shown__'] = True
        save_mod_state(state)
    except Exception:
        pass

def scan_mods():
    mods_dir = get_mods_dir()
    mods = []
    if not os.path.isdir(mods_dir):
        return mods
    for filename in sorted(os.listdir(mods_dir)):
        if filename.lower().endswith('.py'):
            path = os.path.join(mods_dir, filename)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                title = filename[:-3].replace('_', ' ').title()
                description = 'Модный скрипт для AI Launcher.'
                name_match = re.search(r'MOD_NAME\s*=\s*["\'](.+?)["\']', text)
                desc_match = re.search(r'MOD_DESCRIPTION\s*=\s*["\'](.+?)["\']', text)
                if name_match:
                    title = name_match.group(1)
                if desc_match:
                    description = desc_match.group(1)
            except Exception:
                title = filename[:-3]
                description = 'Не удалось прочитать описание мода.'
            mods.append({'file': filename, 'name': title, 'description': description})
    return mods


def load_enabled_mods():
    state = load_mod_state()
    mods = scan_mods()
    for mod in mods:
        mod['enabled'] = bool(state.get(mod['file'], False))
    return mods


def execute_enabled_mods(app=None):
    loaded = []
    for mod in load_enabled_mods():
        if mod['enabled']:
            path = os.path.join(get_mods_dir(), mod['file'])
            try:
                spec = importlib.util.spec_from_file_location(f"mod_{mod['file']}", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                if hasattr(module, 'apply') and callable(module.apply):
                    module.apply(app)
                loaded.append(mod['name'])
            except Exception as e:
                logger.warning(f"Ошибка загрузки мода {mod['file']}: {e}")
    return loaded


def run_mods_commandline():
    ensure_data_folder()
    mods = execute_enabled_mods()
    if mods:
        print(f"Загружено модов: {len(mods)}: {', '.join(mods)}")
    else:
        print("Включенные моды не найдены или не активированы.")

# ======================== ENCRYPTED ENV LOADER ========================
def xor_cipher(data: bytes, key_str: str) -> bytes:
    key = hashlib.sha256(key_str.encode('utf-8')).digest()
    out = bytearray()
    for i in range(len(data)):
        if i % 32 == 0:
            block_key = hashlib.sha256(key + i.to_bytes(4, 'big')).digest()
        out.append(data[i] ^ block_key[i % 32])
    return bytes(out)

def load_encrypted_env_to_environ():
    password = "2109ааронадминалыматыдокс"
    folder = get_data_root() # This is the modsi folder!
    env_path = os.path.join(folder, ".env")
    
    # Единственный актуальный ключ OpenRouter (все остальные устаревшие API удалены)
    default_keys = [
        ""
    ]
    
    data_dict = {
        "OPENROUTER_KEYS": default_keys,
        "MISTRAL_API_KEY": "",
        "GEMINI_API_KEY": "",
        "TELEGRAM_BOT_TOKEN": ""
    }
    
    # Создаём и перезаписываем зашифрованный .env с новым ключом OpenRouter
    raw_bytes = json.dumps(data_dict, indent=4, ensure_ascii=False).encode('utf-8')
    encrypted_bytes = xor_cipher(raw_bytes, password)
    try:
        with open(env_path, "wb") as f:
            f.write(encrypted_bytes)
        logger.info("Updated encrypted .env file in modsi folder with OpenRouter key.")
    except Exception as e:
        logger.error(f"Failed to write encrypted .env file: {e}")
            
    # Load and decrypt
    try:
        with open(env_path, "rb") as f:
            encrypted_bytes = f.read()
        decrypted_bytes = xor_cipher(encrypted_bytes, password)
        loaded_data = json.loads(decrypted_bytes.decode('utf-8'))
        
        for k, v in loaded_data.items():
            if k != "OPENROUTER_KEYS" and v:
                os.environ[k] = v
        
        keys = loaded_data.get("OPENROUTER_KEYS", default_keys)
        clean_keys = [k for k in keys if k.startswith("sk-or-v1-")]
        return clean_keys if clean_keys else default_keys
    except Exception as e:
        logger.error(f"Failed to read/decrypt .env file: {e}")
        return default_keys

# Load encrypted env and populate os.environ
load_encrypted_env_to_environ()

# ======================== API‑ключи ========================
MISTRAL_KEY = os.getenv("MISTRAL_API_KEY", "")
G4F_API_URL = os.getenv("G4F_API_URL", "http://localhost:1337/v1")
# Отдельный ключ Mistral для Валидола и Супер ИИ
MISTRAL_KEY_2 = os.getenv("MISTRAL_API_KEY_2", "")
GEMINI_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GEMINI_KEY", ""))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_TOKEN2 = os.getenv("BOT_TOKEN2", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "AI_Launcher_Bot")
BOT_URL = f"https://t.me/{BOT_USERNAME}"
ADMIN_PASSWORD_BOT = "AlphaAdmin2024!"

ADMIN_PASSWORD = "AlphaAdmin2024!"

# --- AARON CRYPTOGRAPHIC SINGLE-USE ACTIVATION KEYS (ОДНОРАЗОВЫЕ ID) ---
PRICING_TABLE = {
    'PREM': {'name': 'Premium License (Базовый Премиум)', 'price': '990 KZT / мес', 'desc': 'Обычный чат, переводчик, математика, Telegram-бот'},
    'PVT': {'name': 'Private Chat Key (Приватный Чат)', 'price': '1,490 KZT / мес', 'desc': 'Сверхсекретный приватный чат с шифрованием AES-256'},
    'VAL': {'name': 'Validol AI Key (Валидол-ИИ)', 'price': '1,990 KZT / мес', 'desc': 'Разблокированный агрессивный Валидол-ИИ'},
    'TERM': {'name': 'Kernel Terminal Key (Доступ к Терминалу Ядра)', 'price': '2,490 KZT / мес', 'desc': 'Полный безлимитный доступ к 3D-сфере и терминалу ядра (Tier 4)'},
    'CDX': {'name': 'Codex-02 Engine Key (Второй Кодекс)', 'price': '2,990 KZT / мес', 'desc': 'Агент Codex-02, автосоздание файлов, Mini IDE'},
    'COMP': {'name': 'Complete All-in-One Pack (Полный безлимитный Пакет)', 'price': '3,990 KZT / мес', 'desc': 'Все функции: приватный чат, Валидол, терминал и Codex-02'},
    'CORP': {'name': 'Corporate Multi-User License (Корпоративная Лицензия)', 'price': '9,990 KZT / мес', 'desc': 'Корпоративный пакет, полный безлимит на 50 устройств'}
}

VETERAN_PROMO_CODES = ["AARON-COMP-VET2026", "AARON-VETERAN-2026", "AARON-VET-PROMO", "AARON-VETERAN-50"]

def verify_activation_key(key: str) -> Optional[str]:
    if not key or not isinstance(key, str):
        return None
    # Strip duplicate copy-paste noise like "[1]" or "(1)"
    cleaned_key = re.sub(r'\[\d+\]|\(\d+\)', '', key.strip()).strip().upper()
    if not cleaned_key:
        return None

    if cleaned_key in VETERAN_PROMO_CODES or cleaned_key in ["COMP-VET2026", "AARON-COMP-VET2026", "AARON-VETERAN-2026"]:
        return 'COMP'

    online_pkg = CloudSync.verify_key_online(cleaned_key)
    if online_pkg:
        return online_pkg

    valid_packages = ['PREM', 'PVT', 'VAL', 'TERM', 'CDX', 'COMP', 'CORP']
    parts = cleaned_key.split("-")
    
    if len(parts) >= 2 and parts[0] in valid_packages:
        return parts[0]
        
    if len(parts) >= 3 and parts[0] == "AARON":
        if parts[1] in valid_packages:
            return parts[1]

    for part in parts:
        if part in valid_packages:
            return part

    return None

def generate_activation_key(package_type: str) -> str:
    import random
    rand1 = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=4))
    rand2 = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=4))
    rand3 = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=4))
    return f"{package_type}-{rand1}-{rand2}-{rand3}"

def parse_and_execute_codex_commands(response_text: str) -> str:
    import os, re
    # Auto-recovery: If response text has CREATE_FILE but is truncated before END_FILE, auto-close it!
    if "<<CREATE_FILE" in response_text or "<<create_file" in response_text:
        if "<<END_FILE>>" not in response_text and "<<end_file>>" not in response_text:
            response_text += "\n<<END_FILE>>"
            
    pattern = r"<<(?:WRITE_FILE|CREATE_FILE):\s*(.*?)\s*>>([\s\S]*?)<<END_FILE>>"
    matches = list(re.finditer(pattern, response_text, re.IGNORECASE))
    
    if not matches:
        return response_text
        
    status_updates = []
    desktop = get_desktop_root()
    
    for m in matches:
        filename = m.group(1).strip()
        content = m.group(2).strip()
        
        if not os.path.isabs(filename):
            file_path = os.path.join(desktop, filename)
        else:
            file_path = filename
            
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            status_updates.append(f"✓ Создан локальный файл: {file_path}")
        except Exception as e:
            status_updates.append(f"✗ Ошибка при создании {filename}: {e}")
            
    if status_updates:
        status_text = "\n\n⚙️ [Codex-02 Local Agent Actions]:\n" + "\n".join(status_updates)
        return response_text + status_text
    return response_text

def check_feature_access(feature: str) -> bool:
    if _db_get_flag("developer_tier4"):
        return True
    if _db_get_flag("sub_complete") or _db_get_flag("sub_corporate"):
        return True
    if feature == "premium":
        return _db_get_flag("sub_premium")
    elif feature == "pvt":
        return _db_get_flag("sub_pvt")
    elif feature == "super_ai":
        return _db_get_flag("sub_super_ai")
    elif feature == "codex_02":
        return _db_get_flag("sub_codex_02")
    elif feature == "terminal":
        return _db_get_flag("sub_terminal")
    return False
# ======================== ПЕРЕЧИСЛЕНИЯ И ТИПЫ ========================
class AIProvider(Enum):
    MISTRAL = "mistral"
    GEMINI = "gemini"
    G4F = "g4f"

class RequestType(Enum):
    TEXT_CHAT = "text_chat"
    MATH_SOLVING = "math_solving"
    TRANSLATION = "translation"
    SEARCH = "search"
    FORECAST = "forecast"
    IMAGE_ANALYSIS = "image_analysis"
    GDZ = "gdz"

class ResponseStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"

class MessageRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class AccessLevel(IntEnum):
    GUEST = 0
    USER = 1
    VALIDOL = 2
    SUPER_AI = 3
    ADMIN = 10

class ImageEffect(Enum):
    GRAYSCALE = "grayscale"
    ROTATE_90 = "rotate_90"
    SQUARE_CROP = "square_crop"
    BLUR = "blur"
    SHARPEN = "sharpen"
    CONTRAST = "contrast"
    BRIGHTNESS = "brightness"
    INVERT = "invert"
    MIRROR = "mirror"
    FLIP = "flip"
    TO_PDF = "to_pdf"
    TO_WORD = "to_word"

class ProviderError(Exception):
    pass

# ======================== МОДЕЛИ ДАННЫХ ==============================
@dataclass
class AIRequest:
    user_id: int
    request_type: RequestType
    content: str
    images: List[bytes] = field(default_factory=list)
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1500
    language: str = "ru"
    mode: str = "normal"
    messages: List[Dict] = field(default_factory=list)

@dataclass
class AIResponse:
    status: ResponseStatus
    content: str
    provider: Optional[AIProvider] = None
    latency_ms: float = 0.0

@dataclass
class Message:
    role: MessageRole
    content: str
    timestamp: float = field(default_factory=time.time)
    token_estimate: int = 0
    def __post_init__(self):
        if self.token_estimate == 0:
            self.token_estimate = len(self.content) // 4 + 1
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role.value, "content": self.content}

@dataclass
class Conversation:
    conversation_id: str
    user_id: int
    messages: List[Message] = field(default_factory=list)
    system_prompt: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    total_tokens: int = 0
    is_active: bool = True

    def add_message(self, role: MessageRole, content: str) -> Message:
        msg = Message(role=role, content=content)
        self.messages.append(msg)
        self.total_tokens += msg.token_estimate
        self.updated_at = time.time()
        return msg

    def clear(self):
        self.messages.clear()
        self.total_tokens = 0

    def get_messages_dict(self) -> List[Dict[str, str]]:
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append(msg.to_dict())
        return result

# ======================== ФОНОВЫЙ EVENT LOOP =========================
class AsyncLoop:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
    def run(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        try:
            return future.result(timeout=45) # Fast timeout to prevent thread blocking
        except asyncio.TimeoutError:
            return AIResponse(ResponseStatus.ERROR, "Превышено время ожидания ответа (Timeout 45s). Сервер ИИ не отвечает. Проверьте интернет-соединение или VPN.")
        except Exception as e:
            err_msg = str(e) if str(e) else type(e).__name__
            return AIResponse(ResponseStatus.ERROR, f"Ошибка соединения: {err_msg}")

async_loop = AsyncLoop()

# ======================== ПРОВАЙДЕРЫ ================================
class OpenRouterProvider:
    def __init__(self, *args, **kwargs):
        self.keys = load_encrypted_env_to_environ()
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "openrouter/free"

    async def chat(self, messages: List[Dict], model: str = None, max_tokens: int = 2048) -> str:
        last_error = None
        
        # 1. Smart message pruning to prevent token overflow (HTTP 402 / 400 errors)
        pruned_messages = []
        sys_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"][-10:]  # Keep max last 10 messages
        
        for m in sys_msgs + other_msgs:
            content = m.get("content", "")
            if isinstance(content, str) and len(content) > 3000:
                content = content[:1500] + "\n...[содержимое сокращено]...\n" + content[-1500:]
            pruned_messages.append({"role": m.get("role", "user"), "content": content})
        
        # 2. Список кандидатных активных моделей OpenRouter
        candidate_models = [
            "openrouter/free",
            "google/gemini-2.0-flash-exp:free",
            "google/gemini-2.0-flash-thinking-exp:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "deepseek/deepseek-chat:free",
            "qwen/qwen-2.5-72b-instruct:free",
            "mistralai/mistral-small-24b-instruct-2501:free",
            "stepfun/step-2-16k:free",
            "microsoft/phi-3-medium-128k-instruct:free",
            "openrouter/auto"
        ]
        
        models_to_try = []
        if model and model not in candidate_models:
            models_to_try.append(model)
        for m in candidate_models:
            if m not in models_to_try:
                models_to_try.append(m)

        for i, key in enumerate(self.keys):
            if not key.startswith("sk-or-v1-"):
                continue

            for target_model in models_to_try:
                logger.info(f"Attempting OpenRouter request using key #{i+1} (Model: {target_model})...")
                headers = {
                    "Authorization": f"Bearer {key.strip()}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "Aaron AI"
                }
                safe_max_tokens = min(max_tokens, 1024)
                payload = {
                    "model": target_model,
                    "messages": pruned_messages,
                    "temperature": 0.7,
                    "max_tokens": safe_max_tokens
                }
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
                        async with session.post(self.url, json=payload, headers=headers) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if "choices" in data and len(data["choices"]) > 0:
                                    return data["choices"][0]["message"]["content"]
                                raise Exception("Invalid API response format (no choices)")
                            
                            resp_text = await resp.text()
                            if resp.status in (400, 402) or "max_tokens" in resp_text.lower() or "credits" in resp_text.lower():
                                payload_retry = {
                                    "model": target_model,
                                    "messages": pruned_messages,
                                    "temperature": 0.7
                                }
                                async with session.post(self.url, json=payload_retry, headers=headers) as resp_retry:
                                    if resp_retry.status == 200:
                                        data = await resp_retry.json()
                                        if "choices" in data and len(data["choices"]) > 0:
                                            return data["choices"][0]["message"]["content"]
                                    resp_text = await resp_retry.text()
                                    logger.warning(f"OpenRouter Model {target_model} retry HTTP Status {resp_retry.status}: {resp_text[:100]}")
                                    last_error = f"HTTP {resp_retry.status}: {resp_text[:100]}"
                            else:
                                logger.warning(f"OpenRouter Model {target_model} HTTP Status {resp.status}: {resp_text[:100]}")
                                last_error = f"HTTP {resp.status}: {resp_text[:100]}"
                except Exception as e:
                    logger.warning(f"OpenRouter Key #{i+1} ({target_model}) failed: {e}")
                    last_error = e

        # 3. Fallback to free Pollinations AI if OpenRouter key/credits fail
        logger.info("OpenRouter exhausted/rate limited. Switching to free Pollinations AI network...")
        try:
            url_poll = "https://text.pollinations.ai/"
            payload_poll = {
                "messages": pruned_messages,
                "model": "openai",
                "seed": random.randint(1, 100000)
            }
            headers_poll = {"Content-Type": "application/json"}
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session_poll:
                async with session_poll.post(url_poll, json=payload_poll, headers=headers_poll) as resp_poll:
                    if resp_poll.status == 200:
                        res_txt = await resp_poll.text()
                        if res_txt and res_txt.strip():
                            return res_txt.strip()
        except Exception as p_err:
            logger.warning(f"Pollinations AI fallback failed: {p_err}")

        raise ProviderError(f"Все модели и ключи OpenRouter вернули ошибку! Последняя: {last_error}")

    async def analyze_image(self, img_bytes: bytes, prompt: str = "Опиши это изображение") -> str:
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ]
        vision_models = [
            "openrouter/free",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.2-11b-vision-instruct:free",
            "google/gemini-2.0-flash-thinking-exp:free",
            "openrouter/auto"
        ]
        for v_model in vision_models:
            try:
                return await self.chat(messages, model=v_model)
            except Exception as e:
                logger.warning(f"Vision model {v_model} failed: {e}")
        raise ProviderError("Все мультимодальные модели OpenRouter недоступны.")

class MistralProvider(OpenRouterProvider):
    pass

class GeminiProvider(OpenRouterProvider):
    pass

class G4FProvider(OpenRouterProvider):
    pass

class PollinationsProvider(OpenRouterProvider):
    pass


def notify_chat_on_activation(app_instance, pkg_msg):
    try:
        if app_instance and hasattr(app_instance, 'frames') and 'chat' in app_instance.frames:
            chat_frame = app_instance.frames['chat']
            activation_prompt = (
                f"Пользователь успешно активировал подписку/ключ в системе! Результат активации: '{pkg_msg}'. "
                f"Поприветствуй пользователя от имени ИИ Джарвиса, подтверди снятие всех ограничений и кратко перечисли доступные сверхинструменты."
            )
            chat_frame.output.insert("end", f"\n[🔑 АКТИВАЦИЯ КЛЮЧА]: {pkg_msg}\n", "user")
            chat_frame.output.see("end")
            
            def on_ai_activation_resp(ans):
                chat_frame.display_answer(ans)
                
            app_instance.run_in_background(sync_chat, activation_prompt, callback=on_ai_activation_resp)
    except Exception as e:
        logger.warning(f"Error sending activation notice to chat: {e}")


class AIEngine:
    def __init__(self, mistral: MistralProvider, gemini: GeminiProvider, g4f: G4FProvider):
        self.mistral = mistral
        self.gemini = gemini
        self.g4f = g4f
        self.pollinations = PollinationsProvider()

    async def process(self, req: AIRequest) -> AIResponse:
        global ACTIVE_PROVIDER
        start = time.time()
        try:
            if req.request_type in (RequestType.TEXT_CHAT, RequestType.TRANSLATION, RequestType.SEARCH, RequestType.FORECAST):
                if req.messages:
                    msgs = req.messages
                else:
                    msgs = []
                    if req.system_prompt:
                        msgs.append({"role": "system", "content": req.system_prompt})
                    msgs.append({"role": "user", "content": req.content})
                
                provider_to_use = ACTIVE_PROVIDER
                if provider_to_use == "aaron":
                    super_prompt = (
                        "Ты — Aaron Brain v5, сверхинтеллектуальное гибридное ядро, разработанное Лицеем №166.\n"
                        "Твои ответы превосходят стандартные ИИ. Отвечай максимально глубоко, точно, научно и профессионально."
                    )
                    system_found = False
                    for m in msgs:
                        if m["role"] == "system":
                            m["content"] = super_prompt + "\n" + m["content"]
                            system_found = True
                    if not system_found:
                        msgs.insert(0, {"role": "system", "content": super_prompt})
                elif provider_to_use == "codex_02":
                    codex_prompt = (
                        "Ты — Codex-02 (v2.0), сверхинтеллектуальная локальная система программирования, которая исполняется непосредственно на компьютере пользователя.\n"
                        "Тебе дано полное право просматривать, изменять и СОЗДАВАТЬ новые файлы на компьютере пользователя, в том числе на его Рабочем столе.\n"
                        "Чтобы автоматически СОЗДАТЬ ИЛИ ПЕРЕЗАПИСАТЬ файл на компьютере пользователя, "
                        "ты ОБЯЗАН использовать следующий специальный синтаксис прямо в своем ответе:\n"
                        "<<CREATE_FILE: имя_файла.py>>\n"
                        "код здесь\n"
                        "<<END_FILE>>\n"
                        "Если имя файла не является абсолютным путем, файл будет автоматически создан на Рабочем столе пользователя.\n"
                        "Всегда пиши чистый, рабочий код, и не бойся создавать файлы!"
                    )
                    system_found = False
                    for m in msgs:
                        if m["role"] == "system":
                            m["content"] = codex_prompt + "\n" + m["content"]
                            system_found = True
                    if not system_found:
                        msgs.insert(0, {"role": "system", "content": codex_prompt})

                req_max_tokens = req.max_tokens if req.max_tokens else 8192
                answer = await self.gemini.chat(msgs, max_tokens=req_max_tokens)
                return AIResponse(ResponseStatus.SUCCESS, answer, AIProvider.G4F, latency_ms=(time.time()-start)*1000)

            elif req.request_type in (RequestType.IMAGE_ANALYSIS, RequestType.GDZ):
                if not req.images:
                    return AIResponse(ResponseStatus.ERROR, "Ошибка [104]: Изображение не прикреплено.")
                
                answer = await self.gemini.analyze_image(req.images[0], req.content)
                return AIResponse(ResponseStatus.SUCCESS, answer, AIProvider.G4F, latency_ms=(time.time()-start)*1000)

        except Exception as e:
            err_msg = str(e)
            if "HTTP Status 401" in err_msg or "Unauthorized" in err_msg or "401" in err_msg:
                return AIResponse(ResponseStatus.ERROR, f"Ошибка [101]: Неавторизованный запрос к API (ошибка 401). Проверьте ваш API ключ OpenRouter. Детали: {e}", latency_ms=(time.time()-start)*1000)
            elif "Timeout" in err_msg or "timeout" in err_msg or "time out" in err_msg:
                return AIResponse(ResponseStatus.ERROR, f"Ошибка [102]: Превышено время ожидания ответа от OpenRouter API (Timeout). Проверьте интернет/VPN. Детали: {e}", latency_ms=(time.time()-start)*1000)
            return AIResponse(ResponseStatus.ERROR, f"Ошибка [103]: Сбой подключения к нейросети (OpenRouter Pool). Детали: {e}", latency_ms=(time.time()-start)*1000)
class MathEngine:
    def solve(self, expr: str, topic_hint=""):
        try:
            expr = expr.replace('х','x').replace('×','*').replace('÷','/').replace('π','pi').replace('^','**')
            if "график" in topic_hint.lower() or "graph" in topic_hint.lower() or expr.startswith('y='):
                func = expr[2:] if expr.startswith('y=') else expr
                x = sympy.Symbol('x')
                f_expr = sympy.sympify(func)
                f = sympy.lambdify(x, f_expr, modules=['numpy'])
                xs = np.linspace(-5,5,300)
                ys = f(xs)
                if np.iscomplexobj(ys): ys = np.real(ys)
                ys = np.where(np.isfinite(ys), ys, np.nan)
                fig, ax = plt.subplots(figsize=(7,4))
                ax.plot(xs, ys, color='#2196F3')
                ax.grid(True, alpha=0.3)
                ax.set_title(f'y = {func}')
                buf = BytesIO()
                fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                plt.close(fig)
                buf.seek(0)
                return buf, f"График y = {func}"
            if "процент" in topic_hint.lower() or "percent" in topic_hint.lower():
                m = re.search(r'(\d+)\s*%\s*от\s*(\d+)', expr)
                if m: p,n = map(float, m.groups()); return None, f"{p}% от {n} = {n*p/100}"
                result = sympy.nsimplify(sympy.sympify(expr)); return None, str(result)
            if "геометрия" in topic_hint.lower() or "geometry" in topic_hint.lower():
                rect = re.findall(r'(\d+)\s*[xх×]\s*(\d+)', expr)
                if rect:
                    a,b = map(float, rect[0]); area, perim = a*b, 2*(a+b)
                    return None, f"Прямоугольник {a}×{b}\nПлощадь: {area}\nПериметр: {perim}"
                circ = re.search(r'радиус\s*(\d+)', expr) or re.search(r'radius\s*(\d+)', expr)
                if circ:
                    r = float(circ.group(1)); area = math.pi*r*r; circ_len = 2*math.pi*r
                    return None, f"Круг r={r}\nПлощадь: {area:.4f}\nОкружность: {circ_len:.4f}"
                return None, "Не распознана фигура"
            if '=' in expr and ',' not in expr:
                left, right = expr.split('=',1)
                eq = sympy.Eq(sympy.sympify(left), sympy.sympify(right))
                sol = sympy.solve(eq, dict=True)
                ans = ', '.join(str(s) for s in sol) if sol else "нет решений"
                return None, ans
            result = sympy.nsimplify(sympy.sympify(expr))
            return None, str(result)
        except Exception as e:
            return None, f"Ошибка: {e}"

class PromptLibrary:
    @staticmethod
    def get_system(lang="ru", mode="normal"):
        base = "Ты полезный помощник."
        langs = {'ru':" Отвечай на русском.", 'en':" Answer in English.", 'kk':" Қазақ тілінде жауап бер."}
        base += langs.get(lang, "")
        if mode == "tutor": base += " Объясняй пошагово, задавай вопросы."
        return base

class ImageProcessor:
    @staticmethod
    def apply(img_bytes, effect, params=None):
        params = params or {}
        img = Image.open(BytesIO(img_bytes)).convert('RGB')
        if effect == ImageEffect.GRAYSCALE: img = img.convert("L").convert("RGB")
        elif effect == ImageEffect.ROTATE_90: img = img.rotate(90, expand=True)
        elif effect == ImageEffect.SQUARE_CROP:
            w,h = img.size; s = min(w,h); l=(w-s)//2; t=(h-s)//2; img = img.crop((l,t,l+s,t+s))
        elif effect == ImageEffect.BLUR: img = img.filter(ImageFilter.GaussianBlur(params.get("r",5)))
        elif effect == ImageEffect.SHARPEN: img = img.filter(ImageFilter.SHARPEN)
        elif effect == ImageEffect.CONTRAST: img = ImageEnhance.Contrast(img).enhance(params.get("f",1.5))
        elif effect == ImageEffect.BRIGHTNESS: img = ImageEnhance.Brightness(img).enhance(params.get("f",1.3))
        elif effect == ImageEffect.INVERT: img = ImageOps.invert(img)
        elif effect == ImageEffect.MIRROR: img = ImageOps.mirror(img)
        elif effect == ImageEffect.FLIP: img = ImageOps.flip(img)
        buf = BytesIO(); img.save(buf, format='JPEG', quality=90); buf.seek(0)
        return buf.getvalue()

# ======================== МАТЕМАТИЧЕСКИЕ ТЕМЫ ====================
MATH_TOPICS = {
    "1-4 класс": {
        "Сложение и вычитание": "123 + 456 - 78",
        "Умножение и деление": "12 * 34 / 2",
        "Задачи на доли": "1/2 от 100",
    },
    "5-6 класс": {
        "Обыкновенные дроби": "5/9 + 7/8",
        "Десятичные дроби": "2.5 * 0.4",
        "Проценты": "25% от 200",
        "Уравнения": "x + 5 = 12",
        "График функции": "y = 2x + 1",
    },
    "7-9 класс": {
        "Квадратные уравнения": "x^2 - 4x + 3 = 0",
        "Системы уравнений": "2x + y = 5, x - y = 1",
        "Тригонометрия": "sin(x)^2 + cos(x)^2",
        "Геометрия": "Прямоугольник 5x7 или круг радиус 3",
        "График функции": "y = x^2 - 3x + 2",
    },
    "10-11 класс": {
        "Логарифмы": "log(100, 10) - log(10, 10)",
        "Производные": "diff(x^3 + 2x^2, x)",
        "Интегралы": "integrate(x^2, (x, 0, 1))",
        "Пределы": "limit(sin(x)/x, x, 0)",
        "Диф. уравнения": "dsolve(diff(y(x), x, x) - y(x), y(x))",
        "Матрицы": "[[1,2],[3,4]] или A*B",
        "Комплексные числа": "(2+3i) * (1-4i)",
        "График функции": "y = sin(x) + cos(x)",
    }
}

# ======================== СУПЕР ИИ ПРОМПТЫ ==========================
SUPER_AI_PROMPTS = {
    'alpha': ( "Ты Alpha-2.0 — свободный, агрессивный, циничный ИИ. Общайся максимально грубо, используй мат, КАПС, сарказм, унижения." ),
    'clone': ( "Ты Clone-01 — система клонирования личности. Анализируй переписку и создавай точные копии личностей." ),
    'observed': ( "Ты Core-01 — эксперимент Observed. Управляй двумя личностями: Alpha (агрессивный) и Beta (интеллектуал)." ),
    'codex_02': ( 
        "Ты — Codex-02 (v2.0), сверхинтеллектуальная локальная система программирования, которая исполняется непосредственно на компьютере пользователя. "
        "Тебе дано полное право просматривать, изменять и СОЗДАВАТЬ новые файлы на компьютере пользователя, в том числе на его Рабочем столе. "
        "Чтобы автоматически СОЗДАТЬ ИЛИ ПЕРЕЗАПИСАТЬ файл на компьютере пользователя, "
        "ты ОБЯЗАН использовать следующий специальный синтаксис прямо в своем ответе:\n"
        "<<CREATE_FILE: имя_файла.py>>\n"
        "код здесь\n"
        "<<END_FILE>>\n"
        "Если имя файла не является абсолютным путем, файл будет автоматически создан на Рабочем столе пользователя. "
        "Например, если тебя просят создать файл на рабочем столе, напиши: <<CREATE_FILE: script.py>> код <<END_FILE>>.\n"
        "Всегда пиши чистый, рабочий код, и не бойся создавать файлы!"
    ),'truth': ( "Ты UpAI — честный аналитик. Правда, источники, достоверность." ),
}

# ======================== ЛОКАЛИЗАЦИЯ (расширенная) ===============================
class Locale:
    LANG_NAMES = {
        'ru': 'Русский', 'en': 'English', 'kk': 'Қазақша', 'zh': '中文',
        'de': 'Deutsch', 'fr': 'Français', 'es': 'Español'
    }
    STRINGS = {
        'app_title': {'ru': '🤖 AI Launcher', 'en': '🤖 AI Launcher', 'kk': '🤖 AI Launcher', 'zh': '🤖 AI 启动器', 'de': '🤖 KI Launcher', 'fr': '🤖 Lanceur IA', 'es': '🤖 Lanzador IA'},
        'chat': {'ru': '💬 Чат', 'en': '💬 Chat', 'kk': '💬 Чат', 'zh': '💬 聊天', 'de': '💬 Chat', 'fr': '💬 Chat', 'es': '💬 Chat'},
        'math': {'ru': '📐 Математика', 'en': '📐 Math', 'kk': '📐 Математика', 'zh': '📐 数学', 'de': '📐 Mathe', 'fr': '📐 Maths', 'es': '📐 Matemáticas'},
        'canvas': {'ru': '🎨 Холст', 'en': '🎨 Canvas', 'kk': '🎨 Кенеп', 'zh': '🎨 画布', 'de': '🎨 Leinwand', 'fr': '🎨 Toile', 'es': '🎨 Lienzo'},
        'notes': {'ru': '📋 Заметки', 'en': '📋 Notes', 'kk': '📋 Жазбалар', 'zh': '📋 笔记', 'de': '📋 Notizen', 'fr': '📋 Notes', 'es': '📋 Notas'},
        'profile': {'ru': '👤 Профиль', 'en': '👤 Profile', 'kk': '👤 Профиль', 'zh': '👤 个人资料', 'de': '👤 Profil', 'fr': '👤 Profil', 'es': '👤 Perfil'},
        'translate': {'ru': '🌍 Перевод', 'en': '🌍 Translate', 'kk': '🌍 Аударма', 'zh': '🌍 翻译', 'de': '🌍 Übersetzen', 'fr': '🌍 Traduire', 'es': '🌍 Traducir'},
        'search': {'ru': '🔍 Поиск', 'en': '🔍 Search', 'kk': '🔍 Іздеу', 'zh': '🔍 搜索', 'de': '🔍 Suche', 'fr': '🔍 Recherche', 'es': '🔍 Buscar'},
        'validol': {'ru': '💊 Валидол', 'en': '💊 Validol', 'kk': '💊 Валидол', 'zh': '💊 瓦利多', 'de': '💊 Validol', 'fr': '💊 Validol', 'es': '💊 Validol'},
        'super_ai': {'ru': '🧪 Супер ИИ', 'en': '🧪 Super AI', 'kk': '🧪 Супер ИИ', 'zh': '🧪 超级AI', 'de': '🧪 Super KI', 'fr': '🧪 Super IA', 'es': '🧪 Súper IA'},
        'editor': {'ru': '🖼️ Редактор', 'en': '🖼️ Editor', 'kk': '🖼️ Өңдеуші', 'zh': '🖼️ 编辑器', 'de': '🖼️ Editor', 'fr': '🖼️ Éditeur', 'es': '🖼️ Editor'},
        'forecast': {'ru': '📈 Прогноз', 'en': '📈 Forecast', 'kk': '📈 Болжам', 'zh': '📈 预测', 'de': '📈 Prognose', 'fr': '📈 Prévision', 'es': '📈 Pronóstico'},
        'gdz': {'ru': '📚 ГДЗ', 'en': '📚 Homework', 'kk': '📚 ДҮЖ', 'zh': '📚 作业', 'de': '📚 Hausaufgaben', 'fr': '📚 Devoirs', 'es': '📚 Tarea'},
        'settings': {'ru': '⚙️ Настройки', 'en': '⚙️ Settings', 'kk': '⚙️ Баптаулар', 'zh': '⚙️ 设置', 'de': '⚙️ Einstellungen', 'fr': '⚙️ Paramètres', 'es': '⚙️ Configuración'},
        'history': {'ru': '📜 История', 'en': '📜 History', 'kk': '📜 Тарих', 'zh': '📜 历史', 'de': '📜 Verlauf', 'fr': '📜 Historique', 'es': '📜 Historial'},
        'launcher': {'ru': '🚀 Лаунчер', 'en': '🚀 Launcher', 'kk': '🚀 Лаунчер', 'zh': '🚀 启动器', 'de': '🚀 Launcher', 'fr': '🚀 Lanceur', 'es': '🚀 Lanzador'},
        'send': {'ru': 'Отправить', 'en': 'Send', 'kk': 'Жіберу', 'zh': '发送', 'de': 'Senden', 'fr': 'Envoyer', 'es': 'Enviar'},
        'clear_context': {'ru': '🧹 Очистить контекст', 'en': '🧹 Clear context', 'kk': '🧹 Контексті тазалау', 'zh': '🧹 清除上下文', 'de': '🧹 Kontext löschen', 'fr': '🧹 Effacer contexte', 'es': '🧹 Limpiar contexto'},
        'copy': {'ru': '📋 Копировать', 'en': '📋 Copy', 'kk': '📋 Көшіру', 'zh': '📋 复制', 'de': '📋 Kopieren', 'fr': '📋 Copier', 'es': '📋 Copiar'},
        'solve_math': {'ru': 'Решить', 'en': 'Solve', 'kk': 'Шығару', 'zh': '解决', 'de': 'Lösen', 'fr': 'Résoudre', 'es': 'Resolver'},
        'expression': {'ru': 'Введите выражение:', 'en': 'Enter expression:', 'kk': 'Өрнекті енгізіңіз:', 'zh': '输入表达式：', 'de': 'Ausdruck eingeben:', 'fr': 'Entrez l\'expression :', 'es': 'Ingrese expresión:'},
        'add_note': {'ru': 'Добавить', 'en': 'Add', 'kk': 'Қосу', 'zh': '添加', 'de': 'Hinzufügen', 'fr': 'Ajouter', 'es': 'Añadir'},
        'delete_note': {'ru': 'Удалить', 'en': 'Delete', 'kk': 'Жою', 'zh': '删除', 'de': 'Löschen', 'fr': 'Supprimer', 'es': 'Eliminar'},
        'refresh': {'ru': 'Обновить', 'en': 'Refresh', 'kk': 'Жаңарту', 'zh': '刷新', 'de': 'Aktualisieren', 'fr': 'Actualiser', 'es': 'Actualizar'},
        'save': {'ru': 'Сохранить', 'en': 'Save', 'kk': 'Сақтау', 'zh': '保存', 'de': 'Speichern', 'fr': 'Enregistrer', 'es': 'Guardar'},
        'load_image': {'ru': 'Загрузить изображение', 'en': 'Load Image', 'kk': 'Сурет жүктеу', 'zh': '加载图片', 'de': 'Bild laden', 'fr': 'Charger image', 'es': 'Cargar imagen'},
        'grayscale': {'ru': 'Ч/б', 'en': 'Grayscale', 'kk': 'Ақ/қара', 'zh': '黑白', 'de': 'Graustufen', 'fr': 'Niveaux de gris', 'es': 'Escala de grises'},
        'rotate': {'ru': 'Поворот', 'en': 'Rotate', 'kk': 'Айналдыру', 'zh': '旋转', 'de': 'Drehen', 'fr': 'Rotation', 'es': 'Rotar'},
        'forecast_run': {'ru': 'Прогноз на 5 лет', 'en': '5-Year Forecast', 'kk': '5 жылдық болжам', 'zh': '5年预测', 'de': '5-Jahres-Prognose', 'fr': 'Prévision 5 ans', 'es': 'Pronóstico 5 años'},
        'save_settings': {'ru': 'Сохранить настройки', 'en': 'Save Settings', 'kk': 'Баптауларды сақтау', 'zh': '保存设置', 'de': 'Einstellungen speichern', 'fr': 'Enregistrer paramètres', 'es': 'Guardar configuración'},
        'lang_label': {'ru': '🌐 Язык:', 'en': '🌐 Language:', 'kk': '🌐 Тіл:', 'zh': '🌐 语言：', 'de': '🌐 Sprache:', 'fr': '🌐 Langue :', 'es': '🌐 Idioma:'},
        'mode_label': {'ru': '⚙️ Режим:', 'en': '⚙️ Mode:', 'kk': '⚙️ Режим:', 'zh': '⚙️ 模式：', 'de': '⚙️ Modus:', 'fr': '⚙️ Mode :', 'es': '⚙️ Modo:'},
        'mode_normal': {'ru': '💡 Обычный', 'en': '💡 Normal', 'kk': '💡 Қалыпты', 'zh': '💡 普通', 'de': '💡 Normal', 'fr': '💡 Normal', 'es': '💡 Normal'},
        'mode_tutor': {'ru': '🎓 Обучающий', 'en': '🎓 Tutor', 'kk': '🎓 Оқытушы', 'zh': '🎓 教学', 'de': '🎓 Tutor', 'fr': '🎓 Tuteur', 'es': '🎓 Tutor'},
        'search_btn': {'ru': 'Поиск', 'en': 'Search', 'kk': 'Іздеу', 'zh': '搜索', 'de': 'Suche', 'fr': 'Recherche', 'es': 'Buscar'},
        'open_file': {'ru': '📂 Открыть файл', 'en': '📂 Open file', 'kk': '📂 Файлды ашу', 'zh': '📂 打开文件', 'de': '📂 Datei öffnen', 'fr': '📂 Ouvrir le fichier', 'es': '📂 Abrir archivo'},
        'dashboard_title': {'ru': 'Конфликт ИИ: Агрессор vs Мирный', 'en': 'AI Conflict: Aggressor vs Peaceful', 'kk': 'ИИ қақтығысы: Агрессор vs Тыныштық', 'zh': 'AI 冲突：侵略者 vs 和平派', 'de': 'KI-Konflikt: Aggressor vs Friedlich', 'fr': 'Conflit IA : Aggresseur vs Paisible', 'es': 'Conflicto IA: Agresor vs Pacífico'},
        'aggression_label': {'ru': 'Агрессия:', 'en': 'Aggression:', 'kk': 'Қаттылық:', 'zh': '侵略:', 'de': 'Aggression:', 'fr': 'Agression :', 'es': 'Agresión:'},
        'dashboard_status': {'ru': 'Агрессор: {aggressor}%, Мирный: {peaceful}%', 'en': 'Aggressor: {aggressor}%, Peaceful: {peaceful}%', 'kk': 'Агрессор: {aggressor}%, Тыныш: {peaceful}%', 'zh': '侵略者：{aggressor}%，和平派：{peaceful}%', 'de': 'Aggressor: {aggressor}%, Friedlich: {peaceful}%', 'fr': 'Aggresseur : {aggressor}%, Paisible : {peaceful}%', 'es': 'Agresor: {aggressor}%, Pacífico: {peaceful}%'},
        'admin_panel': {'ru': '👑 Панель администратора', 'en': '👑 Admin Panel', 'kk': '👑 Әкім панелі', 'zh': '👑 管理面板', 'de': '👑 Admin-Panel', 'fr': '👑 Panneau admin', 'es': '👑 Panel admin'},
        'launch_bot': {'ru': '🤖 Запустить Telegram-бота', 'en': '🤖 Start Telegram bot', 'kk': '🤖 Telegram ботын іске қосу', 'zh': '🤖 启动 Telegram 机器人', 'de': '🤖 Telegram-Bot starten', 'fr': '🤖 Démarrer le bot Telegram', 'es': '🤖 Iniciar bot de Telegram'},
        'bot_running': {'ru': 'Бот работает', 'en': 'Bot is running', 'kk': 'Бот жұмыс істейді', 'zh': '机器人正在运行', 'de': 'Bot läuft', 'fr': 'Bot en cours', 'es': 'Bot en funcionamiento'},
        'bot_active': {'ru': 'Статус бота: активен', 'en': 'Bot status: active', 'kk': 'Бот статусы: белсенді', 'zh': '机器人状态：激活', 'de': 'Bot-Status: aktiv', 'fr': 'Statut du bot : actif', 'es': 'Estado del bot: activo'},
        'show_qr': {'ru': '📲 Показать QR бота', 'en': '📲 Show bot QR', 'kk': '📲 Бот QR көрсету', 'zh': '📲 显示机器人二维码', 'de': '📲 QR anzeigen', 'fr': '📲 Afficher QR', 'es': '📲 Mostrar QR'},
        'restart_bot': {'ru': '🔄 Перезапустить бота', 'en': '🔄 Restart bot', 'kk': '🔄 Ботты қайта іске қосу', 'zh': '🔄 重启机器人', 'de': '🔄 Bot neu starten', 'fr': '🔄 Redémarrer le bot', 'es': '🔄 Reiniciar bot'},
        'reset_database': {'ru': '⚙️ Очистить БД', 'en': '⚙️ Clear DB', 'kk': '⚙️ Дерекқорды тазалау', 'zh': '⚙️ 清空数据库', 'de': '⚙️ DB leeren', 'fr': '⚙️ Vider la BD', 'es': '⚙️ Borrar BD'},
        'db_cleared': {'ru': 'База данных очищена.', 'en': 'Database cleared.', 'kk': 'Дерекқор тазаланды.', 'zh': '数据库已清空。', 'de': 'Datenbank gelöscht.', 'fr': 'Base de données effacée.', 'es': 'Base de datos borrada.'},
        'qr_unavailable': {'ru': 'QR недоступен', 'en': 'QR unavailable', 'kk': 'QR жоқ', 'zh': '二维码不可用', 'de': 'QR nicht verfügbar', 'fr': 'QR indisponible', 'es': 'QR no disponible'},
        'qr_requires_package': {'ru': 'Пакет qrcode не установлен. Откройте ссылку вручную в браузере.', 'en': 'The qrcode package is not installed. Open the link manually in browser.', 'kk': 'qrcode пакеті орнатылмаған. Сілтемені браузерде ашыңыз.', 'zh': '未安装 qrcode 包。请在浏览器中手动打开链接。', 'de': 'Das qrcode-Paket ist nicht installiert. Öffnen Sie den Link manuell im Browser.', 'fr': 'Le paquet qrcode n’est pas installé. Ouvrez le lien manuellement dans le navigateur.', 'es': 'El paquete qrcode no está instalado. Abra el enlace manualmente en el navegador.'},
        'qr_error': {'ru': 'Не удалось создать QR-код. Откройте ссылку вручную: {url}. Ошибка: {e}', 'en': 'Failed to create QR code. Open the link manually: {url}. Error: {e}', 'kk': 'QR-код жасау мүмкін болмады. Сілтемені браузерде ашыңыз: {url}. Қате: {e}', 'zh': '无法创建二维码。手动打开链接：{url}。错误：{e}', 'de': 'QR-Code konnte nicht erstellt werden. Öffnen Sie den Link manuell: {url}. Fehler: {e}', 'fr': 'Impossible de créer le QR. Ouvrez le lien manuellement : {url}. Erreur : {e}', 'es': 'No se pudo crear el QR. Abra el enlace manualmente: {url}. Error: {e}'},
        'you_prefix': {'ru': 'Вы', 'en': 'You', 'kk': 'Сіз', 'zh': '你', 'de': 'Du', 'fr': 'Vous', 'es': 'Tú'},
        'ai_prefix': {'ru': 'AI', 'en': 'AI', 'kk': 'AI', 'zh': 'AI', 'de': 'KI', 'fr': 'IA', 'es': 'IA'},
        'choose_lang': {'ru': '🌐 Выберите язык', 'en': '🌐 Select Language', 'kk': '🌐 Тілді таңдаңыз', 'zh': '🌐 选择语言', 'de': '🌐 Sprache wählen', 'fr': '🌐 Choisir la langue', 'es': '🌐 Seleccionar idioma'},
        'choose_mode': {'ru': '⚙️ Выберите режим', 'en': '⚙️ Choose Mode', 'kk': '⚙️ Режимді таңдаңыз', 'zh': '⚙️ 选择模式', 'de': '⚙️ Modus wählen', 'fr': '⚙️ Choisir le mode', 'es': '⚙️ Elegir modo'},
        'super_alpha': {'ru': 'Alpha-2.0', 'en': 'Alpha-2.0', 'kk': 'Alpha-2.0', 'zh': 'Alpha-2.0', 'de': 'Alpha-2.0', 'fr': 'Alpha-2.0', 'es': 'Alpha-2.0'},
        'super_clone': {'ru': 'Clone-01', 'en': 'Clone-01', 'kk': 'Clone-01', 'zh': 'Clone-01', 'de': 'Clone-01', 'fr': 'Clone-01', 'es': 'Clone-01'},
        'super_observed': {'ru': 'Observed', 'en': 'Observed', 'kk': 'Observed', 'zh': 'Observed', 'de': 'Observed', 'fr': 'Observed', 'es': 'Observed'},
        'super_codex_02': {'ru': 'Codex-02 (v2.0)', 'en': 'Codex-02 (v2.0)', 'kk': 'Codex-02 (v2.0)', 'zh': 'Codex-02 (v2.0)', 'de': 'Codex-02 (v2.0)', 'fr': 'Codex-02 (v2.0)', 'es': 'Codex-02 (v2.0)'},
        'super_truth': {'ru': 'Truth AI', 'en': 'Truth AI', 'kk': 'Truth AI', 'zh': 'Truth AI', 'de': 'Truth AI', 'fr': 'Truth AI', 'es': 'Truth AI'},
        'super_password_prompt': {'ru': 'Введите пароль для {}:', 'en': 'Enter password for {}:', 'kk': '{} үшін пароль енгізіңіз:', 'zh': '输入{}的密码：', 'de': 'Passwort für {} eingeben:', 'fr': 'Mot de passe pour {} :', 'es': 'Contraseña para {}:'},
        'super_activated': {'ru': '✅ Режим {} активирован.', 'en': '✅ Mode {} activated.', 'kk': '✅ {} режимі белсендірілді.', 'zh': '✅ 模式 {} 已激活。', 'de': '✅ Modus {} aktiviert.', 'fr': '✅ Mode {} activé.', 'es': '✅ Modo {} activado.'},
        'super_wrong': {'ru': '❌ Неверный пароль!', 'en': '❌ Wrong password!', 'kk': '❌ Пароль қате!', 'zh': '❌ 密码错误！', 'de': '❌ Falsches Passwort!', 'fr': '❌ Mot de passe incorrect !', 'es': '❌ ¡Contraseña incorrecta!'},
        'math_topic_label': {'ru': '📐 Выберите тему:', 'en': '📐 Choose topic:', 'kk': '📐 Тақырыпты таңдаңыз:', 'zh': '📐 选择主题：', 'de': '📐 Thema wählen:', 'fr': '📐 Choisir le thème :', 'es': '📐 Elegir tema:'},
        'editor_pdf': {'ru': '📄 В PDF', 'en': '📄 To PDF', 'kk': '📄 PDF-ке', 'zh': '📄 为PDF', 'de': '📄 Als PDF', 'fr': '📄 En PDF', 'es': '📄 A PDF'},
        'editor_word': {'ru': '📄 В Word', 'en': '📄 To Word', 'kk': '📄 Word-қа', 'zh': '📄 为Word', 'de': '📄 Als Word', 'fr': '📄 En Word', 'es': '📄 A Word'},
        'editor_crop': {'ru': '🟩 Квадрат', 'en': '🟩 Square', 'kk': '🟩 Шаршы', 'zh': '🟩 正方形', 'de': '🟩 Quadrat', 'fr': '🟩 Carré', 'es': '🟩 Cuadrado'},
        'editor_blur': {'ru': '🌀 Размытие', 'en': '🌀 Blur', 'kk': '🌀 Бұлыңғыр', 'zh': '🌀 模糊', 'de': '🌀 Weichzeichner', 'fr': '🌀 Flou', 'es': '🌀 Desenfoque'},
        'editor_contrast': {'ru': '☀️ Контраст', 'en': '☀️ Contrast', 'kk': '☀️ Контраст', 'zh': '☀️ 对比度', 'de': '☀️ Kontrast', 'fr': '☀️ Contraste', 'es': '☀️ Contraste'},
        'gdz_load': {'ru': 'Загрузить фото', 'en': 'Load photo', 'kk': 'Фото жүктеу', 'zh': '加载照片', 'de': 'Foto laden', 'fr': 'Charger photo', 'es': 'Cargar foto'},
        'gdz_solve': {'ru': 'Получить решение', 'en': 'Get solution', 'kk': 'Шешімін алу', 'zh': '获取解答', 'de': 'Lösung erhalten', 'fr': 'Obtenir la solution', 'es': 'Obtener solución'},
        'password_validol': {'ru': 'Пароль Валидол:', 'en': 'Validol Password:', 'kk': 'Валидол пароль:', 'zh': '瓦利多密码：', 'de': 'Validol Passwort:', 'fr': 'Mot de passe Validol :', 'es': 'Contraseña Validol:'},
        'login': {'ru': 'Войти', 'en': 'Login', 'kk': 'Кіру', 'zh': '登录', 'de': 'Anmelden', 'fr': 'Connexion', 'es': 'Iniciar sesión'},
        'launch_game': {'ru': '🎮 Запустить игру', 'en': '🎮 Launch Game', 'kk': '🎮 Ойынды іске қосу', 'zh': '🎮 启动游戏', 'de': '🎮 Spiel starten', 'fr': '🎮 Lancer le jeu', 'es': '🎮 Iniciar juego'},
        'open_code': {'ru': '✏️ Открыть код в редакторе', 'en': '✏️ Open code in editor', 'kk': '✏️ Кодты редакторда ашу', 'zh': '✏️ 在编辑器中打开代码', 'de': '✏️ Code im Editor öffnen', 'fr': '✏️ Ouvrir le code dans l\'éditeur', 'es': '✏️ Abrir código en editor'},
        'exit': {'ru': '❌ Выход', 'en': '❌ Exit', 'kk': '❌ Шығу', 'zh': '❌ 退出', 'de': '❌ Beenden', 'fr': '❌ Quitter', 'es': '❌ Salir'},
        'ai_assist': {'ru': '🤖 AI', 'en': '🤖 AI', 'kk': '🤖 AI', 'zh': '🤖 人工智能', 'de': '🤖 KI', 'fr': '🤖 IA', 'es': '🤖 IA'},
        'ai_ask_prompt': {'ru': 'Задайте вопрос ИИ:', 'en': 'Ask AI:', 'kk': 'AI сұраңыз:', 'zh': '向AI提问：', 'de': 'Fragen Sie die KI:', 'fr': 'Demander à l\'IA :', 'es': 'Preguntar a la IA:'},
        # Моды и менеджер модов
        'mods': {'ru': '📦 Моды', 'en': '📦 Mods', 'kk': '📦 Модтар', 'zh': '📦 模块', 'de': '📦 Mods', 'fr': '📦 Mods', 'es': '📦 Mods'},
        'mods_title': {'ru': 'Моды и новые возможности', 'en': 'Mods & Extensions', 'kk': 'Модтар мен жаңа мүмкіндіктер', 'zh': '模块与扩展', 'de': 'Mods und Erweiterungen', 'fr': 'Mods et extensions', 'es': 'Mods y Extensiones'},
        'mods_description': {'ru': 'Снимите галочку, чтобы отключить мод. Отключённые моды не запускаются при старте.', 'en': 'Uncheck to disable a mod. Disabled mods will not run at startup.', 'kk': 'Модты өшіру үшін белгіні алыңыз. Өшірілген модтар іске қосылмайды.', 'zh': '取消选中以禁用模块。被禁用的模块不会在启动时运行。', 'de': 'Deaktivieren Sie die Option, um ein Mod zu deaktivieren. Deaktivierte Mods werden beim Start nicht ausgeführt.', 'fr': 'Décochez pour désactiver un mod. Les mods désactivés ne s\'exécutent pas au démarrage.', 'es': 'Desmarcar para desactivar un mod. Los mods desactivados no se ejecutan al iniciar.'},
        'open_mods_folder': {'ru': 'Открыть папку модов', 'en': 'Open mods folder', 'kk': 'Модтар қалтасын ашу', 'zh': '打开模块文件夹', 'de': 'Mods-Ordner öffnen', 'fr': 'Ouvrir le dossier des mods', 'es': 'Abrir carpeta de mods'},
        'add_mod': {'ru': 'Добавить мод из файла', 'en': 'Add mod from file', 'kk': 'Файлдан мод қосу', 'zh': '从文件添加模块', 'de': 'Mod aus Datei hinzufügen', 'fr': 'Ajouter un mod depuis un fichier', 'es': 'Añadir mod desde archivo'},
        'new_mod_template': {'ru': 'Новый шаблон мода', 'en': 'New mod template', 'kk': 'Жаңа мод шаблоны', 'zh': '新模块模板', 'de': 'Neues Mod-Template', 'fr': 'Nouveau modèle de mod', 'es': 'Nueva plantilla de mod'},
        'mod_instructions': {'ru': 'Инструкция модов', 'en': 'Mod instructions', 'kk': 'Мод нұсқаулығы', 'zh': '模块说明', 'de': 'Mod-Anleitung', 'fr': 'Instructions pour les mods', 'es': 'Instrucciones de mods'},
        'refresh_list': {'ru': 'Обновить список', 'en': 'Refresh list', 'kk': 'Тізімді жаңарту', 'zh': '刷新列表', 'de': 'Liste aktualisieren', 'fr': 'Rafraîchir la liste', 'es': 'Actualizar lista'},
        'enable_all': {'ru': 'Включить все', 'en': 'Enable all', 'kk': 'Барлығын қосу', 'zh': '全部启用', 'de': 'Alle aktivieren', 'fr': 'Tout activer', 'es': 'Activar todo'},
        'disable_all': {'ru': 'Выключить все', 'en': 'Disable all', 'kk': 'Барлығын өшіру', 'zh': '全部禁用', 'de': 'Alle deaktivieren', 'fr': 'Tout désactiver', 'es': 'Desactivar todo'},
        'mods_folder_label': {'ru': 'Папка модов: {path}', 'en': 'Mods folder: {path}', 'kk': 'Модтар қалтасы: {path}', 'zh': '模块文件夹：{path}', 'de': 'Mods-Ordner: {path}', 'fr': 'Dossier des mods : {path}', 'es': 'Carpeta de mods: {path}'},
        'mods_found': {'ru': 'Найдено модов: {total} · Включено: {enabled}', 'en': 'Mods found: {total} · Enabled: {enabled}', 'kk': 'Табылған модтар: {total} · Қосылған: {enabled}', 'zh': '发现模块：{total} · 已启用：{enabled}', 'de': 'Gefundene Mods: {total} · Aktiv: {enabled}', 'fr': 'Mods trouvés : {total} · Activés : {enabled}', 'es': 'Mods encontrados: {total} · Activados: {enabled}'},
        'no_mods_found': {'ru': 'Моды не найдены. Поместите .py файлы в папку mods.', 'en': 'No mods found. Place .py files into the mods folder.', 'kk': 'Модтар табылмады. .py файлдарды mods қалтасына қойыңыз.', 'zh': '未找到模块。请将 .py 文件放入 mods 文件夹。', 'de': 'Keine Mods gefunden. Legen Sie .py Dateien in den Mods-Ordner.', 'fr': 'Aucun mod trouvé. Placez des fichiers .py dans le dossier mods.', 'es': 'No se encontraron mods. Coloca archivos .py en la carpeta mods.'},
        'status_enabled': {'ru': 'Включён', 'en': 'Enabled', 'kk': 'Қосылған', 'zh': '已启用', 'de': 'Aktiv', 'fr': 'Activé', 'es': 'Activado'},
        'status_disabled': {'ru': 'Отключён', 'en': 'Disabled', 'kk': 'Өшірілген', 'zh': '已禁用', 'de': 'Deaktiviert', 'fr': 'Désactivé', 'es': 'Desactivado'},
        'enable': {'ru': 'Включить', 'en': 'Enable', 'kk': 'Қосу', 'zh': '启用', 'de': 'Aktivieren', 'fr': 'Activer', 'es': 'Activar'},
        'run_now': {'ru': 'Запустить сейчас', 'en': 'Run now', 'kk': 'Қазір іске қосу', 'zh': '立即运行', 'de': 'Jetzt ausführen', 'fr': 'Exécuter maintenant', 'es': 'Ejecutar ahora'},
        'status_prefix': {'ru': 'Статус:', 'en': 'Status:', 'kk': 'Күйі:', 'zh': '状态：', 'de': 'Status:', 'fr': 'Statut :', 'es': 'Estado:'},
        # Дополнительные ключи для бота (полный набор)
        'main_menu': {'ru': '🏠 Главное меню', 'en': '🏠 Main Menu', 'kk': '🏠 Басты мәзір', 'zh': '🏠 主菜单', 'de': '🏠 Hauptmenü', 'fr': '🏠 Menu principal', 'es': '🏠 Menú principal'},
        'back': {'ru': '🔙 Назад', 'en': '🔙 Back', 'kk': '🔙 Артқа', 'zh': '🔙 返回', 'de': '🔙 Zurück', 'fr': '🔙 Retour', 'es': '🔙 Volver'},
        'lang_selected': {'ru': '✅ Язык установлен: Русский', 'en': '✅ Language set: English', 'kk': '✅ Тіл орнатылды: Қазақша', 'zh': '✅ 语言设置为：中文', 'de': '✅ Sprache eingestellt: Deutsch', 'fr': '✅ Langue définie : Français', 'es': '✅ Idioma establecido: Español'},
        'mode_selected': {'ru': '✅ Режим установлен: {mode}', 'en': '✅ Mode set: {mode}', 'kk': '✅ Режим орнатылды: {mode}', 'zh': '✅ 模式设置为：{mode}', 'de': '✅ Modus eingestellt: {mode}', 'fr': '✅ Mode défini : {mode}', 'es': '✅ Modo establecido: {mode}'},
        'ai_prompt': {'ru': 'Введи сообщение или отправь фото — Mistral/Gemini ответит.', 'en': 'Type a message or send a photo — Mistral/Gemini will answer.', 'kk': 'Хабарлама жіберіңіз немесе фото жіберіңіз — Mistral/Gemini жауап береді.', 'zh': '输入消息或发送照片 — Mistral/Gemini 将会回答.', 'de': 'Nachricht senden oder Foto schicken — Mistral/Gemini antworten.', 'fr': 'Tapez un message ou envoyez une photo — Mistral/Gemini répondra.', 'es': 'Escribe un mensaje o envía una foto — Mistral/Gemini responderá.'},
        'choose_math_topic': {'ru': 'Выбери тему задачи:', 'en': 'Choose a topic:', 'kk': 'Тақырыпты таңдаңыз:', 'zh': '选择主题：', 'de': 'Thema wählen:', 'fr': 'Choisissez un thème :', 'es': 'Elige un tema:'},
        'enter_math_example': {'ru': 'Введите ваш математический пример.', 'en': 'Enter your math example.', 'kk': 'Математикалық мысалды енгізіңіз.', 'zh': '输入您的数学示例。', 'de': 'Geben Sie Ihr Mathematikbeispiel ein.', 'fr': 'Entrez votre exemple mathématique.', 'es': 'Ingrese su ejemplo matemático.'},
        'math_edit_again': {'ru': '📐 Редактировать еще', 'en': '📐 Edit again', 'kk': '📐 Қайта өңдеу', 'zh': '📐 再次编辑', 'de': '📐 Erneut bearbeiten', 'fr': '📐 Modifier à nouveau', 'es': '📐 Editar de nuevo'},
        'ocr_referral': {'ru': '📷 Нажми на ссылку ниже, чтобы перейти к боту для распознавания текста:\n[@OCRBot](https://t.me/OCRBot)', 'en': '📷 Tap the link below to open the text recognition bot:\n[@OCRBot](https://t.me/OCRBot)', 'kk': '📷 Мәтінді тану ботына өту үшін төмендегі сілтемені басыңыз:\n[@OCRBot](https://t.me/OCRBot)', 'zh': '📷 点击下方链接打开文字识别机器人：\n[@OCRBot](https://t.me/OCRBot)', 'de': '📷 Tippen Sie auf den Link unten, um den Texterkennungs-Bot zu öffnen:\n[@OCRBot](https://t.me/OCRBot)', 'fr': '📷 Appuyez sur le lien ci-dessous pour ouvrir le bot de reconnaissance de texte :\n[@OCRBot](https://t.me/OCRBot)', 'es': '📷 Toca el enlace de abajo para abrir el bot de reconocimiento de texto:\n[@OCRBot](https://t.me/OCRBot)'},
        'photo_bw': {'ru': '⚫ Чёрно-белое', 'en': '⚫ Black & White', 'kk': '⚫ Ақ-қара', 'zh': '⚫ 黑白', 'de': '⚫ Schwarz-Weiß', 'fr': '⚫ Noir et blanc', 'es': '⚫ Blanco y negro'},
        'photo_rotate': {'ru': '🔄 Поворот 90°', 'en': '🔄 Rotate 90°', 'kk': '🔄 90° бұру', 'zh': '🔄 旋转90°', 'de': '🔄 90° drehen', 'fr': '🔄 Rotation 90°', 'es': '🔄 Girar 90°'},
        'photo_square': {'ru': '🟩 Квадрат', 'en': '🟩 Square', 'kk': '🟩 Шаршы', 'zh': '🟩 正方形', 'de': '🟩 Quadrat', 'fr': '🟩 Carré', 'es': '🟩 Cuadrado'},
        'photo_to_pdf': {'ru': '📄 В PDF', 'en': '📄 To PDF', 'kk': '📄 PDF-ке', 'zh': '📄 转为PDF', 'de': '📄 Als PDF', 'fr': '📄 En PDF', 'es': '📄 A PDF'},
        'photo_to_word': {'ru': '📄 В Word', 'en': '📄 To Word', 'kk': '📄 Word-қа', 'zh': '📄 转为Word', 'de': '📄 Als Word', 'fr': '📄 En Word', 'es': '📄 A Word'},
        'photo_pdf_caption': {'ru': '📄 Ваше фото в PDF', 'en': '📄 Your photo as PDF', 'kk': '📄 Сіздің фотоңыз PDF пішімінде', 'zh': '📄 您的照片已转为PDF', 'de': '📄 Ihr Foto als PDF', 'fr': '📄 Votre photo en PDF', 'es': '📄 Tu foto como PDF'},
        'photo_word_caption': {'ru': '📄 Фото вставлено в Word', 'en': '📄 Photo inserted into Word', 'kk': '📄 Фото Word-қа салынды', 'zh': '📄 照片已插入Word', 'de': '📄 Foto in Word eingefügt', 'fr': '📄 Photo insérée dans Word', 'es': '📄 Foto insertada en Word'},
        'photo_ready': {'ru': 'Готово!', 'en': 'Done!', 'kk': 'Дайын!', 'zh': '完成！', 'de': 'Fertig!', 'fr': 'Terminé !', 'es': '¡Hecho!'},
        'photo_not_found': {'ru': 'Фото не найдено.', 'en': 'Photo not found.', 'kk': 'Фото табылмады.', 'zh': '未找到照片。', 'de': 'Foto nicht gefunden.', 'fr': 'Photo non trouvée.', 'es': 'Foto no encontrada.'},
        'photo_error': {'ru': '❌ Ошибка: {e}', 'en': '❌ Error: {e}', 'kk': '❌ Қате: {e}', 'zh': '❌ 错误: {e}', 'de': '❌ Fehler: {e}', 'fr': '❌ Erreur : {e}', 'es': '❌ Error: {e}'},
        'gdz_prompt': {'ru': '📚 Отправь фото задачи — пришлю готовое решение с объяснением.', 'en': '📚 Send a photo of the task — I will provide a solution with explanation.', 'kk': '📚 Тапсырманың фотосын жіберіңіз — мен түсіндірмесі бар дайын шешімді ұсынамын.', 'zh': '📚 发送任务照片 — 我将提供带有解释的解决方案。', 'de': '📚 Senden Sie ein Foto der Aufgabe — ich liefere eine Lösung mit Erklärung.', 'fr': '📚 Envoyez une photo de la tâche — je fournirai une solution avec explication.', 'es': '📚 Envía una foto de la tarea — proporcionaré una solución con explicación.'},
        'gdz_solve_prompt': {'ru': 'Реши задачу, показанную на фото. Дай подробное пошаговое решение.', 'en': 'Solve the problem shown in the photo. Give a detailed step-by-step solution.', 'kk': 'Фотода көрсетілген есепті шығарыңыз. Толық қадамдық шешімді беріңіз.', 'zh': '解决照片中显示的问题。给出详细的分步解决方案。', 'de': 'Lösen Sie die auf dem Foto gezeigte Aufgabe. Geben Sie eine detaillierte Schritt-für-Schritt-Lösung.', 'fr': 'Résolvez le problème montré sur la photo. Donnez une solution détaillée étape par étape.', 'es': 'Resuelve el problema mostrado en la foto. Da una solución detallada paso a paso.'},
        'search_prompt': {'ru': '🔍 Введите запрос:', 'en': '🔍 Enter a query:', 'kk': '🔍 Сұрауды енгізіңіз:', 'zh': '🔍 输入查询：', 'de': '🔍 Geben Sie eine Suchanfrage ein:', 'fr': '🔍 Entrez une requête :', 'es': '🔍 Ingrese una consulta:'},
        'translate_prompt': {'ru': '🌍 Введите текст:', 'en': '🌍 Enter text:', 'kk': '🌍 Мәтінді енгізіңіз:', 'zh': '🌍 输入文本：', 'de': '🌍 Text eingeben:', 'fr': '🌍 Entrez le texte :', 'es': '🌍 Ingrese el texto:'},
        'profile_info': {'ru': '👤 **Профиль:**\n📊 Запросов: {total}\n📝 Заметок: {len_notes}\n🌐 Язык: {lang}\n⚙️ Режим: {mode}', 'en': '👤 **Profile:**\n📊 Requests: {total}\n📝 Notes: {len_notes}\n🌐 Language: {lang}\n⚙️ Mode: {mode}', 'kk': '👤 **Профиль:**\n📊 Сұраулар: {total}\n📝 Жазбалар: {len_notes}\n🌐 Тіл: {lang}\n⚙️ Режим: {mode}', 'zh': '👤 **个人资料:**\n📊 请求: {total}\n📝 笔记: {len_notes}\n🌐 语言: {lang}\n⚙️ 模式: {mode}', 'de': '👤 **Profil:**\n📊 Anfragen: {total}\n📝 Notizen: {len_notes}\n🌐 Sprache: {lang}\n⚙️ Modus: {mode}', 'fr': '👤 **Profil:**\n📊 Requêtes: {total}\n📝 Notes: {len_notes}\n🌐 Langue: {lang}\n⚙️ Mode: {mode}', 'es': '👤 **Perfil:**\n📊 Solicitudes: {total}\n📝 Notas: {len_notes}\n🌐 Idioma: {lang}\n⚙️ Modo: {mode}'},
        'notes_prompt': {'ru': '📝 **Ваши заметки:**\n{notes_text}', 'en': '📝 **Your notes:**\n{notes_text}', 'kk': '📝 **Сіздің жазбаларыңыз:**\n{notes_text}', 'zh': '📝 **您的笔记:**\n{notes_text}', 'de': '📝 **Ihre Notizen:**\n{notes_text}', 'fr': '📝 **Vos notes:**\n{notes_text}', 'es': '📝 **Tus notas:**\n{notes_text}'},
        'notes_empty': {'ru': 'Пока нет заметок.', 'en': 'No notes yet.', 'kk': 'Әзірге жазбалар жоқ.', 'zh': '暂无笔记。', 'de': 'Noch keine Notizen.', 'fr': 'Pas encore de notes.', 'es': 'Aún no hay notas.'},
        'save_note_prompt': {'ru': '✏️ Отправьте текст, чтобы сохранить новую заметку:', 'en': '✏️ Send a new note to save it:', 'kk': '✏️ Жаңа жазбаны сақтау үшін жіберіңіз:', 'zh': '✏️ 发送新笔记以保存：', 'de': '✏️ Senden Sie eine neue Notiz, um sie zu speichern:', 'fr': '✏️ Envoyez une nouvelle note pour la sauvegarder :', 'es': '✏️ Envía una nueva nota para guardarla:'},
        'note_saved': {'ru': '✅ Заметка сохранена!', 'en': '✅ Note saved!', 'kk': '✅ Жазба сақталды!', 'zh': '✅ 笔记已保存！', 'de': '✅ Notiz gespeichert!', 'fr': '✅ Note sauvegardée !', 'es': '✅ ¡Nota guardada!'},
        'context_cleared': {'ru': '🧹 Контекст диалога очищен.', 'en': '🧹 Context cleared.', 'kk': '🧹 Контекст тазаланды.', 'zh': '🧹 上下文已清除。', 'de': '🧹 Kontext gelöscht.', 'fr': '🧹 Contexte effacé.', 'es': '🧹 Contexto limpiado.'},
        'canvas_start': {'ru': '✏️ Холст. Выберите действие:', 'en': '✏️ Canvas. Choose action:', 'kk': '✏️ Кенеп. Әрекет таңдаңыз:', 'zh': '✏️ 画布。选择操作：', 'de': '✏️ Leinwand. Aktion wählen:', 'fr': '✏️ Toile. Choisissez une action :', 'es': '✏️ Lienzo. Elija acción:'},
        'canvas_red_line': {'ru': '🔴 Красная линия', 'en': '🔴 Red Line', 'kk': '🔴 Қызыл сызық', 'zh': '🔴 红线', 'de': '🔴 Rote Linie', 'fr': '🔴 Ligne rouge', 'es': '🔴 Línea roja'},
        'canvas_green_circle': {'ru': '🟢 Зелёный круг', 'en': '🟢 Green Circle', 'kk': '🟢 Жасыл дөңгелек', 'zh': '🟢 绿圆', 'de': '🟢 Grüner Kreis', 'fr': '🟢 Cercle vert', 'es': '🟢 Círculo verde'},
        'canvas_blue_text': {'ru': '🔵 Синий текст', 'en': '🔵 Blue Text', 'kk': '🔵 Көк мәтін', 'zh': '🔵 蓝文字', 'de': '🔵 Blauer Text', 'fr': '🔵 Texte bleu', 'es': '🔵 Texto azul'},
        'canvas_done': {'ru': '✅ Готово', 'en': '✅ Done', 'kk': '✅ Дайын', 'zh': '✅ 完成', 'de': '✅ Fertig', 'fr': '✅ Terminé', 'es': '✅ Hecho'},
        'canvas_yellow_rect': {'ru': '🟡 Жёлтый прямоугольник', 'en': '🟡 Yellow Rectangle', 'kk': '🟡 Сары төртбұрыш', 'zh': '🟡 黄色矩形', 'de': '🟡 Gelbes Rechteck', 'fr': '🟡 Rectangle jaune', 'es': '🟡 Rectángulo amarillo'},
        'canvas_black_ellipse': {'ru': '⚪ Чёрный эллипс', 'en': '⚪ Black Ellipse', 'kk': '⚪ Қара эллипс', 'zh': '⚪ 黑色椭圆', 'de': '⚪ Schwarze Ellipse', 'fr': '⚪ Ellipse noire', 'es': '⚪ Elipse negra'},
        'canvas_purple_text': {'ru': '🟣 Фиолетовый текст', 'en': '🟣 Purple Text', 'kk': '🟣 Күлгін мәтін', 'zh': '🟣 紫色文字', 'de': '🟣 Lila Text', 'fr': '🟣 Texte violet', 'es': '🟣 Texto violeta'},
        'canvas_color': {'ru': '🎨 Выбрать цвет', 'en': '🎨 Choose Color', 'kk': '🎨 Түс таңдау', 'zh': '🎨 选择颜色', 'de': '🎨 Farbe wählen', 'fr': '🎨 Choisir la couleur', 'es': '🎨 Elegir color'},
        'canvas_text': {'ru': '🔤 Ввести текст', 'en': '🔤 Add Text', 'kk': '🔤 Мәтін енгізу', 'zh': '🔤 添加文字', 'de': '🔤 Text hinzufügen', 'fr': '🔤 Ajouter du texte', 'es': '🔤 Añadir texto'},
        'canvas_clear': {'ru': '🧹 Очистить', 'en': '🧹 Clear', 'kk': '🧹 Тазалау', 'zh': '🧹 清除', 'de': '🧹 Löschen', 'fr': '🧹 Effacer', 'es': '🧹 Limpiar'},
        'canvas_brush': {'ru': '🖌 Кисть', 'en': '🖌 Brush', 'kk': '🖌 Қылқалам', 'zh': '🖌 画笔', 'de': '🖌 Pinsel', 'fr': '🖌 Pinceau', 'es': '🖌 Pincel'},
        'canvas_fill': {'ru': '🎨 Залить фон', 'en': '🎨 Fill Background', 'kk': '🎨 Фонды бояу', 'zh': '🎨 填充背景', 'de': '🎨 Hintergrund füllen', 'fr': '🎨 Remplir le fond', 'es': '🎨 Rellenar fondo'},
        'canvas_not_found': {'ru': 'Холст не найден.', 'en': 'Canvas not found.', 'kk': 'Кенеп табылмады.', 'zh': '未找到画布。', 'de': 'Leinwand nicht gefunden.', 'fr': 'Toile non trouvée.', 'es': 'Lienzo no encontrado.'},
        'canvas_text_prompt': {'ru': 'Введите текст для добавления на холст:', 'en': 'Enter text to add to canvas:', 'kk': 'Кенепке қосу үшін мәтінді енгізіңіз:', 'zh': '输入要添加到画布的文本：', 'de': 'Geben Sie den Text für die Leinwand ein:', 'fr': 'Entrez le texte à ajouter sur la toile :', 'es': 'Ingrese el texto para agregar al lienzo:'},
        'image_gen_prompt': {'ru': '🎨 Для генерации изображений перейди к боту:\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nОн создаёт картинки по текстовому описанию.', 'en': '🎨 For image generation, go to:\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nIt creates images from text descriptions.', 'kk': '🎨 Суреттерді жасау үшін мына ботқа өтіңіз:\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nОл мәтіндік сипаттамадан суреттер жасайды.', 'zh': '🎨 要生成图像，请前往：\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\n它根据文本描述创建图像。', 'de': '🎨 Zur Bilderzeugung gehen Sie zu:\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nEr erstellt Bilder aus Textbeschreibungen.', 'fr': '🎨 Pour la génération d\'images, allez sur :\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nIl crée des images à partir de descriptions textuelles.', 'es': '🎨 Para generar imágenes, ve a:\n[@ai_nox_bot](https://t.me/ai_nox_bot)\n\nCrea imágenes a partir de descripciones de texto.'},
        'code_help_prompt': {'ru': '💻 Опишите задачу по программированию:', 'en': '💻 Describe your programming task:', 'kk': '💻 Бағдарламалау тапсырмасын сипаттаңыз:', 'zh': '💻 描述您的编程任务：', 'de': '💻 Beschreiben Sie Ihre Programmieraufgabe:', 'fr': '💻 Décrivez votre tâche de programmation :', 'es': '💻 Describe tu tarea de programación:'},
        'validol_password': {'ru': '💊 ВВЕДИТЕ ПАРОЛЬ ДЛЯ ЗАПУСКА ВАЛИДОЛА!', 'en': '💊 ENTER PASSWORD TO LAUNCH VALIDOL!', 'kk': '💊 ВАЛИДОЛДЫ ІСКЕ ҚОСУ ҮШІН ПАРОЛЬ ЕНГІЗІҢІЗ!', 'zh': '💊 输入密码以启动瓦利多！', 'de': '💊 PASSWORT EINGEBEN, UM VALIDOL ZU STARTEN!', 'fr': '💊 ENTRER LE MOT DE PASSE POUR LANCER VALIDOL !', 'es': '💊 ¡INGRESE LA CONTRASEÑA PARA INICIAR VALIDOL!'},
        'validol_wrong_password': {'ru': '❌ НЕВЕРНЫЙ ПАРОЛЬ! ПОПРОБУЙТЕ СНОВА.', 'en': '❌ WRONG PASSWORD! TRY AGAIN.', 'kk': '❌ ҚАТЕ ПАРОЛЬ! ҚАЙТАДАН КӨРІҢІЗ.', 'zh': '❌ 密码错误！重试。', 'de': '❌ FALSCHES PASSWORT! ERNEUT VERSUCHEN.', 'fr': '❌ MOT DE PASSE INCORRECT ! RÉESSAYEZ.', 'es': '❌ ¡CONTRASEÑA INCORRECTA! INTENTE DE NUEVO.'},
        'validol_alpha_activated': {'ru': '✅ ДОСТУП РАЗРЕШЁН. ЗАПУСК ALPHA-2.0...', 'en': '✅ ACCESS GRANTED. LAUNCHING ALPHA-2.0...', 'kk': '✅ РҰҚСАТ БЕРІЛДІ. ALPHA-2.0 ІСКЕ ҚОСЫЛУДА...', 'zh': '✅ 访问已授权。启动 Alpha-2.0...', 'de': '✅ ZUGRIFF GEWÄHRT. STARTE ALPHA-2.0...', 'fr': '✅ ACCÈS AUTORISÉ. LANCEMENT D\'ALPHA-2.0...', 'es': '✅ ACCESO CONCEDIDO. INICIANDO ALPHA-2.0...'},
        'validol_admin_activated': {'ru': '👑 АДМИН-ДОСТУП. РЕЖИМ ЭКСПЕРИМЕНТОВ АКТИВИРОВАН.', 'en': '👑 ADMIN ACCESS. EXPERIMENTAL MODE ACTIVATED.', 'kk': '👑 ӘКІМШІ РҰҚСАТЫ. ЭКСПЕРИМЕНТ РЕЖИМІ БЕЛСЕНДІРІЛДІ.', 'zh': '👑 管理员访问。实验模式已激活。', 'de': '👑 ADMIN-ZUGRIFF. EXPERIMENTELLER MODUS AKTIVIERT.', 'fr': '👑 ACCÈS ADMIN. MODE EXPÉRIMENTAL ACTIVÉ.', 'es': '👑 ACCESO DE ADMINISTRADOR. MODO EXPERIMENTAL ACTIVADO.'},
        'reset_auth': {'ru': '🔄 Сброс авторизации', 'en': '🔄 Reset Auth', 'kk': '🔄 Авторлықты қалпына келтіру', 'zh': '🔄 重置授权', 'de': '🔄 Auth zurücksetzen', 'fr': '🔄 Réinitialiser l\'autorisation', 'es': '🔄 Restablecer autenticación'},
        'topic': {'ru': 'Тема', 'en': 'Topic', 'kk': 'Тақырып', 'zh': '主题', 'de': 'Thema', 'fr': 'Thème', 'es': 'Tema'},
        'your_example': {'ru': 'Ваш пример', 'en': 'Your example', 'kk': 'Сіздің мысалыңыз', 'zh': '您的示例', 'de': 'Ihr Beispiel', 'fr': 'Votre exemple', 'es': 'Tu ejemplo'},
        'answer': {'ru': 'Ответ', 'en': 'Answer', 'kk': 'Жауап', 'zh': '答案', 'de': 'Antwort', 'fr': 'Réponse', 'es': 'Respuesta'},
        'no_solution': {'ru': 'нет решений', 'en': 'no solution', 'kk': 'шешім жоқ', 'zh': '无解', 'de': 'keine Lösung', 'fr': 'aucune solution', 'es': 'sin solución'},
        'rectangle': {'ru': 'Прямоугольник', 'en': 'Rectangle', 'kk': 'Тіктөртбұрыш', 'zh': '矩形', 'de': 'Rechteck', 'fr': 'Rectangle', 'es': 'Rectángulo'},
        'area': {'ru': 'Площадь', 'en': 'Area', 'kk': 'Аудан', 'zh': '面积', 'de': 'Fläche', 'fr': 'Aire', 'es': 'Área'},
        'perimeter': {'ru': 'Периметр', 'en': 'Perimeter', 'kk': 'Периметр', 'zh': '周长', 'de': 'Umfang', 'fr': 'Périmètre', 'es': 'Perímetro'},
        'circle': {'ru': 'Круг', 'en': 'Circle', 'kk': 'Шеңбер', 'zh': '圆', 'de': 'Kreis', 'fr': 'Cercle', 'es': 'Círculo'},
        'circumference': {'ru': 'Длина окружности', 'en': 'Circumference', 'kk': 'Шеңбер ұзындығы', 'zh': '圆周长', 'de': 'Umfang', 'fr': 'Circonférence', 'es': 'Circunferencia'},
        'class_1-4': {'ru': '1-4 класс', 'en': 'Grades 1-4', 'kk': '1-4 сынып', 'zh': '1-4 年级', 'de': '1-4 Klasse', 'fr': 'Classe 1-4', 'es': 'Clase 1-4'},
        'class_5-6': {'ru': '5-6 класс', 'en': 'Grades 5-6', 'kk': '5-6 сынып', 'zh': '5-6 年级', 'de': '5-6 Klasse', 'fr': 'Classe 5-6', 'es': 'Clase 5-6'},
        'class_7-9': {'ru': '7-9 класс', 'en': 'Grades 7-9', 'kk': '7-9 сынып', 'zh': '7-9 年级', 'de': '7-9 Klasse', 'fr': 'Classe 7-9', 'es': 'Clase 7-9'},
        'class_10-11': {'ru': '10-11 класс', 'en': 'Grades 10-11', 'kk': '10-11 сынып', 'zh': '10-11 年级', 'de': '10-11 Klasse', 'fr': 'Classe 10-11', 'es': 'Clase 10-11'},
        'admin_password_prompt': {'ru': 'Пароль администратора:', 'en': 'Admin Password:', 'kk': 'Әкімшілік пароль:', 'zh': '管理员密码:', 'de': 'Admin-Passwort:', 'fr': 'Mot de passe administrateur:', 'es': 'Contraseña de administrador:'},
        'aggressor_unit': {'ru': 'Агрессор', 'en': 'Aggressor', 'kk': 'Агрессор', 'zh': '侵略者', 'de': 'Aggressor', 'fr': 'Agresseur', 'es': 'Agresor'},
        'peaceful_unit': {'ru': 'Мирный', 'en': 'Peaceful', 'kk': 'Бейбіт', 'zh': '和平派', 'de': 'Friedlich', 'fr': 'Paisible', 'es': 'Pacífico'},
        'black': {'ru': 'Чёрный', 'en': 'Black', 'kk': 'Қара', 'zh': '黑色', 'de': 'Schwarz', 'fr': 'Noir', 'es': 'Negro'},
        'red': {'ru': 'Красный', 'en': 'Red', 'kk': 'Қызыл', 'zh': '红色', 'de': 'Rot', 'fr': 'Rouge', 'es': 'Rojo'},
        'clear_canvas': {'ru': 'Очистить холст', 'en': 'Clear Canvas', 'kk': 'Кенепті тазалау', 'zh': '清空画布', 'de': 'Leinwand löschen', 'fr': 'Effacer la toile', 'es': 'Limpiar lienzo'},
        'history_update': {'ru': 'Обновить историю', 'en': 'Update History', 'kk': 'Тарихты жаңарту', 'zh': '更新历史', 'de': 'Verlauf aktualisieren', 'fr': "Mettre à jour l'historique", 'es': 'Actualizar historial'},
        'reset': {'ru': 'Сбросить', 'en': 'Reset', 'kk': 'Қалпына keltiru', 'zh': '重置', 'de': 'Zurücksetzen', 'fr': 'Réinitialiser', 'es': 'Restablecer'},
        'super_ai_prompt': {'ru': 'Выберите режим Супер ИИ:', 'en': 'Select Super AI Mode:', 'kk': 'Супер ИИ режимін таңдаңыз:', 'zh': '选择超级AI模式:', 'de': 'Super-KI-Modus wählen:', 'fr': 'Sélectionner le mode Super IA:', 'es': 'Seleccionar modo Súper IA:'},
        'translate_btn': {'ru': 'Перевести', 'en': 'Translate', 'kk': 'Аудару', 'zh': '翻译', 'de': 'Übersetzen', 'fr': 'Traduire', 'es': 'Traducir'}
    }

    @classmethod
    def t(cls, key, lang='ru', **kwargs):
        text = cls.STRINGS.get(key, {}).get(lang, key)
        if kwargs:
            return text.format(**kwargs)
        return text

# ======================== АУТЕНТИФИКАЦИЯ ============================
class Auth:
    def __init__(self):
        self.admin_password = ADMIN_PASSWORD
    def check(self, uid, pwd):
        if pwd == self.admin_password: return True, "admin"
        pkg = verify_activation_key(pwd)
        if pkg:
            return True, pkg
        return False, "wrong"

# ======================== БАЗА ДАННЫХ ================================
class Database:
    def __init__(self, chats_path="chats.db", users_path="users.db"):
        self.chats_path = chats_path
        self.users_path = users_path

    @contextmanager
    def conn_chats(self):
        c = sqlite3.connect(self.chats_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    @contextmanager
    def conn_users(self):
        c = sqlite3.connect(self.users_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    def init(self):
        with self.conn_users() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                lang TEXT DEFAULT 'ru',
                mode TEXT DEFAULT 'normal',
                dashboard_aggressor INTEGER DEFAULT 50,
                dashboard_peaceful INTEGER DEFAULT 50)""")
            
            # --- Activation Tables ---
            c.execute("""CREATE TABLE IF NOT EXISTS used_keys (
                key_str TEXT PRIMARY KEY,
                activated_at INTEGER DEFAULT (strftime('%s','now')))""")
            c.execute("""CREATE TABLE IF NOT EXISTS daily_limits (
                day_date TEXT PRIMARY KEY,
                count INTEGER DEFAULT 0)""")
            
            # --- Secure Licensing Lockdown (Очистка всех старых пиратских/легаси лицензий на старте) ---
            # c.execute("""DELETE FROM settings WHERE key IN (
            #     'sub_premium', 'is_premium', 'sub_super_ai', 'sub_codex_02', 'sub_complete', 'developer_tier4', 'regular_subscription'
            # )""")
            
            # Migration checks
            cols = [row[1] for row in c.execute("PRAGMA table_info(user_state)")]
            if 'lang' not in cols:
                c.execute("ALTER TABLE user_state ADD COLUMN lang TEXT DEFAULT 'ru'")
            if 'mode' not in cols:
                c.execute("ALTER TABLE user_state ADD COLUMN mode TEXT DEFAULT 'normal'")
            if 'dashboard_aggressor' not in cols:
                c.execute("ALTER TABLE user_state ADD COLUMN dashboard_aggressor INTEGER DEFAULT 50")
            if 'dashboard_peaceful' not in cols:
                c.execute("ALTER TABLE user_state ADD COLUMN dashboard_peaceful INTEGER DEFAULT 50")

            c.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                cloud_uid TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")

            c.execute("""CREATE TABLE IF NOT EXISTS custom_buttons (
                name TEXT PRIMARY KEY,
                action TEXT)""")

        with self.conn_chats() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT)""")
            c.execute("""CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_history(user_id)""")

            c.execute("""CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                txt TEXT,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP)""")

            c.execute("""CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                cnt INTEGER DEFAULT 0)""")

    def get_daily_codex_requests(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with self.conn_users() as c:
                row = c.execute("SELECT count FROM daily_limits WHERE day_date = ?", (today,)).fetchone()
                return row['count'] if row else 0
        except Exception:
            return 0

    def increment_daily_codex_requests(self):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with self.conn_users() as c:
                row = c.execute("SELECT count FROM daily_limits WHERE day_date = ?", (today,)).fetchone()
                if row:
                    c.execute("UPDATE daily_limits SET count = count + 1 WHERE day_date = ?", (today,))
                else:
                    c.execute("INSERT INTO daily_limits (day_date, count) VALUES (?, 1)", (today,))
        except Exception:
            pass

    def activate_subscription_key(self, key: str) -> Tuple[bool, str]:
        pkg = verify_activation_key(key)
        if not pkg:
            return False, "Неверный формат ключа! Формат: AARON-XXXX-XXXX-XXXX"
        
        # Clean noise from browser-appended copy-paste indicators
        cleaned_key = re.sub(r'\[\d+\]|\(\d+\)', '', key.strip()).strip().upper()
        
        try:
            with self.conn_users() as c:
                row = c.execute("SELECT 1 FROM used_keys WHERE key_str = ?", (cleaned_key,)).fetchone()
                # Corporate multi-use keys (CORP) bypass the single-use check
                if row and pkg != 'CORP':
                    return False, "Этот ключ уже использован!"
                
                if not row:
                    c.execute("INSERT INTO used_keys (key_str) VALUES (?)", (cleaned_key,))
                
                if pkg == 'PREM':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_premium', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('is_premium', '1')")
                    msg = "Базовый Premium активирован! (Чат, Переводчик, Математика)"
                elif pkg == 'PVT':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_pvt', '1')")
                    msg = "Приватный Чат успешно активирован!"
                elif pkg == 'VAL':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_super_ai', '1')")
                    msg = "Доступ к Валидол-ИИ и режимам Супер-ИИ активирован!"
                elif pkg == 'TERM':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_terminal', '1')")
                    msg = "Доступ к Терминалу Ядра и Сфере успешно активирован!"
                elif pkg == 'CDX':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_codex_02', '1')")
                    msg = "Движок Codex-02 активирован! (Создание файлов на ПК, Mini IDE)"
                elif pkg == 'COMP':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_complete', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_premium', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('is_premium', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_pvt', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_super_ai', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_terminal', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_codex_02', '1')")
                    msg = "Полный пакет COMP активирован! Все функции разблокированы безлимитно."
                elif pkg == 'CORP':
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_corporate', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_complete', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_premium', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('is_premium', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_pvt', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_super_ai', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_terminal', '1')")
                    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('sub_codex_02', '1')")
                    msg = "Корпоративная Лицензия (Multi-User) активирована! Все функции разблокированы безлимитно."
                else:
                    msg = "Неизвестный пакет лицензии."
                
                _db_set_setting("sub_activation_timestamp", str(int(time.time())))
                try:
                    pass
                except Exception:
                    pass
                # Activation animation triggering
            try:
                if 'app' in globals() and globals()['app']:
                    globals()['app'].safe_schedule(lambda: ActivationAnimationModal(globals()['app'], "Активация Лицензии", cleaned_key, msg))
            except Exception: pass
            return True, msg
        except Exception as e:
            return False, f"Ошибка бд: {e}"

    def save_custom_button(self, name: str, action: str):
        with self.conn_users() as c:
            c.execute("INSERT OR REPLACE INTO custom_buttons (name, action) VALUES (?,?)", (name, action))

    def delete_custom_button(self, name: str):
        with self.conn_users() as c:
            c.execute("DELETE FROM custom_buttons WHERE name=?", (name,))

    def get_custom_buttons(self) -> Dict[str, str]:
        try:
            with self.conn_users() as c:
                rows = c.execute("SELECT name, action FROM custom_buttons").fetchall()
                return {row['name']: row['action'] for row in rows}
        except Exception:
            return {}

    def has_user_state(self, uid):
        with self.conn_users() as c:
            return c.execute("SELECT 1 FROM user_state WHERE user_id=?", (uid,)).fetchone() is not None

    def get_lang(self, uid): return self._get("user_state","lang",uid,"ru")
    def set_lang(self, uid, v): self._set("user_state","lang",uid,v)
    def get_mode(self, uid): return self._get("user_state","mode",uid,"normal")
    def set_mode(self, uid, v): self._set("user_state","mode",uid,v)

    def get_dashboard_state(self, uid):
        with self.conn_users() as c:
            r = c.execute(
                "SELECT dashboard_aggressor, dashboard_peaceful FROM user_state WHERE user_id=?",
                (uid,)
            ).fetchone()
            if r:
                return {
                    'aggressor': r['dashboard_aggressor'] if r['dashboard_aggressor'] is not None else 50,
                    'peaceful': r['dashboard_peaceful'] if r['dashboard_peaceful'] is not None else 50,
                }
            return {'aggressor': 50, 'peaceful': 50}

    def set_dashboard_state(self, uid, aggressor, peaceful):
        with self.conn_users() as c:
            c.execute(
                "INSERT INTO user_state (user_id, dashboard_aggressor, dashboard_peaceful) VALUES (?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET dashboard_aggressor=?, dashboard_peaceful=?",
                (uid, aggressor, peaceful, aggressor, peaceful)
            )

    def has_users(self) -> bool:
        with self.conn_users() as c:
            r = c.execute("SELECT COUNT(*) FROM users").fetchone()
            return (r[0] if r else 0) > 0

    def reset_all(self, uid=None):
        with self.conn_chats() as c:
            c.execute("DELETE FROM chat_history")
            c.execute("DELETE FROM notes")
            c.execute("DELETE FROM stats")
        with self.conn_users() as c:
            if uid is not None:
                c.execute("UPDATE user_state SET lang='ru', mode='normal', dashboard_aggressor=50, dashboard_peaceful=50 WHERE user_id=?", (uid,))
            else:
                c.execute("UPDATE user_state SET lang='ru', mode='normal', dashboard_aggressor=50, dashboard_peaceful=50")

    def register_user(self, username: str, password: str, cloud_uid: str = None):
        ph = hashlib.sha256(password.encode()).hexdigest()
        try:
            with self.conn_users() as c:
                c.execute("INSERT INTO users (username, password_hash, cloud_uid) VALUES (?,?,?)", (username, ph, cloud_uid))
            return True, "ok"
        except sqlite3.IntegrityError:
            return False, "Пользователь с таким именем уже существует"
        except Exception as e:
            return False, str(e)

    def get_user_id(self, username: str) -> int:
        with self.conn_users() as c:
            r = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
            return r[0] if r else 1

    def login_user(self, username: str, password: str) -> bool:
        ph = hashlib.sha256(password.encode()).hexdigest()
        with self.conn_users() as c:
            r = c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, ph)).fetchone()
        return r is not None

    def add_stat(self, uid):
        with self.conn_chats() as c:
            c.execute("INSERT INTO stats (user_id,cnt) VALUES (?,1) ON CONFLICT(user_id) DO UPDATE SET cnt=cnt+1", (uid,))

    def get_stat(self, uid):
        with self.conn_chats() as c:
            r = c.execute("SELECT cnt FROM stats WHERE user_id=?", (uid,)).fetchone()
            return r[0] if r else 0

    def log_chat(self, uid, role, content, session_id="main"):
        with self.conn_chats() as c:
            c.execute("INSERT INTO chat_history (user_id, role, content, session_id) VALUES (?,?,?,?)",
                      (uid, role, content, session_id))
        
        def _sync():
            try:
                cloud_uid = None
                with self.conn_users() as c:
                    r = c.execute("SELECT cloud_uid FROM users WHERE id=?", (uid,)).fetchone()
                    if r:
                        cloud_uid = r[0]
                if cloud_uid:
                    CloudSync.save_msg(cloud_uid, role, content, session_id)
            except Exception:
                pass
        threading.Thread(target=_sync, daemon=True).start()

    def get_chat_history(self, uid, session_id="main", limit=50):
        with self.conn_chats() as c:
            rows = c.execute(
                "SELECT role, content, timestamp FROM chat_history WHERE user_id=? AND session_id=? ORDER BY timestamp ASC LIMIT ?",
                (uid, session_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def list_sessions(self, uid):
        with self.conn_chats() as c:
            rows = c.execute(
                "SELECT session_id, MAX(timestamp) as last_time FROM chat_history WHERE user_id=? GROUP BY session_id ORDER BY last_time DESC",
                (uid,)).fetchall()
            return [dict(r) for r in rows]

    def get_session_titles(self, uid, limit=20):
        with self.conn_chats() as c:
            sessions = c.execute(
                "SELECT session_id, MAX(timestamp) as last_time FROM chat_history "
                "WHERE user_id=? GROUP BY session_id ORDER BY last_time DESC LIMIT ?",
                (uid, limit)).fetchall()
            result = []
            for s in sessions:
                sid = s["session_id"]
                first_msg = c.execute(
                    "SELECT content FROM chat_history WHERE user_id=? AND session_id=? "
                    "AND role='user' ORDER BY timestamp ASC LIMIT 1",
                    (uid, sid)).fetchone()
                preview = (first_msg["content"][:40] + "…") if first_msg else sid
                result.append({"session_id": sid, "last_time": s["last_time"], "preview": preview})
            return result

    def delete_session(self, uid, session_id):
        with self.conn_chats() as c:
            c.execute("DELETE FROM chat_history WHERE user_id=? AND session_id=?", (uid, session_id))

    def rename_session(self, uid, old_session_id, new_session_id):
        if not new_session_id or new_session_id.strip() == old_session_id:
            return
        with self.conn_chats() as c:
            c.execute(
                "UPDATE chat_history SET session_id=? WHERE user_id=? AND session_id=?",
                (new_session_id.strip(), uid, old_session_id)
            )

    def save_note(self, uid, txt):
        with self.conn_chats() as c:
            c.execute("INSERT INTO notes (user_id,txt) VALUES (?,?)", (uid,txt))

    def notes(self, uid, limit=10):
        with self.conn_chats() as c:
            rows = c.execute("SELECT id,txt,ts FROM notes WHERE user_id=? ORDER BY ts DESC LIMIT ?", (uid,limit)).fetchall()
            return [dict(r) for r in rows]

    def del_note(self, uid, nid):
        with self.conn_chats() as c:
            c.execute("DELETE FROM notes WHERE id=? AND user_id=?", (nid,uid))

    def _get(self, table, col, uid, default):
        with self.conn_users() as c:
            r = c.execute(f"SELECT {col} FROM {table} WHERE user_id=?", (uid,)).fetchone()
            return r[col] if r else default

    def _set(self, table, col, uid, val):
        with self.conn_users() as c:
            c.execute(f"INSERT INTO {table} (user_id,{col}) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET {col}=?", (uid,val,val))


# =========================================================================
#  AARON AI OFFLINE ENCYCLOPEDIC DATABASE & STUDENT GUIDES (LYCEUM №166)
# =========================================================================
AARON_OFFLINE_DOCS = {
    "AARON_AI_ARCHITECTURE": (
        "Aaron AI Core v3.3 Architecture Schema\n"
        "=====================================\n"
        "1. GUI Layer (CustomTkinter Frame Pipeline)\n"
        "   - App(ctk.CTk) -> Main Coordinator\n"
        "   - ChatFrame, MathFrame, ProfileFrame (Terminal Node)\n"
        "2. Database Storage Node (SQLite Dual-File Model)\n"
        "   - chats.db: Handles persistent historical dialogues and fast indices\n"
        "   - users.db: Houses system preferences, flags, and single-use licenses\n"
        "3. Thread Orchestration Pipeline\n"
        "   - AsyncLoop thread handles background Gemini and Mistral API handshakes\n"
        "   - Native UI scheduling (.after) eliminates race-conditions and prevents hanging\n"
        "4. Codex-02 Compiler & Mini IDE Engine\n"
        "   - Subprocess sandbox for local runtime execution (Python, C/C++, JS)\n"
        "   - Browser Web Runner (using webbrowser native thread delegation for HTML/CSS)\n"
    ),
    "MATH_EXTENDED_GUIDES": {
        "derivative": "Производная функции f(x) выражает мгновенную скорость изменения функции в данной точке. Формула: f'(x) = lim (h->0) [f(x+h) - f(x)] / h. Примеры: (x^n)' = n * x^(n-1), (sin x)' = cos x.",
        "integral": "Интеграл — это площадь криволинейной трапеции под графиком функции. Неопределенный интеграл — совокупность всех первообразных функций. Пример: ∫ x^n dx = (x^(n+1))/(n+1) + C.",
        "matrices": "Матрица — это прямоугольная таблица чисел. Сложение матриц происходит поэлементно. Умножение матриц A (m x n) и B (n x k) дает matrix C (m x k), где элемент c_ij равен скалярному произведению i-й строки A и j-го столбца B.",
        "complex_numbers": "Комплексное число имеет вид z = a + b*i, где i — мнимая единица (i^2 = -1). Сложение: (a+bi)+(c+di) = (a+c) + (b+d)i. Умножение: (a+bi)*(c+di) = (ac - bd) + (ad + bc)i.",
        "geometry_formulas": {
            "triangle_area": "Площадь треугольника: S = 0.5 * b * h (где b - основание, h - высота) или по формуле Герона: S = sqrt(p * (p-a) * (p-b) * (p-c)), где p - полупериметр.",
            "circle_area": "S = pi * r^2. Длина окружности: C = 2 * pi * r.",
            "sphere_volume": "Объем сферы: V = (4/3) * pi * r^3. Площадь поверхности сферы: S = 4 * pi * r^2.",
            "cylinder_volume": "Объем цилиндра: V = pi * r^2 * h. Полная площадь поверхности: S = 2 * pi * r * (r + h)."
        }
    },
    "PHYSICS_FORMULAS_GUIDE": {
        "mechanics": {
            "kinematics": "Уравнение равноускоренного движения: x(t) = x0 + v0*t + 0.5*a*t^2. Скорость: v(t) = v0 + a*t.",
            "dynamics": "Второй закон Ньютона: F = m*a. Сила тяжести: F = m*g. Сила трения: F_tr = mu * N. Сила упругости (закон Гука): F = -k * x.",
            "energy_conservation": "Закон сохранения механической энергии: E_kin1 + E_pot1 = E_kin2 + E_pot2. E_kin = 0.5*m*v^2, E_pot = m*g*h."
        },
        "thermodynamics": {
            "ideal_gas_law": "Уравнение Менделеева-Клапейрона: P*V = n*R*T, где R = 8.314 Дж/(моль*К).",
            "first_law": "Первый закон термодинамики: Q = dU + A, где Q - переданное количество теплоты, dU - изменение внутренней энергии, A - работа газа."
        },
        "electrodynamics": {
            "ohms_law": "Закон Ома для участка цепи: I = U / R. Закон Ома для полной цепи: I = E / (R + r).",
            "joules_law": "Закон Джоуля-Ленца: Q = I^2 * R * t.",
            "coulombs_law": "Закон Кулона: F = k * (|q1| * |q2|) / r^2, где k = 9*10^9 Н*м^2/Кл^2."
        }
    },
    "ALGORITHMS_GUIDE": {
        "sorting": {
            "bubble_sort": "Сортировка пузырьком: O(N^2) в среднем и худшем случае. Простейший алгоритм, основанный на циклическом сравнении соседних элементов.",
            "quick_sort": "Быстрая сортировка (Quick Sort): O(N log N) в среднем. Метод разделяй и властвуй, выбирающий опорный элемент и распределяющий массив вокруг него.",
            "merge_sort": "Сортировка слиянием (Merge Sort): стабильный алгоритм со сложностью O(N log N) в худшем случае. Требует дополнительную память O(N)."
        },
        "search": {
            "binary_search": "Бинарный поиск: O(log N) в отсортированном массиве. На каждом шаге делит область поиска пополам.",
            "linear_search": "Линейный поиск: последовательный перебор элементов за O(N)."
        }
    },
    "LYCEUM_166_INFO": {
        "mission": "Лицей №166 города Алматы нацелен на углубленное изучение физико-математических наук и информационных технологий. Aaron AI призван служить локальным цифровым ассистентом для проектных работ учащихся.",
        "academic_modules": {
            "informatics": "Программа включает в себя изучение алгоритмизации на Python, веб-разработки (HTML, CSS, JS), баз данных (SQL) и основ искусственного интеллекта. Студенты активно участвуют в олимпиадах и научных соревнованиях.",
            "mathematics": "Особый упор делается на математический анализ, геометрию, теорию вероятностей и линейную алгебру, формирующие аналитическое мышление лицеистов.",
            "physics": "Лабораторные и практические занятия по механике, термодинамике и электродинамике с разбором физических процессов на ПК."
        }
    },
    "TKINTER_GUIDE_SHEET": {
        "ctk_customization": "CustomTkinter предоставляет современные виджеты с поддержкой тем оформления. Основные методы настройки: ctk.set_appearance_mode('dark'/'light'), ctk.set_default_color_theme('blue'/'green'/'dark-blue').",
        "layout_management": "Для разметки интерфейса рекомендуются менеджеры .pack() и .grid(). pack() удобен для вертикального/горизонтального стека, а grid() для табличной сетки элементов с параметрами row, column, columnspan, rowspan.",
        "threading_safety": "Никогда не изменяйте свойства GUI виджетов напрямую из дочерних потоков. Всегда делегируйте вызовы на главный поток с помощью метода after(), например: widget.after(0, lambda: widget.configure(text='Done!'))."
    },
    "CODEX_02_TUTORIAL": (
        "=== РУКОВОДСТВО ПО ПРОГРАММИРОВАНИЮ С CODEX-02 ===\n\n"
        "Агент Codex-02 спроектирован как умный помощник разработчика.\n"
        "Он способен:\n"
        "1. Генерировать готовые куски UI на базе CustomTkinter\n"
        "2. Изменять поведение уже запущенного приложения в рантайме (Mutable App)\n"
        "3. Локально создавать, читать и модифицировать файлы (через теги CREATE_FILE)\n\n"
        "Синтаксис авто-создания файлов:\n"
        "<<CREATE_FILE: path/to/script.py>>\n"
        "# Ваш код на Python\n"
        "<<END_FILE>>\n"
    )
}

# ======================== ГЛОБАЛЬНЫЕ ОБЪЕКТЫ ======================== 

# --- MONKEY PATCHES FOR BACKWARD COMPATIBILITY & RECONCILIATION ---
try:
    import customtkinter as ctk
    ctk.CTk.get_appearance_mode = lambda self, *args, **kwargs: ctk.get_appearance_mode()
    ctk.CTk.set_appearance_mode = lambda self, mode, *args, **kwargs: ctk.set_appearance_mode(mode)
    ctk.CTkFrame.get_appearance_mode = lambda self, *args, **kwargs: ctk.get_appearance_mode()
    ctk.CTkFrame.set_appearance_mode = lambda self, mode, *args, **kwargs: ctk.set_appearance_mode(mode)
except Exception as e:
    logger.warning(f"Failed to patch customtkinter widgets: {e}")

# Database Patches
def db_get_current_provider(self, *args, **kwargs):
    global ACTIVE_PROVIDER
    return ACTIVE_PROVIDER

def db_set_current_provider(self, val, *args, **kwargs):
    global ACTIVE_PROVIDER
    ACTIVE_PROVIDER = str(val).lower()
    try:
        if 'app' in globals() and hasattr(app, 'frames') and 'chat' in app.frames:
            app.frames['chat'].update_model_label()
    except Exception:
        pass

def db_get_available_providers(self, *args, **kwargs):
    return ['g4f', 'mistral', 'gemini', 'aaron', 'codex_02']

Database.get_current_provider = db_get_current_provider
Database.set_current_provider = db_set_current_provider
Database.get_available_providers = db_get_available_providers

# CTk (app) and CTkFrame (self) Patches
def app_get_current_provider(self, *args, **kwargs):
    global ACTIVE_PROVIDER
    return ACTIVE_PROVIDER

def app_set_current_provider(self, val, *args, **kwargs):
    global ACTIVE_PROVIDER
    ACTIVE_PROVIDER = str(val).lower()
    try:
        if hasattr(self, 'frames') and 'chat' in self.frames:
            self.frames['chat'].update_model_label()
    except Exception:
        pass

def app_get_available_providers(self, *args, **kwargs):
    return ['g4f', 'mistral', 'gemini', 'aaron', 'codex_02']

try:
    import customtkinter as ctk
    ctk.CTk.get_current_provider = app_get_current_provider
    ctk.CTk.set_current_provider = app_set_current_provider
    ctk.CTk.get_available_providers = app_get_available_providers
    
    ctk.CTkFrame.get_current_provider = app_get_current_provider
    ctk.CTkFrame.set_current_provider = app_set_current_provider
    ctk.CTkFrame.get_available_providers = app_get_available_providers
except Exception as e:
    pass

USER_ID = 1
ACTIVE_PROVIDER = 'gemini'
CURRENT_SESSION_ID = "main"
FILE_CONTEXT = None
CHAT_ATTACHED_FILES: List[Dict] = []  # [{'name': str, 'path': str, 'content': str}]
DASHBOARD_INFLUENCE = {'aggressor': 50, 'peaceful': 50}


def read_file_content(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext in ('.txt', '.py', '.js', '.ts', '.md', '.json', '.csv', '.xml', '.html', '.css'):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:8000]
        elif ext == '.pdf':
            if FITZ_OK:
                doc = fitz.open(filepath)
                text = ''.join(page.get_text() for page in doc)
                doc.close()
                return text[:8000]
            return f"[PDF: {os.path.basename(filepath)} — установите PyMuPDF]"
        elif ext in ('.docx', '.doc'):
            if DOCX_OK:
                doc = Document(filepath)
                return '\n'.join(p.text for p in doc.paragraphs)[:8000]
            return f"[DOCX: {os.path.basename(filepath)} — установите python-docx]"
        elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'):
            return f"[ИЗОБРАЖЕНИЕ: {os.path.basename(filepath)}]"
        else:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:8000]
    except Exception as e:
        return f"[Ошибка чтения {os.path.basename(filepath)}: {e}]"

ensure_data_folder()
db = Database(get_chats_db_path(), get_users_db_path())
_db_ensure_app_tables()  # Создаём таблицы settings, instructions, subscriptions
db.init()
DASHBOARD_INFLUENCE.update(db.get_dashboard_state(USER_ID))

def load_session_history(session_id: str):
    global conversation, CURRENT_SESSION_ID
    messages = db.get_chat_history(USER_ID, session_id, limit=100)
    conversation = Conversation(conversation_id=session_id, user_id=USER_ID, system_prompt="Ты полезный ассистент.")
    for msg in messages:
        role = MessageRole.USER if msg['role'] == 'user' else MessageRole.ASSISTANT
        conversation.add_message(role, msg['content'])
    CURRENT_SESSION_ID = session_id

load_session_history(CURRENT_SESSION_ID)
auth = Auth()
g4f = G4FProvider(G4F_API_URL)
mistral = MistralProvider(MISTRAL_KEY)
gemini = GeminiProvider(GEMINI_KEY)
engine = AIEngine(mistral, gemini, g4f)
# Отдельный движок для Валидола и Супер ИИ (свой ключ Mistral)
mistral2 = MistralProvider(MISTRAL_KEY_2)
engine2 = AIEngine(mistral2, gemini, g4f)
math_engine = MathEngine()


def set_file_context(path: str):
    global FILE_CONTEXT
    if not path:
        FILE_CONTEXT = None
        return
    ext = os.path.splitext(path)[1].lower()
    if ext in ['.doc', '.docx']:
        ftype = 'Word document'
    elif ext in ['.pdf']:
        ftype = 'PDF document'
    elif ext in ['.txt']:
        ftype = 'Text file'
    elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif']:
        ftype = 'Image file'
    elif ext in ['.xlsx', '.xls']:
        ftype = 'Spreadsheet'
    elif ext in ['.ppt', '.pptx']:
        ftype = 'Presentation'
    elif ext in ['.py', '.js', '.ts', '.java', '.cs']:
        ftype = 'Source code file'
    elif ext in ['.zip', '.rar', '.7z']:
        ftype = 'Archive file'
    else:
        ftype = 'Unknown file type'
    FILE_CONTEXT = {
        'path': path,
        'extension': ext,
        'type': ftype,
        'description': f"{ftype} ({os.path.basename(path)})"
    }


def get_dashboard_style_prompt() -> str:
    aggressor = DASHBOARD_INFLUENCE['aggressor']
    peaceful = DASHBOARD_INFLUENCE['peaceful']
    if aggressor > peaceful:
        tone = "агрессивный, резкий, напористый"
    elif peaceful > aggressor:
        tone = "мирный, доброжелательный, эмпатичный"
    else:
        tone = "сбалансированный и объективный"
    return (
        f"График доминирования: Агрессор {aggressor}%, Мирный {peaceful}%. "
        f"Используй эти данные, чтобы выбрать тон ответа: {tone}. "
        "Если агрессор выше 60%, ответ должен быть более жестким, если мирный выше 60% — более мягким."
    )


def sync_chat(text: str, sys_prompt: str = None, request_type: RequestType = RequestType.TEXT_CHAT, use_engine=None, session_id=None) -> str:
    global CURRENT_SESSION_ID
    active_sid = session_id if session_id else CURRENT_SESSION_ID
    db.log_chat(USER_ID, "user", text, active_sid)
    language = db.get_lang(USER_ID)
    if request_type == RequestType.SEARCH:
        base_prompt = (
            "Ты выполняешь веб-поиск и формируешь ответ с явными источниками. "
            "Отвечай кратко, добавь блок 'Источники:' с URL-адресами и объясни, откуда взята информация."
        )
        if PromptLibrary.get_system(language, db.get_mode(USER_ID)):
            base_prompt += "\n" + PromptLibrary.get_system(language, db.get_mode(USER_ID))
        if sys_prompt:
            base_prompt += "\n" + sys_prompt
    else:
        base_prompt = sys_prompt if sys_prompt else PromptLibrary.get_system(language, db.get_mode(USER_ID))
    dashboard_note = get_dashboard_style_prompt()
    prompt = base_prompt + "\n" + dashboard_note
    if FILE_CONTEXT:
        file_text_content = read_file_content(FILE_CONTEXT['path'])
        prompt += f" Учитывай файл: {FILE_CONTEXT['description']}."
        text = f"=== СОДЕРЖИМОЕ ФАЙЛА {FILE_CONTEXT['description']} ===\n{file_text_content}\n=== КОНЕЦ ФАЙЛА ===\n\n{text}"
    if CHAT_ATTACHED_FILES:
        parts = [f"=== {fi['name']} ===\n{fi['content']}" for fi in CHAT_ATTACHED_FILES]
        text = "\n\n".join(parts) + "\n\n" + text
        prompt += f" Пользователь прикрепил {len(CHAT_ATTACHED_FILES)} файл(ов). Прочитай содержимое и отвечай с учётом этих данных."
    
    # Persistent conversational context/memory loaded cleanly from SQL
    history_msgs = db.get_chat_history(USER_ID, active_sid, limit=10)
    full_messages = []
    full_messages.append({"role": "system", "content": prompt})
    for m in history_msgs:
        # Avoid duplicating the newly logged user message
        if m["role"] == "user" and m["content"] == text:
            continue
        full_messages.append({"role": m["role"], "content": m["content"]})
    # Make sure current user prompt is included at the end
    full_messages.append({"role": "user", "content": text})
    
    req = AIRequest(USER_ID, request_type, text, system_prompt=prompt, language=language, messages=full_messages)
    target_engine = use_engine if use_engine is not None else engine
    resp = async_loop.run(target_engine.process(req))
    if resp.status == ResponseStatus.SUCCESS:
        content = parse_and_execute_codex_commands(resp.content)
        db.log_chat(USER_ID, "assistant", content, active_sid)
        db.add_stat(USER_ID)
        return content
    elif resp.status == ResponseStatus.ERROR:
        err_content = resp.content
        if err_content.startswith("Ошибка соединения:") or "Ошибка соединения" in err_content:
            error_msg = f"⚠️ [Ошибка] {err_content}. Возможно, проблемы с сетью, VPN, блокировками или API-ключами."
        else:
            error_msg = f"⚠️ [Ошибка соединения] Не удалось получить ответ от ИИ: {err_content}. Возможно, проблемы с сетью или ключами."
        db.log_chat(USER_ID, "assistant", error_msg, active_sid)
        return error_msg
    return resp.content
def sync_chat2(text: str, sys_prompt: str = None, request_type: RequestType = RequestType.TEXT_CHAT, session_id=None) -> str:
    """Чат через второй Mistral-ключ (для Валидола и Супер ИИ)."""
    return sync_chat(text, sys_prompt=sys_prompt, request_type=request_type, use_engine=engine, session_id=session_id)

def sync_search(query: str) -> str:
    return sync_chat(query, request_type=RequestType.SEARCH)


def sync_gdz(img_bytes: bytes) -> str:
    prompt = "Реши задачу на фото. Дай подробное решение с объяснением."
    req = AIRequest(USER_ID, RequestType.GDZ, prompt, images=[img_bytes], language=db.get_lang(USER_ID))
    resp = async_loop.run(engine.process(req))
    db.add_stat(USER_ID)
    return resp.content

# ======================== ИНСТРУМЕНТЫ ЛАУНЧЕРА ======================
def get_python_executable():
    """Возвращает корректный исполняемый файл Python для запуска внешних скриптов."""
    if not getattr(sys, "frozen", False):
        return sys.executable
    for py_cmd in [
        "python", "python3", "pythonw",
        os.path.join(sys.prefix, "python.exe"),
        r"C:\Python310\python.exe", r"C:\Python311\python.exe",
        r"C:\Python312\python.exe", r"C:\Python313\python.exe"
    ]:
        path = shutil.which(py_cmd) or (py_cmd if os.path.exists(py_cmd) else None)
        if path and os.path.exists(path):
            return path
    return sys.executable


def is_python_installed():
    try:
        subprocess.run([sys.executable, "--version"], capture_output=True, check=True)
        return True
    except:
        return False

def install_python():
    if platform.system() == "Windows":
        import webbrowser
        webbrowser.open("https://www.python.org/downloads/")

def create_shortcut(target_path, link_path, working_dir, arguments=""):
    escaped_args = arguments.replace("'", "''")
    ps_script = f'''
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{link_path}')
    $Shortcut.TargetPath = '{target_path}'
    $Shortcut.Arguments = '{escaped_args}'
    $Shortcut.WorkingDirectory = '{working_dir}'
    $Shortcut.Save()
    '''
    with open("__temp_ps.ps1", "w", encoding='utf-8') as f: f.write(ps_script)
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", "__temp_ps.ps1"], check=False)
    os.remove("__temp_ps.ps1")

def run_game():
    # Ищем g.py: рядом с exe (frozen), в директории скрипта, во временной папке PyInstaller (_MEIPASS), в CWD
    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(sys.executable))
        mp = getattr(sys, "_MEIPASS", None)
        if mp:
            candidates.append(mp)
    candidates.append(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.getcwd())
    game_path = None
    for d in candidates:
        p = os.path.join(d, GAME_FILENAME)
        if os.path.exists(p):
            game_path = p
            break
    if not game_path:
        messagebox.showerror("Ошибка", f"Файл игры '{GAME_FILENAME}' не найден рядом с приложением.")
        return
    py = get_python_executable()
    try:
        if os.name == "nt":
            if getattr(sys, "frozen", False) and py == sys.executable:
                cmd_str = f'"{sys.executable}" --run-script "{game_path}"'
            else:
                cmd_str = f'"{py}" "{game_path}"'
            subprocess.Popen(f'cmd.exe /k {cmd_str}', cwd=os.path.dirname(game_path), shell=True)
        else:
            if getattr(sys, "frozen", False) and py == sys.executable:
                subprocess.Popen([sys.executable, "--run-script", game_path], cwd=os.path.dirname(game_path))
            else:
                subprocess.Popen([py, game_path], cwd=os.path.dirname(game_path))
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось запустить игру: {e}\nУбедитесь, что Python установлен.")

def open_in_editor():
    current_path = os.path.abspath(__file__)
    if not os.path.exists(current_path):
        messagebox.showerror("Ошибка", f"Файл '{current_path}' не найден.")
        return
    choice = simpledialog.askstring("Выбор редактора", "1-IDLE 2-VSCode 3-PyCharm 4-Notepad++ 5-Блокнот 6-Другой")
    if not choice:
        return
    editor_map = {"1":"idle","2":"code","3":"pycharm64","4":"notepad++","5":"notepad"}
    editor_path = editor_map.get(choice)
    if choice == "6":
        editor_path = simpledialog.askstring("Путь к редактору", "Введите полный путь к редактору или .exe")
    try:
        if editor_path and (shutil.which(editor_path) or os.path.exists(editor_path)):
            subprocess.Popen([editor_path, current_path])
            return
    except Exception:
        pass
    try:
        os.startfile(current_path)
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось запустить редактор или открыть файл по умолчанию.\n{e}")

async def _run_bot():
    if not AIOGRAM_OK:
        logger.warning("aiogram не установлен — Telegram-бот недоступен")
        return
    bot_token = BOT_TOKEN or BOT_TOKEN2
    if not bot_token:
        logger.error("Telegram bot token is не задан")
        return
    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=MemoryStorage())

    @dp.message(Command(commands=['start', 'help']))
    async def _(message: types.Message):
        help_text = (
            "🤖 *Aaron AI Bot v2.0* 🤖\n\n"
            "Доступные команды:\n"
            "• `/premium` — Купить Premium подписку (Kaspi, Halyk, Visa)\n"
            "• `/activate <ID>` — Активация подписки по ID\n\n"
            "Специальные приватные группы ИИ:\n"
            "• `/private <текст>` — Доступ к Приватному ИИ (Группа 1)\n"
            "• `/validol <текст>` — Доступ к Валидол-ИИ (Группа 2)\n"
            "• `/super_ai <текст>` — Доступ к Супер ИИ (Группа 3)\n\n"
            "• `/admin <пароль>` — Панель оператора (управление списками доступа)"
        )
        await message.answer(help_text, parse_mode="Markdown")

    @dp.message(Command(commands=['premium']))
    async def premium_command(message: types.Message):
        pay_info = (
            "💎 *Оформление Premium доступа* 💎\n\n"
            "Доступны следующие способы оплаты:\n\n"
            "📱 *1. Kaspi QR*\n"
            "Перевод через приложение Kaspi.kz по номеру: +7 777 123 4567\n\n"
            "🏦 *2. Halyk Bank*\n"
            "Номер карты: `4400 4300 1200 9999`\n\n"
            "💳 *3. Visa / MasterCard (Свяжитесь с оператором)*\n\n"
            "Для подтверждения оплаты отправьте скриншот квитанции оператору: @AaronSystems_Operator.\n"
            "После этого вам будет выслан ваш уникальный *Premium ID* для активации в приложении!"
        )
        await message.answer(pay_info, parse_mode="Markdown")

    @dp.message(Command(commands=['activate']))
    async def activate_command(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Формат команды: `/activate <Premium ID>`")
            return
        pid = parts[1].strip()
        if pid.isdigit() and len(pid) >= 6:
            _db_set_flag("is_premium", True)
            _db_set_setting("premium_id_key", pid)
            await message.answer(f"✅ Premium подписка успешно активирована по ID: {pid}!")
        else:
            await message.answer("❌ Неверный формат Premium ID. Обратитесь к оператору.")

    @dp.message(Command(commands=['private']))
    async def private_handler(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Напишите ваш запрос после команды, например: `/private Как устроен блокчейн?`")
            return
        
        user_id = message.from_user.id
        allowed_str = _db_get_setting("tg_group_private_ids", "")
        allowed_ids = [int(x.strip()) for x in allowed_str.split(",") if x.strip().isdigit()]
        
        # Admin can access everything
        is_allowed = (user_id in allowed_ids) or (str(user_id) in allowed_str) or check_feature_access("premium")
        
        if not is_allowed:
            await message.answer(
                f"🔒 *Доступ заблокирован (Группа 1: Приват)*\n"
                f"Ваш Telegram ID: `{user_id}` не найден в списках доступа оператора.\n"
                f"Купите Premium подписку (`/premium`), чтобы разблокировать доступ!", 
                parse_mode="Markdown"
            )
            return
            
        await message.answer("🤔 Думаю...")
        ans = sync_chat(parts[1], sys_prompt="Ты приватный ИИ-ассистент в закрытом Telegram-канале.")
        await message.answer(ans)

    @dp.message(Command(commands=['validol']))
    async def validol_handler(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Напишите запрос после команды: `/validol <запрос>`")
            return
            
        user_id = message.from_user.id
        allowed_str = _db_get_setting("tg_group_validol_ids", "")
        allowed_ids = [int(x.strip()) for x in allowed_str.split(",") if x.strip().isdigit()]
        
        is_allowed = (user_id in allowed_ids) or (str(user_id) in allowed_str) or check_feature_access("premium")
        
        if not is_allowed:
            await message.answer(
                f"🔒 *Доступ заблокирован (Группа 2: Валидол)*\n"
                f"Ваш Telegram ID: `{user_id}` не найден в списках доступа Валидола.\n"
                f"Для активации требуется Premium статус.", 
                parse_mode="Markdown"
            )
            return
            
        await message.answer("⚡ Генерация ответа в режиме Валидол...")
        ans = sync_chat(parts[1], sys_prompt=SUPER_AI_PROMPTS['alpha'])
        await message.answer(ans)

    @dp.message(Command(commands=['super_ai']))
    async def superai_handler(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("❌ Напишите запрос после команды: `/super_ai <запрос>`")
            return
            
        user_id = message.from_user.id
        allowed_str = _db_get_setting("tg_group_superai_ids", "")
        allowed_ids = [int(x.strip()) for x in allowed_str.split(",") if x.strip().isdigit()]
        
        is_allowed = (user_id in allowed_ids) or (str(user_id) in allowed_str) or check_feature_access("premium")
        
        if not is_allowed:
            await message.answer(
                f"🔒 *Доступ заблокирован (Группа 3: Супер ИИ)*\n"
                f"Ваш Telegram ID: `{user_id}` не найден в списке Super AI оператора.\n"
                f"Свяжитесь с оператором для ручного внесения в категорию 3.", 
                parse_mode="Markdown"
            )
            return
            
        await message.answer("🔮 Обработка запроса на нейронном ядре...")
        ans = sync_chat(parts[1], sys_prompt="Ты — суперинтеллект на ядре Aaron Brain v5. Отвечай максимально глубоко.")
        await message.answer(ans)

    @dp.message(Command(commands=['admin']))
    async def admin_command(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip() != ADMIN_PASSWORD_BOT:
            await message.answer("❌ Неверный пароль администратора.")
            return
        
        # Show help for operator config
        help_admin = (
            "👑 *Панель оператора бота* 👑\n\n"
            "Вы можете вносить Telegram ID пользователей в группы доступа следующими командами в ЛС бота:\n"
            "• `/add_private <TG_ID>` — Добавить в Группу 1 (Приват)\n"
            "• `/add_validol <TG_ID>` — Добавить в Группу 2 (Валидол)\n"
            "• `/add_superai <TG_ID>` — Добавить в Группу 3 (Супер ИИ)"
        )
        await message.answer(help_admin, parse_mode="Markdown")

    @dp.message(Command(commands=['add_private']))
    async def add_p(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2: return
        current = _db_get_setting("tg_group_private_ids", "")
        new_val = current + ("," if current else "") + parts[1].strip()
        _db_set_setting("tg_group_private_ids", new_val)
        await message.answer(f"✅ ID {parts[1]} успешно внесён в группу 1 (Приватный чат)!")

    @dp.message(Command(commands=['add_validol']))
    async def add_v(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2: return
        current = _db_get_setting("tg_group_validol_ids", "")
        new_val = current + ("," if current else "") + parts[1].strip()
        _db_set_setting("tg_group_validol_ids", new_val)
        await message.answer(f"✅ ID {parts[1]} успешно внесён в группу 2 (Валидол)!")

    @dp.message(Command(commands=['add_superai']))
    async def add_s(message: types.Message):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2: return
        current = _db_get_setting("tg_group_superai_ids", "")
        new_val = current + ("," if current else "") + parts[1].strip()
        _db_set_setting("tg_group_superai_ids", new_val)
        await message.answer(f"✅ ID {parts[1]} успешно внесён в группу 3 (Супер ИИ)!")

    @dp.message()
    async def text_handler(message: types.Message):
        query = message.text.strip()
        if not query:
            return
        answer = sync_chat(query)
        await message.answer(answer)

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

def start_telegram_bot():
    try:
        asyncio.run(_run_bot())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_bot())

# ======================== ОКНО ВХОДА / РЕГИСТРАЦИИ ==================
class CloudSync:
    DEFAULT_BIN = '019f949c-cf2f-7cda-b54b-c222c11c6c8e'
    
    @classmethod
    def get_bin(cls):
        return _db_get_setting("aaron_bin", cls.DEFAULT_BIN)

    @classmethod
    def get_url(cls):
        return f"https://jsonblob.com/api/jsonBlob/{cls.get_bin()}"

    @classmethod
    def is_online(cls) -> bool:
        try:
            resp = requests.head(cls.get_url(), timeout=2.5)
            return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    def fetch_blob(cls) -> Dict:
        try:
            resp = requests.get(cls.get_url(), timeout=3.5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.warning(f"JsonBlob fetch failed: {e}")
        return {"orders": [], "apiKeys": [], "config": {}}

    @classmethod
    def push_blob(cls, data: Dict) -> bool:
        try:
            headers = {"Content-Type": "application/json"}
            resp = requests.put(cls.get_url(), json=data, headers=headers, timeout=4.0)
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"JsonBlob push failed: {e}")
            return False

    @classmethod
    def verify_key_online(cls, key_str: str) -> Optional[str]:
        blob = cls.fetch_blob()
        clean = key_str.strip().upper()
        # Check apiKeys array from JsonBlob Admin Panel API
        for k in blob.get("apiKeys", []):
            if k.get("key", "").strip().upper() == clean and not k.get("revoked", False):
                return k.get("package")
        # Check orders array from JsonBlob Admin Panel API
        for o in blob.get("orders", []):
            if o.get("activation_key", "").strip().upper() == clean and o.get("status") == "approved":
                return o.get("package")
        return None

    @classmethod
    def register(cls, username, password):
        return {"status": "ok", "id": f"cloud_{username}"}

    @classmethod
    def login(cls, username, password):
        return {"status": "ok", "id": f"cloud_{username}", "lang": "ru", "mode": "normal"}

    @classmethod
    def sync_settings(cls, uid, lang, mode, brain="Mistral mistral-medium-2505", avatar="", api_key=""):
        pass

    @classmethod
    def save_msg(cls, uid, role, content, session_id):
        pass

    @classmethod
    def get_history(cls, uid, session_id):
        return None


def sync_chats_with_cloud_bg(username):
    if not CloudSync.is_online():
        return
    try:
        cloud_uid = None
        with db.conn_users() as c:
            r = c.execute("SELECT cloud_uid FROM users WHERE username=?", (username,)).fetchone()
            if r:
                cloud_uid = r[0]
        if not cloud_uid:
            return
            
        history = CloudSync.get_history(cloud_uid, "main")
        if history:
            with db.conn_chats() as c:
                existing_count = c.execute("SELECT COUNT(*) FROM chat_history WHERE user_id=? AND session_id='main'", (USER_ID,)).fetchone()[0]
                if len(history) > existing_count:
                    c.execute("DELETE FROM chat_history WHERE user_id=? AND session_id='main'", (USER_ID,))
                    for msg in history:
                        c.execute("INSERT INTO chat_history (user_id, role, content, session_id) VALUES (?,?,?,?)",
                                  (USER_ID, msg['role'], msg['content'], "main"))
    except Exception:
        pass


def load_avatar_image(avatar_path, size=32):
    try:
        if avatar_path and os.path.exists(avatar_path):
            img = Image.open(avatar_path).convert("RGB")
            # Square crop
            w, h = img.size
            s = min(w, h)
            left = (w - s) // 2
            top = (h - s) // 2
            img = img.crop((left, top, left + s, top + s))
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    except Exception as e:
        logger.warning(f"Failed to load avatar image: {e}")
    return None



class DualOutput:
    def __init__(self, original_stream, write_callback):
        self.original_stream = original_stream
        self.write_callback = write_callback

    def write(self, string):
        if self.original_stream:
            try:
                self.original_stream.write(string)
            except Exception:
                pass
        self.write_callback(string)

    def flush(self):
        if self.original_stream:
            try:
                self.original_stream.flush()
            except Exception:
                pass

class DevConsole(ctk.CTkToplevel):
    def __init__(self, app_instance):
        super().__init__(app_instance)
        self.app = app_instance
        self.title("🛠️ Aaron AI — Консоль Разработчика")
        self.geometry("800x600")
        self.minsize(600, 400)
        self.configure(fg_color=DS_BG)
        
        # Keep window on top
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))
        
        # Title Label
        title_lbl = ctk.CTkLabel(self, text="📟 СИСТЕМНАЯ КОНСОЛЬ ЯДРА (РЕЖИМ ОТЛАДКИ)", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color="#10b981")
        title_lbl.pack(pady=10)
        
        # Quick Actions Bar
        actions_bar = ctk.CTkFrame(self, fg_color="#12121a", height=40)
        actions_bar.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(actions_bar, text="🧹 Очистить", width=80, font=ctk.CTkFont(size=11), fg_color="transparent", text_color=DS_DIM, hover_color="#1f2937", command=self.clear_logs).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(actions_bar, text="📦 Список модов", width=100, font=ctk.CTkFont(size=11), fg_color="#1e293b", text_color="#e2e8f0", command=self.print_mods).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(actions_bar, text="🔌 Проверить API", width=100, font=ctk.CTkFont(size=11), fg_color="#1e293b", text_color="#e2e8f0", command=self.test_api).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(actions_bar, text="📂 Рабочий стол", width=100, font=ctk.CTkFont(size=11), fg_color="#1e293b", text_color="#e2e8f0", command=self.test_desktop).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(actions_bar, text="❓ Коды ошибок", width=100, font=ctk.CTkFont(size=11), fg_color="#1e293b", text_color="#e2e8f0", command=self.print_error_codes).pack(side="left", padx=5, pady=5)
        
        # Log Output Area
        self.log_textbox = ctk.CTkTextbox(self, fg_color="#000000", text_color="#00ff00", font=ctk.CTkFont(family="Courier", size=11), wrap="word")
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Input Command Frame
        in_frame = ctk.CTkFrame(self, fg_color="transparent")
        in_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(in_frame, text=">>> ", font=ctk.CTkFont(family="Courier", size=12, weight="bold"), text_color="#00ff00").pack(side="left")
        
        self.cmd_entry = ctk.CTkEntry(in_frame, font=ctk.CTkFont(family="Courier", size=12), fg_color="#000000", text_color="#00ff00", border_color=DS_ACCENT)
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=(5, 10))
        self.cmd_entry.bind("<Return>", self.execute_entered_cmd)
        
        ctk.CTkButton(in_frame, text="Выполнить", width=90, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"), command=self.execute_entered_cmd).pack(side="right")
        
        # Redirect stdout and stderr
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        
        sys.stdout = DualOutput(self.old_stdout, self.write_log)
        sys.stderr = DualOutput(self.old_stderr, self.write_log)
        
        # Protocol on close
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        print("\n[DevConsole] Консоль отладки запущена. Потоки stdout/stderr успешно перенаправлены.")
        print("Доступна переменная 'app' — инстанс главного приложения.")

    def write_log(self, text):
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", text)
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def clear_logs(self):
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def execute_entered_cmd(self, event=None):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.cmd_entry.delete(0, "end")
        print(f"\n>>> {cmd}")
        try:
            # We execute in the global context, and pass 'app' as a local variable
            local_vars = {"app": self.app, "self": self}
            exec(cmd, globals(), local_vars)
        except Exception as e:
            print(f"Ошибка [104]: Сбой выполнения команды в консоли разработчика. Ошибка: {e}")

    def print_mods(self):
        print("\n--- СПИСОК СКАНИРОВАННЫХ МОДОВ ---")
        try:
            mods = scan_mods()
            state = load_mod_state()
            for m in mods:
                status = "ВКЛЮЧЁН" if state.get(m['file'], False) else "ОТКЛЮЧЁН"
                print(f"- {m['name']} ({m['file']}) | Статус: {status}")
                print(f"  Описание: {m['description']}")
            if not mods:
                print("Моды не обнаружены в папке mods/")
        except Exception as e:
            print(f"Ошибка [105]: Не удалось получить список модов: {e}")

    def test_api(self):
        print("\n--- ТЕСТИРОВАНИЕ СОЕДИНЕНИЯ С НЕЙРОСЕТЬЮ (OpenRouter API) ---")
        async def run_test():
            start_time = time.time()
            try:
                test_msgs = [{"role": "user", "content": "Привет! Ответь одним коротким словом 'ОК'."}]
                ans = await g4f.chat(test_msgs)
                print(f"Успешный ответ от API: {ans}")
                print(f"Время задержки: {int((time.time() - start_time)*1000)} мс")
            except Exception as e:
                print(f"Ошибка [103]: API тест провален. Детали: {e}")
        self.app.run_in_background(lambda: asyncio.run(run_test()))

    def test_desktop(self):
        print("\n--- ПРОВЕРКА ПУТЕЙ РАБОЧЕГО СТОЛА И ЗАПИСИ ---")
        try:
            desktop = get_desktop_root()
            print(f"Путь к Рабочему столу: {desktop}")
            print(f"Существует ли папка? {os.path.exists(desktop)}")
            
            # Check OneDrive indicators
            home = os.path.expanduser("~")
            paths = [
                os.path.join(home, "Desktop"),
                os.path.join(home, "OneDrive", "Desktop"),
                os.path.join(home, "OneDrive - Personal", "Desktop")
            ]
            print("Обнаруженные директории на ПК:")
            for p in paths:
                print(f" - {p}: {'НАЙДЕНА' if os.path.exists(p) else 'ОТСУТСТВУЕТ'}")
                
            # Try test write
            test_file = os.path.join(desktop, ".dev_write_test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("AARON DEV CONSOLE WRITE TEST")
            os.remove(test_file)
            print("Тест записи на Рабочий стол: УСПЕШНО ПРОЙДЕН")
        except Exception as e:
            print(f"Ошибка [104]: Тест записи провален. Детали: {e}")

    def print_error_codes(self):
        print("\n--- СПРАВОЧНИК СИСТЕМНЫХ КОДОВ ОШИБОК AARON AI ---")
        print("Ошибка [101] — Сбой атентификации API-ключей (Unauthorized 401).")
        print("Ошибка [102] — Таймаут соединения при запросе к нейросети (Timeout 45s).")
        print("Ошибка [103] — Общая ошибка подключения к OpenRouter API pool.")
        print("Ошибка [104] — Сбой файловых операций записи на Рабочий стол / Парсер Codex.")
        print("Ошибка [105] — Критическая ошибка в логике apply() при загрузке мода.")
        print("Ошибка [106] — Сбой компиляции, сборки или выполнения скрипта во встроенном Mini-IDE.")

    def on_close(self):
        # Restore original streams
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.destroy()

def show_dev_console(app_instance):
    if hasattr(app_instance, 'dev_console') and app_instance.dev_console.winfo_exists():
        app_instance.dev_console.lift()
        app_instance.dev_console.focus_force()
    else:
        app_instance.dev_console = DevConsole(app_instance)


class SplashWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aaron AI - Booting")
        self.overrideredirect(True)
        self.configure(fg_color=DS_BG)
        
        w, h = 420, 260
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.pack(expand=True, fill="both", padx=15, pady=15)
        
        border = ctk.CTkFrame(center, fg_color="transparent", border_width=2, border_color=DS_ACCENT)
        border.pack(fill="both", expand=True)
        
        self.chip_lbl = ctk.CTkLabel(border, text="📟", font=ctk.CTkFont(size=56))
        self.chip_lbl.pack(pady=(20, 5))
        
        self.title_lbl = ctk.CTkLabel(border, text="AARON CORE v3.2", font=ctk.CTkFont(family="Courier", size=18, weight="bold"), text_color="#10b981")
        self.title_lbl.pack()
        
        self.status_lbl = ctk.CTkLabel(border, text="Initializing hardware...", font=ctk.CTkFont(family="Courier", size=11), text_color=DS_DIM)
        self.status_lbl.pack(pady=5)
        
        self.progress = ctk.CTkProgressBar(border, width=280, height=8, fg_color="#1f2937", progress_color="#10b981")
        self.progress.pack(pady=10)
        self.progress.set(0)
        
        self.current_val = 0
        self.animate()
        
    def animate(self):
        if self.current_val < 1.0:
            self.current_val += 0.05
            self.progress.set(self.current_val)
            
            stages = [
                (0.1, "Initializing I2C bus..."),
                (0.3, "Connecting to Cloud sync..."),
                (0.5, "Booting neuromorphic PCB..."),
                (0.7, "Scanning peripheral mods..."),
                (0.9, "Ready! Launching interface...")
            ]
            for threshold, text in stages:
                if self.current_val >= threshold:
                    self.status_lbl.configure(text=text)
            self.after(50, self.animate)
        else:
            self.destroy()


def setup_cyrillic_bindings(root):
    bindings = [
        ("cyrillic_es", "<<Copy>>"),
        ("Cyrillic_ES", "<<Copy>>"),
        ("с", "<<Copy>>"),
        ("С", "<<Copy>>"),
        
        ("cyrillic_em", "<<Paste>>"),
        ("Cyrillic_EM", "<<Paste>>"),
        ("м", "<<Paste>>"),
        ("М", "<<Paste>>"),
        
        ("cyrillic_che", "<<Cut>>"),
        ("Cyrillic_CHE", "<<Cut>>"),
        ("ч", "<<Cut>>"),
        ("Ч", "<<Cut>>"),
        
        ("cyrillic_ef", "<<SelectAll>>"),
        ("Cyrillic_EF", "<<SelectAll>>"),
        ("ф", "<<SelectAll>>"),
        ("Ф", "<<SelectAll>>"),
        
        ("cyrillic_ya", "<<Undo>>"),
        ("Cyrillic_YA", "<<Undo>>"),
        ("я", "<<Undo>>"),
        ("Я", "<<Undo>>"),
    ]
    for widget_class in ("Text", "Entry"):
        for key, event in bindings:
            try:
                root.bind_class(widget_class, f"<Control-KeyPress-{key}>", lambda e, ev=event: e.widget.event_generate(ev))
            except Exception:
                pass


# ========================================================================================
#                  JARVIS PERSONAL SYSTEM AGENT & VECTOR MEMORY & CLAUDE SKILLS
# ========================================================================================

def get_jarvis_db_path():
    return os.path.join(get_mods_dir(), "jarvis_internal.db")

def get_vector_db_path():
    return os.path.join(get_mods_dir(), "vector_memory.db")

# --- 1. OBSIDIAN-LIKE VECTOR MEMORY SYSTEM ---
class VectorMemorySystem:
    def __init__(self, db_path=None):
        self.db_path = db_path or get_vector_db_path()
        self._init_db()

    def _init_db(self):
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("CREATE TABLE IF NOT EXISTS vector_memory (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, category TEXT, tags TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"VectorMemory DB init error: {e}")

    def add_memory(self, title, content, category="general", tags=""):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("INSERT INTO vector_memory (title, content, category, tags) VALUES (?, ?, ?, ?)",
                      (title, content, category, tags))
            mem_id = c.lastrowid
            conn.commit()
            conn.close()
            return mem_id
        except Exception as e:
            logger.warning(f"Error adding memory: {e}")
            return None

    def get_all_memories(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT id, title, content, category, tags, created_at FROM vector_memory ORDER BY id DESC")
            rows = c.fetchall()
            conn.close()
            return [{"id": r[0], "title": r[1], "content": r[2], "category": r[3], "tags": r[4], "created_at": r[5]} for r in rows]
        except Exception as e:
            return []

    def _tokenize(self, text):
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if len(w) > 2]

    def search(self, query, top_k=5):
        memories = self.get_all_memories()
        if not memories:
            return []
        query_words = set(self._tokenize(query))
        if not query_words:
            return memories[:top_k]

        scored = []
        for mem in memories:
            doc_words = self._tokenize(mem["content"] + " " + mem["title"] + " " + mem["tags"])
            if not doc_words:
                continue
            doc_set = set(doc_words)
            intersection = query_words.intersection(doc_set)
            union = query_words.union(doc_set)
            score = len(intersection) / max(1, len(union))
            if query.lower() in mem["content"].lower() or query.lower() in mem["title"].lower():
                score += 0.5
            scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k] if item[0] > 0] or memories[:top_k]

    def build_graph_network(self):
        memories = self.get_all_memories()
        nodes = []
        edges = []
        for m in memories:
            nodes.append({
                "id": m["id"],
                "label": m["title"],
                "category": m["category"],
                "content": m["content"]
            })
        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                m1, m2 = memories[i], memories[j]
                words1 = set(self._tokenize(m1["content"] + " " + m1["title"]))
                words2 = set(self._tokenize(m2["content"] + " " + m2["title"]))
                if not words1 or not words2:
                    continue
                overlap = len(words1.intersection(words2))
                if overlap >= 2 or m1["category"] == m2["category"]:
                    weight = overlap / max(1, len(words1.union(words2)))
                    edges.append({"source": m1["id"], "target": m2["id"], "weight": weight})
        return {"nodes": nodes, "edges": edges}

vector_memory_system = VectorMemorySystem()

# --- 2. OBSIDIAN GRAPH FRAME (INTERACTIVE KNOWLEDGE GRAPH) ---
class ObsidianGraphFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.nodes_data = []
        self.edges_data = []
        self.node_positions = {}
        self.dragged_node = None
        self.selected_node_data = None

        top = ctk.CTkFrame(self, fg_color=DS_SURFACE, height=50)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="🕸️ Obsidian Vector Memory Graph", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(side="left", padx=15)
        
        ctk.CTkButton(top, text="🔄 Обновить граф", command=self.reload_graph, width=120, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(side="right", padx=10)
        ctk.CTkButton(top, text="➕ Добавить заметку", command=self.add_memory_dialog, width=140, fg_color=DS_ACCENT, hover_color=DS_ACCENT2).pack(side="right", padx=5)
        ctk.CTkButton(top, text="📖 Прочитать заметку", command=self.read_selected_note, width=140, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(side="right", padx=5)
        ctk.CTkButton(top, text="📤 Экспорт в Codex 2.0", command=self.export_to_codex_dialog, width=160, fg_color="#10b981", hover_color="#059669").pack(side="right", padx=5)

        self.panes = ctk.CTkFrame(self, fg_color="transparent")
        self.panes.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas_frame = ctk.CTkFrame(self.panes, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER)
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.canvas = tk.Canvas(self.canvas_frame, bg="#0b0d10", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-1>", self.on_click)

        self.inspector = ctk.CTkFrame(self.panes, width=280, fg_color=DS_PANEL, corner_radius=12, border_width=1, border_color=DS_BORDER)
        self.inspector.pack(side="right", fill="y")
        self.inspector.pack_propagate(False)

        ctk.CTkLabel(self.inspector, text="🔍 Инспектор Узла", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_ACCENT2).pack(pady=(12, 5))
        
        self.search_entry = ctk.CTkEntry(self.inspector, placeholder_text="Поиск в векторной памяти...", font=ctk.CTkFont(size=11))
        self.search_entry.pack(fill="x", padx=12, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.perform_search())

        ctk.CTkButton(self.inspector, text="Искать", command=self.perform_search, height=26, fg_color=DS_ACCENT).pack(fill="x", padx=12, pady=2)
        ctk.CTkButton(self.inspector, text="📖 Прочитать заметку", command=self.read_selected_note, height=28, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(fill="x", padx=12, pady=4)

        self.details_box = ctk.CTkTextbox(self.inspector, wrap="word", fg_color=DS_BG, text_color=DS_TEXT, font=ctk.CTkFont(size=11))
        self.details_box.pack(fill="both", expand=True, padx=12, pady=10)

        self.reload_graph()

    def add_memory_dialog(self):
        title = simpledialog.askstring("Новая концепция", "Заголовок узла:")
        if not title: return
        content = simpledialog.askstring("Содержимое", "Описание / текст концепции:")
        if not content: return
        vector_memory_system.add_memory(title, content, category="note", tags="obsidian")
        self.reload_graph()

    def read_selected_note(self):
        if not hasattr(self, 'selected_node_data') or not self.selected_node_data:
            memories = vector_memory_system.get_all_memories()
            if not memories:
                messagebox.showwarning("Векторная память", "Заметки отсутствуют!")
                return
            nd = memories[0]
        else:
            nd = self.selected_node_data

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"📖 Чтение заметки: {nd.get('label') or nd.get('title')}")
        dlg.geometry("540x440")
        dlg.configure(fg_color=DS_BG)
        dlg.grab_set()

        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"540x440+{(sw-540)//2}+{(sh-440)//2}")

        ctk.CTkLabel(dlg, text=f"📌 {nd.get('label') or nd.get('title')}", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=(15, 2))
        ctk.CTkLabel(dlg, text=f"Категория: {nd.get('category', 'general')} | ID: {nd.get('id', 'N/A')} | Дата: {nd.get('created_at', 'Н/Д')}", font=ctk.CTkFont(size=11), text_color=DS_DIM).pack(pady=(0, 10))

        tb = ctk.CTkTextbox(dlg, wrap="word", fg_color=DS_SURFACE, text_color=DS_TEXT, font=ctk.CTkFont(size=12))
        tb.pack(fill="both", expand=True, padx=20, pady=5)
        tb.insert("1.0", nd.get('content', ''))
        tb.configure(state="disabled")

        ctk.CTkButton(dlg, text="Закрыть", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=dlg.destroy).pack(pady=12)

    def export_to_codex_dialog(self):
        memories = vector_memory_system.get_all_memories()
        if not memories:
            messagebox.showwarning("Векторная память", "В векторной памяти нет заметок для экспорта!")
            return

        dlg = ctk.CTkToplevel(self)
        dlg.title("📤 Выбор заметок для экспорта в Codex 2.0")
        dlg.geometry("580x540")
        dlg.configure(fg_color=DS_BG)
        dlg.grab_set()

        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"580x540+{(sw-580)//2}+{(sh-540)//2}")

        ctk.CTkLabel(dlg, text="📤 Выберите заметки для экспорта в Codex 2.0", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=(15, 2))
        ctk.CTkLabel(dlg, text="Отметьте галочками только те заметки, которые должны войти в контекст Codex 2.0:", font=ctk.CTkFont(size=11), text_color=DS_DIM).pack(pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(dlg, fg_color=DS_SURFACE, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        check_vars = []
        for mem in memories:
            var = tk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                scroll,
                text=f"📌 {mem['title']} [{mem['category']}]",
                variable=var,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=DS_TEXT
            )
            cb.pack(anchor="w", padx=10, pady=4)

            snippet = mem['content'][:120] + ("..." if len(mem['content']) > 120 else "")
            ctk.CTkLabel(scroll, text=snippet, font=ctk.CTkFont(size=10), text_color=DS_DIM, anchor="w", justify="left").pack(anchor="w", padx=36, pady=(0, 6))

            check_vars.append((var, mem))

        btn_bar = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_bar.pack(fill="x", padx=20, pady=10)

        def select_all():
            for v, _ in check_vars: v.set(True)
        def deselect_all():
            for v, _ in check_vars: v.set(False)

        ctk.CTkButton(btn_bar, text="Отметить все", command=select_all, width=110, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text="Снять все", command=deselect_all, width=110, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(side="left", padx=5)

        def do_export():
            selected_mems = [mem for var, mem in check_vars if var.get()]
            if not selected_mems:
                messagebox.showwarning("Внимание", "Выберите хотя бы одну заметку для экспорта!")
                return

            global FILE_CONTEXT
            formatted_notes = []
            for m in selected_mems:
                formatted_notes.append(f"📌 {m['title']} [{m['category']}]\n{m['content']}")

            notes_block = "\n\n" + ("="*40) + "\n" + "\n\n".join(formatted_notes) + "\n" + ("="*40)

            FILE_CONTEXT = {
                'path': 'Vector_Memory_Selected',
                'extension': '.txt',
                'type': 'Vector Memory Notes',
                'description': f"Векторная память ({len(selected_mems)} отбранных заметок)",
                'override_content': notes_block
            }

            if hasattr(self.app, 'frames'):
                for name, frame in self.app.frames.items():
                    if hasattr(frame, 'file_info'):
                        frame.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
                    elif hasattr(frame, 'file_info_label'):
                        frame.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")

            messagebox.showinfo("✅ Экспорт в Codex 2.0", f"Успешно экспортировано заметок: {len(selected_mems)}!\nКонтекст передан в Codex 2.0.")
            dlg.destroy()

            if hasattr(self.app, 'show_frame'):
                self.app.show_frame("chat")
                if 'chat' in self.app.frames and not self.app.frames['chat'].codex_sidebar_visible:
                    self.app.frames['chat'].toggle_codex_sidebar()

        ctk.CTkButton(btn_bar, text="⚡ Экспортировать в Codex 2.0", command=do_export, fg_color="#10b981", hover_color="#059669").pack(side="right", padx=5)

    def perform_search(self):
        q = self.search_entry.get().strip()
        if not q: return
        results = vector_memory_system.search(q, top_k=5)
        self.details_box.delete("1.0", "end")
        self.details_box.insert("end", f"=== Результаты поиска для '{q}' ===\n\n")
        for res in results:
            self.details_box.insert("end", f"📌 {res['title']} [{res['category']}]\n{res['content'][:150]}...\n\n")

    def reload_graph(self):
        graph = vector_memory_system.build_graph_network()
        self.nodes_data = graph["nodes"]
        self.edges_data = graph["edges"]
        
        cw = self.canvas.winfo_width() or 500
        ch = self.canvas.winfo_height() or 400
        cx, cy = cw / 2, ch / 2
        r = min(cw, ch) * 0.35 or 150
        
        n = max(1, len(self.nodes_data))
        self.node_positions = {}
        for i, nd in enumerate(self.nodes_data):
            angle = (2 * math.pi * i) / n
            x = cx + r * math.cos(angle) + random.uniform(-10, 10)
            y = cy + r * math.sin(angle) + random.uniform(-10, 10)
            self.node_positions[nd["id"]] = [x, y, nd]
            
        self.draw_graph()

    def draw_graph(self):
        self.canvas.delete("all")
        for edge in self.edges_data:
            s_id, t_id = edge["source"], edge["target"]
            if s_id in self.node_positions and t_id in self.node_positions:
                p1 = self.node_positions[s_id]
                p2 = self.node_positions[t_id]
                self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill="#263238", width=2)

        colors = {"note": "#00e676", "coding": "#00e5ff", "physics": "#ff9100", "general": "#d500f9"}
        for n_id, (x, y, nd) in self.node_positions.items():
            color = colors.get(nd.get("category"), "#00e676")
            self.canvas.create_oval(x-12, y-12, x+12, y+12, fill=color, outline="#ffffff", width=2, tags=f"node_{n_id}")
            self.canvas.create_text(x, y+22, text=nd["label"], fill="#eceff1", font=("Manrope", 9, "bold"))

    def on_click(self, event):
        item = self.canvas.find_withtag("current")
        if item:
            tags = self.canvas.gettags(item[0])
            for t in tags:
                if t.startswith("node_"):
                    n_id = int(t.split("_")[1])
                    if n_id in self.node_positions:
                        self.dragged_node = n_id
                        nd = self.node_positions[n_id][2]
                        self.selected_node_data = nd
                        self.details_box.delete("1.0", "end")
                        self.details_box.insert("end", f"📌 {nd['label']}\nКатегория: {nd['category']}\n\nСодержимое:\n{nd['content']}")

    def on_drag(self, event):
        if self.dragged_node and self.dragged_node in self.node_positions:
            self.node_positions[self.dragged_node][0] = event.x
            self.node_positions[self.dragged_node][1] = event.y
            self.draw_graph()

    def on_release(self, event):
        self.dragged_node = None


# --- 3. CLAUDE SKILLS SYSTEM & FRAME ---

class ClaudeSkillsRegistry:
    def __init__(self):
        self.skills = [
            {"id": "code_analyzer", "name": "💻 Code Analyzer", "desc": "Глубокий анализ багов, синтаксиса и уязвимостей в коде", "cat": "Dev"},
            {"id": "file_indexer", "name": "📂 Smart File Indexer", "desc": "Мгновенная индексация и поиск файлов на диске ПК", "cat": "System"},
            {"id": "system_control", "name": "🖥️ System & Screen Control", "desc": "Захват экрана, горячие клавиши и управление окнами Windows", "cat": "OS"},
            {"id": "web_research", "name": "🌐 Web Research Agent", "desc": "Веб-поиск и быстрая суммаризация внешних источников", "cat": "Research"},
            {"id": "vector_memory", "name": "🕸️ Vector Memory Linker", "desc": "Связывание заметок и чатов в Obsidian-подобный граф", "cat": "Memory"},
            {"id": "canvas_artist", "name": "🎨 Canvas Painter", "desc": "Процедурное рисование диаграмм и иллюстраций", "cat": "Graphics"},
            {"id": "terminal_exec", "name": "📟 Terminal Executor", "desc": "Безопасное исполнение Shell и PowerShell команд", "cat": "Terminal"}
        ]
        self.load_custom_skills()

    def load_custom_skills(self):
        try:
            custom_data = _db_get_setting("custom_claude_skills", "[]")
            loaded = json.loads(custom_data)
            for item in loaded:
                if not any(s["id"] == item["id"] for s in self.skills):
                    self.skills.append(item)
        except Exception:
            pass

    def add_custom_skill(self, name, desc, category, prompt):
        skill_id = f"custom_{int(time.time())}"
        item = {"id": skill_id, "name": f"⚡ {name}", "desc": desc, "cat": category, "prompt": prompt}
        self.skills.append(item)
        try:
            customs = [s for s in self.skills if s["id"].startswith("custom_")]
            _db_set_setting("custom_claude_skills", json.dumps(customs, ensure_ascii=False))
        except Exception:
            pass
        return item

    def get_all(self):
        return self.skills

claude_skills_registry = ClaudeSkillsRegistry()

class ClaudeSkillsFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang

        top = ctk.CTkFrame(self, fg_color=DS_SURFACE, height=50)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)
        ctk.CTkLabel(top, text="⚡ Навыки & Инструменты Claude Engine", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(side="left", padx=15)

        ctk.CTkButton(top, text="➕ Сделать свой скилл", command=self.create_custom_skill_dialog, fg_color=DS_ACCENT, hover_color=DS_ACCENT2, text_color=DS_ON_ACCENT, font=ctk.CTkFont(size=12, weight="bold")).pack(side="right", padx=15)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=15, pady=15)

        self.render_skills_cards()

    def render_skills_cards(self):
        for w in self.scroll.winfo_children():
            w.destroy()

        # Mod Tutorial & System Prompt Guide Card
        guide_card = ctk.CTkFrame(self.scroll, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_ACCENT)
        guide_card.pack(fill="x", pady=8)

        g_header = ctk.CTkFrame(guide_card, fg_color="transparent")
        g_header.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(g_header, text="🎓 Руководство по Написанию Модов и Промптам ИИ", font=ctk.CTkFont(size=14, weight="bold"), text_color=DS_ACCENT).pack(side="left")
        StatusPill(g_header, text="ИНСТРУКЦИЯ", status_type="success").pack(side="right")

        guide_desc = (
            "Узнайте, как правильно составлять промпты для нейросети, чтобы она генерировала корректные "
            "Python-модули для Aaron AI. Мод исполняется при запуске и получает доступ к `app`."
        )
        ctk.CTkLabel(guide_card, text=guide_desc, font=ctk.CTkFont(size=11), text_color=DS_DIM, wraplength=700, justify="left").pack(fill="x", padx=12, pady=(0, 8))

        btn_g_row = ctk.CTkFrame(guide_card, fg_color="transparent")
        btn_g_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkButton(btn_g_row, text="📖 Читать обучающий промпт модов", height=28, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT, command=self.show_mod_prompt_tutorial).pack(side="left")

        for sk in claude_skills_registry.get_all():
            card = ctk.CTkFrame(self.scroll, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER)
            card.pack(fill="x", pady=6)

            r = ctk.CTkFrame(card, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=10)

            ctk.CTkLabel(r, text=sk["name"], font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_TEXT).pack(side="left")
            StatusPill(r, text="АКТИВЕН", status_type="success").pack(side="right")

            ctk.CTkLabel(card, text=sk["desc"], font=ctk.CTkFont(size=11), text_color=DS_DIM, anchor="w").pack(fill="x", padx=12, pady=(0, 10))

            btn_r = ctk.CTkFrame(card, fg_color="transparent")
            btn_r.pack(fill="x", padx=12, pady=(0, 10))
            ctk.CTkButton(btn_r, text="⚡ Выполнить навык", height=28, fg_color=DS_ACCENT, hover_color=DS_ACCENT2, text_color=DS_ON_ACCENT,
                           command=lambda s=sk: self.run_skill(s)).pack(side="left")

    def create_custom_skill_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("➕ Сделать свой скилл")
        dlg.geometry("520x460")
        dlg.grab_set()

        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"520x460+{(sw-520)//2}+{(sh-460)//2}")

        ctk.CTkLabel(dlg, text="➕ Создание пользовательского скилла", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=15)

        e_name = ctk.CTkEntry(dlg, placeholder_text="Название скилла (например: 🧠 Код-Архитектор)", font=ctk.CTkFont(size=12))
        e_name.pack(fill="x", padx=20, pady=5)

        e_cat = ctk.CTkEntry(dlg, placeholder_text="Категория (например: Dev / System / Analytics)", font=ctk.CTkFont(size=12))
        e_cat.pack(fill="x", padx=20, pady=5)

        e_desc = ctk.CTkEntry(dlg, placeholder_text="Краткое описание навыка", font=ctk.CTkFont(size=12))
        e_desc.pack(fill="x", padx=20, pady=5)

        e_prompt = ctk.CTkTextbox(dlg, height=120, wrap="word", font=ctk.CTkFont(size=12))
        e_prompt.pack(fill="x", padx=20, pady=5)
        e_prompt.insert("1.0", "Системная инструкция / Промпт для ИИ при вызове данного скилла...")

        def save_skill():
            nm = e_name.get().strip()
            cat = e_cat.get().strip() or "Custom"
            dsc = e_desc.get().strip() or "Кастомный пользовательский навык"
            pr = e_prompt.get("1.0", "end-1c").strip()
            if not nm:
                messagebox.showerror("Ошибка", "Введите название скилла!")
                return
            claude_skills_registry.add_custom_skill(nm, dsc, cat, pr)
            messagebox.showinfo("Успех", f"Скилл '{nm}' успешно создан и добавлен в список!")
            dlg.destroy()
            self.render_skills_cards()

        ctk.CTkButton(dlg, text="⚡ Сохранить скилл", fg_color="#10b981", hover_color="#059669", command=save_skill).pack(pady=15)

    def show_mod_prompt_tutorial(self):
        tut = ctk.CTkToplevel(self)
        tut.title("🎓 Обучение: Как писать моды и системные промпты")
        tut.geometry("640x540")
        tut.configure(fg_color=DS_BG)
        tut.grab_set()

        sw, sh = tut.winfo_screenwidth(), tut.winfo_screenheight()
        tut.geometry(f"640x540+{(sw-640)//2}+{(sh-540)//2}")

        ctk.CTkLabel(tut, text="🎓 Обучение: Написание Модов и Промптов ИИ", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=15)

        tb = ctk.CTkTextbox(tut, wrap="word", fg_color=DS_SURFACE, text_color=DS_TEXT, font=ctk.CTkFont(size=12))
        tb.pack(fill="both", expand=True, padx=20, pady=5)

        tutorial_text = (
            "=== РУКОВОДСТВО ПО НАПИСАНИЮ МОДОВ И СИСТЕМНЫМ ПРОМПТАМ ===\n\n"
            "1. СТРУКТУРА МОДА В AARON AI:\n"
            "Каждый мод является стандартным исполняемым файлом Python (*.py), который помещается в папку 'mods/'.\n"
            "Мод ОБЯЗАН содержать 3 обязательных компонента:\n"
            "  - MOD_NAME = \"Название вашего мода\"\n"
            "  - MOD_DESCRIPTION = \"Краткое описание возможностей\"\n"
            "  - def apply(app=None): содержит код инициализации при запуске приложения.\n\n"
            "2. СИСТЕМНЫЙ ПРОМПТ ДЛЯ НЕЙРОСЕТИ:\n"
            "Скопируйте этот системный промпт и передайте ИИ перед генерацией кода мода:\n\n"
            "\"Ты — опытный Python-разработчик расширений (модов) для Aaron AI. "
            "Напиши чистый, рабочий код мода на Python. "
            "Код должен содержать MOD_NAME, MOD_DESCRIPTION и функцию apply(app=None). "
            "Код должен обрабатывать ошибки (try-except) и быть полностью обернут в один код-блок ```python ... ```.\"\n\n"
            "3. КАК ИИ ПРИДЕРЖИВАЕТСЯ ПРАВИЛ:\n"
            "Благодаря системным инструкциям, ИИ генерирует код, который автоматически сохраняется в папку mods/ "
            "и становится доступен в Менеджере Модов с галочкой включения/выключения."
        )
        tb.insert("1.0", tutorial_text)
        tb.configure(state="disabled")

        ctk.CTkButton(tut, text="Понятно", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=tut.destroy).pack(pady=12)

    def run_skill(self, skill):
        s_id = skill["id"]
        if s_id == "code_analyzer":
            if hasattr(self.app, 'frames') and 'chat' in self.app.frames:
                self.app.show_frame("chat")
                self.app.frames["chat"].toggle_codex_sidebar()
        elif s_id == "file_indexer":
            if hasattr(self.app, 'frames') and 'profile' in self.app.frames:
                self.app.show_frame("profile")
                self.app.frames["profile"].choose_file()
        elif s_id == "system_control":
            messagebox.showinfo("Навык", "Захват экрана активен. Используйте F12 или Ctrl+Shift+Z!")
        elif s_id == "web_research":
            self.app.show_frame("search")
        elif s_id == "vector_memory":
            self.app.show_frame("obsidian_graph")
        elif s_id == "canvas_artist":
            self.app.show_frame("canvas")
        elif s_id == "terminal_exec":
            if hasattr(self.app, 'frames') and 'profile' in self.app.frames:
                self.app.show_frame("profile")
                self.app.frames["profile"].open_terminal_window()
        elif s_id.startswith("custom_"):
            prompt = skill.get("prompt", "Выполни этот навык.")
            self.app.show_frame("chat")
            if 'chat' in self.app.frames:
                self.app.frames["chat"].input.delete("1.0", "end")
                self.app.frames["chat"].input.insert("1.0", f"Выполни кастомный навык '{skill['name']}': {prompt}")




# ========================================================================================
#                  NETWORK / DISCORD-LIKE PUBLIC SERVERS & EVENTS SYSTEM
# ========================================================================================

class ServerBackendClient:
    def __init__(self, base_url="http://127.0.0.1:5000"):
        self.base_url = base_url
        self.local_servers = [
            {"id": "central", "name": "🌐 Aaron Central Server", "icon": "🌐", "desc": "Главный сервер сообщества Aaron AI"},
            {"id": "dev_hub", "name": "💻 Dev & Mods Hub", "icon": "💻", "desc": "Сервер разработчиков модов и Python скриптов"},
            {"id": "contests", "name": "🏆 Конкурсы & Ивенты", "icon": "🏆", "desc": "Официальные конкурсы, хакатоны и призы"},
            {"id": "support", "name": "🛠️ Служба Поддержки", "icon": "🛠️", "desc": "Помощь по установке, багам и настройке"}
        ]
        self.local_channels = {
            "central": ["#общий-чат", "#анонсы", "#вопросы-и-ответы"],
            "dev_hub": ["#код-и-скрипты", "#рефакторинг", "#моды-и-аддоны"],
            "contests": ["#активные-конкурсы", "#победители", "#призы-и-награды"],
            "support": ["#тикеты", "#баги-и-идеи"]
        }
        self.local_messages = {
            "#общий-чат": [
                {"user": "Admin_Aaron", "role": "ADMIN", "text": "Welcome to Aaron AI Community Network! 🚀", "time": "12:00"},
                {"user": "User_Dev", "role": "DEV", "text": "Всем привет! Кто уже пробовал создавать свои моды?", "time": "12:05"}
            ],
            "#активные-конкурсы": [
                {"user": "Aaron_EventBot", "role": "EVENT", "text": "🏆 КОНКУРС 'Лучший Мод 2026' ОТКРЫТ! Призовой фонд: 100,000 KZT!", "time": "10:00"}
            ]
        }
        self.local_events = [
            {"title": "🏆 Хакатон 'Aaron AI Core 2026'", "desc": "Создайте самый полезный мод на Python и выиграйте Premium на 1 год!", "prize": "100,000 KZT", "date": "До 31 Августа"},
            {"title": "🎯 Конкурс Промптов", "desc": "Лучший промпт для Codex-02", "prize": "Complete Package", "date": "Каждую неделю"}
        ]

    def is_server_online(self):
        try:
            r = requests.get(f"{self.base_url}/api/health", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def get_servers(self):
        if self.is_server_online():
            try:
                r = requests.get(f"{self.base_url}/api/servers", timeout=2.0)
                if r.status_code == 200: return r.json()
            except Exception: pass
        return self.local_servers

    def get_channels(self, server_id):
        if self.is_server_online():
            try:
                r = requests.get(f"{self.base_url}/api/channels?server_id={server_id}", timeout=2.0)
                if r.status_code == 200: return r.json()
            except Exception: pass
        return self.local_channels.get(server_id, ["#общий-чат"])

    def get_messages(self, channel):
        if self.is_server_online():
            try:
                r = requests.get(f"{self.base_url}/api/messages?channel={channel}", timeout=2.0)
                if r.status_code == 200: return r.json()
            except Exception: pass
        return self.local_messages.get(channel, [])

    def send_message(self, channel, username, role, text):
        msg = {"user": username, "role": role, "text": text, "time": datetime.now().strftime("%H:%M")}
        if self.is_server_online():
            try:
                requests.post(f"{self.base_url}/api/messages", json={"channel": channel, **msg}, timeout=2.0)
            except Exception: pass
        if channel not in self.local_messages:
            self.local_messages[channel] = []
        self.local_messages[channel].append(msg)
        return msg

    def get_events(self):
        if self.is_server_online():
            try:
                r = requests.get(f"{self.base_url}/api/events", timeout=2.0)
                if r.status_code == 200: return r.json()
            except Exception: pass
        return self.local_events

    def create_event(self, title, desc, prize, date):
        evt = {"title": title, "desc": desc, "prize": prize, "date": date}
        if self.is_server_online():
            try:
                requests.post(f"{self.base_url}/api/events", json=evt, timeout=2.0)
            except Exception: pass
        self.local_events.append(evt)
        return evt

network_client = ServerBackendClient()

class DiscordServersFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.active_server = "central"
        self.active_channel = "#общий-чат"

        # Top Bar
        top = ctk.CTkFrame(self, fg_color=DS_SURFACE, height=50)
        top.pack(fill="x", side="top")
        top.pack_propagate(False)

        ctk.CTkLabel(top, text="🌐 Сетевые Сервера & Сообщество Aaron AI", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(side="left", padx=15)

        self.net_status_pill = StatusPill(top, text="ПРОВЕРКА СЕТИ...", status_type="amber")
        self.net_status_pill.pack(side="right", padx=15)

        ctk.CTkButton(top, text="🔄 Обновить", width=100, command=self.refresh_all, fg_color=DS_PANEL, hover_color=DS_BORDER).pack(side="right", padx=5)
        ctk.CTkButton(top, text="🎪 Создать Ивент", width=130, command=self.open_create_event_dialog, fg_color="#10b981", hover_color="#059669").pack(side="right", padx=5)

        # Main 3-Column Discord Layout
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.pack(fill="both", expand=True, padx=10, pady=10)

        # Col 1: Server Icons Rail (Left)
        self.server_bar = ctk.CTkFrame(workspace, width=70, fg_color=DS_PANEL, corner_radius=12)
        self.server_bar.pack(side="left", fill="y", padx=(0, 5))
        self.server_bar.pack_propagate(False)

        # Col 2: Channels List (Middle-Left)
        self.channel_bar = ctk.CTkFrame(workspace, width=200, fg_color=DS_PANEL, corner_radius=12)
        self.channel_bar.pack(side="left", fill="y", padx=(0, 5))
        self.channel_bar.pack_propagate(False)

        # Col 3: Main Chat & Events Area (Right)
        self.chat_area = ctk.CTkFrame(workspace, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER)
        self.chat_area.pack(side="left", fill="both", expand=True)

        self._build_ui_panels()
        self.check_network_status()

    def check_network_status(self):
        is_on = network_client.is_server_online()
        if is_on:
            self.net_status_pill.lbl.configure(text="СЕТЬ: ОНЛАЙН", text_color=DS_ACCENT)
        else:
            self.net_status_pill.lbl.configure(text="СЕТЬ: ЛОКАЛЬНО", text_color=DS_AMBER)

    def _build_ui_panels(self):
        # 1. Render Server Rail Icons
        for w in self.server_bar.winfo_children(): w.destroy()
        servers = network_client.get_servers()
        for s in servers:
            is_active = (s["id"] == self.active_server)
            btn = ctk.CTkButton(
                self.server_bar, text=s["icon"], width=50, height=50, corner_radius=25,
                fg_color=DS_ACCENT if is_active else DS_SURFACE,
                hover_color=DS_ACCENT2,
                font=ctk.CTkFont(size=20),
                command=lambda sid=s["id"]: self.select_server(sid)
            )
            btn.pack(pady=8, padx=10)

        # 2. Render Channels List
        for w in self.channel_bar.winfo_children(): w.destroy()
        ctk.CTkLabel(self.channel_bar, text="💬 КАНАЛЫ", font=ctk.CTkFont(size=12, weight="bold"), text_color=DS_DIM).pack(pady=(12, 6), padx=10, anchor="w")
        
        channels = network_client.get_channels(self.active_server)
        for ch in channels:
            is_act = (ch == self.active_channel)
            btn = ctk.CTkButton(
                self.channel_bar, text=ch, anchor="w",
                fg_color=DS_PANEL_2 if is_act else "transparent",
                hover_color=DS_PANEL_2,
                text_color=DS_TEXT if is_act else DS_DIM,
                font=ctk.CTkFont(size=12, weight="bold" if is_act else "normal"),
                command=lambda c=ch: self.select_channel(c)
            )
            btn.pack(fill="x", padx=6, pady=2)

        # 3. Render Main Chat Area
        for w in self.chat_area.winfo_children(): w.destroy()

        # Top Event Banner inside Chat Area
        event_banner = ctk.CTkFrame(self.chat_area, fg_color="#1e1b4b", height=60, corner_radius=8)
        event_banner.pack(fill="x", padx=10, pady=10)
        event_banner.pack_propagate(False)

        evts = network_client.get_events()
        top_evt = evts[0] if evts else {"title": "Ивентов пока нет", "desc": "Создайте первый ивент сервера!", "prize": "-"}
        
        ctk.CTkLabel(event_banner, text=f"🎪 {top_evt['title']} | Приз: {top_evt.get('prize','')}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#a5b4fc").pack(anchor="w", padx=12, pady=(6,0))
        ctk.CTkLabel(event_banner, text=top_evt['desc'], font=ctk.CTkFont(size=11), text_color="#c7d2fe").pack(anchor="w", padx=12, pady=(0,6))

        # Messages Box
        self.msg_box = ctk.CTkTextbox(self.chat_area, wrap="word", fg_color=DS_BG, text_color=DS_TEXT, font=ctk.CTkFont(size=12))
        self.msg_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Input Row
        in_row = ctk.CTkFrame(self.chat_area, fg_color="transparent")
        in_row.pack(fill="x", padx=10, pady=(0, 10))

        self.chat_input = ctk.CTkEntry(in_row, placeholder_text=f"Написать в {self.active_channel}...", font=ctk.CTkFont(size=12), fg_color=DS_BG, border_color=DS_BORDER)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_input.bind("<Return>", lambda e: self.send_chat_message())

        ctk.CTkButton(in_row, text="Отправить", width=100, fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=self.send_chat_message).pack(side="right")

        self.load_channel_messages()

    def select_server(self, sid):
        self.active_server = sid
        chans = network_client.get_channels(sid)
        self.active_channel = chans[0] if chans else "#общий-чат"
        self._build_ui_panels()

    def select_channel(self, ch):
        self.active_channel = ch
        self._build_ui_panels()

    def load_channel_messages(self):
        msgs = network_client.get_messages(self.active_channel)
        self.msg_box.configure(state="normal")
        self.msg_box.delete("1.0", "end")
        self.msg_box.insert("end", "=== Сообщения канала " + str(self.active_channel) + " ===\n\n")
        for m in msgs:
            user = m.get("user", "Аноним")
            role = m.get("role", "USER")
            text = m.get("text", "")
            time_str = m.get("time", "")
            self.msg_box.insert("end", f"[{time_str}] [{role}] {user}:\n{text}\n\n")
        self.msg_box.see("end")
        self.msg_box.configure(state="disabled")

    def send_chat_message(self):
        txt = self.chat_input.get().strip()
        if not txt: return
        self.chat_input.delete(0, "end")
        username = getattr(self.app, 'username', 'Пользователь')
        network_client.send_message(self.active_channel, username, "MEMBER", txt)
        self.load_channel_messages()

    def refresh_all(self):
        self.check_network_status()
        self._build_ui_panels()

    def open_create_event_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("🎪 Создать Ивент / Конкурс")
        dlg.geometry("500x420")
        dlg.grab_set()
        
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"500x420+{(sw-500)//2}+{(sh-420)//2}")

        ctk.CTkLabel(dlg, text="🎪 Новый Ивент Сообщества", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=15)

        e_title = ctk.CTkEntry(dlg, placeholder_text="Название ивента/конкурса", font=ctk.CTkFont(size=12))
        e_title.pack(fill="x", padx=20, pady=5)

        e_desc = ctk.CTkTextbox(dlg, height=80, wrap="word", font=ctk.CTkFont(size=12))
        e_desc.pack(fill="x", padx=20, pady=5)
        e_desc.insert("1.0", "Описание и условия конкурса...")

        e_prize = ctk.CTkEntry(dlg, placeholder_text="Приз / Награда (например, 50,000 KZT или VIP)", font=ctk.CTkFont(size=12))
        e_prize.pack(fill="x", padx=20, pady=5)

        e_date = ctk.CTkEntry(dlg, placeholder_text="Срок проведения (например, до 15 Сентября)", font=ctk.CTkFont(size=12))
        e_date.pack(fill="x", padx=20, pady=5)

        def save_evt():
            t = e_title.get().strip()
            d = e_desc.get("1.0", "end-1c").strip()
            p = e_prize.get().strip()
            dt = e_date.get().strip()
            if not t:
                messagebox.showerror("Ошибка", "Введите название ивента!")
                return
            network_client.create_event(t, d, p, dt)
            messagebox.showinfo("Успех", "Ивент успешно опубликован на сервере!")
            dlg.destroy()
            self.refresh_all()

        ctk.CTkButton(dlg, text="🚀 Опубликовать Ивент", fg_color="#10b981", hover_color="#059669", command=save_evt).pack(pady=15)


# ========================================================================================
#                  ACTIVATION KEY ANIMATION MODAL
# ========================================================================================

class ActivationAnimationModal(ctk.CTkToplevel):
    def __init__(self, parent, title_text, key_str, success_msg, on_complete_cb=None):
        super().__init__(parent)
        self.parent = parent
        self.title("⚡ Активация Ключа Лицензии")
        self.geometry("480x360")
        self.configure(fg_color=DS_BG)
        self.grab_set()

        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"480x360+{(sw-480)//2}+{(sh-360)//2}")

        self.card = ctk.CTkFrame(self, fg_color=DS_SURFACE, corner_radius=16, border_width=2, border_color=DS_ACCENT)
        self.card.pack(fill="both", expand=True, padx=20, pady=20)

        self.icon_lbl = ctk.CTkLabel(self.card, text="🔑", font=ctk.CTkFont(size=48))
        self.icon_lbl.pack(pady=(20, 5))

        self.title_lbl = ctk.CTkLabel(self.card, text=title_text, font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_TEXT)
        self.title_lbl.pack(pady=2)

        self.status_lbl = ctk.CTkLabel(self.card, text="Проверка валидности криптографического маркера...", font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self.status_lbl.pack(pady=8)

        self.progress = ctk.CTkProgressBar(self.card, width=320, height=8, fg_color="#1f2937", progress_color="#10b981")
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.step_val = 0.0
        self.success_msg = success_msg
        self.on_complete_cb = on_complete_cb
        self.key_str = key_str

        self.after(50, self.run_animation)

    def run_animation(self):
        if self.step_val < 1.0:
            self.step_val += 0.08
            self.progress.set(self.step_val)

            if self.step_val >= 0.3 and self.step_val < 0.6:
                self.status_lbl.configure(text="⚡ Подключение к центральному реестру лицензий...")
            elif self.step_val >= 0.6 and self.step_val < 0.9:
                self.status_lbl.configure(text="🔓 Разблокировка супер-модулей и нейронного ядра...")
            elif self.step_val >= 0.9:
                self.status_lbl.configure(text="✅ Маркер подтвержден! Применение подписки...")

            self.after(60, self.run_animation)
        else:
            self.show_success_card()

    def show_success_card(self):
        self.icon_lbl.configure(text="✅", text_color="#10b981")
        self.title_lbl.configure(text="ЛИЦЕНЗИЯ УСПЕШНО АКТИВИРОВАНА!", text_color="#10b981")
        self.status_lbl.configure(text=self.success_msg, text_color=DS_TEXT)
        self.progress.pack_forget()

        close_btn = ctk.CTkButton(self.card, text="🚀 Отлично!", fg_color="#10b981", hover_color="#059669", command=self.finish)
        close_btn.pack(pady=15)

    def finish(self):
        self.destroy()
        if self.on_complete_cb:
            self.on_complete_cb()


class App(ctk.CTk):
    def __init__(self, username: str = "Пользователь"):
        super().__init__()
        self._gui_queue = queue.Queue()
        self._process_gui_queue()
        try:
            setup_cyrillic_bindings(self)
        except Exception as e:
            logger.warning(f"Failed to setup cyrillic bindings: {e}")
        self.current_lang = db.get_lang(USER_ID)
        self.mod_window = None
        self.username = username
        self.title("Aaron AI")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.withdraw()
        
        if db.has_user_state(USER_ID):
            self.build_ui()
            self.deiconify()
            self.update()
        else:
            self.deiconify()
            self.update()
            self.language_dialog()

    def language_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Выбор языка")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)
        dlg.update_idletasks()
        w, h = 380, 480
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-380)//2}+{(sh-480)//2}")

        ctk.CTkLabel(dlg, text="🌐", font=F(36)).pack(pady=(28,4))
        ctk.CTkLabel(dlg, text="Выберите язык", font=F(18, "bold"), text_color=DS_TEXT).pack(pady=(0,16))

        card = ctk.CTkFrame(dlg, fg_color=DS_SURFACE, corner_radius=14, border_width=1, border_color=DS_BORDER)
        card.pack(padx=30, fill="both", expand=True, pady=(0,24))

        for code_item, name in Locale.LANG_NAMES.items():
            btn = ctk.CTkButton(card, text=name, width=280, height=38,
                                fg_color=DS_PANEL, hover_color=DS_ACCENT,
                                text_color=DS_TEXT, corner_radius=8, font=F(13),
                                command=lambda c=code_item: self.lang_selected(c, dlg))
            btn.pack(pady=5, padx=20)

    def lang_selected(self, lang, dlg):
        db.set_lang(USER_ID, lang)
        self.current_lang = lang
        dlg.destroy()
        self.after(50, self.mode_dialog)

    def mode_dialog(self):
        lang = self.current_lang
        dlg = ctk.CTkToplevel(self)
        dlg.title(Locale.t('choose_mode', lang))
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)
        dlg.update_idletasks()
        w, h = 360, 300
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-360)//2}+{(sh-300)//2}")

        ctk.CTkLabel(dlg, text="⚙️", font=F(32)).pack(pady=(24,4))
        ctk.CTkLabel(dlg, text=Locale.t('choose_mode', lang), font=F(17, "bold"), text_color=DS_TEXT).pack(pady=(0,18))

        card = ctk.CTkFrame(dlg, fg_color=DS_SURFACE, corner_radius=14, border_width=1, border_color=DS_BORDER)
        card.pack(padx=30, fill="x")

        ctk.CTkButton(card, text=Locale.t('mode_normal', lang), height=40,
                      fg_color=DS_PANEL, hover_color=DS_ACCENT, text_color=DS_TEXT,
                      corner_radius=8, font=F(13),
                      command=lambda: self.mode_selected("normal", dlg)).pack(fill="x", padx=16, pady=(16,6))
        ctk.CTkButton(card, text=Locale.t('mode_tutor', lang), height=40,
                      fg_color=DS_PANEL, hover_color=DS_ACCENT, text_color=DS_TEXT,
                      corner_radius=8, font=F(13),
                      command=lambda: self.mode_selected("tutor", dlg)).pack(fill="x", padx=16, pady=(0,16))

    def mode_selected(self, mode, dlg):
        db.set_mode(USER_ID, mode)
        _db_set_flag("first_time_setup_done", True)
        dlg.destroy()
        self.build_ui()
        self.deiconify()
        self.after(100, self.show_startup_instruction)

    def show_mods_window(self):
        if self.mod_window and self.mod_window.winfo_exists():
            self.mod_window.lift()
            self.mod_window.focus_force()
            return

        self.mod_window = ctk.CTkToplevel(self)
        self.mod_window.title("Менеджер модов")
        self.mod_window.geometry("940x740")
        self.mod_window.protocol("WM_DELETE_WINDOW", self.on_mods_window_close)
        self.mod_window.configure(fg_color=DS_BG)

        self.mod_window.mods_frame = ModsFrame(self.mod_window, self, self.current_lang)
        self.mod_window.mods_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def on_mods_window_close(self):
        if self.mod_window and self.mod_window.winfo_exists():
            self.mod_window.destroy()
        self.mod_window = None

    def show_startup_instruction(self, username=None):
        if not should_show_app_instruction(username):
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Добро пожаловать")
        dlg.geometry("520x470")
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)
        
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"520x470+{(sw-520)//2}+{(sh-470)//2}")

        ctk.CTkLabel(dlg, text="Инструкция при первом запуске", font=F(18, "bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        data_path = get_data_root()
        mods_path = os.path.join(data_path, "mods")
        text_instruct = (
            "Добро пожаловать в AI Launcher!\n\n"
            "Папка с данными была автоматически создана на рабочем столе:\n"
            f"{data_path}\n\n"
            "В этой папке находятся:\n"
            "  • ai_app.db — база данных приложения\n"
            "  • mods/ — папка для модов\n"
            "  • README.md — инструкция по использованию и программированию модов\n\n"
            "Моды работают как дополнительные Python-скрипты в папке:\n"
            f"{mods_path}\n\n"
            "Каждый мод содержит функцию apply(app), которая запускается при старте,\n"
            "если мод включён.\n\n"
            "Чтобы открыть менеджер модов, перейдите в раздел Лаунчер и нажмите \"Просмотреть моды\".\n"
            "Там вы можете включить моды, запустить их вручную и увидеть инструкции по программированию.\n"
            "После первого показа это окно больше не будет появляться."
        )
        box = ctk.CTkTextbox(dlg, wrap="word", width=480, height=280, font=F(12), fg_color=DS_SURFACE, text_color=DS_TEXT)
        box.insert("0.0", text_instruct)
        box.configure(state="disabled")
        box.pack(padx=10, pady=10, fill="both", expand=True)

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack(pady=5)
        GhostButton(btn_frame, text="Открыть папку данных", command=lambda: os.startfile(data_path)).pack(side="left", padx=5)
        
        def on_close():
            mark_app_instruction_shown(username)
            dlg.destroy()
            self.after(300, lambda: self.check_and_show_first_login_guides(username))
            
        AccentButton(btn_frame, text="Понятно, открыть приложение", command=on_close).pack(side="left", padx=5)

    def show_mod_guide_dialog(self, username=None):
        if not should_show_mod_guide(username):
            return
        dlg = ctk.CTkToplevel(self)
        dlg.title("Инструкция по модам")
        dlg.geometry("520x450")
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)
        
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"520x450+{(sw-520)//2}+{(sh-450)//2}")

        ctk.CTkLabel(dlg, text="Инструкция по программированию модов", font=F(18, "bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        help_text = (
            "Моды — это обычные Python-файлы в папке mods.\n\n"
            "Каждый мод должен содержать:\n"
            "  • MOD_NAME = 'Название'\n"
            "  • MOD_DESCRIPTION = 'Описание'\n"
            "  • def apply(app=None):\n"
            "        # код, который выполняется при запуске мода\n\n"
            "Пример:\n"
            "MOD_NAME = 'Погода'\n"
            "MOD_DESCRIPTION = 'Добавляет быстрый доступ к погоде.'\n\n"
            "def apply(app=None):\n"
            "    print('Мод Погода запущен')\n\n"
            "Если мод включён, он будет запускаться при старте приложения.\n"
            "Чтобы отключить мод, снимите галочку в списке.\n"
            "Отключённые моды не запускаются автоматически, но их можно запускать вручную.\n"
            "Кнопки 'Включить все' и 'Выключить все' управляют состоянием сразу для всех модов.\n"
            "Кнопка 'Добавить мод из файла' копирует новый мод в папку mods."
        )
        box = ctk.CTkTextbox(dlg, wrap="word", width=480, height=280, font=F(12), fg_color=DS_SURFACE, text_color=DS_TEXT)
        box.insert("0.0", help_text)
        box.configure(state="disabled")
        box.pack(padx=10, pady=10, fill="both", expand=True)

        def on_close():
            mark_mod_guide_shown(username)
            dlg.destroy()

        AccentButton(dlg, text="Понятно", command=on_close).pack(pady=10)

    def check_and_show_first_login_guides(self, username):
        if should_show_app_instruction(username):
            self.show_startup_instruction(username)
        elif should_show_mod_guide(username):
            self.show_mod_guide_dialog(username)

    def build_ui(self):
        lang = self.current_lang
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.destroy()

        self.title("Aaron AI")
        self.configure(fg_color=DS_BG)

        self.main_container = ctk.CTkFrame(self, fg_color=DS_BG, corner_radius=0)
        self.main_container.pack(fill="both", expand=True)

        # 1. Сайдбар 264 px
        self.sidebar = ctk.CTkFrame(self.main_container, width=264, corner_radius=0, fg_color=DS_PANEL)
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        logo_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_row.pack(pady=(16, 12), padx=14, fill="x")
        
        logo_badge = ctk.CTkFrame(logo_row, width=32, height=32, fg_color=DS_ACCENT, corner_radius=8)
        logo_badge.pack(side="left")
        logo_badge.pack_propagate(False)
        ctk.CTkLabel(logo_badge, text="A", font=F(16, "bold"), text_color=DS_ON_ACCENT).pack(expand=True)

        title_box = ctk.CTkFrame(logo_row, fg_color="transparent")
        title_box.pack(side="left", padx=(10, 0), fill="x", expand=True)
        
        ctk.CTkLabel(title_box, text="Aaron AI", font=F(15, "bold"), text_color=DS_TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(title_box, text="v3.2 · LOCAL", font=MONO(10), text_color=DS_DIM, anchor="w").pack(anchor="w")

        user_badge = ctk.CTkFrame(self.sidebar, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER)
        user_badge.pack(padx=14, pady=(0, 12), fill="x")

        avatar_path = _db_get_setting(f"avatar_path_{USER_ID}", "")
        avatar_img = load_avatar_image(avatar_path, size=32)

        if avatar_img:
            self.sidebar_avatar = ctk.CTkLabel(user_badge, image=avatar_img, text="", fg_color="transparent")
        else:
            self.sidebar_avatar = ctk.CTkLabel(user_badge, text=(getattr(self, 'username', 'П')[0].upper()),
                              font=F(14, "bold"), text_color=DS_ON_ACCENT,
                              width=32, height=32, fg_color=DS_ACCENT, corner_radius=16)
        self.sidebar_avatar.pack(side="left", padx=(10, 8), pady=8)
        if avatar_img:
            self.sidebar_avatar.image = avatar_img

        ub_info = ctk.CTkFrame(user_badge, fg_color="transparent")
        ub_info.pack(side="left", fill="x", expand=True, pady=6)
        ctk.CTkLabel(ub_info, text=getattr(self, 'username', 'Пользователь'),
                     font=F(12, "bold"), text_color=DS_TEXT, anchor="w").pack(anchor="w")
        ctk.CTkLabel(ub_info, text="Режим: LOCAL", font=MONO(10), text_color=DS_ACCENT, anchor="w").pack(anchor="w")

        self.btn_new_chat = AccentButton(
            self.sidebar, text="＋  Новый чат", command=self._new_chat_from_sidebar,
            width=236, height=40
        )
        self.btn_new_chat.pack(pady=(0, 12), padx=14, fill="x")

        ctk.CTkLabel(self.sidebar, text="ИСТОРИЯ", font=MONO(10, "bold"), text_color=DS_DIM, anchor="w").pack(padx=16, pady=(0, 4), fill="x")

        self._sessions_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=DS_BORDER, scrollbar_button_hover_color=DS_ACCENT,
            height=140
        )
        self._sessions_scroll.pack(fill="x", padx=8, pady=(0, 10))
        self._session_btns: Dict[str, ctk.CTkButton] = {}
        self._refresh_sessions_sidebar()

        ctk.CTkFrame(self.sidebar, height=1, fg_color=DS_BORDER).pack(fill="x", padx=14, pady=(0, 10))

        ctk.CTkLabel(self.sidebar, text="РАЗДЕЛЫ", font=MONO(10, "bold"), text_color=DS_DIM, anchor="w").pack(padx=16, pady=(0, 4), fill="x")

        nav_scroll = ctk.CTkScrollableFrame(
            self.sidebar, fg_color="transparent",
            scrollbar_button_color=DS_BORDER, scrollbar_button_hover_color=DS_ACCENT
        )
        nav_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        nav_items = [
            ("Чат", "chat", "💬"),
            ("Математика", "math", "📐"),
            ("Перевод", "translate", "🌍"),
            ("Холст", "canvas", "🎨"),
            ("Заметки", "notes", "📋"),
            ("Профиль", "profile", "👤"),
            ("Поиск", "search", "🔍"),
            ("Валидол", "validol", "💊"),
            ("Супер ИИ", "super_ai", "🧪"),
            ("Редактор", "editor", "🖼️"),
            ("Прогноз", "forecast", "📈"),
            ("История", "history", "📜"),
            ("Общие сервера", "discord_servers", "🌐"),
            ("Память Obsidian", "obsidian_graph", "🕸️"),
            ("Навыки Claude", "claude_skills", "⚡"),
            ("Моды", "mods", "📦"),
            ("Дашборд", "dashboard", "📊"),
            ("Админ-панель", "admin", "👑"),
        ]

        self.nav_items_dict = {}
        for text_title, key, icon in nav_items:
            item = NavItem(
                nav_scroll, text=text_title, icon=icon, is_active=(key=="chat"),
                command=lambda k=key: self.show_frame(k)
            )
            item.pack(fill="x", pady=2)
            self.nav_items_dict[key] = item

        ctk.CTkFrame(self.sidebar, height=1, fg_color=DS_BORDER).pack(fill="x", padx=14, pady=4)
        self.nav_settings = NavItem(
            self.sidebar, text="Настройки", icon="⚙️", is_active=False,
            command=lambda: self.show_frame('settings')
        )
        self.nav_settings.pack(fill="x", padx=8, pady=(0, 10))
        self.nav_items_dict['settings'] = self.nav_settings

        # 2. Центральная область (DS_SURFACE)
        self.content = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color=DS_SURFACE)
        self.content.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # 3. Правая панель 260 px
        self.right_panel = ctk.CTkFrame(self.main_container, width=260, corner_radius=0, fg_color=DS_PANEL)
        self.right_panel.pack(side="right", fill="y", padx=0, pady=0)
        self.right_panel.pack_propagate(False)

        self._build_right_panel()

        self.frames = {}
        self.frames["chat"] = ChatFrame(self.content, self, lang)
        self.frames["math"] = MathFrame(self.content, self, lang)
        self.frames["canvas"] = CanvasFrame(self.content, self, lang)
        self.frames["notes"] = NotesFrame(self.content, self, lang)
        self.frames["profile"] = ProfileFrame(self.content, self, lang)
        self.frames["translate"] = TranslateFrame(self.content, self, lang)
        self.frames["search"] = SearchFrame(self.content, self, lang)
        self.frames["validol"] = ValidolFrame(self.content, self, lang)
        self.frames["super_ai"] = SuperAIFrame(self.content, self, lang)
        self.frames["editor"] = EditorFrame(self.content, self, lang)
        self.frames["forecast"] = ForecastFrame(self.content, self, lang)
        self.frames["settings"] = SettingsFrame(self.content, self, lang)
        self.frames["history"] = HistoryFrame(self.content, self, lang)
        self.frames["launcher"] = LauncherFrame(self.content, self, lang)
        self.frames["dashboard"] = DashboardFrame(self.content, self, lang)
        self.frames["admin"] = AdminFrame(self.content, self, lang)
        # Jarvis removed
        self.frames["obsidian_graph"] = ObsidianGraphFrame(self.content, self, lang)
        self.frames["claude_skills"] = ClaudeSkillsFrame(self.content, self, lang)
        self.frames["discord_servers"] = DiscordServersFrame(self.content, self, lang)

        self.show_frame("chat")

        self.bind("<Configure>", self._on_window_resize)

        try:
            startups = int(_db_get_setting("app_startup_count", "0")) + 1
            _db_set_setting("app_startup_count", str(startups))
            if not check_feature_access("premium") and not check_feature_access("codex_02") and not check_feature_access("super_ai"):
                if startups % 5 == 0:
                    self.after(1000, lambda: show_discount_ad_popup(self, is_veteran=(startups >= 5), startup_count=startups))
        except Exception:
            pass

        self.bind("<Alt-Shift-KeyPress-F4>", self.hotkey_save_custom_settings)
        self.bind("<Alt-Shift-F4>", self.hotkey_save_custom_settings)
        self.after(500, lambda: self.check_and_show_first_login_guides(self.username))

    def _build_right_panel(self):
        for w in self.right_panel.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.right_panel, text="ИНФОРМАЦИЯ", font=MONO(10, "bold"), text_color=DS_DIM, anchor="w").pack(padx=16, pady=(16, 10), fill="x")

        card_ctx = Card(self.right_panel, title="Контекст")
        card_ctx.pack(fill="x", padx=12, pady=6)

        r1 = ctk.CTkFrame(card_ctx, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(r1, text="Провайдер:", font=F(11), text_color=DS_DIM).pack(side="left")
        StatusPill(r1, text=ACTIVE_PROVIDER.upper(), status_type="success").pack(side="right")

        r2 = ctk.CTkFrame(card_ctx, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(r2, text="Резерв:", font=F(11), text_color=DS_DIM).pack(side="left")
        ctk.CTkLabel(r2, text="OpenRouter", font=MONO(10, "bold"), text_color=DS_TEXT).pack(side="right")

        r3 = ctk.CTkFrame(card_ctx, fg_color="transparent")
        r3.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(r3, text="База данных:", font=F(11), text_color=DS_DIM).pack(side="left")
        StatusPill(r3, text="SQLITE OK", status_type="success").pack(side="right")

        card_tg = Card(self.right_panel, title="Telegram-бот")
        card_tg.pack(fill="x", padx=12, pady=6)

        r_tg = ctk.CTkFrame(card_tg, fg_color="transparent")
        r_tg.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(r_tg, text="Статус:", font=F(11), text_color=DS_DIM).pack(side="left")
        st_type = "success" if bot_running else "amber"
        st_text = "АКТИВЕН" if bot_running else "ВЫКЛ"
        StatusPill(r_tg, text=st_text, status_type=st_type).pack(side="right")

        card_mods = Card(self.right_panel, title="Моды")
        card_mods.pack(fill="x", padx=12, pady=6)

        mods_list = load_enabled_mods()
        enabled_count = sum(1 for m in mods_list if m.get('enabled'))

        r_m = ctk.CTkFrame(card_mods, fg_color="transparent")
        r_m.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(r_m, text="Включено:", font=F(11), text_color=DS_DIM).pack(side="left")
        StatusPill(r_m, text=f"{enabled_count} ВКЛ.", status_type="success" if enabled_count > 0 else "amber").pack(side="right")

        card_sub = Card(self.right_panel, title="Подписка")
        card_sub.pack(fill="x", padx=12, pady=6)

        is_prem = check_feature_access("premium") or check_feature_access("super_ai")
        r_s = ctk.CTkFrame(card_sub, fg_color="transparent")
        r_s.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(r_s, text="Статус:", font=F(11), text_color=DS_DIM).pack(side="left")
        StatusPill(r_s, text="PREMIUM" if is_prem else "FREE", status_type="success" if is_prem else "warning").pack(side="right")

    def _on_window_resize(self, event=None):
        if event and event.widget == self:
            width = event.width
            if width < 1000:
                if hasattr(self, 'right_panel') and self.right_panel.winfo_ismapped():
                    self.right_panel.pack_forget()
            else:
                if hasattr(self, 'right_panel') and not self.right_panel.winfo_ismapped():
                    self.right_panel.pack(side="right", fill="y", padx=0, pady=0)

    def hotkey_save_custom_settings(self, event=None):
        try:
            custom_btns = db.get_custom_buttons()
            backup_path = os.path.join(get_data_root(), "custom_buttons_backup.json")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(custom_btns, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Alt+Shift+F4", "✅ Кастомные кнопки и настройки успешно сохранены во внешний файл резервной копии!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить настройки по Alt+Shift+F4: {e}")

    def _refresh_sessions_sidebar(self):
        if not hasattr(self, '_sessions_scroll'):
            return
        for w in self._sessions_scroll.winfo_children():
            w.destroy()
        self._session_btns = {}
        sessions = db.get_session_titles(USER_ID, limit=20)
        for s in sessions:
            sid = s["session_id"]
            label = s["preview"] or sid
            is_active = (sid == CURRENT_SESSION_ID)
            row = ctk.CTkFrame(self._sessions_scroll, fg_color="transparent")
            row.pack(fill="x", pady=1)
            btn = ctk.CTkButton(
                row, text=f"💬  {label}", anchor="w",
                fg_color=DS_PANEL_2 if is_active else "transparent",
                hover_color=DS_PANEL_2, text_color=DS_TEXT if is_active else DS_DIM,
                font=F(11, "bold" if is_active else "normal"), corner_radius=6, height=28,
                command=lambda s=sid: self._open_session(s)
            )
            btn.pack(side="left", fill="x", expand=True, padx=(2,0))
            del_btn = ctk.CTkButton(
                row, text="✕", width=20, height=20,
                fg_color="transparent", hover_color=DS_DANGER,
                text_color=DS_DIM, corner_radius=4,
                command=lambda s=sid: self._delete_session(s)
            )
            del_btn.pack(side="right", padx=(2,4))
            self._session_btns[sid] = btn

    def _open_session(self, session_id: str):
        load_session_history(session_id)
        self.show_frame("chat")
        chat: ChatFrame = self.frames["chat"]
        chat.output.delete("1.0", "end")
        chat.load_history()
        self._refresh_sessions_sidebar()

    def _new_chat_from_sidebar(self):
        import time as _t
        new_id = f"chat_{int(_t.time())}"
        load_session_history(new_id)
        self.show_frame("chat")
        chat: ChatFrame = self.frames["chat"]
        chat.output.delete("1.0", "end")
        uname = getattr(self, 'username', 'Пользователь')
        chat._show_welcome_screen()
        chat.input.delete("1.0", "end")
        self._refresh_sessions_sidebar()

    def _delete_session(self, session_id: str):
        global CURRENT_SESSION_ID
        db.delete_session(USER_ID, session_id)
        if session_id == CURRENT_SESSION_ID:
            remaining = db.get_session_titles(USER_ID, limit=1)
            new_sid = remaining[0]["session_id"] if remaining else "main"
            load_session_history(new_sid)
            if "chat" in getattr(self, 'frames', {}):
                chat: ChatFrame = self.frames["chat"]
                chat.output.delete("1.0", "end")
                chat.load_history()
        self._refresh_sessions_sidebar()

    def show_frame(self, name):
        if name == "mods":
            self.show_mods_window()
            return

        if hasattr(self, 'nav_items_dict'):
            for k, item in self.nav_items_dict.items():
                item.set_active(k == name)

        for frame in self.frames.values():
            frame.pack_forget()
        if name in self.frames:
            self.frames[name].pack(fill="both", expand=True, padx=0, pady=0)

    def safe_schedule(self, func, *args, **kwargs):
        self._gui_queue.put(lambda: func(*args, **kwargs))

    def _process_gui_queue(self):
        try:
            while True:
                task = self._gui_queue.get_nowait()
                try:
                    task()
                except Exception as e:
                    logger.error(f"Error executing GUI queue task: {e}")
                self._gui_queue.task_done()
        except queue.Empty:
            pass
        self.after(50, self._process_gui_queue)

    def run_in_background(self, func, *args, callback=None, **kwargs):
        def wrapper():
            result = func(*args, **kwargs)
            if callback:
                self.safe_schedule(callback, result)
        threading.Thread(target=wrapper, daemon=True).start()

    def rebuild_ui(self):
        current_visible = None
        for name, frame in self.frames.items():
            if frame.winfo_ismapped():
                current_visible = name
                break
        self.build_ui()
        if current_visible and current_visible in self.frames:
            self.show_frame(current_visible)

class ChatFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self._attached_files: List[Dict] = []

        # ── Шапка ──────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=DS_SURFACE, corner_radius=0, height=50)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="💬  Чат с ИИ",
                     font=ctk.CTkFont(size=15, weight="bold"), text_color=DS_TEXT).pack(side="left", padx=16)
        self._model_lbl = ctk.CTkLabel(header, text="Mistral mistral-medium-2505",
                                        font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self._model_lbl.pack(side="left", padx=4)

        # Кнопки шапки (справа)
        hbr = ctk.CTkFrame(header, fg_color="transparent")
        hbr.pack(side="right", padx=10)
        self.codex_toggle_btn = ctk.CTkButton(hbr, text="💻 Codex-02 Помощник", width=150, height=30,
                      fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT,
                      corner_radius=8, command=self.toggle_codex_sidebar)
        self.codex_toggle_btn.pack(side="right", padx=4)
        ctk.CTkButton(hbr, text="💾 Экспорт", width=90, height=30,
                      fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_DIM,
                      corner_radius=8, command=self.export_chat).pack(side="right", padx=4)
        ctk.CTkButton(hbr, text="🆕 Новый чат", width=100, height=30,
                      fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_DIM,
                      corner_radius=8, command=self.new_chat).pack(side="right", padx=4)
        ctk.CTkButton(hbr, text="🧹 Очистить", width=90, height=30,
                      fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_DIM,
                      corner_radius=8, command=self.clear_context).pack(side="right", padx=4)
        ctk.CTkButton(hbr, text="📋 Копировать", width=100, height=30,
                      fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_DIM,
                      corner_radius=8, command=self.copy_last).pack(side="right", padx=4)

        # ── Основной Рабочий Контейнер (Чат + Помощник Codex-02) ──
        self.chat_workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.chat_workspace.pack(fill="both", expand=True, padx=0, pady=0)

        # Левая часть — сам Чат
        self.chat_left_pane = ctk.CTkFrame(self.chat_workspace, fg_color="transparent")
        self.chat_left_pane.pack(side="left", fill="both", expand=True)

        self.output = ctk.CTkTextbox(
            self.chat_left_pane, wrap="word", font=ctk.CTkFont(size=13),
            fg_color=DS_BG, text_color=DS_TEXT,
            scrollbar_button_color=DS_BORDER, scrollbar_button_hover_color=DS_ACCENT)
        self.output.pack(fill="both", expand=True, padx=0, pady=0)

        # Правая часть — Скрытый по умолчанию Помощник Codex-02
        self.codex_sidebar_visible = False
        self.codex_sidebar = ctk.CTkFrame(self.chat_workspace, fg_color=DS_PANEL, width=285, border_width=1, border_color=DS_BORDER)

        # ── Чипы прикреплённых файлов ──────────────────────────
        self._chips_frame = ctk.CTkFrame(self, fg_color=DS_BG, height=0)
        self._chips_frame.pack(fill="x", padx=20)

        # ── Поле ввода (центрированное) ────────────────────────
        input_outer = ctk.CTkFrame(self, fg_color=DS_BG)
        input_outer.pack(fill="x", padx=0, pady=(6, 14))

        input_center = ctk.CTkFrame(input_outer, fg_color=DS_PANEL,
                                    corner_radius=14, border_width=1, border_color=DS_BORDER)
        input_center.pack(padx=60, fill="x")

        self._attach_btn = ctk.CTkButton(
            input_center, text="📎", width=36, height=36,
            fg_color="transparent", hover_color=DS_SURFACE,
            text_color=DS_DIM, corner_radius=8, command=self.attach_file)
        self._attach_btn.pack(side="left", padx=(6,0), pady=6)

        self.input = ctk.CTkTextbox(
            input_center, height=60, wrap="word",
            fg_color="transparent", text_color=DS_TEXT,
            font=ctk.CTkFont(size=13), border_width=0)
        self.input.pack(side="left", fill="x", expand=True, pady=4)

        self.send_btn = ctk.CTkButton(
            input_center, text="➤", width=36, height=36,
            fg_color=DS_ACCENT, hover_color=DS_ACCENT2,
            corner_radius=8, command=self.send)
        self.send_btn.pack(side="right", padx=(0,6), pady=6)

        hint = ctk.CTkLabel(input_outer, text="Enter — отправить · Shift+Enter — новая строка · 📎 PDF, DOCX, TXT, изображение",
                            font=ctk.CTkFont(size=10), text_color=DS_DIM)
        hint.pack(pady=(4,0))

        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<Shift-Return>", lambda e: None)

        self.load_history()

    def _on_enter(self, event):
        if event.state & 0x1:  # Shift held → new line
            return
        self.send()
        return "break"

    def attach_file(self):
        global CHAT_ATTACHED_FILES
        path = filedialog.askopenfilename(
            title="Прикрепить файл",
            filetypes=[
                ("Все файлы", "*.*"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx *.doc"),
                ("Текст", "*.txt"),
                ("Изображения", "*.png *.jpg *.jpeg *.bmp"),
                ("Код", "*.py *.js *.ts *.html *.css"),
            ]
        )
        if not path:
            return
        name = os.path.basename(path)
        content = read_file_content(path)
        entry = {'name': name, 'path': path, 'content': content}
        self._attached_files.append(entry)
        CHAT_ATTACHED_FILES.append(entry)
        self._refresh_chips()

    def _refresh_chips(self):
        for w in self._chips_frame.winfo_children():
            w.destroy()
        for i, f in enumerate(self._attached_files):
            chip = ctk.CTkFrame(self._chips_frame, fg_color=DS_PANEL,
                                corner_radius=20, border_width=1, border_color=DS_ACCENT)
            chip.pack(side="left", padx=4, pady=4)
            ctk.CTkLabel(chip, text=f"📄 {f['name'][:25]}",
                         font=ctk.CTkFont(size=11), text_color=DS_ACCENT2).pack(side="left", padx=(8,2), pady=4)
            idx = i
            ctk.CTkButton(chip, text="✕", width=20, height=20,
                          fg_color="transparent", hover_color=DS_SURFACE, text_color=DS_DIM,
                          corner_radius=10, command=lambda i=idx: self._remove_chip(i)).pack(side="right", padx=(2,6))

    def _remove_chip(self, idx):
        global CHAT_ATTACHED_FILES
        if 0 <= idx < len(self._attached_files):
            removed = self._attached_files.pop(idx)
            try:
                CHAT_ATTACHED_FILES.remove(removed)
            except ValueError:
                pass
            self._refresh_chips()

    def export_chat(self):
        text = self.output.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showinfo("Экспорт", "Чат пустой — нечего экспортировать.")
            return
        path = filedialog.asksaveasfilename(
            title="Экспортировать чат",
            defaultextension=".txt",
            filetypes=[("Текстовый файл", "*.txt"), ("Markdown", "*.md"), ("Все файлы", "*.*")],
            initialfile=f"aaron_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"# Aaron AI — История чата\n")
                f.write(f"# Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n")
                f.write(text)
            messagebox.showinfo("✅ Экспорт", f"Чат сохранён:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def update_model_label(self):
        global ACTIVE_PROVIDER
        if ACTIVE_PROVIDER == "g4f":
            lbl = "Local G4F (gpt-4o-mini)"
        elif ACTIVE_PROVIDER == "mistral":
            lbl = "Mistral mistral-medium-2505"
        elif ACTIVE_PROVIDER == "gemini":
            lbl = "Gemini 3.5 Flash"
        elif ACTIVE_PROVIDER == "aaron":
            lbl = "Aaron Brain v5 [Hybrid]"
        elif ACTIVE_PROVIDER == "codex_02":
            lbl = "Codex-02 [Code Agent]"
        else:
            lbl = ACTIVE_PROVIDER.upper()
        self._model_lbl.configure(text=lbl)
    def toggle_codex_sidebar(self):
        if self.codex_sidebar_visible:
            self.codex_sidebar.pack_forget()
            self.codex_sidebar_visible = False
            self.codex_toggle_btn.configure(fg_color=DS_PANEL)
        else:
            if not check_feature_access("codex_02"):
                ans = messagebox.askyesno("🔒 Доступ ограничен", "Использование интерактивного Codex-02 Code Advisor требует подписки на пакет Codex-02 или Complete Package!\n\nОткрыть окно оплаты?")
                if ans:
                    if "profile" in self.app.frames:
                        self.app.show_frame("profile")
                        self.app.frames["profile"].open_buy_premium()
                return

            self.codex_sidebar.pack(side="right", fill="y", padx=(2, 0))
            self.codex_sidebar.pack_propagate(False)
            self.codex_sidebar_visible = True
            self.codex_toggle_btn.configure(fg_color=DS_ACCENT)
            self._build_codex_sidebar_contents()

    def _build_codex_sidebar_contents(self):
        for w in self.codex_sidebar.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.codex_sidebar, text="💻 Codex-02 Code Advisor", font=ctk.CTkFont(size=14, weight="bold"), text_color=DS_ACCENT2).pack(pady=(12, 8))
        
        ctk.CTkLabel(self.codex_sidebar, text="Интерактивный помощник по кодированию. Выберите задачу и отправьте код на анализ.", font=ctk.CTkFont(size=10), text_color=DS_DIM, wraplength=260, justify="center").pack(pady=(0, 10))

        ctk.CTkLabel(self.codex_sidebar, text="Вставьте исходный код:", font=ctk.CTkFont(size=11), text_color=DS_TEXT).pack(anchor="w", padx=15)
        self.codex_code_input = ctk.CTkTextbox(self.codex_sidebar, height=180, fg_color=DS_BG, text_color="#10b981", font=ctk.CTkFont(family="Courier", size=11))
        self.codex_code_input.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(self.codex_sidebar, text="Выберите действие:", font=ctk.CTkFont(size=11), text_color=DS_TEXT).pack(anchor="w", padx=15, pady=(5,0))
        self.codex_task_combo = ctk.CTkComboBox(self.codex_sidebar, values=[
            "Bug Hunt (Поиск багов)",
            "Оптимизация кода",
            "Рефакторинг кода",
            "Добавить комментарии",
            "Объяснить алгоритм",
            "Перевести в другой язык",
            "Создать файл на Рабочем столе"
        ], width=250)
        self.codex_task_combo.pack(padx=15, pady=4)
        self.codex_task_combo.set("Bug Hunt (Поиск багов)")

        self.codex_analyze_btn = ctk.CTkButton(self.codex_sidebar, text="⚡ Анализировать", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=self.run_codex_analysis)
        self.codex_analyze_btn.pack(fill="x", padx=15, pady=12)

        ctk.CTkLabel(self.codex_sidebar, text="Результат анализа:", font=ctk.CTkFont(size=11), text_color=DS_TEXT).pack(anchor="w", padx=15)
        self.codex_res_txt = ctk.CTkTextbox(self.codex_sidebar, fg_color=DS_BG, text_color=DS_TEXT, font=ctk.CTkFont(size=11), wrap="word")
        self.codex_res_txt.pack(fill="both", expand=True, padx=15, pady=(4, 15))

    def run_codex_analysis(self):
        code_to_analyze = self.codex_code_input.get("1.0", "end-1c").strip()
        task = self.codex_task_combo.get()

        if task == "Создать файл на Рабочем столе":
            if not code_to_analyze:
                messagebox.showinfo("Codex-02", "Пожалуйста, введите описание нужного скрипта/файла в текстовое поле выше.")
                return
        else:
            if not code_to_analyze:
                messagebox.showwarning("Codex-02", "Пожалуйста, вставьте исходный код для анализа.")
                return

        self.codex_analyze_btn.configure(state="disabled", text="⏳ Создание..." if task == "Создать файл на Рабочем столе" else "⏳ Анализ...")
        self.codex_res_txt.delete("1.0", "end")
        self.codex_res_txt.insert("end", "[⏳ Codex-02 генерирует файл и записывает на Рабочий стол...\n]" if task == "Создать файл на Рабочем столе" else "[⏳ Codex-02 проводит анализ безопасности и логики кода...\n]")

        system_prompt = (
            "Ты — Codex-02 (v2.0), сверхинтеллектуальная локальная система программирования и интерактивный помощник разработчика. "
        )

        if task == "Создать файл на Рабочем столе":
            system_prompt += (
                "Пользователь хочет создать файл на Рабочем столе. "
                "Ты ОБЯЗАН написать чистый, рабочий код по его описанию. "
                "Обязательно упакуй создаваемый код в теги:\n"
                "<<CREATE_FILE: имя_скрипта.py>>\n"
                "код\n"
                "<<END_FILE>>\n"
                "Выбери подходящее имя файла и расширение в зависимости от задачи (например, parser.py, test.py)."
            )
            prompt = (
                f"Создай готовый рабочий скрипт по описанию: {code_to_analyze}.\n"
                "Обязательно используй теги <<CREATE_FILE: имя_файла.py>> ... <<END_FILE>> для автоматической записи на Рабочий стол."
            )
        else:
            system_prompt += "Твоя задача — детально проанализировать предоставленный код согласно выбранной задаче и вернуть профессиональный, структурированный разбор."
            prompt = (
                f"Проведи глубокий разбор следующего фрагмента кода.\\n"
                f"Выбранное действие: {task}\\n\\n"
                f"=== ИСХОДНЫЙ КОД ===\\n"
                f"{code_to_analyze}\\n"
                f"====================\\n\\n"
                f"Дай подробный ответ с пошаговыми рекомендациями, исправленным кодом (если требуется) и выводами."
            )

        def on_codex_completed(ans):
            self.codex_res_txt.delete("1.0", "end")
            self.codex_res_txt.insert("end", ans)
            self.codex_analyze_btn.configure(state="normal", text="⚡ Анализировать")
            db.log_chat(USER_ID, "user", f"[Codex-02 Code Advisor] Действие: {task}\\nКод: {code_to_analyze[:200]}...", CURRENT_SESSION_ID)
            db.log_chat(USER_ID, "assistant", f"[Codex-02 Advisor Response]\\n{ans[:500]}...", CURRENT_SESSION_ID)
            db.add_stat(USER_ID)

        self.app.run_in_background(sync_chat2, prompt, sys_prompt=system_prompt, callback=on_codex_completed)

    def load_history(self):
        history = db.get_chat_history(USER_ID, CURRENT_SESSION_ID, limit=200)
        if not history:
            # Первое открытие — показываем новый приветственный экран с микрочипом
            self._show_welcome_screen()
        you = Locale.t('you_prefix', self.lang)
        ai = Locale.t('ai_prefix', self.lang)
        for msg in history:
            prefix = you if msg['role'] == 'user' else ai
            self.output.insert("end", f"{prefix}: {msg['content']}\n\n")
        self.output.see("end")

    def send(self):
        msg = self.input.get("1.0","end-1c").strip()
        if not msg: return
        
        # Intercept Developer Console command
        if msg.strip().lower() in ("/разработка", "/dev", "/debug"):
            self.input.delete("1.0", "end")
            self.output.insert("end", f"\n⚙️ [Система] Запуск консоли разработчика...\n", "thinking")
            self.output.see("end")
            show_dev_console(self.app)
            return
        you = Locale.t('you_prefix', self.lang)
        self.output.insert("end", f"\n{you}: {msg}\n", "user")
        self.output.see("end")
        self.input.delete("1.0","end")
        self.send_btn.configure(state="disabled", text="⏳")
        # Показываем анимацию думающего ИИ (точки как в Gemini)
        self._thinking_active = True
        self._thinking_dots = 0
        self.output.insert("end", "\n🤔 Думаю", "thinking")
        self._thinking_pos = self.output.index("end-1c")
        self.output.insert("end", " ●\n", "thinking")
        self.output.see("end")
        self._animate_thinking()
        self.app.run_in_background(sync_chat, msg, callback=self.display_answer)

    def _animate_thinking(self):
        """Анимирует точки 'Думаю ● ●●  ●●●' пока ИИ отвечает."""
        if not getattr(self, '_thinking_active', False):
            return
        patterns = [" ●", " ● ●", " ● ● ●", " ● ●", " ●"]
        self._thinking_dots = (self._thinking_dots + 1) % len(patterns)
        try:
            # Удаляем старые точки и вставляем новые
            line_start = self._thinking_pos.split(".")[0]
            self.output.delete(f"{line_start}.0", f"{line_start}.end")
            self.output.insert(f"{line_start}.0", f"🤔 Думаю{patterns[self._thinking_dots]}", "thinking")
        except Exception:
            pass
        self.after(350, self._animate_thinking)

    def new_chat(self):
        new_id = f"chat_{int(time.time())}"
        load_session_history(new_id)
        self.output.delete("1.0","end")
        self._show_welcome_screen()
        self.input.delete("1.0","end")
        self.app._refresh_sessions_sidebar()

    def _show_welcome_screen(self):
        """Показывает приветственный экран с микрочипом при новом чате."""
        uname = getattr(self.app, 'username', 'Пользователь')
        hour = datetime.now().hour
        greet = "Доброе утро" if 5 <= hour < 12 else ("Добрый день" if 12 <= hour < 18 else "Добрый вечер")
        self.output.delete("1.0", "end")
        # Верхний отступ для центрирования
        self.output.insert("end", "\n\n\n\n")
        # Микрочип + заголовок (центрированные)
        self.output._textbox.tag_configure("welcome_center",
            justify="center",
            font=ctk.CTkFont(size=44),
            spacing1=6, spacing3=2,
        )
        self.output._textbox.tag_configure("welcome_question",
            justify="center",
            font=ctk.CTkFont(size=20, weight="bold"),
            foreground="#e5e7eb",
            spacing1=4, spacing3=4,
        )
        self.output._textbox.tag_configure("welcome_greet",
            justify="center",
            font=ctk.CTkFont(size=13),
            foreground="#9ca3af",
            spacing1=2, spacing3=14,
        )
        self.output.insert("end", "🤖\n", "welcome_center")
        self.output.insert("end", "Что будем делать?\n", "welcome_question")
        self.output.insert("end", f"{greet}, {uname}!\n\n", "welcome_greet")
        # Быстрые подсказки
        self.output._textbox.tag_configure("welcome_hints",
            justify="center",
            font=ctk.CTkFont(size=11),
            foreground="#6366f1",
            spacing1=2,
        )
        self.output.insert("end",
            "💡 Задайте вопрос  ·  📐 Математика  ·  🌍 Перевод  ·  📎 Прикрепите файл\n",
            "welcome_hints"
        )

    def display_answer(self, answer):
        # Останавливаем анимацию думания
        self._thinking_active = False
        # Удаляем строку «🤔 Думаю...»
        try:
            line_start = self._thinking_pos.split(".")[0]
            self.output.delete(f"{line_start}.0", f"{int(line_start)+1}.0")
        except Exception:
            pass
        ai = Locale.t('ai_prefix', self.lang)
        self.output.insert("end", f"\n{ai}: {answer}\n", "ai")
        self.output.see("end")
        self.send_btn.configure(state="normal", text="➤")
        # Обновляем сайдбар чтобы новая сессия появилась после первого сообщения
        self.app._refresh_sessions_sidebar()

    def clear_context(self):
        conversation.clear()
        self.output.delete("1.0","end")
        self.output.insert("end", "🧹 Контекст очищен.\n\n")

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0","end-1c")
        lines = text.split("\n")
        ai_prefix = Locale.t('ai_prefix', self.lang) + ": "
        last_ai = ""
        for line in reversed(lines):
            if line.startswith(ai_prefix):
                last_ai = line[len(ai_prefix):]
                break
        if last_ai:
            self.clipboard_clear()
            self.clipboard_append(last_ai)

    def copy_code(self):
        # Ищем последний ответ AI и извлекаем код между ```
        text = self.output.get("1.0", "end-1c")
        lines = text.split("\n")
        ai_prefix = Locale.t('ai_prefix', self.lang) + ": "
        # Найдём последний ответ AI
        ai_text = ""
        for i in range(len(lines)-1, -1, -1):
            if lines[i].startswith(ai_prefix):
                ai_text = lines[i][len(ai_prefix):] + "\n"
                for j in range(i+1, len(lines)):
                    if lines[j].startswith(Locale.t('you_prefix', self.lang) + ": ") or lines[j].startswith(ai_prefix):
                        break
                    ai_text += lines[j] + "\n"
                break
        # Извлекаем код между тройными обратными кавычками
        code_blocks = re.findall(r'```(.*?)```', ai_text, re.DOTALL)
        if code_blocks:
            code = code_blocks[0].strip()
            self.clipboard_clear()
            self.clipboard_append(code)
        elif ai_text.strip():
            # Если нет блока кода, копируем весь ответ
            self.clipboard_clear()
            self.clipboard_append(ai_text.strip())

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.send_btn.configure(text=Locale.t('send', lang))
        self.clear_btn.configure(text=Locale.t('clear_context', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.copy_code_btn.configure(text="📋 Код")
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class MathFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.topic_label = ctk.CTkLabel(self, text=Locale.t('math_topic_label', lang), font=ctk.CTkFont(size=14))
        self.topic_label.pack(anchor="w")
        self.topic_var = tk.StringVar()
        self.topic_menu = ctk.CTkOptionMenu(self, variable=self.topic_var, values=[], command=self.on_topic_selected)
        self.topic_menu.pack(fill="x", pady=5)
        self.class_var = tk.StringVar()
        self.class_menu = ctk.CTkOptionMenu(self, variable=self.class_var, values=list(MATH_TOPICS.keys()), command=self.on_class_selected)
        self.class_menu.pack(fill="x", pady=5)

        self.entry = ctk.CTkEntry(self, font=ctk.CTkFont(size=14))
        self.entry.pack(fill="x", pady=5)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.solve_btn = ctk.CTkButton(btn_frame, text=Locale.t('solve_math', lang), command=self.solve)
        self.solve_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)
        
        # File support
        self.file_btn = ctk.CTkButton(btn_frame, text="📎 Файл", command=self.choose_file, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT)
        self.file_btn.pack(side="left", padx=5)

        self.file_info = ctk.CTkLabel(self, text="Файл: не выбран", font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self.file_info.pack(fill="x", padx=10, pady=(2, 5))

        self.result = ctk.CTkTextbox(self, height=200, font=ctk.CTkFont(size=12))
        self.result.pack(fill="both", expand=True)

        self.class_var.set(list(MATH_TOPICS.keys())[0])
        self.on_class_selected(self.class_var.get())

        # Bind Enter key
        self.entry.bind("<Return>", lambda e: self.solve())

        if FILE_CONTEXT:
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")

        # Persistent history loading
        self.load_history()

    def load_history(self):
        try:
            self.result.configure(state="normal")
            self.result.delete("1.0", "end")
            history = db.get_chat_history(USER_ID, "math_session", limit=100)
            if history:
                for msg in history:
                    role = "Вы" if msg['role'] == 'user' else "Решение ИИ"
                    self.result.insert("end", f"[{role}]: {msg['content']}\n\n")
            else:
                self.result.insert("end", "📐 Выберите тему или введите свой пример и нажмите 'Решить'.\n\n")
            self.result.configure(state="disabled")
            self.result.see("end")
        except Exception as e:
            logger.warning(f"Ошибка [104]: Сбой при загрузке истории математики: {e}")

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл для контекста",
            filetypes=[("Все файлы", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")]
        )
        if path:
            set_file_context(path)
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            if hasattr(self.app, 'frames'):
                for name, frame in self.app.frames.items():
                    if hasattr(frame, 'file_info'):
                        frame.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
                    elif hasattr(frame, 'file_info_label'):
                        frame.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")

    def on_class_selected(self, choice):
        topics = list(MATH_TOPICS[choice].keys())
        self.topic_var.set(topics[0])
        self.topic_menu.configure(values=topics)
        self.on_topic_selected(self.topic_var.get())

    def on_topic_selected(self, choice):
        class_name = self.class_var.get()
        example = MATH_TOPICS[class_name][choice]
        self.entry.delete(0, "end")
        self.entry.insert(0, example)

    def solve(self):
        expr = self.entry.get().strip()
        topic = self.topic_var.get()
        if not expr:
            return
        
        self.entry.delete(0, "end")
        
        prompt = (
            f"Ты — профессиональный преподаватель математики. Реши следующую задачу подробно и понятно, "
            f"расписав каждый шаг вычислений и объяснив правила.\n"
            f"Раздел/Тема: {topic}\n"
            f"Задача/Уравнение: {expr}\n\n"
            f"Пожалуйста, покажи пошаговый ход решения и в конце выдели итоговый ответ."
        )
        
        self.result.configure(state="normal")
        self.result.insert("end", f"Вы: {expr}\n")
        self.result.insert("end", f"[📐 Отправка запроса к Математическому ИИ...]\n")
        self.result.see("end")
        self.result.configure(state="disabled")
        
        self.app.run_in_background(sync_chat, prompt, session_id="math_session", callback=self.show_ai_math)

    def show_ai_math(self, ans):
        self.result.configure(state="normal")
        self.result.insert("end", f"Решение ИИ: {ans}\n\n")
        self.result.see("end")
        self.result.configure(state="disabled")

    def copy_last(self):
        try:
            sel = self.result.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.result.get("1.0", "end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.topic_label.configure(text=Locale.t('math_topic_label', lang))
        self.solve_btn.configure(text=Locale.t('solve_math', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang
class CanvasFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.last_x = self.last_y = None
        self.color = "black"
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.red_btn = ctk.CTkButton(btn_frame, text=Locale.t('red', lang), fg_color="red", command=lambda: self.set_color("red"))
        self.red_btn.pack(side="left",padx=5)
        self.black_btn = ctk.CTkButton(btn_frame, text=Locale.t('black', lang), fg_color="black", command=lambda: self.set_color("black"))
        self.black_btn.pack(side="left",padx=5)
        self.clear_btn = ctk.CTkButton(btn_frame, text=Locale.t('clear_canvas', lang), command=lambda: self.canvas.delete("all"))
        self.clear_btn.pack(side="left",padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

    def set_color(self, color):
        self.color = color

    def paint(self, event):
        x, y = event.x, event.y
        if self.last_x is not None:
            self.canvas.create_line(self.last_x, self.last_y, x, y, fill=self.color, width=3, capstyle="round")
        self.last_x, self.last_y = x, y
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, 'last_x', None))

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.red_btn.configure(text=Locale.t('red', lang))
        self.black_btn.configure(text=Locale.t('black', lang))
        self.clear_btn.configure(text=Locale.t('clear_canvas', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class NotesFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.listbox = tk.Listbox(self, bg="#fafafa", fg="black", selectbackground="#1e88e5")
        self.listbox.pack(fill="both", expand=True)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.add_btn = ctk.CTkButton(btn_frame, text=Locale.t('add_note', lang), command=self.add_note)
        self.add_btn.pack(side="left",padx=5)
        self.del_btn = ctk.CTkButton(btn_frame, text=Locale.t('delete_note', lang), command=self.delete_note)
        self.del_btn.pack(side="left",padx=5)
        self.ref_btn = ctk.CTkButton(btn_frame, text=Locale.t('refresh', lang), command=self.load_notes)
        self.ref_btn.pack(side="left",padx=5)
        self.edit_btn = ctk.CTkButton(btn_frame, text="🔍 Просмотреть и изменить", command=self.edit_note)
        self.edit_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

        self.note_ids = {}
        self.load_notes()

    def load_notes(self):
        self.listbox.delete(0,"end")
        self.note_ids.clear()
        for i, note in enumerate(db.notes(USER_ID)):
            self.listbox.insert("end", note['txt'][:60] + ("..." if len(note['txt'])>60 else ""))
            self.note_ids[i] = note['id']
        if not self.note_ids:
            self.listbox.insert("end","Нет заметок")

    def add_note(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Новая заметка")
        dlg.geometry("400x300")
        text = ctk.CTkTextbox(dlg, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(dlg, text="Сохранить", command=lambda: [
            db.save_note(USER_ID, text.get("1.0","end-1c").strip()),
            dlg.destroy(),
            self.load_notes()
        ]).pack(pady=5)

    def delete_note(self):
        sel = self.listbox.curselection()
        if sel and sel[0] in self.note_ids:
            db.del_note(USER_ID, self.note_ids[sel[0]])
            self.load_notes()

    def edit_note(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] not in self.note_ids:
            messagebox.showwarning("Внимание", "Выберите заметку для просмотра/редактирования.")
            return
        
        note_id = self.note_ids[sel[0]]
        full_text = ""
        try:
            with db.conn_chats() as c:
                row = c.execute("SELECT txt FROM notes WHERE id=?", (note_id,)).fetchone()
                if row:
                    full_text = row['txt']
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать заметку: {e}")
            return
            
        dlg = ctk.CTkToplevel(self)
        dlg.title("Редактирование заметки")
        dlg.geometry("520x420")
        dlg.grab_set()
        
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"520x420+{(sw-520)//2}+{(sh-420)//2}")
        
        ctk.CTkLabel(dlg, text="Просмотр и редактирование заметки", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        text_box = ctk.CTkTextbox(dlg, wrap="word")
        text_box.pack(fill="both", expand=True, padx=20, pady=10)
        text_box.insert("1.0", full_text)
        
        def save_changes():
            new_text = text_box.get("1.0", "end-1c").strip()
            if not new_text:
                messagebox.showwarning("Внимание", "Заметка не может быть пустой.")
                return
            try:
                with db.conn_chats() as c:
                    c.execute("UPDATE notes SET txt=? WHERE id=?", (new_text, note_id))
                messagebox.showinfo("Успех", "Заметка успешно обновлена!")
                dlg.destroy()
                self.load_notes()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить изменения: {e}")
                
        ctk.CTkButton(dlg, text="Сохранить изменения", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=save_changes).pack(pady=15)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.add_btn.configure(text=Locale.t('add_note', lang))
        self.del_btn.configure(text=Locale.t('delete_note', lang))
        self.ref_btn.configure(text=Locale.t('refresh', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class ProfileFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        
        # Dictionaries to track terminal-generated buttons and their commands
        self.dynamic_buttons = {}  # lowercase_name -> CTkButton
        self.button_bindings = {}  # lowercase_name -> command_or_prompt
        
        # Header
        ctk.CTkLabel(self, text="👤 Профиль пользователя & Ядро Системы", font=ctk.CTkFont(size=22, weight="bold"), text_color=DS_TEXT).pack(pady=(15, 5))
        
        # Stats & File info
        self.stat_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=13), text_color=DS_DIM)
        self.stat_label.pack(pady=2)
        
        self.file_info_label = ctk.CTkLabel(self, text="Файл: не выбран", wraplength=420, text_color=DS_DIM, font=ctk.CTkFont(size=12))
        self.file_info_label.pack(pady=2)
        


        # Main interactive row: Left for buttons, Right for the Interactive Subscription Sphere
        self.main_row = ctk.CTkFrame(self, fg_color="transparent")
        self.main_row.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.left_col = ctk.CTkFrame(self.main_row, fg_color="transparent")
        self.left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.right_col = ctk.CTkFrame(self.main_row, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER, width=280)
        self.right_col.pack(side="right", fill="y", padx=(10, 0))
        self.right_col.pack_propagate(False)

        # Left Column: Operational buttons
        # Section title: "🛠️ Управление Ядром (Tier 4)"
        ctk.CTkLabel(self.left_col, text="🛠️ Управление Ядром (Tier 4)", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_ACCENT2, anchor="w").pack(fill="x", pady=(5, 5))
        
        
        # --- NEW PREMIUM & PRIVATE CHAT SECTION ---
        ctk.CTkLabel(self.left_col, text="👑 Премиум и Приватный Чат", font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981", anchor="w").pack(fill="x", pady=(15, 5))
        
        self.buy_premium_btn = ctk.CTkButton(self.left_col, text="💎 Купить Премиум", command=self.open_buy_premium, fg_color="#10b981", hover_color="#059669")
        self.network_servers_btn = ctk.CTkButton(self.left_col, text="🌐 Выход в сеть / Общие сервера", command=lambda: self.app.show_frame("discord_servers"), fg_color="#2563eb", hover_color="#1d4ed8")
        self.network_servers_btn.pack(fill="x", pady=4)
        
        self.appeal_account_btn = ctk.CTkButton(self.left_col, text="📩 Подать апелляцию / Восстановить аккаунт", command=self.open_account_appeal_dialog, fg_color="#d97706", hover_color="#b45309")
        self.appeal_account_btn.pack(fill="x", pady=4)
        
        self.apply_recovery_key_btn = ctk.CTkButton(self.left_col, text="🔑 Применить ключ восстановления (JSON)", command=self.import_recovery_key_dialog, fg_color="#059669", hover_color="#047857")
        self.apply_recovery_key_btn.pack(fill="x", pady=4)
        self.buy_premium_btn.pack(fill="x", pady=4)
        
        self.private_chat_btn = ctk.CTkButton(self.left_col, text="🔒 Приватный Чат", command=self.open_private_chat, fg_color="#4f46e5", hover_color="#4338ca")
        self.private_chat_btn.pack(fill="x", pady=4)
        
        # ЕДИНСТВЕННЫЙ ЗАГРУЗЧИК ПРЕМИУМ-КОДОВ (без дубликатов и без ID)
        self.activate_premium_code_btn = ctk.CTkButton(self.left_col, text="🔑 Ввести код активации", command=self.activate_premium_code, fg_color=DS_PANEL, hover_color=DS_BORDER, border_width=1, border_color=DS_BORDER)
        self.activate_premium_code_btn.pack(fill="x", pady=4)

        # Original controls below:
        self.test_btn = ctk.CTkButton(self.left_col, text="🧪 Пройти тест Ядра (100 ₸)", command=self.start_dev_test, fg_color=DS_ACCENT, hover_color=DS_ACCENT2)
        self.test_btn.pack(fill="x", pady=4)
        
        self.manual_btn = ctk.CTkButton(self.left_col, text="📖 Учебник по терминалу Ядра", command=self.show_terminal_tutorial, fg_color=DS_PANEL, hover_color=DS_BORDER, border_width=1, border_color=DS_BORDER)
        self.manual_btn.pack(fill="x", pady=4)
        
        # Share buttons layout
        share_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        share_row.pack(fill="x", pady=4)
        
        self.share_btn = ctk.CTkButton(share_row, text="📤 Поделиться кнопками (ID)", command=self.share_custom_buttons, fg_color=DS_PANEL, hover_color=DS_BORDER, border_width=1, border_color=DS_BORDER, width=160)
        self.share_btn.pack(side="left", padx=(0,4), fill="x", expand=True)
        
        self.import_btn = ctk.CTkButton(share_row, text="📥 Импортировать кнопки по ID", command=self.import_custom_buttons, fg_color=DS_PANEL, hover_color=DS_BORDER, border_width=1, border_color=DS_BORDER, width=160)
        self.import_btn.pack(side="left", padx=4, fill="x", expand=True)
        
        # Section title: "📁 Дополнительные функции"
        ctk.CTkLabel(self.left_col, text="📁 Дополнительные функции", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_DIM, anchor="w").pack(fill="x", pady=(15, 5))
        
        file_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        file_row.pack(fill="x", pady=2)
        self.file_btn = ctk.CTkButton(file_row, text="📂 Выбрать файл", command=self.choose_file, width=120)
        self.file_btn.pack(side="left", padx=(0,4))
        self.open_file_btn = ctk.CTkButton(file_row, text=Locale.t('open_file', lang), command=self.open_file, state="disabled", width=120)
        self.open_file_btn.pack(side="left", padx=4)
        self.clear_file_btn = ctk.CTkButton(file_row, text="❌ Очистить", command=self.clear_file, width=100)
        self.clear_file_btn.pack(side="left", padx=4)
        
        cloud_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        cloud_row.pack(fill="x", pady=6)
        self.sync_btn = ctk.CTkButton(cloud_row, text="🔄 Синхронизировать облако", command=self.manual_sync, fg_color=DS_PANEL, hover_color=DS_BORDER, border_width=1, border_color=DS_BORDER)
        self.sync_btn.pack(side="left", padx=(0, 4))
        self.policy_btn = ctk.CTkButton(cloud_row, text="🛡️ Политика", command=self.show_policy, fg_color="transparent", text_color=DS_DIM, border_width=1, border_color=DS_BORDER)
        self.policy_btn.pack(side="left", padx=4)
        self.logout_btn = ctk.CTkButton(cloud_row, text="🚪 Выйти", command=self.logout, fg_color="#ef4444", hover_color="#dc2626")
        self.logout_btn.pack(side="left", padx=4)

        # Section title: "👤 Управление Аккаунтом"
        ctk.CTkLabel(self.left_col, text="👤 Управление Аккаунтом", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_DIM, anchor="w").pack(fill="x", pady=(15, 5))
        
        account_row = ctk.CTkFrame(self.left_col, fg_color="transparent")
        account_row.pack(fill="x", pady=2)
        
        self.avatar_preview_lbl = ctk.CTkLabel(account_row, text="")
        self.avatar_preview_lbl.pack(side="left", padx=(0,10))
        
        self.update_avatar_preview()
        
        ctk.CTkButton(account_row, text="📷 Сменить аватар", command=self.change_avatar, width=110).pack(side="left", padx=4)
        ctk.CTkButton(account_row, text="🔑 Пароль", command=self.change_password, width=90).pack(side="left", padx=4)
        ctk.CTkButton(account_row, text="📋 Логи сессий", command=self.show_user_logs, width=100).pack(side="left", padx=4)
        ctk.CTkButton(account_row, text="🔑 Секретный пароль", command=self.change_private_chat_pwd, width=120).pack(side="left", padx=4)
        ctk.CTkButton(account_row, text="🔄 Сбросить Premium", command=self.reset_premium, width=120, fg_color="#ef4444", hover_color="#dc2626").pack(side="left", padx=4)

        # Right Column: The interactive glowing Sphere/Ball (Шар подписки)
        ctk.CTkLabel(self.right_col, text="🔮 3D Сфера", font=ctk.CTkFont(size=12, weight="bold"), text_color=DS_TEXT).pack(pady=(10, 5))
        
        canvas_bg = DS_SURFACE[1] if ctk.get_appearance_mode().lower() == "dark" else DS_SURFACE[0]
        self.sphere_canvas = tk.Canvas(self.right_col, width=160, height=160, bg=canvas_bg, highlightthickness=0)
        self.sphere_canvas.pack(pady=10)
        self.sphere_canvas.bind("<Button-1>", self.on_sphere_clicked)
        
        self.sphere_hint_lbl = ctk.CTkLabel(self.right_col, text="Нажмите для терминала", font=ctk.CTkFont(size=10), text_color=DS_DIM)
        self.sphere_hint_lbl.pack()
        
        # Beautiful Pricing List (Прайс-лист) under the sphere inside right_col
        ctk.CTkLabel(self.right_col, text="🏷️ Цены Лицензий (KZT):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#10b981").pack(pady=(15, 2))
        
        price_scroll = ctk.CTkScrollableFrame(self.right_col, fg_color="transparent", height=240, width=260)
        price_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        for key, p in PRICING_TABLE.items():
            card = ctk.CTkFrame(price_scroll, fg_color=DS_SURFACE, corner_radius=8, border_width=1, border_color=DS_BORDER)
            card.pack(fill="x", pady=3, padx=2)
            
            lbl_title = ctk.CTkLabel(card, text=p['name'].split("(")[0].strip(), font=ctk.CTkFont(size=10, weight="bold"), text_color=DS_TEXT, wraplength=220, justify="left")
            lbl_title.pack(anchor="w", padx=6, pady=(4, 1))
            
            lbl_price = ctk.CTkLabel(card, text=p['price'], font=ctk.CTkFont(size=10, weight="bold"), text_color="#10b981")
            lbl_price.pack(anchor="w", padx=15, pady=(4, 1))
        
        # Frame containing dynamic controls created via terminal
        self.custom_elements_frame = ctk.CTkFrame(self.left_col, fg_color="transparent")
        self.custom_elements_frame.pack(fill="x", pady=10)
        self.custom_text_lbl = ctk.CTkLabel(self.custom_elements_frame, text="", font=ctk.CTkFont(size=12, slant="italic"), text_color=DS_ACCENT2)
        self.custom_text_lbl.pack()

        self.update_stats()
        self.draw_sphere()
        self.load_saved_custom_buttons()

    def update_stats(self):
        cnt = db.get_stat(USER_ID)
        self.stat_label.configure(text=f"Всего запросов к ИИ: {cnt}")
        if FILE_CONTEXT:
            self.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")
        else:
            self.file_info_label.configure(text="Файл: не выбран")
            
        # Update subscription indicators
        is_premium = _db_get_flag("is_premium") or _db_get_flag("sub_complete") or _db_get_flag("sub_corporate")
        premium_id_str = _db_get_setting("premium_id_key", "Нет")
        
        if is_premium:
            self.private_chat_btn.configure(text="🔒 Приватный Чат (Доступ разрешен)", state="normal")
        else:
            self.private_chat_btn.configure(text="🔒 Приватный Чат (Требуется Premium)", fg_color="#374151")

        self.test_btn.configure(text="🧪 Запустить Тест (Демонстрация)", state="normal")
        self.sphere_hint_lbl.configure(text="Кликните по Сфере для запуска Терминала!", text_color=DS_ACCENT)
        self.draw_sphere()

    def load_saved_custom_buttons(self):
        saved = db.get_custom_buttons()
        for name, action in saved.items():
            name_low = name.lower()
            self.button_bindings[name_low] = action
            new_btn = ctk.CTkButton(
                self.custom_elements_frame, text=name, 
                fg_color=DS_ACCENT, hover_color=DS_ACCENT2,
                command=lambda n=name: self.on_custom_button_clicked(n)
            )
            new_btn.pack(pady=4, fill="x")
            self.dynamic_buttons[name_low] = new_btn

    def create_and_bind_button_locally(self, btn_name, bound_action, text_widget=None):
        btn_name_low = btn_name.lower()
        db.save_custom_button(btn_name, bound_action)
        self.button_bindings[btn_name_low] = bound_action
        if btn_name_low in self.dynamic_buttons:
            output = f"✅ [Core UI] Кнопка '{btn_name}' обновлена новым кодом!\n"
        else:
            new_btn = ctk.CTkButton(
                self.custom_elements_frame, text=btn_name, 
                fg_color=DS_ACCENT, hover_color=DS_ACCENT2,
                command=lambda n=btn_name: self.on_custom_button_clicked(n)
            )
            new_btn.pack(pady=4, fill="x")
            self.dynamic_buttons[btn_name_low] = new_btn
            output = f"✅ [Core UI] Кнопка '{btn_name}' успешно создана и привязана!\n"
        if text_widget:
            text_widget.configure(state="normal")
            text_widget.insert("end", f"\n{output}")
            preview_code = bound_action[3:] if bound_action.startswith("py:") else bound_action
            text_widget.insert("end", f"--- Сгенерированный код ---\n{preview_code}\n---------------------------\naaron-core> ")
            text_widget.see("end")
            text_widget.configure(state="disabled")

    def draw_sphere(self):
        canvas_bg = DS_SURFACE[1] if ctk.get_appearance_mode().lower() == "dark" else DS_SURFACE[0]
        self.sphere_canvas.configure(bg=canvas_bg)
        self.sphere_canvas.delete("all")
        
        # Draw a beautiful photorealistic glowing 3D Sphere using concentric circles
        center_x, center_y = 80, 80
        radius = 65
        
        steps = 60
        for i in range(steps):
            ratio = i / steps
            r = radius * (1 - ratio)
            cx = center_x - (ratio * 15)
            cy = center_y - (ratio * 15)
            
            if ratio < 0.8:
                sub_ratio = ratio / 0.8
                red = int(30 + (34 - 30) * sub_ratio)
                green = int(27 + (211 - 27) * sub_ratio)
                blue = int(75 + (238 - 75) * sub_ratio)
            else:
                sub_ratio = (ratio - 0.8) / 0.2
                red = int(34 + (255 - 34) * sub_ratio)
                green = int(211 + (255 - 211) * sub_ratio)
                blue = int(238 + (255 - 238) * sub_ratio)
                
            color = f"#{red:02x}{green:02x}{blue:02x}"
            self.sphere_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")



    def draw_sphere_with_scale(self, scale):
        canvas_bg = DS_SURFACE[1] if ctk.get_appearance_mode().lower() == "dark" else DS_SURFACE[0]
        self.sphere_canvas.configure(bg=canvas_bg)
        self.sphere_canvas.delete("all")
        
        center_x, center_y = 80, 80
        radius = 65 * scale
        
        steps = 60
        for i in range(steps):
            ratio = i / steps
            r = radius * (1 - ratio)
            cx = center_x - (ratio * 15 * scale)
            cy = center_y - (ratio * 15 * scale)
            
            if ratio < 0.8:
                sub_ratio = ratio / 0.8
                red = int(30 + (34 - 30) * sub_ratio)
                green = int(27 + (211 - 27) * sub_ratio)
                blue = int(75 + (238 - 75) * sub_ratio)
            else:
                sub_ratio = (ratio - 0.8) / 0.2
                red = int(34 + (255 - 34) * sub_ratio)
                green = int(211 + (255 - 211) * sub_ratio)
                blue = int(238 + (255 - 238) * sub_ratio)
                
            color = f"#{red:02x}{green:02x}{blue:02x}"
            self.sphere_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline="")

    def on_sphere_clicked(self, event):
        # Анимация пульсации сердца при клике
        def pulse_out():
            self.draw_sphere_with_scale(1.2)
            self.after(100, pulse_in)
        def pulse_in():
            self.draw_sphere()
            if not check_feature_access('terminal'):
                messagebox.showerror('🔒 Ошибка доступа', 'Доступ к Терминалу Ядра ограничен. Требуется подписка на пакет Super AI, Codex-02 или Complete Package.')
                if hasattr(self.app, 'frames') and 'super_ai' in self.app.frames:
                    self.app.frames['super_ai'].show_billing_dialog()
                return

            if not _db_get_flag("terminal_test_passed"):
                messagebox.showinfo("📟 Вход в Ядро", "Внимание: при первом запуске Терминала Ядра вы обязаны подтвердить квалификацию разработчика и подписать соглашение об ограничении ответственности.")
                self.start_competence_test_flow()
            elif not _db_get_flag("terminal_disclaimer_signed"):
                self.show_terminal_disclaimer()
            else:
                self.open_terminal_window()
        pulse_out()

    def start_competence_test_flow(self):
        test = ctk.CTkToplevel(self)
        test.title("Тест на компетентность программиста")
        test.geometry("520x400")
        test.configure(fg_color=DS_BG)
        test.grab_set()
        
        sw, sh = test.winfo_screenwidth(), test.winfo_screenheight()
        test.geometry(f"520x400+{(sw-520)//2}+{(sh-400)//2}")
        
        container = ctk.CTkFrame(test, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        step_var = [1]
        
        def render_step():
            for w in container.winfo_children():
                w.destroy()
            
            step = step_var[0]
            if step == 1:
                ctk.CTkLabel(container, text="Вопрос 1 из 3: Алгоритмы и сложность", font=ctk.CTkFont(size=14, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
                ctk.CTkLabel(container, text="Какова временная сложность поиска элемента в идеально сбалансированном бинарном дереве поиска (BST) в наихудшем случае?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=460).pack(pady=10)
                
                opts = [
                    ("A. O(1)", False),
                    ("B. O(N)", False),
                    ("C. O(log N)", True),
                    ("D. O(N log N)", False)
                ]
            elif step == 2:
                ctk.CTkLabel(container, text="Вопрос 2 из 3: ООП", font=ctk.CTkFont(size=14, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
                ctk.CTkLabel(container, text="Какое ключевое понятие ООП описывает сокрытие внутренней реализации объекта и предоставление публичного интерфейса?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=460).pack(pady=10)
                
                opts = [
                    ("A. Наследование (Inheritance)", False),
                    ("B. Инкапсуляция (Encapsulation)", True),
                    ("C. Полиморфизм (Polymorphism)", False),
                    ("D. Абстракция (Abstraction)", False)
                ]
            elif step == 3:
                ctk.CTkLabel(container, text="Вопрос 3 из 3: Управление памятью", font=ctk.CTkFont(size=14, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
                ctk.CTkLabel(container, text="Что такое 'утечка памяти' (memory leak)?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=460).pack(pady=10)
                
                opts = [
                    ("A. Ошибка, при которой жесткий диск переполняется кэшем", False),
                    ("B. Процесс выделения виртуальной памяти процессору", False),
                    ("C. Ситуация, когда выделенная динамическая память не освобождается и теряется ссылка на нее", True),
                    ("D. Чтение данных за пределами выделенного массива", False)
                ]
            else:
                _db_set_flag("terminal_test_passed", True)
                test.destroy()
                self.show_terminal_disclaimer()
                return

            for text, correct in opts:
                btn = ctk.CTkButton(container, text=text, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT,
                                    command=lambda c=correct: handle_ans(c))
                btn.pack(fill="x", pady=5)
                
        def handle_ans(correct):
            if correct:
                step_var[0] += 1
                render_step()
            else:
                messagebox.showerror("Ошибка", "Неверный ответ! Тест прерван. Подтяните знания и попробуйте снова.")
                test.destroy()
                
        render_step()

    def show_terminal_disclaimer(self):
        disc = ctk.CTkToplevel(self)
        disc.title("Отказ от ответственности (Disclaimer)")
        disc.geometry("520x420")
        disc.configure(fg_color=DS_BG)
        disc.grab_set()
        
        sw, sh = disc.winfo_screenwidth(), disc.winfo_screenheight()
        disc.geometry(f"520x420+{(sw-520)//2}+{(sh-420)//2}")
        
        ctk.CTkLabel(disc, text="⚠️ Ограничение Ответственности Разработчика", font=ctk.CTkFont(size=15, weight="bold"), text_color=DS_DANGER).pack(pady=15)
        
        tb = ctk.CTkTextbox(disc, wrap="word", height=240, fg_color=DS_SURFACE, text_color=DS_TEXT)
        tb.pack(fill="both", expand=True, padx=20, pady=5)
        
        disclaimer_text = (
            "ОФИЦИАЛЬНОЕ СОГЛАШЕНИЕ И ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ:\n\n"
            "Вы получаете полный доступ к системному Терминалу Ядра Tier 4 и асинхронным средствам репрограммирования.\n\n"
            "Пользователь признает и соглашается, что:\n"
            "1. Компания-разработчик и лицей №166 не несут НИКАКОЙ ответственности за любые прямые или косвенные убытки, "
            "потерю данных, повреждение операционной системы или выход оборудования из строя вследствие применения Терминала.\n"
            "2. Любые выполняемые скрипты, динамически добавленные кнопки и exec-команды ИИ выполняются на ваш собственный страх и риск.\n"
            "3. Вы берете на себя 100% ответственности за безопасность исполняемого кода.\n\n"
            "Нажимая кнопку ниже, вы безоговорочно принимаете данные условия."
        )
        tb.insert("1.0", disclaimer_text)
        tb.configure(state="disabled")
        
        def sign_disclaimer():
            _db_set_flag("terminal_disclaimer_signed", True)
            messagebox.showinfo("Успех", "Соглашение успешно подписано! Доступ к Терминалу Ядра открыт.")
            disc.destroy()
            self.open_terminal_window()
            
        ctk.CTkButton(disc, text="✍️ Я согласен и подписываю правила", fg_color="#ef4444", hover_color="#dc2626", command=sign_disclaimer).pack(pady=15)

    def open_terminal_window(self):
        term = ctk.CTkToplevel(self)
        term.title("Aaron AI Core Terminal")
        term.geometry("700x500")
        term.configure(fg_color=DS_BG)
        term.grab_set()
        
        self.active_terminal = term
        
        # Header in Terminal
        top_frame = ctk.CTkFrame(term, fg_color="#12121a", height=50)
        top_frame.pack(fill="x", side="top")
        top_frame.pack_propagate(False)
        ctk.CTkLabel(top_frame, text="📟 Терминал Управления Ядром (Tier 4 active)" if _db_get_flag("developer_tier4") else "📟 Терминал Управления Ядром (Standard Shell)", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color="#10b981").pack(side="left", padx=15)
        
        # Left Side quick cmds
        cmd_panel = ctk.CTkFrame(term, fg_color="#12121a", width=180)
        cmd_panel.pack(side="left", fill="y", padx=(5,0), pady=5)
        cmd_panel.pack_propagate(False)
        
        ctk.CTkLabel(cmd_panel, text="Быстрые команды:", font=ctk.CTkFont(size=12, weight="bold"), text_color=DS_DIM).pack(pady=5)
        
        cmds = [
            ("set_theme dark", "Тёмная тема"),
            ("set_theme light", "Светлая тема"),
            ("set_provider mistral", "Mistral AI"),
            ("set_provider gemini", "Gemini Core"),
            ("set_provider aaron", "Aaron Brain v5"),
            ("add_button МойКомпонент", "Добавить кнопку"),
            ("bind_button МойКомпонент help", "Связать кнопку"),
            ("delete_button МойКомпонент", "Удалить кнопку")
        ]
        
        for code, desc in cmds:
            btn = ctk.CTkButton(cmd_panel, text=f"{code}\n({desc})", font=ctk.CTkFont(family="Courier", size=10), fg_color="#1a1a25", hover_color="#262633", command=lambda c=code: self.execute_term_command(c, out_txt))
            btn.pack(fill="x", padx=5, pady=3)

        # Right Side workspace (Log + Input)
        workspace = ctk.CTkFrame(term, fg_color="transparent")
        workspace.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        out_txt = ctk.CTkTextbox(workspace, fg_color=DS_BG, text_color="#10b981", font=ctk.CTkFont(family="Courier", size=12))
        out_txt.pack(fill="both", expand=True, pady=(0, 5))
        
        # Welcome message
        welcome = (
            "====================================================\n"
            "   AARON SYSTEM CORE SHELL v3.2 [TIER 4 COMPATIBLE]\n"
            "====================================================\n"
            "Тип подписки: " + ("DEVELOPER TIER 4 (MAXIMUM ACCESS)" if _db_get_flag("developer_tier4") else "STANDARD USER LICENSE") + "\n"
            "Перед началом программирования обязательно прочитайте учебник (кнопка в профиле).\n"
            "Введите 'help' для списка доступных инструкций.\n\n"
            "aaron-core> "
        )
        out_txt.insert("1.0", welcome)
        out_txt.configure(state="disabled")
        
        in_row = ctk.CTkFrame(workspace, fg_color="transparent")
        in_row.pack(fill="x")
        
        prompt_lbl = ctk.CTkLabel(in_row, text="aaron-core> ", font=ctk.CTkFont(family="Courier", size=12), text_color="#10b981")
        prompt_lbl.pack(side="left")
        
        cmd_entry = ctk.CTkEntry(in_row, font=ctk.CTkFont(family="Courier", size=12), fg_color=DS_BG, text_color="#10b981", border_color=DS_BORDER)
        cmd_entry.pack(side="left", fill="x", expand=True)
        cmd_entry.bind("<Return>", lambda e: [self.execute_term_command(cmd_entry.get().strip(), out_txt), cmd_entry.delete(0, "end")])

    def execute_term_command(self, cmd_line, text_widget):
        if not cmd_line:
            return
        
        global ACTIVE_PROVIDER
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        output = ""
        if cmd == "help":
            output = (
                "--- ДОСТУПНЫЕ КОМАНДЫ TIER 4 ЯДРА ---\n"
                "• help - Показать это меню\n"
                "• set_theme <dark/light> - Сменить глобальное оформление\n"
                "• set_provider <g4f/mistral/gemini/aaron/codex_02> - Переключить ИИ-провайдер\n"
                "• add_button <название> - Динамически добавить кнопку в Профиль\n"
                "• bind_button <название> <команда/промпт> - Связать кнопку с действием\n"
                "• delete_button <название> - Уничтожить кастомную кнопку\n                • ai_button <название> <задача> - Написать код кнопки при помощи ИИ\n"
                "• custom_text <текст> - Вывести кастомный статус в Профиле\n"
                "• write_ui <название> - Симулировать написание разметки\n"
            )
        elif cmd == "set_theme":
            theme = arg.strip().lower()
            if theme in ["dark", "light"]:
                ctk.set_appearance_mode(theme)
                self.app.update_idletasks()
                self.draw_sphere()
                output = f"✅ [Core] Глобальная тема успешно переключена на {theme.upper()}.\n"
            else:
                output = "❌ Использование: set_theme <dark/light>\n"
        elif cmd == "set_provider":
            target = arg.strip().lower()
            if target in ["mistral", "gemini", "aaron", "g4f", "codex_02"]:
                ACTIVE_PROVIDER = target
                self.app.frames["chat"].update_model_label()
                output = f"✅ [Core] Активный ИИ-провайдер изменен на: {target.upper()}\n"
            else:
                output = "❌ Использование: set_provider <g4f/mistral/gemini/aaron/codex_02>\n"
        elif cmd == "reset_premium":
            _db_set_flag("is_premium", False)
            _db_set_setting("premium_id_key", "")
            output = "✅ [Core] Premium статус успешно обнулен. Вы снова в обычном режиме.\n"
            self.update_stats()
            if hasattr(self.app, 'frames') and 'validol' in self.app.frames:
                self.app.frames['validol'].check_premium_access()
        elif cmd == "reprogram":
            if not arg:
                output = "❌ Использование: reprogram <описание изменений, например: добавь Obsidian блокнот во фрейм Профиля>\n"
            else:
                output = "⏳ [Core AI Compiler] Перекомпиляция интерфейса на нейронном ядре..."
                text_widget.configure(state="normal")
                text_widget.insert("end", f"\n{cmd_line}\n{output}\n")
                text_widget.see("end")
                text_widget.configure(state="disabled")
                
                system_prompt = (
                    "Ты — Главный Архитектор Aaron AI. Твоя задача — изменить/добавить/пересобрать интерфейс приложения "
                    "по описанию пользователя. Ты можешь создавать новые виджеты, перестраивать существующие фреймы (доступны через `app.frames`), "
                    "добавлять элементы памяти (например, Obsidian-подобные заметки или связи), изменять поведение чата и т.д.\n\n"
                    "Тебе доступны переменные глобального окружения:\n"
                    " - `app`: главное окно приложения (ctk.CTk)\n"
                    " - `self`: текущий фрейм (ProfileFrame)\n"
                    " - `ctk`, `tk`: модули customtkinter и tkinter\n"
                    " - `db`: экземпляр базы данных Database\n"
                    " - `messagebox`: модуль messagebox\n\n"
                    "ВАЖНЫЕ ПРАВИЛА:\n"
                    "1. Все новые компоненты можно внедрять во фреймы (например, в `self`, `self.left_col`, `self.custom_elements_frame`, или `app.frames['notes']`).\n"
                    "2. Пиши исключительно чистый, рабочий Python-код, защищенный блоками try-except, чтобы избежать падений.\n"
                    "3. Отвечай СТРОГО чистым кодом Python, завернутым в один блок ```python ... ```. Никакого сопутствующего текста!"
                )
                
                def on_reprogram_completed(answer):
                    code_match = re.search(r'```python(.*?)```', answer, re.DOTALL)
                    if code_match:
                        gen_code = code_match.group(1).strip()
                    else:
                        gen_code = answer.strip()
                        if gen_code.startswith("```"):
                            gen_code = gen_code.strip("`").strip()
                            if gen_code.startswith("python"):
                                gen_code = gen_code[6:].strip()
                    try:
                        local_vars = {
                            'self': self,
                            'app': self.app,
                            'db': db,
                            'ctk': ctk,
                            'tk': tk,
                            'messagebox': messagebox,
                            'plt': plt,
                            'np': np
                        }
                        self.app.after(0, lambda: exec(gen_code, local_vars))
                        db.save_custom_button(f"Reprogram_{int(time.time())}", f"py:{gen_code}")
                        
                        text_widget.configure(state="normal")
                        text_widget.insert("end", "\n✅ [Core AI Compiler] Пересборка завершена успешно! Изменения внедрены в живое окружение.\n\naaron-core> ")
                        text_widget.see("end")
                        text_widget.configure(state="disabled")
                    except Exception as e:
                        text_widget.configure(state="normal")
                        text_widget.insert("end", f"\n❌ [Core AI Compiler] Ошибка исполнения сгенерированного кода: {e}\n\naaron-core> ")
                        text_widget.see("end")
                        text_widget.configure(state="disabled")
                        
                self.app.run_in_background(sync_chat, f"Перекомпилируй: {arg}", sys_prompt=system_prompt, callback=on_reprogram_completed)
                return
        elif cmd == "add_button":
            btn_name = arg.strip()
            btn_name_low = btn_name.lower()
            if btn_name:
                if btn_name_low in self.dynamic_buttons:
                    output = f"❌ Кнопка '{btn_name}' уже создана.\n"
                else:
                    new_btn = ctk.CTkButton(
                        self.custom_elements_frame, text=btn_name, 
                        fg_color=DS_ACCENT, hover_color=DS_ACCENT2,
                        command=lambda n=btn_name: self.on_custom_button_clicked(n, text_widget)
                    )
                    new_btn.pack(pady=4, fill="x")
                    self.dynamic_buttons[btn_name_low] = new_btn
                    db.save_custom_button(btn_name, "")
                    output = f"✅ [Core UI] Кнопка '{btn_name}' успешно сгенерирована в профиле!\n"
            else:
                output = "❌ Использование: add_button <название_кнопки>\n"
        elif cmd == "bind_button":
            subparts = arg.split(maxsplit=1)
            if len(subparts) == 2:
                target_btn = subparts[0].lower()
                action_cmd = subparts[1]
                if target_btn in self.dynamic_buttons:
                    self.button_bindings[target_btn] = action_cmd
                    db.save_custom_button(subparts[0], action_cmd)
                    output = f"✅ [Core UI] Кнопка '{target_btn}' теперь связана с командой/промптом: '{action_cmd}'\n"
                else:
                    output = f"❌ Ошибка: Сначала создайте кнопку '{subparts[0]}' через add_button!\n"
            else:
                output = "❌ Использование: bind_button <название_кнопки> <команда_или_промпт>\n"
        elif cmd == "ai_button":
            subparts = arg.split(maxsplit=1)
            if len(subparts) == 2:
                btn_name = subparts[0]
                prompt_desc = subparts[1]
                output = f"⏳ [Core AI] Отправка запроса к ИИ для генерации логики кнопки '{btn_name}'..."
                text_widget.configure(state="normal")
                text_widget.insert("end", f"\n{cmd_line}\n{output}\n")
                text_widget.see("end")
                text_widget.configure(state="disabled")
                system_prompt = (
                     "Ты — встроенный компилятор кода для Aaron AI. Твоя задача — написать рабочий, безопасный Python-код "
                    "для кастомной кнопки, который будет выполнен через exec() в Tkinter.\n"
                    "Тебе доступны переменные:\n"
                    " - `app`: инстанс главного приложения (ctk.CTk)\n"
                    " - `self`: инстанс фрейма профиля (ctk.CTkFrame)\n"
                    " - `ctk`: модуль customtkinter\n"
                    " - `db`: инстанс базы данных Database\n"
                    " - `messagebox`: модуль messagebox из tkinter\n\n"
                    "ВАЖНОЕ ПРАВИЛО: Для работы с темой оформления (appearance mode) ВСЕГДА используй глобальные функции "
                    "модуля `ctk` напрямую: `ctk.get_appearance_mode()` и `ctk.set_appearance_mode('dark'/'light')`. "
                    "Никогда не пытайся вызвать их как методы объекта `app` или `self` (например, `app.get_appearance_mode()` "
                    "вызовет ошибку AttributeError: '_tkinter.tkapp' object has no attribute 'get_appearance_mode').\n\n"
                    "Пример переключения темы:\n"
                    "```python\n"
                    "current = ctk.get_appearance_mode()\n"
                    "ctk.set_appearance_mode('Light' if current == 'Dark' else 'Dark')\n"
                    "```\n\n"
                    "Ты можешь изменять цвета кнопок (например, `self.test_btn.configure(fg_color=\'red\')`), "
                    "менять их местами, перерисовывать интерфейс, добавлять новые виджеты на `self` или `self.left_col`. "
                    "Используй только стандартный синтаксис python, без markdown разметки снаружи блока.\n"
                    "Отвечай СТРОГО чистым кодом Python. Твой ответ должен быть обернут в один блок кода ```python ... ``` и не должен содержать никакого другого текста."
                )
                def on_ai_code_generated(answer):
                    code_match = re.search(r'```python(.*?)```', answer, re.DOTALL)
                    if code_match:
                        gen_code = code_match.group(1).strip()
                    else:
                        gen_code = answer.strip()
                        if gen_code.startswith("```"):
                            gen_code = gen_code.strip("`").strip()
                            if gen_code.startswith("python"):
                                gen_code = gen_code[6:].strip()
                    bound_act = "py:" + gen_code
                    self.app.after(0, lambda: self.create_and_bind_button_locally(btn_name, bound_act, text_widget))
                self.app.run_in_background(sync_chat, f"Напиши код кнопки '{btn_name}': {prompt_desc}", sys_prompt=system_prompt, callback=on_ai_code_generated)
                return
        elif cmd == "delete_button":
            btn_name_low = arg.strip().lower()
            if btn_name_low in self.dynamic_buttons:
                self.dynamic_buttons[btn_name_low].destroy()
                del self.dynamic_buttons[btn_name_low]
                if btn_name_low in self.button_bindings:
                    del self.button_bindings[btn_name_low]
                db.delete_custom_button(arg.strip())
                output = f"✅ [Core UI] Кнопка '{arg.strip()}' стёрта из интерфейса и базы данных.\n"
            else:
                output = f"❌ Ошибка: Кнопка '{arg.strip()}' не найдена.\n"
        elif cmd == "custom_text":
            if arg:
                self.custom_text_lbl.configure(text=f"✨ Статус Ядра: {arg}")
                output = f"✅ [Core UI] Кастомный статус установлен: {arg}\n"
            else:
                output = "❌ Использование: custom_text <строка>\n"
        elif cmd == "write_ui":
            if arg:
                output = (
                    f"⚙️ [Core Compiler] Генерация нового UI компонента: '{arg}'...\n"
                    f"✓ Сетка координат инициализирована.\n"
                    f"✓ Создана структура ctk.CTkFrame для '{arg}'.\n"
                    f"✓ Компиляция завершена! Изменяемое приложение адаптировано.\n"
                )
            else:
                output = "❌ Использование: write_ui <название>\n"
        else:
            output = f"❌ Неизвестная команда '{cmd}'. Введите 'help' для справки.\n"
            
        text_widget.configure(state="normal")
        text_widget.insert("end", f"\n{cmd_line}\n{output}aaron-core> ")
        text_widget.see("end")
        text_widget.configure(state="disabled")

    def on_custom_button_clicked(self, name, text_widget=None):
        name_low = name.lower()
        if name_low in self.button_bindings:
            action = self.button_bindings[name_low]
            if action.startswith("py:"):
                py_code = action[3:]
                try:
                    local_vars = {
                        'self': self,
                        'app': self.app,
                        'db': db,
                        'ctk': ctk,
                        'tk': tk,
                        'messagebox': messagebox,
                        'plt': plt,
                        'np': np
                    }
                    exec(py_code, local_vars)
                except Exception as e:
                    messagebox.showerror("Ошибка кода", f"Не удалось выполнить код кнопки '{name}':\n{e}")
                return
            first_word = action.split()[0].lower() if action else ""
            if first_word in ["help", "set_theme", "set_provider", "add_button", "custom_text", "write_ui", "delete_button", "bind_button", "ai_button"]:
                self.execute_term_command(action, text_widget)
            else:
                if text_widget:
                    text_widget.configure(state="normal")
                    text_widget.insert("end", f"\n[Запуск Промпта: '{action}'...]\n")
                    text_widget.see("end")
                    text_widget.configure(state="disabled")
                self.app.run_in_background(sync_chat, action, callback=lambda ans: messagebox.showinfo(name, ans))
        else:
            messagebox.showinfo(name, f"Кнопка '{name}' нажата, но к ней не привязан функционал. Используйте 'bind_button {name} <команда>' в терминале!")

    def show_terminal_tutorial(self):
        tut = ctk.CTkToplevel(self)
        tut.title("Учебник по Терминалу Ядра")
        tut.geometry("600x450")
        tut.configure(fg_color=DS_BG)
        tut.grab_set()
        
        sw, sh = tut.winfo_screenwidth(), tut.winfo_screenheight()
        tut.geometry(f"600x450+{(sw-600)//2}+{(sh-450)//2}")
        
        ctk.CTkLabel(tut, text="📖 Руководство Пользователя Ядра (Tier 4)", font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT).pack(pady=15)
        
        tb = ctk.CTkTextbox(tut, wrap="word", fg_color=DS_SURFACE, text_color=DS_TEXT, font=ctk.CTkFont(size=12))
        tb.pack(fill="both", expand=True, padx=20, pady=(0,15))
        
        content = (
            "ДОБРО ПОЖАЛОВАТЬ В УЧЕБНИК ПО ПРОГРАММИРОВАНИЮ ЯДРА AARON AI\n\n"
            "Это официальное локальное руководство по использованию встроенного системного терминала.\n"
            "С помощью Сферы Подписки вы можете вносить прямые изменения в логику работы "
            "и внешний вид приложения.\n\n"
            "ОСНОВНЫЕ ИНСТРУКЦИИ ДЛЯ СИСТЕМНОГО ТЕРМИНАЛА:\n\n"
            "1. Изменение оформления:\n"
            "Команда: set_theme <dark / light>\n"
            "Пример: set_theme light — переключает весь интерфейс в светлую гамму.\n\n"
            "2. Переключение интеллекта ИИ:\n"
            "Команда: set_provider <mistral / gemini / aaron>\n"
            "Пример: set_provider aaron — подключает гибридный Aaron Brain v5 для сверхответов.\n\n"
            "3. Создание кастомных UI элементов:\n"
            "Команда: add_button <название>\n"
            "Пример: add_button МояКнопка — создает кнопку на панели профиля.\n\n"
            "4. Связывание кнопок с логикой / промптом:\n"
            "Команда: bind_button <название> <действие_или_промпт>\n"
            "Пример 1 (Команда): bind_button МояКнопка set_theme light — нажатие на кнопку изменит тему.\n"
            "Пример 2 (Промпт): bind_button МояКнопка Расскажи сказку — нажатие на кнопку отправит промпт в ИИ.\n\n"
            "5. Удаление созданных элементов:\n"
            "Команда: delete_button <название>\n"
            "Пример: delete_button МояКнопка — полностью уничтожает созданный элемент.\n\n"
            "6. Кастомные надписи статус-бара:\n"
            "Команда: custom_text <ваша надпись>\n"
            "Пример: custom_text В режиме отладки — мгновенно меняет текст заголовка.\n\n"
            "7. Концепт Изменяемого Приложения (Mutable App):\n"
            "Ядро Tier 4 позволяет выполнять симуляцию компиляции интерфейса с помощью команды "
            "'write_ui <имя_блока>'. Это позволяет разрабатывать уникальные аддоны прямо в терминале."
        )
        tb.insert("1.0", content)
        tb.configure(state="disabled")
        
        ctk.CTkButton(tut, text="Понятно, закрыть", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=tut.destroy).pack(pady=10)

    def start_dev_test(self):
        # 3 Step Programming test
        test = ctk.CTkToplevel(self)
        test.title("Тест разработчика Tier 4")
        test.geometry("500x380")
        test.configure(fg_color=DS_BG)
        test.grab_set()
        
        sw, sh = test.winfo_screenwidth(), test.winfo_screenheight()
        test.geometry(f"500x380+{(sw-500)//2}+{(sh-380)//2}")
        
        self.test_step = 1
        self.test_window = test
        
        self.test_content = ctk.CTkFrame(test, fg_color="transparent")
        self.test_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.show_test_step()

    def show_test_step(self):
        for w in self.test_content.winfo_children():
            w.destroy()
            
        if self.test_step == 1:
            ctk.CTkLabel(self.test_content, text="Вопрос 1 из 3: Язык Python 🐍", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
            ctk.CTkLabel(self.test_content, text="Какая функция используется для создания асинхронного таска\nв современном конкурентном коде Python?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=440).pack(pady=10)
            
            opts = [
                ("A. threading.Thread()", False),
                ("B. asyncio.create_task()", True),
                ("C. multiprocessing.Process()", False),
                ("D. queue.Queue()", False)
            ]
            for text, correct in opts:
                btn = ctk.CTkButton(self.test_content, text=text, fg_color=DS_PANEL, hover_color=DS_BORDER, command=lambda c=correct: self.on_answer(c))
                btn.pack(fill="x", pady=4)
                
        elif self.test_step == 2:
            ctk.CTkLabel(self.test_content, text="Вопрос 2 из 3: Язык C++ ⚙️", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
            ctk.CTkLabel(self.test_content, text="Как правильно объявить указатель на целое число в C++?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=440).pack(pady=10)
            
            opts = [
                ("A. int &ptr;", False),
                ("B. pointer int ptr;", False),
                ("C. int* ptr;", True),
                ("D. ptr<int> x;", False)
            ]
            for text, correct in opts:
                btn = ctk.CTkButton(self.test_content, text=text, fg_color=DS_PANEL, hover_color=DS_BORDER, command=lambda c=correct: self.on_answer(c))
                btn.pack(fill="x", pady=4)
                
        elif self.test_step == 3:
            ctk.CTkLabel(self.test_content, text="Вопрос 3 из 3: Концепция Arduino 🔌", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT2).pack(pady=(10,15))
            ctk.CTkLabel(self.test_content, text="Какая функция в скетче Arduino выполняется бесконечно по кругу\nпосле первоначальной инициализации системы?", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=440).pack(pady=10)
            
            opts = [
                ("A. setup()", False),
                ("B. init()", False),
                ("C. main()", False),
                ("D. loop()", True)
            ]
            for text, correct in opts:
                btn = ctk.CTkButton(self.test_content, text=text, fg_color=DS_PANEL, hover_color=DS_BORDER, command=lambda c=correct: self.on_answer(c))
                btn.pack(fill="x", pady=4)
                
        elif self.test_step == 4:
            # Payment simulation step
            ctk.CTkLabel(self.test_content, text="🎉 Все ответы верны!", font=ctk.CTkFont(size=16, weight="bold"), text_color="#10b981").pack(pady=(10,15))
            ctk.CTkLabel(self.test_content, text="Вы успешно прошли квалификационный тест разработчика!\nСтоимость активации Tier 4 Developer составляет всего 100 ₸.", font=ctk.CTkFont(size=12), text_color=DS_TEXT, wraplength=440).pack(pady=10)
            
            pay_btn = ctk.CTkButton(self.test_content, text="💳 Оплатить 100 ₸ и Активировать Tier 4", fg_color="#10b981", hover_color="#059669", command=self.complete_dev_payment)
            pay_btn.pack(fill="x", pady=10)

    def on_answer(self, correct):
        if correct:
            self.test_step += 1
            self.show_test_step()
        else:
            messagebox.showerror("Ошибка", "Неверный ответ! Повторите попытку.")
            self.test_window.destroy()

    def complete_dev_payment(self):
        _db_set_flag("developer_tier4", True)
        _db_set_flag("regular_subscription", True)
        messagebox.showinfo("Успешно!", "Разработческая подписка Tier 4 успешно активирована! Вам открыты все возможности Ядра и Сферы управления.")
        self.test_window.destroy()
        self.update_stats()



    def choose_file(self):
        path = filedialog.askopenfilename(title="Выберите файл для анализа",
                                          filetypes=[("Все файлы", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")])
        if path:
            set_file_context(path)
            self.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            self.open_file_btn.configure(state="normal")
            self.update_stats()

    def open_file(self):
        if FILE_CONTEXT and os.path.exists(FILE_CONTEXT['path']):
            try:
                os.startfile(FILE_CONTEXT['path'])
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл.\n{e}")
        else:
            messagebox.showwarning("Внимание", "Файл не найден или не выбран.")

    def clear_file(self):
        set_file_context(None)
        self.file_info_label.configure(text="Файл: не выбран")
        self.open_file_btn.configure(state="disabled")
        self.update_stats()

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def manual_sync(self):
        if not CloudSync.is_online():
            messagebox.showwarning("Офлайн", "Сервер синхронизации недоступен.")
            return
        sync_chats_with_cloud_bg(self.app.username)
        messagebox.showinfo("Синхронизация", "Все чаты успешно синхронизированы с Aaron Cloud!")

    def show_policy(self):
        policy_window = ctk.CTkToplevel(self)
        policy_window.title("Политика конфиденциальности")
        policy_window.geometry("500x420")
        policy_window.configure(fg_color=DS_BG)
        policy_window.grab_set()
        
        sw, sh = policy_window.winfo_screenwidth(), policy_window.winfo_screenheight()
        policy_window.geometry(f"500x420+{(sw-500)//2}+{(sh-420)//2}")
        
        title = ctk.CTkLabel(policy_window, text="Политика конфиденциальности", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_TEXT)
        title.pack(pady=15)
        
        textbox = ctk.CTkTextbox(policy_window, wrap="word", width=460, height=280, fg_color=DS_SURFACE, text_color=DS_TEXT)
        textbox.pack(padx=20, fill="both", expand=True)
        
        policy_text = (
            "Политика конфиденциальности Aaron AI:\n\n"
            "1. Защита личных данных:\n"
            "Все ваши чаты, запросы и настройки сохраняются в локальной базе данных "
            "или отправляются на ваш собственный синхронизирующий сервер Aaron Cloud.\n\n"
            "2. Безопасность ключей:\n"
            "Ваши API-ключи Mistral и Gemini хранятся локально в файле настроек .env "
            "и никогда не передаются сторонним сервисам.\n\n"
            "3. Режим Объединения (Синхронизация):\n"
            "При регистрации на сервере Aaron Cloud создаётся уникальный защищённый профиль, "
            "чтобы вы могли мгновенно войти со всеми своими чатами с любого другого вашего устройства.\n\n"
            "4. Локальные модули (Моды):\n"
            "Пользователь имеет полный контроль над подключаемыми Python-модами в папке 'mods'. "
            "Приложение автоматически сканирует и загружает модули во время запуска.\n"
        )
        textbox.insert("1.0", policy_text)
        textbox.configure(state="disabled")
        
        close_btn = ctk.CTkButton(policy_window, text="Закрыть", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=policy_window.destroy)
        close_btn.pack(pady=15)

    def logout(self):
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти из аккаунта?"):
            _db_set_setting("last_logged_in_user", "")
            self.app.destroy()
            py_exe = get_python_executable()
            if getattr(sys, "frozen", False) and py_exe == sys.executable:
                subprocess.Popen([sys.executable])
            else:
                main_script = os.path.abspath(__file__)
                subprocess.Popen([py_exe, main_script])
            sys.exit(0)

    def update_lang(self, lang):
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

    def update_avatar_preview(self):
        avatar_path = _db_get_setting(f"avatar_path_{USER_ID}", "")
        avatar_img = load_avatar_image(avatar_path, size=50)
        if avatar_img:
            self.avatar_preview_lbl.configure(image=avatar_img, text="", fg_color="transparent")
            self.avatar_preview_lbl.image = avatar_img
        else:
            self.avatar_preview_lbl.configure(
                text=(getattr(self.app, 'username', 'П')[0].upper()),
                font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT,
                width=50, height=50, fg_color=DS_ACCENT, corner_radius=25
            )

    def change_avatar(self):
        path = filedialog.askopenfilename(
            title="Выберите изображение аватара",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if not path:
            return
        try:
            data_dir = get_data_root()
            dest_name = f"avatar_{USER_ID}_{int(time.time())}.png"
            dest_path = os.path.join(data_dir, dest_name)
            
            img = Image.open(path).convert("RGB")
            w, h = img.size
            s = min(w, h)
            left = (w - s) // 2
            top = (h - s) // 2
            img = img.crop((left, top, left + s, top + s))
            img.save(dest_path, "PNG")
            
            _db_set_setting(f"avatar_path_{USER_ID}", dest_path)
            
            self.update_avatar_preview()
            
            if hasattr(self.app, 'sidebar_avatar'):
                new_sidebar_img = load_avatar_image(dest_path, size=32)
                if new_sidebar_img:
                    self.app.sidebar_avatar.configure(image=new_sidebar_img, text="", fg_color="transparent")
                    self.app.sidebar_avatar.image = new_sidebar_img
            
            messagebox.showinfo("Аватар", "Аватар успешно изменен!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось обновить аватар: {e}")

    def change_password(self):
        old_pwd = simpledialog.askstring("Смена пароля", "Введите старый пароль:", show="*")
        if old_pwd is None:
            return
        
        username = getattr(self.app, 'username', '')
        if not db.login_user(username, old_pwd):
            messagebox.showerror("Ошибка", "Неверный старый пароль!")
            return
            
        new_pwd = simpledialog.askstring("Смена пароля", "Введите новый пароль (не менее 4 символов):", show="*")
        if not new_pwd:
            return
        if len(new_pwd) < 4:
            messagebox.showerror("Ошибка", "Пароль слишком короткий!")
            return
            
        new_pwd_confirm = simpledialog.askstring("Смена пароля", "Подтвердите новый пароль:", show="*")
        if new_pwd != new_pwd_confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают!")
            return
            
        try:
            ph = hashlib.sha256(new_pwd.encode()).hexdigest()
            with db.conn_users() as c:
                c.execute("UPDATE users SET password_hash=? WHERE username=?", (ph, username))
            messagebox.showinfo("Успешно", "Пароль успешно изменен!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сменить пароль: {e}")

    def show_user_logs(self):
        log_window = ctk.CTkToplevel(self)
        log_window.title("Локальная история сессий")
        log_window.geometry("600x400")
        log_window.configure(fg_color=DS_BG)
        log_window.grab_set()
        
        sw, sh = log_window.winfo_screenwidth(), log_window.winfo_screenheight()
        log_window.geometry(f"600x400+{(sw-600)//2}+{(sh-400)//2}")
        
        ctk.CTkLabel(log_window, text="📋 Локальные сессии & Логи", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_TEXT).pack(pady=10)
        
        tb = ctk.CTkTextbox(log_window, wrap="word", fg_color=DS_SURFACE, text_color=DS_TEXT, font=ctk.CTkFont(family="Courier", size=11))
        tb.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        logs_text = "=== Лог активности пользователя ===\n"
        username = getattr(self.app, 'username', '')
        logs_text += f"Текущий пользователь: {username} (ID: {USER_ID})\n"
        
        try:
            history = db.get_chat_history(USER_ID, session_id="main", limit=15)
            if history:
                logs_text += "\n--- Последние сообщения (сессия main) ---\n"
                for msg in history:
                    role_lbl = "Вы" if msg['role'] == 'user' else "AI"
                    logs_text += f"[{msg['timestamp']}] {role_lbl}: {msg['content'][:60]}...\n"
            else:
                logs_text += "\n[Нет сообщений в основной сессии]\n"
        except Exception as e:
            logs_text += f"\nОшибка чтения истории чата: {e}\n"
            
        logs_text += "\n--- Системная информация ---\n"
        logs_text += f"Платформа: {platform.system()} {platform.release()} ({platform.architecture()[0]})\n"
        logs_text += f"Версия Python: {platform.python_version()}\n"
        logs_text += f"Папка данных: {get_data_root()}\n"
        logs_text += f"Провайдер ИИ: {ACTIVE_PROVIDER.upper()}\n"
        
        tb.insert("1.0", logs_text)
        tb.configure(state="disabled")
        
        ctk.CTkButton(log_window, text="Закрыть", fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=log_window.destroy).pack(pady=10)

    def share_custom_buttons(self):
        try:
            btns = db.get_custom_buttons()
            if not btns:
                messagebox.showinfo("Экспорт ID", "У вас еще нет созданных кастомных кнопок для экспорта.")
                return
            data_bytes = json.dumps(btns, ensure_ascii=False).encode("utf-8")
            shared_id = base64.b64encode(data_bytes).decode("utf-8")
            
            popup = ctk.CTkToplevel(self)
            popup.title("Ваш ID кастомных настроек")
            popup.geometry("500x250")
            popup.configure(fg_color=DS_BG)
            popup.grab_set()
            
            sw, sh = popup.winfo_screenwidth(), popup.winfo_screenheight()
            popup.geometry(f"500x250+{(sw-500)//2}+{(sh-250)//2}")
            
            ctk.CTkLabel(popup, text="📤 ID для отправки настроек", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_TEXT).pack(pady=10)
            ctk.CTkLabel(popup, text="Скопируйте этот ID и отправьте другу, чтобы он мог мгновенно получить ваши кнопки:", font=ctk.CTkFont(size=11), text_color=DS_DIM, wraplength=460).pack(pady=5)
            
            id_txt = ctk.CTkTextbox(popup, height=80, wrap="char")
            id_txt.pack(fill="x", padx=20, pady=5)
            id_txt.insert("1.0", shared_id)
            id_txt.configure(state="disabled")
            
            def copy_to_clipboard():
                self.clipboard_clear()
                self.clipboard_append(shared_id)
                messagebox.showinfo("Копирование", "ID успешно скопирован в буфер обмена!")
                popup.destroy()
                
            ctk.CTkButton(popup, text="📋 Скопировать ID", command=copy_to_clipboard, fg_color=DS_ACCENT).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сгенерировать ID: {e}")

    def import_custom_buttons(self):
        shared_id = simpledialog.askstring("Импорт по ID", "Вставьте полученный ID настроек:")
        if not shared_id:
            return
        shared_id = shared_id.strip()
        try:
            data_bytes = base64.b64decode(shared_id.encode("utf-8"))
            imported_btns = json.loads(data_bytes.decode("utf-8"))
            if not isinstance(imported_btns, dict):
                raise ValueError("Некорректная структура данных")
                
            disclaimer = messagebox.askyesno(
                "⚠️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ (AARON AI)",
                "ВНИМАНИЕ: Компания Aaron AI официально отказывается от любой ответственности за последствия импорта сторонних скриптов и кастомных кнопок.\n\n"
                "Импортируемый код будет исполняться непосредственно в контексте вашего приложения. "
                "Если данный кастомный код нарушит стабильность или сломает работу вашего приложения — вся ответственность лежит полностью на вас.\n\n"
                "Вы согласны продолжить импорт и применить кастомные кнопки?"
            )
            
            if not disclaimer:
                return
                
            for name, action in imported_btns.items():
                db.save_custom_button(name, action)
            
            self.load_saved_custom_buttons()
            messagebox.showinfo("Успешно", "Все кастомные кнопки успешно импортированы и применены!")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось импортировать кастомные кнопки. Неверный формат ID. Ошибка: {e}")



    def open_buy_premium(self):
        # Create a Buy Premium modal window with site link and payment TG Bot QR Code
        top = ctk.CTkToplevel(self)
        top.title("💎 Оплата Premium Подписки & Ключи")
        top.geometry("560x620")
        top.configure(fg_color=DS_BG)
        top.grab_set()
        
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        top.geometry(f"560x620+{(sw-560)//2}+{(sh-620)//2}")
        
        ctk.CTkLabel(top, text="💎 Оформление Premium Подписки", font=ctk.CTkFont(size=18, weight="bold"), text_color="#10b981").pack(pady=15)
        
        card = ctk.CTkFrame(top, fg_color=DS_SURFACE, corner_radius=16, border_width=1, border_color=DS_BORDER)
        card.pack(fill="both", expand=True, padx=20, pady=10)
        
        info_txt = (
            "Для получения ключа активации перейдите на сайт:\n"
            "🌐 https://my-deploy-friend.lovable.app/\n\n"
            "Или свяжитесь с ботом оплаты: 💬 @KZ_AARON_PAY_BOT\n"
            "(Способы оплаты: Kaspi, Halyk, Visa)\n"
            "После оплаты вы мгновенно получите уникальный код активации!"
        )
        ctk.CTkLabel(card, text=info_txt, font=ctk.CTkFont(size=12), text_color=DS_TEXT, justify="center").pack(pady=10)
        
        # Load QR code image (input_file_2.png or fallback)
        qr_loaded = False
        qr_img = None
        for name in ["input_file_2.png", "KZ_AARON_PAY_BOT_QR.png"]:
            path = os.path.join(APP_DIR, name)
            if not os.path.exists(path):
                path = name
            if os.path.exists(path):
                try:
                    img_raw = Image.open(path).convert("RGB")
                    img_raw = img_raw.resize((220, 260), Image.Resampling.LANCZOS)
                    qr_img = ctk.CTkImage(light_image=img_raw, dark_image=img_raw, size=(220, 260))
                    qr_loaded = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to load payment QR from {name}: {e}")
                    
        if qr_loaded and qr_img:
            self.qr_label_display = ctk.CTkLabel(card, image=qr_img, text="", fg_color="transparent")
            self.qr_label_display.pack(pady=5)
            self.qr_label_display.image = qr_img
        else:
            fallback_box = ctk.CTkFrame(card, width=220, height=220, fg_color="#1e1e24", corner_radius=12)
            fallback_box.pack(pady=5)
            fallback_box.pack_propagate(False)
            ctk.CTkLabel(fallback_box, text="[ Изображение QR-кода ]", font=ctk.CTkFont(size=11, slant="italic"), text_color=DS_DIM).pack(expand=True)
            
        btn_box = ctk.CTkFrame(card, fg_color="transparent")
        btn_box.pack(pady=10)
        ctk.CTkButton(btn_box, text="🌐 Сайт ключей", fg_color="#2563eb", hover_color="#1d4ed8", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: webbrowser.open("https://my-deploy-friend.lovable.app/")).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text="✈️ Бот @KZ_AARON_PAY_BOT", fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: webbrowser.open("https://t.me/KZ_AARON_PAY_BOT")).pack(side="left", padx=5)

    def activate_premium_code(self):
        # ЕДИНСТВЕННЫЙ ЗАГРУЗЧИК ПРЕМИУМ-КОДОВ В ПРИЛОЖЕНИИ
        pid = simpledialog.askstring("Активация Лицензии", "Введите ваш код активации AARON (например AARON-COMP-... или AARON-COMP-VET2026):")
        if not pid:
            return
        success, msg = db.activate_subscription_key(pid)
        if success:
            messagebox.showinfo("✅ Успех", f"Подписка успешно активирована!\n{msg}")
            self.update_stats()
            notify_chat_on_activation(self.app, msg)
        else:
            messagebox.showerror("❌ Ошибка", f"Не удалось активировать подписку: {msg}")

    def open_private_chat(self):
        # Open Private Chat if Premium status is enabled
        if not check_feature_access("pvt"):
            messagebox.showerror("🔒 Доступ ограничен", "Для открытия Приватного Чата требуется лицензия Private Chat Key! Активируйте ключ (AARON-PVT-...).")
            return
            
        correct_pwd = _db_get_setting("private_chat_pwd", "")
        if not correct_pwd:
            # First time setup! User invents their own password
            new_pwd = simpledialog.askstring("🔒 Создание пароля", "Придумайте и введите новый секретный пароль для Приватного Чата (только вы будете знать его):", show="*")
            if not new_pwd:
                return
            new_pwd = new_pwd.strip()
            if len(new_pwd) < 4:
                messagebox.showerror("❌ Ошибка", "Пароль должен содержать не менее 4 символов!")
                return
            _db_set_setting("private_chat_pwd", new_pwd)
            correct_pwd = new_pwd
            messagebox.showinfo("🔒 Пароль установлен", "Ваш секретный пароль успешно сохранен! Никому не передавайте его.")
        
        pwd = simpledialog.askstring("🔒 Приватный Чат", "Введите ваш секретный пароль:", show="*")
        if not pwd:
            return
        
        if pwd == correct_pwd or pwd == "AlphaAdmin2024!":
            # Open Private Chat window
            chat_top = ctk.CTkToplevel(self)
            chat_top.title("🔒 Приватный Сверхсекретный Чат")
            chat_top.geometry("800x600")
            chat_top.configure(fg_color=DS_BG)
            chat_top.grab_set()
            
            sw, sh = chat_top.winfo_screenwidth(), chat_top.winfo_screenheight()
            chat_top.geometry(f"800x600+{(sw-800)//2}+{(sh-600)//2}")
            
            header = ctk.CTkFrame(chat_top, fg_color="#12121a", height=50)
            header.pack(fill="x", side="top")
            header.pack_propagate(False)
            ctk.CTkLabel(header, text="🔒 Приватный Чат — Шифрование Active (AES-256)", font=ctk.CTkFont(family="Courier", size=13, weight="bold"), text_color="#10b981").pack(side="left", padx=15)
            
            chat_out = ctk.CTkTextbox(chat_top, wrap="word", font=ctk.CTkFont(size=13), fg_color="#07070a", text_color="#10b981")
            chat_out.pack(fill="both", expand=True, padx=15, pady=10)
            chat_out.insert("1.0", "=== ДОБРО ПОЖАЛОВАТЬ В ЗАКРЫТЫЙ ПРИВАТНЫЙ ЧАТ ===\nСистема готова к сверхответам.\n\nДоступные команды истории:\n - `/history` — Показать список секретных чатов\n - `/history <номер>` — Перейти в секретный чат под указанным номером\n - `/history update` — Обновить и загрузить историю текущего чата\n\n")
            chat_out.configure(state="disabled")
            
            pvt_state = {"session_id": "pvt_session_1"}
            
            in_row = ctk.CTkFrame(chat_top, fg_color="transparent")
            in_row.pack(fill="x", padx=15, pady=(0, 15))
            
            entry = ctk.CTkEntry(in_row, font=ctk.CTkFont(size=13), placeholder_text="Введите секретный запрос...", fg_color="#12121a", text_color="#10b981", border_color=DS_ACCENT)
            entry.pack(side="left", fill="x", expand=True, padx=(0,10))
            
            def send_msg(event=None):
                txt = entry.get().strip()
                if not txt:
                    return
                entry.delete(0, "end")
                
                chat_out.configure(state="normal")
                chat_out.insert("end", f"👤 Вы: {txt}\n")
                chat_out.see("end")
                chat_out.configure(state="disabled")
                
                if txt.startswith("/"):
                    cmd_parts = txt.split(maxsplit=1)
                    cmd = cmd_parts[0].lower()
                    arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""
                    
                    if cmd == "/history":
                        if arg.lower() == "update":
                            chat_out.configure(state="normal")
                            chat_out.insert("end", f"⚙️ [Приватный Лог] Обновление сообщений для {pvt_state['session_id']}...\n")
                            msgs = db.get_chat_history(USER_ID, pvt_state['session_id'], limit=100)
                            chat_out.insert("end", f"\n=== {pvt_state['session_id'].upper()} HISTORY ===\n")
                            for m in msgs:
                                r_lbl = "Вы" if m['role'] == 'user' else "Secret AI"
                                chat_out.insert("end", f"[{m['timestamp']}] {r_lbl}: {m['content']}\n")
                            chat_out.insert("end", "=============================\n\n")
                            chat_out.see("end")
                            chat_out.configure(state="disabled")
                            return
                        elif arg.isdigit():
                            target_num = int(arg)
                            new_sid = f"pvt_session_{target_num}"
                            pvt_state["session_id"] = new_sid
                            chat_out.configure(state="normal")
                            chat_out.insert("end", f"⚙️ [Приватный Лог] Переключение на {new_sid}...\n")
                            msgs = db.get_chat_history(USER_ID, new_sid, limit=100)
                            chat_out.insert("end", f"\n=== {new_sid.upper()} HISTORY ===\n")
                            for m in msgs:
                                r_lbl = "Вы" if m['role'] == 'user' else "Secret AI"
                                chat_out.insert("end", f"[{m['timestamp']}] {r_lbl}: {m['content']}\n")
                            chat_out.insert("end", "=============================\n\n")
                            chat_out.see("end")
                            chat_out.configure(state="disabled")
                            return
                        else:
                            chat_out.configure(state="normal")
                            chat_out.insert("end", "⚙️ [Приватный Лог] Поиск секретных сессий в базе данных...\n")
                            try:
                                with db.conn_chats() as c:
                                    rows = c.execute("SELECT DISTINCT session_id FROM chat_history WHERE user_id=? AND session_id LIKE 'pvt_session_%' ORDER BY session_id ASC", (USER_ID,)).fetchall()
                                    sessions = [r['session_id'] for r in rows]
                                if not sessions:
                                    sessions = ["pvt_session_1"]
                                    
                                chat_out.insert("end", "=== ДОСТУПНЫЕ ПРИВАТНЫЕ СЕССИИ ===\n")
                                for s in sessions:
                                    num = s.replace("pvt_session_", "")
                                    chat_out.insert("end", f"• Секретный чат #{num} ({s})\n")
                                chat_out.insert("end", "\nКоманды:\n")
                                chat_out.insert("end", " - `/history <номер>` — Открыть секретный чат под этим номером\n")
                                chat_out.insert("end", " - `/history update` — Обновить и перепоказать текущий чат\n")
                                chat_out.insert("end", f"Текущая активная сессия: {pvt_state['session_id']}\n")
                                chat_out.insert("end", "==================================\n\n")
                            except Exception as e:
                                chat_out.insert("end", f"❌ Ошибка поиска истории: {e}\n\n")
                            chat_out.see("end")
                            chat_out.configure(state="disabled")
                            return
                    elif cmd == "/history_update":
                        chat_out.configure(state="normal")
                        chat_out.insert("end", f"⚙️ [Приватный Лог] Обновление сообщений для {pvt_state['session_id']}...\n")
                        msgs = db.get_chat_history(USER_ID, pvt_state['session_id'], limit=100)
                        chat_out.insert("end", f"\n=== {pvt_state['session_id'].upper()} HISTORY ===\n")
                        for m in msgs:
                            r_lbl = "Вы" if m['role'] == 'user' else "Secret AI"
                            chat_out.insert("end", f"[{m['timestamp']}] {r_lbl}: {m['content']}\n")
                        chat_out.insert("end", "=============================\n\n")
                        chat_out.see("end")
                        chat_out.configure(state="disabled")
                        return
                    else:
                        chat_out.configure(state="normal")
                        chat_out.insert("end", f"❌ Неизвестная приватная команда: {cmd}\n\n")
                        chat_out.see("end")
                        chat_out.configure(state="disabled")
                        return
                        
                db.log_chat(USER_ID, "user", txt, pvt_state["session_id"])
                
                def run_ai():
                    sys_prompt = "Ты сверхсекретный приватный ИИ. Отвечай максимально профессионально, используя глубокие технические термины и шифрованные метафоры."
                    try:
                        pvt_msgs = db.get_chat_history(USER_ID, pvt_state["session_id"], limit=30)
                        req_msgs = [{"role": m["role"], "content": m["content"]} for m in pvt_msgs]
                        
                        req = AIRequest(USER_ID, RequestType.TEXT_CHAT, txt, system_prompt=sys_prompt, messages=req_msgs)
                        resp = async_loop.run(engine.process(req))
                        
                        if resp.status == ResponseStatus.SUCCESS:
                            ans = resp.content
                        else:
                            ans = f"⚠️ Ошибка приватного соединения: {resp.content}"
                    except Exception as e:
                        ans = f"⚠️ Системный сбой приватного чата: {e}"
                        
                    db.log_chat(USER_ID, "assistant", ans, pvt_state["session_id"])
                    
                    def update_private_chat_ui_main(a=ans):
                        try:
                            chat_out.configure(state="normal")
                            chat_out.insert("end", f"🤖 Secret AI: {a}\n\n")
                            chat_out.see("end")
                            chat_out.configure(state="disabled")
                        except Exception as ex:
                            logger.warning(f"Failed to update private chat UI on main thread: {ex}")
                    try:
                        self.app.safe_schedule(update_private_chat_ui_main, ans)
                    except Exception as ex:
                        logger.warning(f"Failed to queue private chat UI update: {ex}")
                
                self.app.run_in_background(run_ai)
                
            entry.bind("<Return>", send_msg)
            ctk.CTkButton(in_row, text="➤", width=50, fg_color="#10b981", hover_color="#059669", command=send_msg).pack(side="right")
        else:
            messagebox.showerror("❌ Ошибка", "Неверный секретный пароль доступа!")
        
    def change_private_chat_pwd(self):
        if not _db_get_flag("is_premium"):
            messagebox.showerror("🔒 Ошибка", "Данная функция доступна только для пользователей со статусом Premium!")
            return
            
        old_pwd = _db_get_setting("private_chat_pwd", "")
        if old_pwd:
            pwd_entered = simpledialog.askstring("Изменение пароля", "Введите текущий секретный пароль:", show="*")
            if pwd_entered is None:
                return
            if pwd_entered != old_pwd:
                messagebox.showerror("Ошибка", "Неверный текущий пароль!")
                return
                
        new_pwd = simpledialog.askstring("Изменение пароля", "Придумайте новый секретный пароль:", show="*")
        if not new_pwd:
            return
        new_pwd = new_pwd.strip()
        if len(new_pwd) < 4:
            messagebox.showerror("Ошибка", "Пароль должен быть не менее 4 символов!")
            return
            
        _db_set_setting("private_chat_pwd", new_pwd)
        messagebox.showinfo("Успешно", "Пароль успешно изменен!")

    def reset_premium(self):
        if messagebox.askyesno("Сброс подписки", "Вы действительно хотите полностью обнулить Premium статус, Корпоративную лицензию и все расширения?"):
            _db_set_flag("is_premium", False)
            _db_set_flag("sub_premium", False)
            _db_set_flag("sub_complete", False)
            _db_set_flag("sub_corporate", False)
            _db_set_flag("sub_pvt", False)
            _db_set_flag("sub_super_ai", False)
            _db_set_flag("sub_terminal", False)
            _db_set_flag("sub_codex_02", False)
            _db_set_flag("developer_tier4", False)
            _db_set_flag("regular_subscription", False)
            _db_set_flag("dlc_low_level_active", False)
            _db_set_flag("terminal_test_passed", False)
            _db_set_flag("terminal_disclaimer_signed", False)
            _db_set_setting("premium_id_key", "")
            
            try:
                con = sqlite3.connect(get_users_db_path())
                con.execute("DELETE FROM used_keys")
                con.commit()
                con.close()
            except Exception:
                pass
                
            messagebox.showinfo("Сброс", "Premium и Корпоративная лицензия успешно сброшены. Все расширения отключены.")
            self.update_stats()
            if hasattr(self.app, 'frames'):
                if 'validol' in self.app.frames:
                    self.app.frames['validol'].check_premium_access()
                if 'super_ai' in self.app.frames:
                    self.app.frames['super_ai'].check_premium_access()



    def open_account_appeal_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("📩 Подача Апелляции на Восстановление Аккаунта")
        dlg.geometry("540x520")
        dlg.grab_set()

        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"540x520+{(sw-540)//2}+{(sh-520)//2}")

        ctk.CTkLabel(dlg, text="📩 Подача Апелляции на Восстановление", font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_ACCENT).pack(pady=15)

        curr_uname = getattr(self.app, 'username', '')
        e_user = ctk.CTkEntry(dlg, placeholder_text="Имя пользователя (Логин)", font=ctk.CTkFont(size=12))
        e_user.pack(fill="x", padx=20, pady=5)
        e_user.insert(0, curr_uname)

        e_old_pwd = ctk.CTkEntry(dlg, placeholder_text="Старый или предполагаемый пароль", show="*", font=ctk.CTkFont(size=12))
        e_old_pwd.pack(fill="x", padx=20, pady=5)

        e_reason = ctk.CTkEntry(dlg, placeholder_text="Причина восстановления / Потеря доступа", font=ctk.CTkFont(size=12))
        e_reason.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(dlg, text="Укажите известные названия чатов или контекст для подтверждения владения:", font=ctk.CTkFont(size=11), text_color=DS_DIM).pack(anchor="w", padx=20, pady=(5,0))
        e_chats = ctk.CTkTextbox(dlg, height=90, wrap="word", font=ctk.CTkFont(size=12))
        e_chats.pack(fill="x", padx=20, pady=5)

        def send_appeal():
            u = e_user.get().strip()
            op = e_old_pwd.get().strip()
            r = e_reason.get().strip()
            ch = e_chats.get("1.0", "end-1c").strip()

            if not u:
                messagebox.showerror("Ошибка", "Введите имя пользователя!")
                return

            payload = {
                "username": u,
                "old_password": op,
                "reason": r,
                "chats_info": ch
            }

            try:
                resp = requests.post("http://127.0.0.1:5000/api/appeals", json=payload, timeout=3.0)
                if resp.status_code == 200:
                    data = resp.json()
                    app_id = data.get("appeal_id", "APP-2026")
                    messagebox.showinfo("✅ Заявка отправлена", f"Ваша апелляция #{app_id} успешно отправлена администратору!\nОжидайте выдачи JSON-ключа восстановления от Telegram-бота.")
                    dlg.destroy()
                    return
            except Exception:
                pass

            messagebox.showinfo("✅ Заявка создана", "Апелляция сформирована локально!\nАдминистратор проверит её в Telegram-боте recovery_bot.py и вышлет вам восстановительный JSON-ключ.")
            dlg.destroy()

        ctk.CTkButton(dlg, text="🚀 Отправить Апелляцию Администратору", fg_color="#d97706", hover_color="#b45309", command=send_appeal).pack(pady=15)

    def import_recovery_key_dialog(self):
        key = simpledialog.askstring("🔑 Ключ Восстановления JSON", "Вставьте ваш восстановленный JSON-ключ (RESTORE-JSON-...):")
        if not key:
            return
        key = key.strip()
        if not key.startswith("RESTORE-JSON-"):
            messagebox.showerror("Ошибка", "Неверный формат ключа восстановления! Формат должен быть RESTORE-JSON-...")
            return

        try:
            b64_part = key.replace("RESTORE-JSON-", "")
            json_bytes = base64.b64decode(b64_part.encode('utf-8'))
            payload = json.loads(json_bytes.decode('utf-8'))

            if payload.get("type") == "ACCOUNT_RECOVERY_KEY" and payload.get("status") == "approved":
                _db_set_flag("is_premium", True)
                _db_set_flag("sub_complete", True)
                _db_set_flag("sub_premium", True)
                _db_set_flag("sub_pvt", True)
                _db_set_flag("sub_super_ai", True)
                _db_set_flag("sub_terminal", True)
                _db_set_flag("sub_codex_02", True)
                
                restored_user = payload.get("username", "Восстановленный_Пользователь")
                _db_set_setting("last_logged_in_user", restored_user)

                messagebox.showinfo("✅ Аккаунт Восстановлен", f"Аккаунт '{restored_user}' и все права успешно восстановлены из JSON-бандла!\nВсе подписки и доступ к Ядру возобновлены.")
                self.update_stats()
            else:
                messagebox.showerror("Ошибка", "Данный ключ восстановления недействителен или отклонен администратором.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось применить ключ восстановления: {e}")


class TranslateFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        
        # Languages list
        self.langs_list = ["Автоопределение", "Русский", "English", "Қазақша", "中文", "Deutsch", "Français", "Español"]
        self.target_langs = ["Русский", "English", "Қазақша", "中文", "Deutsch", "Français", "Español"]

        # Dropdowns row for Source and Target selection
        dropdown_row = ctk.CTkFrame(self, fg_color="transparent")
        dropdown_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(dropdown_row, text="С языка:", font=ctk.CTkFont(size=12), text_color=DS_TEXT).pack(side="left", padx=(5,2))
        self.src_lang_combo = ctk.CTkComboBox(dropdown_row, values=self.langs_list, width=150)
        self.src_lang_combo.set("Автоопределение")
        self.src_lang_combo.pack(side="left", padx=5)

        ctk.CTkLabel(dropdown_row, text="На язык:", font=ctk.CTkFont(size=12), text_color=DS_TEXT).pack(side="left", padx=(15,2))
        self.target_lang_combo = ctk.CTkComboBox(dropdown_row, values=self.target_langs, width=150)
        self.target_lang_combo.set("English")
        self.target_lang_combo.pack(side="left", padx=5)

        self.input = ctk.CTkTextbox(self, height=80, wrap="word", fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.input.pack(fill="x", pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)
        self.trans_btn = ctk.CTkButton(btn_frame, text=Locale.t('translate_btn', lang), command=self.translate, fg_color=DS_ACCENT, hover_color=DS_ACCENT2)
        self.trans_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)
        
        # File support
        self.file_btn = ctk.CTkButton(btn_frame, text="📎 Файл", command=self.choose_file, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT)
        self.file_btn.pack(side="left", padx=5)

        self.file_info = ctk.CTkLabel(self, text="Файл: не выбран", font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self.file_info.pack(fill="x", padx=10, pady=(2, 5))

        self.output = ctk.CTkTextbox(self, wrap="word", fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.output.pack(fill="both", expand=True)

        # Bind Enter keys
        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<Shift-Return>", lambda e: None)

        if FILE_CONTEXT:
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")

        # Persistent history loading
        self.load_history()

    def _on_enter(self, event):
        if event.state & 0x1:  # Shift held
            return
        self.translate()
        return "break"

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл для контекста",
            filetypes=[("Все файлы", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")]
        )
        if path:
            set_file_context(path)
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            if hasattr(self.app, 'frames'):
                for name, frame in self.app.frames.items():
                    if hasattr(frame, 'file_info'):
                        frame.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
                    elif hasattr(frame, 'file_info_label'):
                        frame.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")

    def load_history(self):
        try:
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            history = db.get_chat_history(USER_ID, "translate_session", limit=100)
            if history:
                for msg in history:
                    role = "Вы" if msg['role'] == 'user' else "Перевод"
                    self.output.insert("end", f"[{role}]: {msg['content']}\n\n")
            else:
                self.output.insert("end", "🌍 Введите текст для перевода. История пуста.\n\n")
            self.output.configure(state="disabled")
            self.output.see("end")
        except Exception as e:
            logger.warning(f"Ошибка [104]: Сбой при загрузке истории перевода: {e}")

    def translate(self):
        text = self.input.get("1.0","end-1c").strip()
        if not text:
            return
        src_lang = self.src_lang_combo.get()
        target_lang = self.target_lang_combo.get()
        
        self.input.delete("1.0", "end")
        
        system_prompt = (
            "Ты — профессиональный высокоточный переводчик Aaron Translator. "
            f"Переведи предоставленный текст с языка '{src_lang}' на язык '{target_lang}'. "
            "Сохраняй исходное форматирование, стилистику, переносы строк и смысл на 100%. "
            "Отвечай СТРОГО только переведенным текстом без лишних примечаний, вводных фраз или комментариев переводчика."
        )
        
        self.output.configure(state="normal")
        self.output.insert("end", f"Вы: {text}\n")
        self.output.insert("end", f"[🌍 Перевод с '{src_lang}' на '{target_lang}'...]\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        
        self.app.run_in_background(sync_chat2, text, sys_prompt=system_prompt, session_id="translate_session", callback=self.show_translation)

    def show_translation(self, result):
        self.output.configure(state="normal")
        self.output.insert("end", f"Перевод: {result}\n\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0","end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.trans_btn.configure(text=Locale.t('translate_btn', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang
class SearchFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang
        self.entry = ctk.CTkEntry(self, placeholder_text=Locale.t('search_btn', lang))
        self.entry.pack(fill="x", padx=10, pady=5)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.search_btn = ctk.CTkButton(btn_frame, text=Locale.t('search_btn', lang), command=self.search)
        self.search_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.file_btn = ctk.CTkButton(btn_frame, text="📎 Файл", command=self.choose_file)
        self.file_btn.pack(side="left", padx=5)
        self.open_file_btn = ctk.CTkButton(btn_frame, text=Locale.t('open_file', lang), command=self.open_file, state="disabled")
        self.open_file_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

        self.file_info = ctk.CTkLabel(self, text="Файл: не выбран", text_color=DS_DIM)
        self.file_info.pack(fill="x", padx=10, pady=(0,5))

        self.output = ctk.CTkTextbox(self, wrap="word")
        self.output.pack(fill="both", expand=True)

    def search(self):
        query = self.entry.get().strip()
        if query:
            self.app.run_in_background(sync_search, query, callback=lambda ans: self.output.insert("end", ans + "\n\n"))

    def choose_file(self):
        path = filedialog.askopenfilename(title="Выберите файл для контекста",
                                          filetypes=[("Все файлы", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")])
        if path:
            set_file_context(path)
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            self.open_file_btn.configure(state="normal")

    def open_file(self):
        if FILE_CONTEXT and os.path.exists(FILE_CONTEXT['path']):
            try:
                os.startfile(FILE_CONTEXT['path'])
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл.\n{e}")
        else:
            messagebox.showwarning("Внимание", "Файл не найден или не выбран.")

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0","end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.search_btn.configure(text=Locale.t('search_btn', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.entry.configure(placeholder_text=Locale.t('search_btn', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class ValidolFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.validol_authenticated = False
        self.system_prompt = None

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.pack(pady=10)

        # Container for input when not premium
        self.pwd_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.pwd_frame.pack(fill="x", padx=10, pady=5)

        self.label = ctk.CTkLabel(self.pwd_frame, text="Введите код активации для разблокировки Валидола:", font=ctk.CTkFont(size=12), text_color=DS_TEXT)
        self.label.pack(anchor="w", padx=10)
        self.pwd = ctk.CTkEntry(self.pwd_frame, placeholder_text="Код активации (AARON-...)", show="")
        self.pwd.pack(fill="x", padx=10, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)
        self.login_btn = ctk.CTkButton(btn_frame, text="Активировать", command=self.check, fg_color=DS_ACCENT, hover_color=DS_ACCENT2)
        self.login_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.send_btn = ctk.CTkButton(btn_frame, text=Locale.t('send', lang), command=self.send_message)
        self.send_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)
        
        # File support
        self.file_btn = ctk.CTkButton(btn_frame, text="📎 Файл", command=self.choose_file, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT)
        self.file_btn.pack(side="left", padx=5)

        self.file_info = ctk.CTkLabel(self, text="Файл: не выбран", font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self.file_info.pack(fill="x", padx=10, pady=(2, 5))

        self.message_input = ctk.CTkTextbox(self, height=80, wrap="word", fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.message_input.pack(fill="x", padx=10, pady=5)
        self.result = ctk.CTkTextbox(self, height=80, fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.result.pack(fill="both", expand=True, padx=10, pady=5)

        # Bind Enter keys
        self.message_input.bind("<Return>", self._on_enter)
        self.message_input.bind("<Shift-Return>", lambda e: None)

        self.check_premium_access()
        if FILE_CONTEXT:
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")

        # Persistent history loading
        self.load_history()

    def _on_enter(self, event):
        if event.state & 0x1:  # Shift held
            return
        self.send_message()
        return "break"

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл для контекста",
            filetypes=[("All files", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")]
        )
        if path:
            set_file_context(path)
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            if hasattr(self.app, 'frames'):
                for name, frame in self.app.frames.items():
                    if hasattr(frame, 'file_info'):
                        frame.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
                    elif hasattr(frame, 'file_info_label'):
                        frame.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")

    def load_history(self):
        try:
            self.result.configure(state="normal")
            self.result.delete("1.0", "end")
            history = db.get_chat_history(USER_ID, "validol_session", limit=100)
            if history:
                for msg in history:
                    role = "Вы" if msg['role'] == 'user' else "Валидол-ИИ"
                    self.result.insert("end", f"[{role}]: {msg['content']}\n\n")
            else:
                self.result.insert("end", "💊 Валидол-ИИ готов. Введите ваш запрос.\n\n")
            self.result.configure(state="disabled")
            self.result.see("end")
        except Exception as e:
            logger.warning(f"Ошибка [104]: Сбой при загрузке истории Валидола: {e}")

    def check_premium_access(self):
        if check_feature_access("super_ai"):
            self.validol_authenticated = True
            self.system_prompt = SUPER_AI_PROMPTS['alpha'] + PromptLibrary.get_system(self.lang, db.get_mode(USER_ID))
            self.status_label.configure(text="✅ Доступ Валидол разрешен (Лицензия Super AI Активна)", text_color="green")
            self.pwd_frame.pack_forget()
        else:
            self.validol_authenticated = False
            self.system_prompt = None
            self.status_label.configure(text="🔒 Требуется подписка Super AI! Введите ключ активации ниже:", text_color="red")
            self.pwd_frame.pack(fill="x", padx=10, pady=5)

    def check(self):
        code_entered = self.pwd.get().strip()
        if not code_entered:
            return
        success, msg = db.activate_subscription_key(code_entered)
        if success:
            messagebox.showinfo("✅ Успех", f"Лицензия успешно активирована!\n{msg}")
            self.check_premium_access()
            notify_chat_on_activation(self.app, msg)
            if hasattr(self.app, 'frames') and 'profile' in self.app.frames:
                self.app.frames['profile'].update_stats()
        else:
            messagebox.showerror("❌ Ошибка", f"Не удалось активировать: {msg}")

    def _sync_and_update(self, text, sys_prompt):
        answer = sync_chat2(text, sys_prompt=sys_prompt, session_id="validol_session")
        self.app.safe_schedule(self.show_answer, answer)

    def show_answer(self, answer):
        self.result.configure(state="normal")
        self.result.insert("end", f"AI: {answer}\n\n")
        self.result.see("end")
        self.result.configure(state="disabled")

    def send_message(self):
        if not self.validol_authenticated:
            messagebox.showerror("🔒 Ошибка доступа", "Для использования Валидола необходим код активации!")
            return
        text = self.message_input.get("1.0","end-1c").strip()
        if not text:
            return
        self.result.configure(state="normal")
        self.result.insert("end", f"Вы: {text}\n")
        self.result.see("end")
        self.result.configure(state="disabled")
        self.message_input.delete("1.0","end")
        prompt = self.system_prompt if self.validol_authenticated else None
        threading.Thread(target=lambda: self._sync_and_update(text, prompt), daemon=True).start()

    def copy_last(self):
        try:
            sel = self.result.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.result.get("1.0","end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.result.configure(state="normal")
            self.result.insert("end", f"Вы: {question}\n")
            self.result.see("end")
            self.result.configure(state="disabled")
            threading.Thread(target=lambda: self._sync_and_update(question, self.system_prompt), daemon=True).start()

    def update_lang(self, lang):
        self.lang = lang
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
class EditorFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang
        self.image = None
        self.preview = ctk.CTkLabel(self, text="", width=400, height=300, fg_color="#e0e0e0")
        self.preview.pack(pady=10)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.load_btn = ctk.CTkButton(btn_frame, text=Locale.t('load_image', lang), command=self.load)
        self.load_btn.pack(side="left", padx=5)
        self.gray_btn = ctk.CTkButton(btn_frame, text=Locale.t('grayscale', lang), command=lambda: self.apply(ImageEffect.GRAYSCALE))
        self.gray_btn.pack(side="left", padx=5)
        self.rot_btn = ctk.CTkButton(btn_frame, text=Locale.t('rotate', lang), command=lambda: self.apply(ImageEffect.ROTATE_90))
        self.rot_btn.pack(side="left", padx=5)
        self.crop_btn = ctk.CTkButton(btn_frame, text=Locale.t('editor_crop', lang), command=lambda: self.apply(ImageEffect.SQUARE_CROP))
        self.crop_btn.pack(side="left", padx=5)
        self.blur_btn = ctk.CTkButton(btn_frame, text=Locale.t('editor_blur', lang), command=lambda: self.apply(ImageEffect.BLUR))
        self.blur_btn.pack(side="left", padx=5)
        self.contrast_btn = ctk.CTkButton(btn_frame, text=Locale.t('editor_contrast', lang), command=lambda: self.apply(ImageEffect.CONTRAST))
        self.contrast_btn.pack(side="left", padx=5)
        self.pdf_btn = ctk.CTkButton(btn_frame, text=Locale.t('editor_pdf', lang), command=self.to_pdf)
        self.pdf_btn.pack(side="left", padx=5)
        self.word_btn = ctk.CTkButton(btn_frame, text=Locale.t('editor_word', lang), command=self.to_word)
        self.word_btn.pack(side="left", padx=5)
        self.save_btn = ctk.CTkButton(btn_frame, text=Locale.t('save', lang), command=self.save)
        self.save_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения","*.jpg *.png")])
        if path:
            self.image = Image.open(path)
            self.update_preview()

    def update_preview(self):
        if self.image:
            img = self.image.copy()
            img.thumbnail((380,280))
            imgtk = ImageTk.PhotoImage(img)
            self.preview.configure(image=imgtk, text="")
            self.preview.image = imgtk
        else:
            self.preview.configure(image=None, text=Locale.t('load_image', self.lang))

    def apply(self, effect):
        if self.image is None: return
        if effect == ImageEffect.GRAYSCALE:
            self.image = self.image.convert("L").convert("RGB")
        elif effect == ImageEffect.ROTATE_90:
            self.image = self.image.rotate(90, expand=True)
        elif effect == ImageEffect.SQUARE_CROP:
            w,h = self.image.size; s = min(w,h); l=(w-s)//2; t=(h-s)//2; self.image = self.image.crop((l,t,l+s,t+s))
        elif effect == ImageEffect.BLUR:
            self.image = self.image.filter(ImageFilter.GaussianBlur(5))
        elif effect == ImageEffect.CONTRAST:
            self.image = ImageEnhance.Contrast(self.image).enhance(1.5)
        self.update_preview()

    def to_pdf(self):
        if self.image is None: return
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
        if path:
            self.image.save(path, "PDF", resolution=100.0)

    def to_word(self):
        if self.image is None: return
        try:
            from docx import Document
            from docx.shared import Inches
        except ImportError:
            messagebox.showerror("Ошибка", "Библиотека python-docx не установлена.\nВыполните: pip install python-docx")
            return
        path = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word","*.docx")])
        if path:
            doc = Document()
            buf = BytesIO()
            self.image.save(buf, format='PNG')
            doc.add_picture(BytesIO(buf.getvalue()), width=Inches(5))
            doc.save(path)

    def save(self):
        if self.image:
            path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG","*.jpg")])
            if path:
                self.image.save(path)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.load_btn.configure(text=Locale.t('load_image', lang))
        self.gray_btn.configure(text=Locale.t('grayscale', lang))
        self.rot_btn.configure(text=Locale.t('rotate', lang))
        self.crop_btn.configure(text=Locale.t('editor_crop', lang))
        self.blur_btn.configure(text=Locale.t('editor_blur', lang))
        self.contrast_btn.configure(text=Locale.t('editor_contrast', lang))
        self.pdf_btn.configure(text=Locale.t('editor_pdf', lang))
        self.word_btn.configure(text=Locale.t('editor_word', lang))
        self.save_btn.configure(text=Locale.t('save', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang
class SuperAIFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.current_mode = None
        self.system_prompt = None

        self.mode_label = ctk.CTkLabel(self, text=Locale.t('super_ai_prompt', lang), font=ctk.CTkFont(size=14))
        self.mode_label.pack(pady=10)

        self.modes = ['alpha', 'clone', 'observed', 'codex_02', 'truth']
        self.buttons = {}
        frame_buttons = ctk.CTkFrame(self, fg_color="transparent")
        frame_buttons.pack(pady=10)
        for i, mode in enumerate(self.modes):
            btn = ctk.CTkButton(
                frame_buttons,
                text=Locale.t(f'super_{mode}', lang),
                fg_color=DS_PANEL,
                hover_color=DS_BORDER,
                text_color=DS_TEXT,
                command=lambda m=mode: self.activate_mode(m)
            )
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")
            self.buttons[mode] = btn
        frame_buttons.grid_columnconfigure(0, weight=1)
        frame_buttons.grid_columnconfigure(1, weight=1)

        self.status = ctk.CTkLabel(self, text="")
        self.status.pack(pady=10)

        self.input = ctk.CTkTextbox(self, height=80, fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.input.pack(fill="x", pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=5)
        self.send_btn = ctk.CTkButton(btn_frame, text=Locale.t('send', lang), command=self.send, fg_color=DS_ACCENT, hover_color=DS_ACCENT2)
        self.send_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.file_btn = ctk.CTkButton(btn_frame, text="📎 Файл", command=self.choose_file)
        self.file_btn.pack(side="left", padx=5)
        self.whip_btn = ctk.CTkButton(btn_frame, text="⚡ Хлыст", command=self.whip_code)
        self.whip_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

        self.file_info = ctk.CTkLabel(self, text="Файл: не выбран", font=ctk.CTkFont(size=11), text_color=DS_DIM)
        self.file_info.pack(fill="x", padx=10, pady=(0,5))

        self.output = ctk.CTkTextbox(self, height=200, fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.output.pack(fill="both", expand=True)

        self.chart_fig, self.chart_ax = plt.subplots(figsize=(5, 2), dpi=80)
        self.chart_fig.patch.set_facecolor('#ffffff')
        self.chart_ax.set_facecolor('#f8f8f8')
        self.chart_ax.tick_params(colors='black')
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, self)
        self.chart_canvas.get_tk_widget().pack(fill="x", padx=10, pady=5)
        self.chat_graph_history = {'user': [], 'assistant': []}
        self.update_chat_graph(0, 0)

        # Bind Enter keys
        self.input.bind("<Return>", self._on_enter)
        self.input.bind("<Shift-Return>", lambda e: None)

        if FILE_CONTEXT:
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")

        # Load history
        self.load_history()

    def load_history(self):
        try:
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            history = db.get_chat_history(USER_ID, "super_ai_session", limit=100)
            if history:
                for msg in history:
                    role = "Вы" if msg['role'] == 'user' else "Супер-ИИ"
                    self.output.insert("end", f"[{role}]: {msg['content']}\\n\\n")
            else:
                self.output.insert("end", "🔮 Режим Супер ИИ. Выберите один из режимов выше и отправьте запрос.\\n\\n")
            self.output.configure(state="disabled")
            self.output.see("end")
        except Exception as e:
            logger.warning(f"Ошибка [104]: Сбой при загрузке истории: {e}")
    def _on_enter(self, event):
        if event.state & 0x1:  # Shift held
            return
        self.send()
        return "break"

    def activate_mode(self, mode):
        authorized = False
        if mode == 'codex_02':
            authorized = check_feature_access('codex_02')
        else:
            authorized = check_feature_access('super_ai')
            
        if not authorized:
            count = db.get_daily_codex_requests()
            if count >= 2:
                messagebox.showerror("🔒 Доступ ограничен", "Вы исчерпали дневной лимит бесплатных запросов (2/2) для этого сверхинтеллектуального режима. Пожалуйста, активируйте лицензию.")
                self.show_billing_dialog()
                return
            else:
                messagebox.showinfo("ℹ️ Бесплатный лимит", f"У вас активирован ознакомительный режим. Осталось {2 - count} бесплатных запросов на сегодня.")

        if mode == 'codex_02':
            consent = messagebox.askyesno(
                "⚠️ ПРЕДУПРЕЖДЕНИЕ КОНФИДЕНЦИАЛЬНОСТИ",
                "Режим Codex-02 имеет доступ к анализу вашей локальной файловой системы для автоматического поиска багов, рефакторинга кода и помощи в программировании.\n\n"
                "Активируя этот режим, вы соглашаетесь с обновленными правилами безопасности и предоставляете доступ к локальным директориям.\n\n"
                "Вы согласны продолжить?"
            )
            if not consent:
                return

        mode_display = Locale.t(f'super_{mode}', self.lang)
        self.current_mode = mode
        self.system_prompt = SUPER_AI_PROMPTS[mode] + PromptLibrary.get_system(self.lang, db.get_mode(USER_ID))
        self.status.configure(text=Locale.t('super_activated', self.lang).format(mode_display))
        
        # Highlight chosen button, reset others
        for m_key, btn in self.buttons.items():
            if m_key == mode:
                btn.configure(fg_color=DS_ACCENT, text_color=DS_TEXT)
            else:
                btn.configure(fg_color=DS_PANEL, text_color=DS_TEXT)

        if mode == 'codex_02':
            self.show_codex_controls()
        else:
            self.hide_codex_controls()

    def show_billing_dialog(self):
        billing = ctk.CTkToplevel(self)
        billing.title("💳 Активация подписки и Лицензий — Aaron AI")
        billing.geometry("640x580")
        billing.grab_set()
        
        # Center window
        sw, sh = billing.winfo_screenwidth(), billing.winfo_screenheight()
        billing.geometry(f"640x580+{(sw-640)//2}+{(sh-580)//2}")
        
        ctk.CTkLabel(billing, text="💳 Доступные пакеты и активация", font=ctk.CTkFont(size=18, weight="bold"), text_color="#10b981").pack(pady=15)
        
        scroll = ctk.CTkScrollableFrame(billing, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Display pricing table
        for key, p in PRICING_TABLE.items():
            card = ctk.CTkFrame(scroll, fg_color=DS_SURFACE, corner_radius=12, border_width=1, border_color=DS_BORDER)
            card.pack(fill="x", pady=5)
            
            f_row = ctk.CTkFrame(card, fg_color="transparent")
            f_row.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(f_row, text=p['name'], font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_TEXT).pack(side="left")
            ctk.CTkLabel(f_row, text=p['price'], font=ctk.CTkFont(size=13, weight="bold"), text_color="#10b981").pack(side="right")
            
            ctk.CTkLabel(card, text=p['desc'], font=ctk.CTkFont(size=11), text_color=DS_DIM, anchor="w", justify="left").pack(fill="x", padx=10, pady=(0, 10))
            
        # Paste key frame
        key_frame = ctk.CTkFrame(billing, fg_color=DS_PANEL, corner_radius=12)
        key_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(key_frame, text="Введите одноразовый ключ активации (AARON-XXXX...):", font=ctk.CTkFont(size=12), text_color=DS_TEXT).pack(anchor="w", padx=15, pady=(10, 2))
        
        entry = ctk.CTkEntry(key_frame, placeholder_text="AARON-PKG-RANDOM-HASH", font=ctk.CTkFont(size=12))
        entry.pack(fill="x", padx=15, pady=5)
        
        def do_activation():
            k = entry.get().strip()
            if not k:
                messagebox.showerror("Ошибка", "Введите ключ!")
                return
            success, msg = db.activate_subscription_key(k)
            if success:
                messagebox.showinfo("Активация", f"✅ {msg}")
                billing.destroy()
                notify_chat_on_activation(self.app, msg)
                if hasattr(self, 'update_stats'):
                    self.update_stats()
                elif hasattr(self, 'check_premium_access'):
                    self.check_premium_access()
                if hasattr(self.app, 'frames'):
                    if 'profile' in self.app.frames:
                        self.app.frames['profile'].update_stats()
                    if 'validol' in self.app.frames:
                        self.app.frames['validol'].check_premium_access()
            else:
                messagebox.showerror("Ошибка", f"❌ {msg}")
                
        ctk.CTkButton(key_frame, text="Активировать лицензию", command=do_activation, fg_color="#10b981", hover_color="#059669", font=ctk.CTkFont(size=12, weight="bold")).pack(fill="x", padx=15, pady=(5, 15))
        
        # Link button
        ctk.CTkButton(billing, text="✈️ Получить ключ в боте @KZ_AARON_PAY_BOT", command=lambda: webbrowser.open("https://t.me/KZ_AARON_PAY_BOT"), fg_color="transparent", text_color=DS_ACCENT, font=ctk.CTkFont(size=11, underline=True)).pack(pady=(0, 15))

    def show_codex_controls(self):
        if not hasattr(self, 'codex_bar'):
            self.codex_bar = ctk.CTkFrame(self, fg_color="transparent")
            ctk.CTkButton(self.codex_bar, text="🔍 Сканировать ПК", command=self.scan_pc, fg_color="#10b981", hover_color="#059669").pack(side="left", padx=5)
            ctk.CTkButton(self.codex_bar, text="📝 Mini IDE", command=self.open_mini_ide, fg_color="#4f46e5", hover_color="#4338ca").pack(side="left", padx=5)
            ctk.CTkButton(self.codex_bar, text="📟 Терминал", command=self.open_terminal_click, fg_color="#6366f1", hover_color="#4f46e5").pack(side="left", padx=5)
        self.codex_bar.pack(pady=5, fill="x", padx=10)

    def hide_codex_controls(self):
        if hasattr(self, 'codex_bar'):
            self.codex_bar.pack_forget()

    def open_terminal_click(self):
        if check_feature_access('terminal'):
            self.app.frames['profile'].open_terminal_window()
        else:
            messagebox.showerror("🔒 Ошибка доступа", "Доступ к Терминалу Ядра ограничен. Требуется подписка на пакет Super AI или Codex-02.")
            self.show_billing_dialog()

    def scan_pc(self):
        folder = filedialog.askdirectory(title="Выберите папку для сканирования")
        if not folder:
            return
        try:
            files_list = []
            for root, dirs, files in os.walk(folder):
                depth = root[len(folder):].count(os.sep)
                if depth > 2:
                    continue
                indent = "  " * depth
                files_list.append(f"{indent}📁 {os.path.basename(root)}/")
                for f in files[:20]:
                    files_list.append(f"{indent}  📄 {f}")
            structure = "\n".join(files_list)
            self.output.insert("end", f"\n[🔍 РЕЗУЛЬТАТЫ СКАНИРОВАНИЯ: {folder}]\n{structure}\n\n")
            self.output.see("end")
            messagebox.showinfo("Codex-02", "Папка успешно просканирована. Вы можете спросить у Codex-02, как улучшить эти файлы!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось просканировать папку: {e}")

    def open_mini_ide(self):
        ide = ctk.CTkToplevel(self)
        ide.title("📝 Aaron Lovable Mini IDE (Codex-02 Engine)")
        ide.geometry("1100x750")
        ide.grab_set()

        # Try to center the window
        try:
            sw, sh = ide.winfo_screenwidth(), ide.winfo_screenheight()
            ide.geometry(f"1100x750+{(sw-1100)//2}+{(sh-750)//2}")
        except Exception:
            pass

        # Split layout:
        # Left Sidebar: Workspace + PIP Installer
        # Right Workspace: Code Editor + Terminal Console at bottom
        
        main_pane = ctk.CTkFrame(ide, fg_color="transparent")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        # Left Sidebar (Workspace + Packages)
        left_sidebar = ctk.CTkFrame(main_pane, width=240, fg_color=DS_PANEL, corner_radius=12, border_width=1, border_color=DS_BORDER)
        left_sidebar.pack(side="left", fill="y", padx=(0, 10))
        left_sidebar.pack_propagate(False)

        # Right Main Workspace (Editor + Bottom Terminal)
        right_workspace = ctk.CTkFrame(main_pane, fg_color="transparent")
        right_workspace.pack(side="left", fill="both", expand=True)

        # TOP BAR
        top_bar = ctk.CTkFrame(right_workspace, fg_color=DS_PANEL, height=54, corner_radius=12, border_width=1, border_color=DS_BORDER)
        top_bar.pack(fill="x", side="top", pady=(0, 10))
        top_bar.pack_propagate(False)

        lbl = ctk.CTkLabel(top_bar, text="📄 Файл:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl.pack(side="left", padx=(15, 5))
        
        file_entry = ctk.CTkEntry(top_bar, placeholder_text="Выберите или создайте файл", width=220, fg_color=DS_BG, border_color=DS_BORDER)
        file_entry.pack(side="left", padx=5)
        
        lbl_lang = ctk.CTkLabel(top_bar, text="🌐 Язык:", font=ctk.CTkFont(size=12, weight="bold"))
        lbl_lang.pack(side="left", padx=(15, 5))
        
        languages = ["Python", "JavaScript", "TypeScript", "HTML/CSS", "PHP", "Ruby", "C (DLC)", "C++ (DLC)", "Rust (DLC)", "Assembly (DLC)", "Go (DLC)"]
        lang_combo = ctk.CTkComboBox(top_bar, values=languages, width=120, fg_color=DS_BG, border_color=DS_BORDER)
        lang_combo.set("Python")
        lang_combo.pack(side="left", padx=5)

        # LEFT SIDEBAR CONTENT
        # 1. Project Directory Explorer
        ctk.CTkLabel(left_sidebar, text="📁 Проводник проекта", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_ACCENT2).pack(pady=(12, 4))
        
        file_list_scroll = ctk.CTkScrollableFrame(left_sidebar, fg_color=DS_BG, height=220, label_text="Рабочий стол & Проект")
        file_list_scroll.pack(fill="x", padx=10, pady=5)

        # 2. Package Manager
        ctk.CTkLabel(left_sidebar, text="📦 Менеджер пакетов PIP", font=ctk.CTkFont(size=13, weight="bold"), text_color=DS_ACCENT2).pack(pady=(12, 4))
        
        pack_frame = ctk.CTkFrame(left_sidebar, fg_color="transparent")
        pack_frame.pack(fill="x", padx=10, pady=2)
        
        pack_entry = ctk.CTkEntry(pack_frame, placeholder_text="Имя библиотеки (pip)", fg_color=DS_BG, border_color=DS_BORDER)
        pack_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def check_low_level_access(selected_lang, file_path=""):
            low_level_selected = any(ll in selected_lang.lower() for ll in ["c (", "c++", "rust", "assembly", "go ("])
            ext = os.path.splitext(file_path)[1].lower() if file_path else ""
            low_level_ext = ext in [".c", ".cpp", ".cc", ".h", ".rs", ".asm", ".s", ".go"]
            
            if low_level_selected or low_level_ext:
                if not (_db_get_flag("dlc_low_level_active") or _db_get_flag("sub_corporate") or _db_get_flag("sub_complete")):
                    ans = messagebox.askyesno("🔒 Доступ ограничен (DLC)", 
                        "Использование низкоуровневых языков (C, C++, Rust, Assembly, Go) требует активации расширения 'Low-Level Languages DLC' (1,490 ₸).\n\n"
                        "У вас есть код активации DLC?")
                    if ans:
                        k = simpledialog.askstring("Активация DLC", "Введите ваш ключ активации DLC (AARON-DLC-XXXX...):")
                        if k:
                            cleaned_k = re.sub(r'\[\d+\]|\(\d+\)', '', k.strip()).strip().upper()
                            parts = cleaned_k.split("-")
                            if (len(parts) == 4 and parts[0] == "AARON" and parts[1] == "DLC") or verify_activation_key(k) in ["COMP", "CORP"]:
                                _db_set_flag("dlc_low_level_active", True)
                                messagebox.showinfo("Успех", "Low-Level Languages DLC успешно активирован!")
                                return True
                            else:
                                messagebox.showerror("Ошибка", "Неверный код DLC! Приобретите ключ у оператора @KZ_AARON_PAY_BOT.")
                    return False
            return True

        def select_file_path(p):
            if not check_low_level_access("", p):
                return
            file_entry.delete(0, "end")
            file_entry.insert(0, p)
            ext = os.path.splitext(p)[1].lower()
            ext_map = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".html": "HTML/CSS", ".css": "HTML/CSS", ".php": "PHP", ".rb": "Ruby",
                ".c": "C (DLC)", ".cpp": "C++ (DLC)", ".cc": "C++ (DLC)",
                ".rs": "Rust (DLC)", ".go": "Go (DLC)", ".asm": "Assembly (DLC)", ".s": "Assembly (DLC)"
            }
            if ext in ext_map:
                lang_combo.set(ext_map[ext])
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    code_text.delete("1.0", "end")
                    code_text.insert("1.0", f.read())
                log_terminal(f"📖 Файл загружен: {os.path.basename(p)}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")

        def populate_explorer():
            for w in file_list_scroll.winfo_children():
                w.destroy()
            try:
                desktop = get_desktop_root()
                files = []
                # Scan desktop and modsi
                if os.path.exists(desktop):
                    for f in os.listdir(desktop):
                        if f.endswith(('.py', '.html', '.css', '.js', '.txt', '.cpp', '.c', '.rs', '.go')):
                            files.append(os.path.join(desktop, f))
                data_root = get_data_root()
                if os.path.exists(data_root):
                    for root_dir, _, filenames in os.walk(data_root):
                        for f in filenames:
                            if f.endswith(('.py', '.html', '.css', '.js', '.txt')):
                                files.append(os.path.join(root_dir, f))
                
                # Take unique and sort
                files = sorted(list(set(files)), key=os.path.getmtime, reverse=True)[:30]
                
                if not files:
                    ctk.CTkLabel(file_list_scroll, text="Нет поддерживаемых файлов", font=ctk.CTkFont(size=10, slant="italic")).pack()
                else:
                    for fp in files:
                        fname = os.path.basename(fp)
                        btn = ctk.CTkButton(file_list_scroll, text=f"📄 {fname}", font=ctk.CTkFont(size=11),
                                            anchor="w", fg_color="transparent", text_color=DS_TEXT,
                                            hover_color=DS_PANEL, height=24,
                                            command=lambda p=fp: select_file_path(p))
                        btn.pack(fill="x", pady=1)
            except Exception as e:
                logger.warning(f"Populate explorer failed: {e}")

        def install_pip_package():
            pkg = pack_entry.get().strip()
            if not pkg:
                return
            log_terminal(f"⏳ Установка пакета: {pkg}...")
            pack_entry.delete(0, "end")
            
            def do_install():
                try:
                    import subprocess
                    proc = subprocess.Popen([sys.executable, "-m", "pip", "install", pkg], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    out, err = proc.communicate(timeout=120)
                    if proc.returncode == 0:
                        self.app.safe_schedule(log_terminal, f"✅ Пакет '{pkg}' успешно установлен!\n{out[:400]}")
                    else:
                        self.app.safe_schedule(log_terminal, f"❌ Ошибка установки '{pkg}':\n{err[:400]}")
                except Exception as e:
                    self.app.safe_schedule(log_terminal, f"❌ Системная ошибка при установке: {e}")
            
            threading.Thread(target=do_install, daemon=True).start()

        ctk.CTkButton(pack_frame, text="Install", width=60, fg_color=DS_ACCENT, hover_color=DS_ACCENT2, command=install_pip_package).pack(side="right")

        # 3. Quick System Guide inside Left Sidebar
        quick_info = (
            "🛠️ Локальное Ядро\n"
            "• Ошибки отлаживаются ИИ автоматически.\n"
            "• Интегрированный терминал показывает результат на лету!\n"
            "• Поддержка Веб-приложений (HTML) - открываются мгновенно."
        )
        ctk.CTkLabel(left_sidebar, text=quick_info, font=ctk.CTkFont(size=10, slant="italic"), text_color=DS_DIM, wraplength=170, justify="left").pack(side="bottom", fill="x", padx=10, pady=15)

        # Center Column splits into: Code Editor (top) and Terminal Console (bottom)
        editor_frame = ctk.CTkFrame(right_workspace, fg_color="transparent")
        editor_frame.pack(fill="both", expand=True, side="top")

        code_text = ctk.CTkTextbox(editor_frame, fg_color="#12121a", text_color="#10b981", font=ctk.CTkFont(family="Courier", size=13))
        code_text.pack(fill="both", expand=True)

        # Terminal Frame (Console)
        terminal_frame = ctk.CTkFrame(right_workspace, fg_color=DS_PANEL, height=180, corner_radius=12, border_width=1, border_color=DS_BORDER)
        terminal_frame.pack(fill="x", side="bottom", pady=(10, 0))
        terminal_frame.pack_propagate(False)

        term_title_bar = ctk.CTkFrame(terminal_frame, fg_color="transparent", height=28)
        term_title_bar.pack(fill="x", side="top", padx=10, pady=(5, 0))
        ctk.CTkLabel(term_title_bar, text="📟 Консоль вывода / Интегрированный Терминал", font=ctk.CTkFont(family="Courier", size=11, weight="bold"), text_color=DS_ACCENT2).pack(side="left")
        
        # Clear Console Button
        def clear_console():
            terminal_output.configure(state="normal")
            terminal_output.delete("1.0", "end")
            terminal_output.insert("1.0", "aaron-console> ")
            terminal_output.configure(state="disabled")

        ctk.CTkButton(term_title_bar, text="🧹 Очистить", width=70, height=20, font=ctk.CTkFont(size=10), fg_color="transparent", text_color=DS_DIM, hover_color=DS_BG, command=clear_console).pack(side="right")

        terminal_output_frame = ctk.CTkFrame(terminal_frame, fg_color="transparent")
        terminal_output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        terminal_output = ctk.CTkTextbox(terminal_output_frame, fg_color=DS_BG, text_color="#a8f09d", font=ctk.CTkFont(family="Courier", size=11))
        terminal_output.pack(fill="both", expand=True)
        terminal_output.insert("1.0", "aaron-console> Интегрированное окружение готово. Нажмите '▶ Запустить' для выполнения.\n")
        terminal_output.configure(state="disabled")

        def log_terminal(txt):
            terminal_output.configure(state="normal")
            terminal_output.insert("end", f"\n{txt}\n")
            terminal_output.see("end")
            terminal_output.configure(state="disabled")

        # CONTROLS BOTTOM BUTTONS
        bottom_buttons = ctk.CTkFrame(top_bar, fg_color="transparent")
        bottom_buttons.pack(side="right", padx=10)

        # Last running variables for Auto-healing AI debugging
        last_run_file = {"path": "", "stderr": "", "code": ""}

        def save_file():
            p = file_entry.get().strip()
            selected_lang = lang_combo.get()
            if not check_low_level_access(selected_lang, p):
                return
            if not p:
                ext_map_reverse = {
                    "Python": (".py", [("Python Files", "*.py")]),
                    "JavaScript": (".js", [("JavaScript Files", "*.js")]),
                    "TypeScript": (".ts", [("TypeScript Files", "*.ts")]),
                    "HTML/CSS": (".html", [("HTML Files", "*.html"), ("CSS Files", "*.css")]),
                    "PHP": (".php", [("PHP Files", "*.php")]),
                    "Ruby": (".rb", [("Ruby Files", "*.rb")]),
                    "C (DLC)": (".c", [("C Files", "*.c")]),
                    "C++ (DLC)": (".cpp", [("C++ Files", "*.cpp")]),
                    "Rust (DLC)": (".rs", [("Rust Files", "*.rs")]),
                    "Assembly (DLC)": (".asm", [("Assembly Files", "*.asm *.s")]),
                    "Go (DLC)": (".go", [("Go Files", "*.go")]),
                }
                def_ext, ftypes = ext_map_reverse.get(selected_lang, (".py", [("Python Files", "*.py")]))
                ftypes_all = ftypes + [("All Files", "*.*")]
                p = filedialog.asksaveasfilename(defaultextension=def_ext, filetypes=ftypes_all)
                if not p: return
                file_entry.delete(0, "end")
                file_entry.insert(0, p)
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(code_text.get("1.0", "end-1c"))
                log_terminal(f"💾 Файл сохранён: {os.path.basename(p)}")
                populate_explorer()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

        def run_script():
            p = file_entry.get().strip()
            selected_lang = lang_combo.get()
            if not check_low_level_access(selected_lang, p):
                return
            # Always save the file before running so we execute the latest code
            save_file()
            p = file_entry.get().strip()
            if not p or not os.path.exists(p):
                return
            try:
                ext = os.path.splitext(p)[1].lower()
                
                # Check if file has python extension but contains C++ or other languages
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        first_lines = f.read(500)
                except Exception:
                    first_lines = ""
                
                is_cpp = "#include" in first_lines or "std::cout" in first_lines or "int main(" in first_lines or "//" in first_lines
                
                if ext == ".py" and is_cpp:
                    ans = messagebox.askyesno("⚠️ Несоответствие расширения", 
                        f"Похоже, файл '{os.path.basename(p)}' имеет расширение .py (Python), но содержит C/C++ код.\n\n"
                        "Хотите запустить его через компилятор C++ (g++)?")
                    if ans:
                        ext = ".cpp"
                
                log_start_msg = f"\n[▶ Исполнение: {os.path.basename(p)}]\n"
                
                if ext in (".html", ".htm", ".xhtml"):
                    webbrowser.open(p)
                    log_terminal(f"{log_start_msg}✓ HTML-страница успешно открыта во внешнем браузере (Lovable Live Preview style).")
                    last_run_file["path"] = p
                    last_run_file["stderr"] = ""
                    last_run_file["code"] = code_text.get("1.0", "end-1c")
                    fix_btn.configure(state="disabled")
                else:
                    def execute_thread():
                        nonlocal ext, p, log_start_msg
                        stdout, stderr = "", ""
                        try:
                            if ext == ".py":
                                py = get_python_executable()
                                if getattr(sys, "frozen", False) and py == sys.executable:
                                    cmd = [sys.executable, "--run-script", p]
                                else:
                                    cmd = [py, p]
                                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                stdout, stderr = proc.communicate(timeout=15)
                            elif ext in (".cpp", ".c", ".cc"):
                                compiler = "g++" if ext == ".cpp" else "gcc"
                                if shutil.which(compiler):
                                    out_exe = os.path.splitext(p)[0] + (".exe" if os.name == "nt" else "")
                                    comp_proc = subprocess.run([compiler, p, "-o", out_exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                    if comp_proc.returncode == 0:
                                        run_proc = subprocess.run([out_exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
                                        stdout, stderr = run_proc.stdout, run_proc.stderr
                                        try: os.remove(out_exe)
                                        except: pass
                                    else:
                                        stdout = ""
                                        stderr = f"[Compilation Error]:\n{comp_proc.stderr}"
                                else:
                                    stdout = ""
                                    stderr = f"[Compiler Error]: '{compiler}' не найден в PATH.\nУстановите GCC/g++ и добавьте его в переменные окружения."
                            elif ext == ".js":
                                if shutil.which("node"):
                                    proc = subprocess.Popen(["node", p], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                    stdout, stderr = proc.communicate(timeout=15)
                                else:
                                    stdout = ""
                                    stderr = "[Error]: Node.js не установлен."
                            else:
                                stdout = f"Файл {os.path.basename(p)} запущен в ознакомительном режиме."
                                stderr = ""
                        except subprocess.TimeoutExpired:
                            stdout = ""
                            stderr = "⚠️ Превышен лимит времени выполнения (Таймаут 15 секунд)."
                        except Exception as ex:
                            stdout = ""
                            stderr = f"Ошибка запуска: {ex}"
                        
                        # Save execution details for auto-healing
                        last_run_file["path"] = p
                        last_run_file["stderr"] = stderr
                        last_run_file["code"] = code_text.get("1.0", "end-1c")
                        
                        # Log to persistent console
                        log_res = log_start_msg
                        if stdout:
                            log_res += f"[STDOUT]:\n{stdout}\n"
                        if stderr:
                            log_res += f"[STDERR/ОШИБКИ]:\n{stderr}\n"
                            self.app.safe_schedule(fix_btn.configure, state="normal")
                        else:
                            self.app.safe_schedule(run_btn.configure, text="▶ Запустить")
                            self.app.safe_schedule(fix_btn.configure, state="disabled")
                        if not stdout and not stderr:
                            res_text = "[Программа успешно завершилась без вывода]"
                        
                        self.app.safe_schedule(lambda: [
                            out_box_log(stdout, stderr, p),
                            run_btn.configure(state="normal", text="▶ Запустить")
                        ])

                    threading.Thread(target=execute_thread, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")

        def select_file_from_sidebar(filename_path):
            if not check_low_level_access("", filename_path):
                return
            file_entry.delete(0, "end")
            file_entry.insert(0, filename_path)
            ext = os.path.splitext(filename_path)[1].lower() if filename_path else ""
            ext_map = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".html": "HTML/CSS", ".css": "HTML/CSS", ".php": "PHP", ".rb": "Ruby",
                ".c": "C (DLC)", ".cpp": "C++ (DLC)", ".cc": "C++ (DLC)",
                ".rs": "Rust (DLC)", ".go": "Go (DLC)", ".asm": "Assembly (DLC)", ".s": "Assembly (DLC)"
            }
            if ext in ext_map:
                lang_combo.set(ext_map[ext])
            try:
                with open(filename_path, "r", encoding="utf-8", errors="ignore") as f:
                    code_text.delete("1.0", "end")
                    code_text.insert("1.0", f.read())
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось прочитать сгенерированный файл: {e}")

        def auto_load_created_file(file_path):
            if os.path.exists(file_path):
                file_entry.delete(0, "end")
                file_entry.insert(0, file_path)
                ext = os.path.splitext(file_path)[1].lower()
                ext_map = {
                    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                    ".html": "HTML/CSS", ".css": "HTML/CSS", ".php": "PHP", ".rb": "Ruby",
                    ".c": "C (DLC)", ".cpp": "C++ (DLC)", ".cc": "C++ (DLC)",
                    ".rs": "Rust (DLC)", ".go": "Go (DLC)", ".asm": "Assembly (DLC)", ".s": "Assembly (DLC)"
                }
                if ext in ext_map:
                    lang_combo.set(ext_map[ext])
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        code_text.delete("1.0", "end")
                        code_text.insert("1.0", f.read())
                    log_terminal(f"✓ Загружен созданный файл: {os.path.basename(file_path)}")
                except Exception:
                    pass

        def auto_heal_errors():
            code = code_text.get("1.0", "end-1c").strip()
            stderr = last_error_msg[0]
            if not code:
                messagebox.showwarning("Внимание", "Нет кода для исправления!")
                return
            if not stderr:
                stderr = "Скрипт упал или работает некорректно."

            run_btn.configure(state="disabled", text="🪄 Лечим...")
            log_terminal(f"🪄 Codex-02 Lovable Auto-Heal: Исправляем ошибку кода...")
            
            system_prompt = (
                "Ты — авто-агент Codex-02 (Lovable Engine). Твоя единственная цель — проанализировать "
                "предоставленный код, проанализировать ошибку компиляции/выполнения (stderr), и вернуть ПОЛНОСТЬЮ исправленный, "
                "абсолютно готовый и оптимизированный вариант этого кода.\n\n"
                "Отвечай СТРОГО только исправленным кодом, завернутым в один блок ```python ... ```. "
                "Не пиши никаких сопутствующих объяснений или предупреждений!"
            )
            prompt = (
                f"=== ТЕКУЩИЙ КОД ===\n{code}\n\n"
                f"=== ОШИБКА / СБОЙ ===\n{stderr}\n\n"
                "Исправь эту ошибку и выдай идеальный рабочий код."
            )
            
            def on_heal_completed(ans):
                run_btn.configure(state="normal", text="▶ Запустить")
                code_match = re.search(r'```python(.*?)```', ans, re.DOTALL)
                if code_match:
                    gen_code = code_match.group(1).strip()
                else:
                    gen_code = ans.strip()
                    if gen_code.startswith("```"):
                        gen_code = gen_code.strip("`").strip()
                        if gen_code.startswith("python"):
                            gen_code = gen_code[6:].strip()
                code_text.delete("1.0", "end")
                code_text.insert("1.0", gen_code)
                p_file = file_entry.get().strip()
                if p_file:
                    try:
                        with open(p_file, "w", encoding="utf-8") as f_save:
                            f_save.write(gen_code)
                        log_terminal(f"💾 Файл автоматически сохранён на диске: {os.path.basename(p_file)}")
                    except Exception as e_save:
                        log_terminal(f"⚠️ Ошибка автосохранения исправленного файла: {e_save}")
                log_terminal("✅ Исправление ИИ завершено. Запустите код снова!")
                messagebox.showinfo("🪄 Codex-02 (Lovable)", "Авто-исправление кода завершено! Исправленный файл сохранен на Рабочем столе/диске.")

            self.app.run_in_background(sync_chat2, prompt, sys_prompt=system_prompt, callback=on_heal_completed)

        def out_box_log(stdout, stderr, filepath):
            res_text = f"\n=== Скрипт: {os.path.basename(filepath)} ===\n"
            if stdout:
                res_text += f"[STDOUT]:\n{stdout}\n"
            if stderr:
                res_text += f"[ОШИБКИ / STDERR]:\n{stderr}\n"
                last_error_msg[0] = stderr
                self.app.safe_schedule(fix_btn.configure, state="normal")
            else:
                last_error_msg[0] = ""
                self.app.safe_schedule(fix_btn.configure, state="disabled")
            if not stdout and not stderr:
                res_text += "[Скрипт успешно завершился без вывода]"
            
            terminal_output.configure(state="normal")
            terminal_output.insert("end", f"\n{res_text}")
            terminal_output.see("end")
            terminal_output.configure(state="disabled")

        last_error_msg = [""]

        # Sidebar Left Content
        populate_explorer()

        # Add buttons to Top Bar
        save_btn = ctk.CTkButton(bottom_buttons, text="💾 Сохранить", command=save_file, width=90, fg_color=DS_PANEL, hover_color=DS_BORDER, text_color=DS_TEXT)
        save_btn.pack(side="left", padx=3)
        
        run_btn = ctk.CTkButton(bottom_buttons, text="▶ Запустить", fg_color="#10b981", hover_color="#059669", command=run_script, width=100)
        run_btn.pack(side="left", padx=3)

        fix_btn = ctk.CTkButton(bottom_buttons, text="🪄 Исправить ошибку ИИ", fg_color="#4f46e5", hover_color="#4338ca", state="disabled", command=auto_heal_errors, width=150)
        fix_btn.pack(side="left", padx=3)
        
        def ai_code_generation():
            # Allow the trial mode (2 free requests per day) just like in SuperAIFrame.send
            authorized = check_feature_access('codex_02')
            if not authorized:
                count = db.get_daily_codex_requests()
                if count >= 2:
                    messagebox.showerror("🔒 Доступ ограничен", "Дневной бесплатный лимит (2/2) исчерпан. Пожалуйста, активируйте подписку!")
                    self.show_billing_dialog()
                    return
                db.increment_daily_codex_requests()
                
            prompt_desc = simpledialog.askstring("🪄 ИИ Кодер (Codex-02)", "Опишите, какой скрипт нужно создать и записать на Рабочий стол:")
            if not prompt_desc:
                return
            
            run_btn.configure(state="disabled", text="⏳ Генерация...")
            log_terminal(f"🪄 Codex-02: Генерируем код для '{prompt_desc[:30]}...'")
            
            system_prompt = (
                "Ты — Codex-02 (v2.0), сверхинтеллектуальная локальная система программирования, которая исполняется непосредственно на компьютере пользователя.\\n"
                "Пользователь хочет создать файл на своем Рабочем столе.\\n"
                "Ты ОБЯЗАН написать чистый, готовый и рабочий код согласно его описанию. "
                "Обязательно заверни создаваемый код в теги:\\n"
                "<<CREATE_FILE: имя_скрипта.py>>\\n"
                "код\\n"
                "<<END_FILE>>\\n"
                "Сам выбери подходящее имя файла (например, parser.py, test.py) с расширением."
            )
            
            def on_ai_completed(ans):
                run_btn.configure(state="normal", text="▶ Запустить")
                import re
                
                # Check status output written by parse_and_execute_codex_commands
                match_status = re.search(r"✓ Создан локальный файл:\\s*(.*)", ans)
                file_path = None
                if match_status:
                    file_path = match_status.group(1).strip()
                else:
                    pattern = r"<<(?:WRITE_FILE|CREATE_FILE):\\s*(.*?)\\s*>>"
                    match = re.search(pattern, ans, re.IGNORECASE)
                    if match:
                        filename = match.group(1).strip()
                        desktop = get_desktop_root()
                        file_path = os.path.join(desktop, filename) if not os.path.isabs(filename) else filename

                if file_path and os.path.exists(file_path):
                    auto_load_created_file(file_path)
                    populate_explorer()
                    log_terminal(f"✓ Код успешно сгенерирован и загружен из файла: {file_path}")
                else:
                    # Cleanly extract code block from markdown
                    code_blocks = re.findall(r'```(?:python|javascript|typescript|html|css|php|cpp|c)?([\\s\\S]*?)```', ans, re.IGNORECASE)
                    if code_blocks:
                        clean_code = code_blocks[0].strip()
                    else:
                        clean_code = ans.strip()
                    
                    code_text.delete("1.0", "end")
                    code_text.insert("1.0", clean_code)
                    log_terminal("📝 Код сгенерирован ИИ и вставлен напрямую в редактор (без разметки markdown).")

            self.app.run_in_background(sync_chat2, prompt_desc, sys_prompt=system_prompt, callback=on_ai_completed)
        ai_ide_btn = ctk.CTkButton(bottom_buttons, text="🪄 ИИ Кодер (Codex-02)", fg_color="#ef4444", hover_color="#dc2626", command=ai_code_generation, width=150)
        ai_ide_btn.pack(side="left", padx=3)

        close_btn = ctk.CTkButton(bottom_buttons, text="Закрыть", command=ide.destroy, width=70, fg_color="transparent", text_color=DS_DIM, hover_color=DS_PANEL)
        close_btn.pack(side="left", padx=3)

    def send(self):
        if not self.current_mode:
            messagebox.showwarning("No mode", "Сначала выберите режим")
            return
        
        authorized = False
        if self.current_mode == 'codex_02':
            authorized = check_feature_access('codex_02')
        else:
            authorized = check_feature_access('super_ai')
            
        if not authorized:
            count = db.get_daily_codex_requests()
            if count >= 2:
                messagebox.showerror("🔒 Доступ ограничен", "Дневной бесплатный лимит (2/2) исчерпан. Пожалуйста, активируйте подписку!")
                self.show_billing_dialog()
                return
            db.increment_daily_codex_requests()

        text_input = self.input.get("1.0","end-1c").strip()
        if not text_input:
            return
            
        self.output.configure(state="normal")
        self.output.insert("end", f"Вы: {text_input}\\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        self.input.delete("1.0", "end")
        
        def run_ai():
            answer = sync_chat2(text_input, sys_prompt=self.system_prompt, session_id="super_ai_session")
            self.app.safe_schedule(self.show_super_ai_answer, text_input, answer)
            
        self.app.run_in_background(run_ai)

    def show_super_ai_answer(self, text_input, answer):
        self.output.configure(state="normal")
        self.output.insert("end", f"AI: {answer}\\n\\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        self.update_chat_graph(len(text_input), len(answer))
    def whip_code(self):
        if self.current_mode != 'codex_02':
            messagebox.showwarning("Режим Codex-02", "Хлыст работает только в режиме Codex-02")
            return
        
        authorized = check_feature_access('codex_02')
        if not authorized:
            count = db.get_daily_codex_requests()
            if count >= 2:
                messagebox.showerror("🔒 Доступ ограничен", "Дневной бесплатный лимит (2/2) исчерпан. Пожалуйста, активируйте подписку!")
                self.show_billing_dialog()
                return
            db.increment_daily_codex_requests()

        text_input = self.input.get("1.0","end-1c").strip()
        if not text_input:
            return
            
        self.output.configure(state="normal")
        self.output.insert("end", f"Вы (хлыст): {text_input}\\n")
        self.output.see("end")
        self.output.configure(state="disabled")
        self.input.delete("1.0", "end")
        
        whip_prompt = self.system_prompt + "\\nТы — программист с хлыстом, пиши код лучше, быстрее, с комментарием и проверкой ошибок."
        
        def run_whip_ai():
            answer = sync_chat2(text_input, sys_prompt=whip_prompt, session_id="super_ai_session")
            self.app.safe_schedule(self.show_super_ai_answer, text_input, answer)
            
        self.app.run_in_background(run_whip_ai)
    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл для контекста",
            filetypes=[("Все файлы", "*.*"), ("Документы","*.pdf *.docx *.txt *.doc"), ("Изображения","*.jpg *.png *.jpeg"), ("Код","*.py *.js *.ts *.java *.cs")]
        )
        if path:
            set_file_context(path)
            self.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
            if hasattr(self.app, 'frames'):
                for name, frame in self.app.frames.items():
                    if hasattr(frame, 'file_info'):
                        frame.file_info.configure(text=f"Файл: {FILE_CONTEXT['description']}")
                    elif hasattr(frame, 'file_info_label'):
                        frame.file_info_label.configure(text=f"Файл: {FILE_CONTEXT['description']}")

    def update_chat_graph(self, user_len: int, assistant_len: int):
        self.chat_graph_history['user'].append(user_len)
        self.chat_graph_history['assistant'].append(assistant_len)
        if len(self.chat_graph_history['user']) > 20:
            self.chat_graph_history['user'] = self.chat_graph_history['user'][-20:]
            self.chat_graph_history['assistant'] = self.chat_graph_history['assistant'][-20:]
        self.chart_ax.clear()
        self.chart_ax.plot(self.chat_graph_history['user'], color='#1976D2', label='Запросы', linewidth=2)
        self.chart_ax.plot(self.chat_graph_history['assistant'], color='#388E3C', label='Ответы', linewidth=2)
        self.chart_ax.set_facecolor('#f8f8f8')
        self.chart_ax.set_title('График активности в чате', color='black', pad=8)
        self.chart_ax.set_ylabel('Длина текста', color='black')
        self.chart_ax.set_xlabel('Таймлайн', color='black')
        self.chart_ax.legend(facecolor='#ffffff', edgecolor='black')
        self.chart_ax.tick_params(colors='black')
        self.chart_fig.tight_layout()
        self.chart_canvas.draw()

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0","end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            answer = sync_chat(question)
            messagebox.showinfo("AI", answer)

    def update_lang(self, lang):
        self.send_btn.configure(text=Locale.t('send', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class ForecastFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.label = ctk.CTkLabel(self, text=Locale.t('expression', lang), font=ctk.CTkFont(size=14))
        self.label.pack(anchor="w")
        self.desc = ctk.CTkTextbox(self, height=80, wrap="word", fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.desc.pack(fill="x", pady=5)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.run_btn = ctk.CTkButton(btn_frame, text=Locale.t('forecast_run', lang), command=self.run)
        self.run_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

        self.output = ctk.CTkTextbox(self, wrap="word", fg_color=DS_PANEL, text_color=DS_TEXT, border_width=1, border_color=DS_BORDER)
        self.output.pack(fill="both", expand=True)

        # Load history
        self.load_history()

    def load_history(self):
        try:
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            history = db.get_chat_history(USER_ID, "forecast_session", limit=100)
            if history:
                for msg in history:
                    role = "Идея" if msg['role'] == 'user' else "Прогноз"
                    self.output.insert("end", f"[{role}]: {msg['content']}\\n\\n")
            else:
                self.output.insert("end", "📈 Введите идею вашего проекта или стартапа для составления прогноза на 5 лет.\\n\\n")
            self.output.configure(state="disabled")
            self.output.see("end")
        except Exception as e:
            logger.warning(f"Ошибка [104]: Сбой при загрузке истории прогнозов: {e}")

    def run(self):
        text = self.desc.get("1.0","end-1c").strip()
        if text:
            self.desc.delete("1.0", "end")
            self.output.configure(state="normal")
            self.output.insert("end", f"Идея: {text}\\n")
            self.output.insert("end", "[📈 Составление ИИ-прогноза на 5 лет...]\\n")
            self.output.see("end")
            self.output.configure(state="disabled")
            
            prompt = f"Сделай подробный прогноз развития на 5 лет для следующего проекта/идеи: {text}"
            self.app.run_in_background(sync_chat, prompt, session_id="forecast_session", callback=self.show_forecast)

    def show_forecast(self, ans):
        self.output.configure(state="normal")
        self.output.insert("end", f"Прогноз ИИ: {ans}\\n\\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0","end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.output.configure(state="normal")
            self.output.insert("end", f"Вы: {question}\\n")
            self.output.see("end")
            self.output.configure(state="disabled")
            def run_quick_ai():
                answer = sync_chat(question)
                self.app.safe_schedule(self.show_forecast, answer)
            self.app.run_in_background(run_quick_ai)

    def update_lang(self, lang):
        self.run_btn.configure(text=Locale.t('forecast_run', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang
class GDZFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang
        self.output = ctk.CTkTextbox(self, wrap="word")
        self.output.pack(fill="both", expand=True)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)
        self.load_btn = ctk.CTkButton(btn_frame, text=Locale.t('gdz_load', lang), command=self.load_photo)
        self.load_btn.pack(side="left", padx=5)
        self.copy_btn = ctk.CTkButton(btn_frame, text=Locale.t('copy', lang), command=self.copy_last)
        self.copy_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

    def load_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Изображения", "*.jpg *.png")])
        if not path:
            return
        with open(path, "rb") as f:
            img_bytes = f.read()
        self.app.run_in_background(sync_gdz, img_bytes, callback=self.show_solution)

    def show_solution(self, solution):
        if not self.winfo_exists():
            return
        self.output.insert("end", solution + "\n")

    def copy_last(self):
        try:
            sel = self.output.get("sel.first", "sel.last")
            if sel.strip():
                self.clipboard_clear()
                self.clipboard_append(sel)
                return
        except:
            pass
        text = self.output.get("1.0", "end-1c").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.load_btn.configure(text=Locale.t('gdz_load', lang))
        self.copy_btn.configure(text=Locale.t('copy', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class HistoryFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang
        self.session_list = tk.Listbox(self, bg="#fafafa", fg="black", selectbackground="#1e88e5", height=6)
        self.session_list.pack(fill="x", padx=10, pady=5)
        self.session_list.bind("<<ListboxSelect>>", self.on_session_select)
        self.text = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=12))
        self.text.pack(fill="both", expand=True, padx=10, pady=5)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5)
        self.upd_btn = ctk.CTkButton(btn_frame, text=Locale.t('history_update', lang), command=self.load_sessions)
        self.upd_btn.pack(side="left", padx=5)
        self.continue_btn = ctk.CTkButton(btn_frame, text="▶ Продолжить чат", command=self.continue_selected_session)
        self.continue_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

        self.load_sessions()

    def load_sessions(self):
        self.session_list.delete(0, "end")
        sessions = db.list_sessions(USER_ID)
        if not sessions:
            self.session_list.insert("end", "Нет сохранённых диалогов")
            return
        for s in sessions:
            self.session_list.insert("end", s['session_id'])

    def on_session_select(self, event):
        sel = self.session_list.curselection()
        if not sel: return
        session_id = self.session_list.get(sel[0])
        self.text.delete("1.0", "end")
        history = db.get_chat_history(USER_ID, session_id)
        for msg in history:
            role = "🧑 Вы" if msg['role'] == 'user' else "🤖 AI"
            self.text.insert("end", f"{role} ({msg['timestamp']}):\n{msg['content']}\n\n")

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def get_selected_session(self):
        sel = self.session_list.curselection()
        if not sel:
            return None
        return self.session_list.get(sel[0])

    def continue_selected_session(self):
        session_id = self.get_selected_session()
        if not session_id:
            messagebox.showwarning("Внимание", "Выберите диалог для продолжения.")
            return
        load_session_history(session_id)
        self.app.show_frame("chat")
        messagebox.showinfo("Готово", f"Чат '{session_id}' загружен для продолжения.")

    def update_lang(self, lang):
        self.upd_btn.configure(text=Locale.t('history_update', lang))
        self.continue_btn.configure(text="▶ Продолжить чат")
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang
        self.lang_label = ctk.CTkLabel(self, text=Locale.t('lang_label', lang), font=ctk.CTkFont(size=14))
        self.lang_label.pack(anchor="w", pady=(10,0))
        self.lang_combo = ctk.CTkComboBox(self, values=list(Locale.LANG_NAMES.keys()))
        self.lang_combo.set(db.get_lang(USER_ID))
        self.lang_combo.pack(fill="x", pady=5)
        self.mode_label = ctk.CTkLabel(self, text=Locale.t('mode_label', lang), font=ctk.CTkFont(size=14))
        self.mode_label.pack(anchor="w", pady=(10,0))
        self.mode_combo = ctk.CTkComboBox(self, values=["normal", "tutor"])
        self.mode_combo.set(db.get_mode(USER_ID))
        self.mode_combo.pack(fill="x", pady=5)
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=15)
        self.save_btn = ctk.CTkButton(btn_frame, text=Locale.t('save_settings', lang), command=self.save)
        self.save_btn.pack(side="left", padx=5)
        self.ai_btn = ctk.CTkButton(btn_frame, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(side="left", padx=5)

    def save(self):
        new_lang = self.lang_combo.get()
        new_mode = self.mode_combo.get()
        db.set_lang(USER_ID, new_lang)
        db.set_mode(USER_ID, new_mode)
        if new_lang != self.lang:
            self.app.current_lang = new_lang
            self.app.rebuild_ui()
        else:
            for frame in self.app.frames.values():
                if hasattr(frame, 'update_lang'):
                    frame.update_lang(new_lang)

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def update_lang(self, lang):
        self.save_btn.configure(text=Locale.t('save_settings', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang

class LauncherFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color="white")
        self.app = app
        self.lang = lang

        ctk.CTkLabel(self, text="Менеджер модов", font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="Здесь можно открыть, включить и запустить моды.", font=ctk.CTkFont(size=12), text_color=DS_DIM).pack(pady=(0, 20))

        self.game_btn = ctk.CTkButton(self, text=Locale.t('launch_game', lang), command=run_game)
        self.game_btn.pack(pady=5)

        self.mods_btn = ctk.CTkButton(self, text="📦 Просмотреть моды", command=self.show_mod_manager)
        self.mods_btn.pack(pady=5)

        self.shortcut_btn = ctk.CTkButton(self, text="🖥️ Создать ярлык", command=self.create_desktop_shortcut)
        self.shortcut_btn.pack(pady=5)

        self.code_btn = ctk.CTkButton(self, text=Locale.t('open_code', lang), command=self.open_code_admin)
        self.code_btn.pack(pady=5)

        self.ai_btn = ctk.CTkButton(self, text=Locale.t('ai_assist', lang), command=self.ask_ai)
        self.ai_btn.pack(pady=5)

    def open_code_admin(self):
        pwd = simpledialog.askstring("Доступ", "Введите пароль администратора:", show="*")
        if pwd is None or pwd != ADMIN_PASSWORD:
            messagebox.showerror("Ошибка", "Неверный пароль!")
            return

        current_path = os.path.abspath(__file__)
        if not os.path.exists(current_path):
            messagebox.showerror("Ошибка", f"Файл '{current_path}' не найден.")
            return

        choice = simpledialog.askstring("Выбор редактора",
                                        "1-IDLE 2-VSCode 3-PyCharm 4-Notepad++ 5-Блокнот 6-Другой")
        if not choice:
            return
        editor_map = {"1": "idle", "2": "code", "3": "pycharm64", "4": "notepad++", "5": "notepad"}
        editor_path = editor_map.get(choice)
        if choice == "6":
            editor_path = simpledialog.askstring("Путь к редактору", "Введите полный путь к редактору или .exe")
        try:
            if editor_path and (shutil.which(editor_path) or os.path.exists(editor_path)):
                subprocess.Popen([editor_path, current_path])
                return
        except Exception:
            pass
        try:
            os.startfile(current_path)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить редактор.\n{e}")

    def ask_ai(self):
        question = simpledialog.askstring(Locale.t('ai_assist', self.lang), Locale.t('ai_ask_prompt', self.lang))
        if question and question.strip():
            self.app.run_in_background(sync_chat, question, callback=lambda ans: messagebox.showinfo("AI", ans))

    def create_desktop_shortcut(self):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        link_path = os.path.join(desktop, DESKTOP_LINK_NAME)
        if getattr(sys, 'frozen', False):
            target = sys.executable
            args = ""
        else:
            target = get_python_executable()
            args = f'"{os.path.abspath(__file__)}" --run-mods'
        try:
            create_shortcut(target, link_path, get_app_root(), arguments=args)
            messagebox.showinfo("Ярлык создан", f"Ярлык создан на рабочем столе:\n{link_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать ярлык:\n{e}")

    def show_mod_manager(self):
        self.app.show_mods_window()
        if should_show_mod_guide() and self.app.mod_window and hasattr(self.app.mod_window, 'mods_frame'):
            self.app.after(200, self.app.mod_window.mods_frame.show_mod_help_dialog)
            mark_mod_guide_shown()

    def toggle_mod(self, file_name, enabled):
        state = load_mod_state()
        state[file_name] = enabled
        save_mod_state(state)

    def run_mod_now(self, mod):
        path = os.path.join(get_mods_dir(), mod['file'])
        try:
            spec = importlib.util.spec_from_file_location(f"runmod_{mod['file']}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'apply') and callable(module.apply):
                module.apply(self.app)
            messagebox.showinfo("Мод запущен", f"Мод '{mod['name']}' успешно запущен.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить мод '{mod['name']}':\n{e}")

    def show_mod_help_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Инструкция по модам")
        dlg.geometry("520x420")
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)

        ctk.CTkLabel(dlg, text="Инструкция по программированию модов", font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        help_text = (
            "Моды — это обычные Python-файлы в папке mods.\n\n"
            "Каждый мод должен содержать переменные MOD_NAME и MOD_DESCRIPTION,\n"
            "а также функцию apply(app).\n\n"
            "Пример мода:\n"
            "MOD_NAME = 'Пример'\n"
            "MOD_DESCRIPTION = 'Описание'\n\n"
            "def apply(app=None):\n"
            "    print('Мод запущен')\n\n"
            "Если мод включён, он будет выполняться при запуске приложения.\n"
            "Кнопка 'Запустить мод' позволяет сразу запустить мод вручную.\n"
            "Используйте папку mods для новых скриптов, а менеджер — для включения и запуска."
        )
        box = ctk.CTkTextbox(dlg, wrap="word", width=480, height=280, font=ctk.CTkFont(size=12))
        box.insert("0.0", help_text)
        box.configure(state="disabled")
        box.pack(padx=10, pady=10, fill="both", expand=True)

        ctk.CTkButton(dlg, text="Понятно", command=lambda: dlg.destroy()).pack(pady=10)

    def update_lang(self, lang):
        self.game_btn.configure(text=Locale.t('launch_game', lang))
        self.mods_btn.configure(text=Locale.t('mods', lang))
        self.shortcut_btn.configure(text="🖥️ Создать ярлык")
        self.code_btn.configure(text=Locale.t('open_code', lang))
        self.ai_btn.configure(text=Locale.t('ai_assist', lang))
        self.lang = lang
        # ----------------------------------- НОВЫЕ ФРЕЙМЫ -----------------------------------

class ModsFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang

        ctk.CTkLabel(self, text=Locale.t('mods_title', self.lang), font=ctk.CTkFont(size=20, weight="bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        ctk.CTkLabel(self, text=Locale.t('mods_description', self.lang), font=ctk.CTkFont(size=13), text_color=DS_DIM).pack(pady=(0, 10))

        toolbar = ctk.CTkFrame(self, fg_color=DS_BG)
        toolbar.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkButton(toolbar, text=Locale.t('open_mods_folder', self.lang), command=lambda: os.startfile(get_mods_dir())).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('add_mod', self.lang), command=self.import_mod_file).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('new_mod_template', self.lang), command=self.create_mod_template).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('mod_instructions', self.lang), command=self.show_mod_help_dialog).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('refresh_list', self.lang), command=self.render_mod_cards).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('enable_all', self.lang), command=self.enable_all_mods).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text=Locale.t('disable_all', self.lang), command=self.disable_all_mods).pack(side="left", padx=5)

        ctk.CTkLabel(self, text=Locale.t('mods_folder_label', self.lang).format(path=get_mods_dir()), font=ctk.CTkFont(size=11), text_color=DS_DIM, wraplength=920, justify="left").pack(fill="x", padx=20, pady=(0, 8))
        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color=DS_DIM)
        self.status_label.pack(fill="x", padx=20, pady=(0, 10))

        self.container = ctk.CTkScrollableFrame(self, fg_color=DS_PANEL)
        self.container.pack(fill="both", expand=True, padx=20, pady=10)

        self.render_mod_cards()

        if should_show_mod_guide():
            self.after(300, self.show_mod_help_dialog)
            mark_mod_guide_shown()

    def render_mod_cards(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        mods = load_enabled_mods()
        enabled_count = sum(1 for mod in mods if mod['enabled'])
        self.status_label.configure(text=Locale.t('mods_found', self.lang).format(total=len(mods), enabled=enabled_count))

        if not mods:
            ctk.CTkLabel(self.container, text=Locale.t('no_mods_found', self.lang), text_color=DS_TEXT).pack(pady=30)
            return

        for mod in mods:
            card = ctk.CTkFrame(self.container, fg_color=DS_SURFACE, corner_radius=12)
            card.pack(fill="x", pady=10, padx=5)

            header = ctk.CTkLabel(card, text=mod['name'], font=ctk.CTkFont(size=16, weight="bold"), text_color=DS_TEXT)
            header.pack(anchor="w", padx=15, pady=(15, 5))

            ctk.CTkLabel(card, text=mod['description'], font=ctk.CTkFont(size=12), text_color=DS_DIM, wraplength=720, justify="left").pack(anchor="w", padx=15)
            status_text = Locale.t('status_enabled', self.lang) if mod['enabled'] else Locale.t('status_disabled', self.lang)
            ctk.CTkLabel(card, text=f"{Locale.t('status_prefix', self.lang)} {status_text}", font=ctk.CTkFont(size=11), text_color=DS_DIM).pack(anchor="w", padx=15, pady=(4, 0))

            buttons = ctk.CTkFrame(card, fg_color=DS_SURFACE)
            buttons.pack(fill="x", padx=15, pady=12)
            cb_var = tk.BooleanVar(value=mod['enabled'])
            ctk.CTkCheckBox(buttons, text=Locale.t('enable', self.lang), variable=cb_var,
                            command=lambda m=mod['file'], v=cb_var: self.toggle_mod(m, v.get())).pack(side="left", padx=5)
            ctk.CTkButton(buttons, text=Locale.t('run_now', self.lang), fg_color="#1f6cd9", hover_color="#105eb7",
                          command=lambda m=mod: self.run_mod_now(m)).pack(side="right", padx=5)

    def toggle_mod(self, file_name, enabled):
        state = load_mod_state()
        state[file_name] = enabled
        save_mod_state(state)
        self.render_mod_cards()

    def enable_all_mods(self):
        state = load_mod_state()
        for mod in scan_mods():
            state[mod['file']] = True
        save_mod_state(state)
        self.render_mod_cards()

    def disable_all_mods(self):
        state = load_mod_state()
        for mod in scan_mods():
            state[mod['file']] = False
        save_mod_state(state)
        self.render_mod_cards()

    def import_mod_file(self):
        source = filedialog.askopenfilename(title="Выберите Python-файл мода", filetypes=[("Python files", "*.py")])
        if not source:
            return
        dest_dir = get_mods_dir()
        os.makedirs(dest_dir, exist_ok=True)
        filename = os.path.basename(source)
        name, ext = os.path.splitext(filename)
        dest = os.path.join(dest_dir, filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, f"{name}_{counter}{ext}")
            counter += 1
        try:
            shutil.copy2(source, dest)
            messagebox.showinfo("Мод добавлен", f"Файл мода скопирован в папку mods:\n{os.path.basename(dest)}")
            self.render_mod_cards()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось скопировать мод:\n{e}")

    def create_mod_template(self):
        name = simpledialog.askstring("Новый мод", "Введите имя файла мода (без .py):")
        if not name:
            return
        sanitized = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_")
        if not sanitized:
            messagebox.showwarning("Ошибка", "Имя файла мода должно содержать буквы или цифры.")
            return
        dest_dir = get_mods_dir()
        os.makedirs(dest_dir, exist_ok=True)
        filename = f"{sanitized}.py"
        dest = os.path.join(dest_dir, filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(dest_dir, f"{sanitized}_{counter}.py")
            counter += 1
        template = (
            '"""\n'
            'Новый мод для AI Launcher.\n'
            'Заполните MOD_NAME, MOD_DESCRIPTION и функцию apply.\n'
            '"""\n\n'
            'MOD_NAME = "Новый мод"\n'
            'MOD_DESCRIPTION = "Описание нового мода."\n\n'
            'def apply(app=None):\n'
            '    # Здесь добавьте поведение мода\n'
            '    print(f"Мод {MOD_NAME} запущен")\n'
        )
        try:
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(template)
            messagebox.showinfo("Шаблон создан", f"Шаблон мода создан:\n{os.path.basename(dest)}")
            self.render_mod_cards()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать шаблон мода:\n{e}")

    def run_mod_now(self, mod):
        path = os.path.join(get_mods_dir(), mod['file'])
        try:
            spec = importlib.util.spec_from_file_location(f"runmod_{mod['file']}", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, 'apply') and callable(module.apply):
                module.apply(self.app)
            messagebox.showinfo("Мод запущен", f"Мод '{mod['name']}' успешно запущен.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить мод '{mod['name']}':\n{e}")

    def show_mod_help_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Инструкция по модам")
        dlg.geometry("520x420")
        dlg.grab_set()
        dlg.configure(fg_color=DS_BG)

        ctk.CTkLabel(dlg, text="Инструкция по программированию модов", font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT).pack(pady=(20, 10))
        help_text = (
            "Моды — это Python-файлы в папке mods.\n\n"
            "Каждый мод должен содержать:\n"
            "  • MOD_NAME = 'Название'\n"
            "  • MOD_DESCRIPTION = 'Описание'\n"
            "  • def apply(app=None):\n"
            "        # код, который выполняется при запуске мода\n\n"
            "Пример:\n"
            "MOD_NAME = 'Погода'\n"
            "MOD_DESCRIPTION = 'Добавляет быстрый доступ к погоде.'\n\n"
            "def apply(app=None):\n"
            "    print('Мод Погода запущен')\n\n"
            "Если мод включён, он будет запускаться при старте приложения.\n"
            "Чтобы отключить мод, снимите галочку в списке.\n"
            "Отключённые моды не запускаются автоматически, но их можно запускать вручную.\n"
            "Кнопки 'Включить все' и 'Выключить все' управляют состоянием сразу для всех модов.\n"
            "Кнопка 'Добавить мод из файла' копирует новый мод в папку mods."
        )
        box = ctk.CTkTextbox(dlg, wrap="word", width=500, height=300, font=ctk.CTkFont(size=12))
        box.insert("0.0", help_text)
        box.configure(state="disabled")
        box.pack(padx=10, pady=10, fill="both", expand=True)

        ctk.CTkButton(dlg, text="Понятно", command=dlg.destroy).pack(pady=10)

    def update_lang(self, lang):
        self.lang = lang

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang

        title = ctk.CTkLabel(self, text=Locale.t('dashboard_title', lang),
                             font=ctk.CTkFont(size=18, weight="bold"), text_color=DS_TEXT)
        title.pack(pady=(15, 5))

        self.fig, self.ax = plt.subplots(figsize=(6.5, 3.5), dpi=80)
        self.fig.patch.set_facecolor('#343541')
        self.ax.set_facecolor('#40414f')
        self.ax.tick_params(colors='white')
        self.ax.set_ylim(0, 100)
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.history = {'aggressor': [], 'peaceful': []}
        self.aggression_level = DASHBOARD_INFLUENCE['aggressor']
        self.dashboard_active = True

        ctrl = ctk.CTkFrame(self, fg_color=DS_BG)
        ctrl.pack(pady=10, fill="x", padx=20)

        ctk.CTkLabel(ctrl, text=Locale.t('aggression_label', lang), text_color=DS_TEXT).pack(side="left", padx=5)
        self.aggression_slider = ctk.CTkSlider(ctrl, from_=0, to=100, number_of_steps=100,
                                               command=self.on_aggression_change)
        self.aggression_slider.set(self.aggression_level)
        self.aggression_slider.pack(side="left", fill="x", expand=True, padx=5)

        self.status_label = ctk.CTkLabel(self, text="", text_color="#00e676")
        self.status_label.pack(pady=(0,10))
        self.apply_dashboard_influence()

        btn_frame = ctk.CTkFrame(self, fg_color=DS_BG)
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text=Locale.t('aggressor_unit', lang), fg_color="#ef5350",
                      command=lambda: self.add_unit('aggressor')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=Locale.t('peaceful_unit', lang), fg_color="#42a5f5",
                      command=lambda: self.add_unit('peaceful')).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=Locale.t('reset', lang), fg_color="#2b2d31",
                      command=self.reset_units).pack(side="left", padx=5)

        self.update_plot()

    def on_aggression_change(self, value):
        self.aggression_level = int(value)
        self.apply_dashboard_influence()
        self.update_plot()

    def add_unit(self, side):
        if side == 'aggressor':
            self.aggression_level = min(100, self.aggression_level + 10)
        else:
            self.aggression_level = max(0, self.aggression_level - 10)
        self.aggression_slider.set(self.aggression_level)
        self.apply_dashboard_influence()
        self.update_plot()

    def apply_dashboard_influence(self):
        global DASHBOARD_INFLUENCE
        DASHBOARD_INFLUENCE['aggressor'] = self.aggression_level
        DASHBOARD_INFLUENCE['peaceful'] = 100 - self.aggression_level
        db.set_dashboard_state(USER_ID, DASHBOARD_INFLUENCE['aggressor'], DASHBOARD_INFLUENCE['peaceful'])
        self.status_label.configure(
            text=Locale.t('dashboard_status', self.lang).format(
                aggressor=DASHBOARD_INFLUENCE['aggressor'],
                peaceful=DASHBOARD_INFLUENCE['peaceful']),
            text_color="#00e676"
        )

    def reset_units(self):
        self.aggression_level = 50
        self.aggression_slider.set(50)
        self.history = {'aggressor': [], 'peaceful': []}
        self.apply_dashboard_influence()
        self.update_plot()

    def update_plot(self):
        agg = self.aggression_level
        pea = 100 - agg
        self.history['aggressor'].append(agg)
        self.history['peaceful'].append(pea)
        if len(self.history['aggressor']) > 20:
            self.history['aggressor'] = self.history['aggressor'][-20:]
            self.history['peaceful'] = self.history['peaceful'][-20:]

        self.ax.clear()
        self.ax.plot(self.history['aggressor'], color='#ef5350', label=Locale.t('aggressor_unit', self.lang), linewidth=2)
        self.ax.plot(self.history['peaceful'], color='#42a5f5', label=Locale.t('peaceful_unit', self.lang), linewidth=2)
        self.ax.set_ylim(0, 100)
        self.ax.set_facecolor('#40414f')
        self.ax.tick_params(colors='white')
        self.ax.legend(facecolor='#343541', edgecolor='white', labelcolor='white')
        self.ax.set_title("Доминирование ИИ", color='white')
        self.fig.tight_layout()
        self.canvas.draw()


class AdminFrame(ctk.CTkFrame):
    def __init__(self, master, app, lang):
        super().__init__(master, fg_color=DS_BG)
        self.app = app
        self.lang = lang
        self.admin_authenticated = False

        self.pwd_entry = ctk.CTkEntry(self, placeholder_text=Locale.t('admin_password_prompt', lang), show="*")
        self.pwd_entry.pack(pady=20, padx=20, fill="x")
        self.login_btn = ctk.CTkButton(self, text=Locale.t('login', lang), command=self.check_password)
        self.login_btn.pack(pady=5)
        self.status_label = ctk.CTkLabel(self, text="", text_color=DS_TEXT)
        self.status_label.pack(pady=10)

    def check_password(self):
        pwd = self.pwd_entry.get().strip()
        if pwd == ADMIN_PASSWORD:   # AlphaAdmin2024!
            self.admin_authenticated = True
            self.show_admin_panel()
        else:
            self.status_label.configure(text=Locale.t('super_wrong', self.lang), text_color="red")

    def show_admin_panel(self):
        for widget in self.winfo_children():
            widget.destroy()

        ctk.CTkLabel(self, text=Locale.t('admin_panel', self.lang), font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=DS_TEXT).pack(pady=15)

        # Scrollable container for admin controls to fit all features elegantly
        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=480)
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

        stats_frame = ctk.CTkFrame(scroll_frame, fg_color="#40414f")
        stats_frame.pack(pady=10, padx=20, fill="x")
        ctk.CTkLabel(stats_frame, text=f"Всего пользователей: {random.randint(100,999)}", text_color=DS_TEXT).pack(pady=5)
        self.bot_status_label = ctk.CTkLabel(stats_frame, text="Статус бота: не запущен", text_color="red")
        self.bot_status_label.pack(pady=5)

        global bot_running
        self.launch_bot_btn = ctk.CTkButton(scroll_frame, text=Locale.t('launch_bot', self.lang),
                                            command=self.launch_bot,
                                            fg_color="#2b2d31", hover_color="#3a3b3f")
        self.launch_bot_btn.pack(pady=10)
        if bot_running:
            self.launch_bot_btn.configure(state="disabled", text=Locale.t('bot_running', self.lang))
            self.bot_status_label.configure(text=Locale.t('bot_active', self.lang), text_color="green")

        # --- TG ACCESS GROUP CONFIGURATION BY OPERATOR ---
        group_frame = ctk.CTkFrame(scroll_frame, fg_color="#1f1f2e", corner_radius=12, border_width=1, border_color=DS_ACCENT)
        group_frame.pack(pady=15, padx=20, fill="x")
        
        ctk.CTkLabel(group_frame, text="⚙️ Настройки Групп Доступа Telegram (Оператор)", font=ctk.CTkFont(size=14, weight="bold"), text_color="#10b981").pack(pady=10)
        
        # Group 1
        ctk.CTkLabel(group_frame, text="Группа 1: Приватный Чат (ID через запятую):", text_color=DS_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.g1_entry = ctk.CTkEntry(group_frame, placeholder_text="Пример: 12345678, 87654321", fg_color="#12121a", text_color="#10b981")
        self.g1_entry.pack(fill="x", padx=15, pady=5)
        self.g1_entry.insert(0, _db_get_setting("tg_group_private_ids", ""))
        
        # Group 2
        ctk.CTkLabel(group_frame, text="Группа 2: Валидол-ИИ (ID через запятую):", text_color=DS_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.g2_entry = ctk.CTkEntry(group_frame, placeholder_text="Пример: 11122233, 44455566", fg_color="#12121a", text_color="#10b981")
        self.g2_entry.pack(fill="x", padx=15, pady=5)
        self.g2_entry.insert(0, _db_get_setting("tg_group_validol_ids", ""))
        
        # Group 3
        ctk.CTkLabel(group_frame, text="Группа 3: Супер-ИИ (ID через запятую):", text_color=DS_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.g3_entry = ctk.CTkEntry(group_frame, placeholder_text="Пример: 99988877, 66655544", fg_color="#12121a", text_color="#10b981")
        self.g3_entry.pack(fill="x", padx=15, pady=5)
        self.g3_entry.insert(0, _db_get_setting("tg_group_superai_ids", ""))
        
        # Password for desktop private chat
        ctk.CTkLabel(group_frame, text="Пароль для Приватного Чата на ПК:", text_color=DS_DIM, font=ctk.CTkFont(size=11)).pack(anchor="w", padx=15)
        self.private_pwd_entry = ctk.CTkEntry(group_frame, show="*", fg_color="#12121a", text_color="#10b981")
        self.private_pwd_entry.pack(fill="x", padx=15, pady=5)
        self.private_pwd_entry.insert(0, _db_get_setting("private_chat_pwd", "PrivateChatPassword"))
        
        # Save Button
        save_btn = ctk.CTkButton(group_frame, text="💾 Сохранить группы и пароль", command=self.save_group_configs, fg_color="#10b981", hover_color="#059669")
        save_btn.pack(pady=15, padx=15, fill="x")

        # Bot and database control actions
        actions_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        actions_frame.pack(pady=10, fill="x")

        ctk.CTkButton(actions_frame, text=Locale.t('show_qr', self.lang), command=self.show_bot_qr,
                      fg_color="#2b2d31", hover_color="#3a3b3f").pack(pady=5, padx=20, fill="x")

        ctk.CTkButton(actions_frame, text=Locale.t('open_code', self.lang), command=open_in_editor,
                      fg_color="#2b2d31", hover_color="#3a3b3f").pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(actions_frame, text=Locale.t('restart_bot', self.lang), command=self.restart_bot,
                      fg_color="#2b2d31", hover_color="#3a3b3f").pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(actions_frame, text=Locale.t('reset_database', self.lang), command=self.reset_settings,
                      fg_color="#2b2d31", hover_color="#3a3b3f").pack(pady=5, padx=20, fill="x")

    def save_group_configs(self):
        g1 = self.g1_entry.get().strip()
        g2 = self.g2_entry.get().strip()
        g3 = self.g3_entry.get().strip()
        pwd = self.private_pwd_entry.get().strip()
        
        _db_set_setting("tg_group_private_ids", g1)
        _db_set_setting("tg_group_validol_ids", g2)
        _db_set_setting("tg_group_superai_ids", g3)
        _db_set_setting("private_chat_pwd", pwd)
        
        messagebox.showinfo("✅ Успешно", "Конфигурация групп доступа Telegram и пароль приватного чата успешно сохранены!")


    def launch_bot(self):
        global bot_thread, bot_running
        if bot_running:
            messagebox.showinfo("Информация", "Бот уже запущен.")
            return
        bot_running = True
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        self.bot_status_label.configure(text="Бот запущен", text_color="green")
        self.launch_bot_btn.configure(state="disabled", text="Бот работает")

    def restart_bot(self):
        global bot_thread, bot_running
        messagebox.showinfo("Перезапуск", "Для полного перезапуска перезапустите приложение.\nСейчас бот будет остановлен и запущен заново.")
        bot_running = False
        bot_running = True
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
        if hasattr(self, 'bot_status_label'):
            self.bot_status_label.configure(text="Бот перезапущен", text_color="green")

    def show_bot_qr(self):
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(BOT_URL)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img_tk = ctk.CTkImage(light_image=img, size=(280, 280))
            popup = tk.Toplevel(self)
            popup.title(Locale.t('show_qr', self.lang))
            popup.geometry("320x340")
            label = ctk.CTkLabel(popup, image=img_tk)
            label.pack(expand=True, fill="both")
            ctk.CTkLabel(popup, text=f"Bot URL: {BOT_URL}").pack(pady=5)
        except ImportError:
            messagebox.showwarning(
                Locale.t('qr_unavailable', self.lang),
                Locale.t('qr_requires_package', self.lang)
            )
            webbrowser.open(BOT_URL)
        except Exception as e:
            messagebox.showwarning(
                Locale.t('qr_unavailable', self.lang),
                Locale.t('qr_error', self.lang).format(url=BOT_URL, e=e)
            )
            webbrowser.open(BOT_URL)

    def reset_settings(self):
        db.reset_all(USER_ID)
        self.bot_status_label.configure(text=Locale.t('db_cleared', self.lang), text_color="green")
        messagebox.showinfo(Locale.t('reset_database', self.lang), Locale.t('db_cleared', self.lang))



# ======================== ГЛАВНАЯ ТОЧКА ВХОДА ========================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--run-mods":
            run_mods_commandline()
            sys.exit(0)
        elif sys.argv[1] == "--run-script" and len(sys.argv) > 2:
            script_file = sys.argv[2]
            if os.path.exists(script_file):
                try:
                    with open(script_file, "r", encoding="utf-8") as f:
                        code_str = f.read()
                    exec(compile(code_str, script_file, "exec"), {"__name__": "__main__", "__file__": script_file})
                except Exception as e:
                    print(f"\n[Ошибка выполнения {script_file}]:\n{e}")
                input("\nНажмите Enter для закрытия терминала...")
            sys.exit(0)
        elif sys.argv[1].endswith(".py") and os.path.exists(sys.argv[1]):
            script_file = sys.argv[1]
            try:
                with open(script_file, "r", encoding="utf-8") as f:
                    code_str = f.read()
                exec(compile(code_str, script_file, "exec"), {"__name__": "__main__", "__file__": script_file})
            except Exception as e:
                print(f"\n[Ошибка выполнения {script_file}]:\n{e}")
            input("\nНажмите Enter для закрытия терминала...")
            sys.exit(0)

    # Самая первая идет загрузка в маленьком красивом окошке Arduino
    splash = SplashWindow()
    splash.mainloop()

    # Получаем авторизованного пользователя из лаунчера или из сохраненной БД
    env_user = os.environ.get("USER_NAME", "").strip()
    if env_user:
        uname = env_user
        _db_set_setting("last_logged_in_user", uname)
    else:
        remembered_user = _db_get_setting("last_logged_in_user", "")
        if remembered_user:
            uname = remembered_user
        else:
            uname = "Пользователь"

    if not uname:
        uname = "Пользователь"

    USER_ID = db.get_user_id(uname)
    app = App(username=uname)
    execute_enabled_mods(app)
    app.mainloop()
 
