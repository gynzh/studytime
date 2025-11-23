from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field

CONFIG_FILE = "config.json"


@dataclass
class TimeConfig:
    """时间相关配置（单位：分钟/秒）"""
    study_duration: int = 90                # 学习总时长（分钟）
    wrapup_time: int = 80                   # 收尾提示时间点（分钟）
    rest_duration: int = 20                 # 休息时长（分钟）
    micro_break_interval_min: int = 5       # 微休最小间隔（分钟）
    micro_break_interval_max: int = 8       # 微休最大间隔（分钟）
    micro_break_duration: int = 10          # 微休建议时长（秒）


@dataclass
class SoundConfig:
    """音效文件路径配置"""
    micro_break: str = ""
    wrapup: str = ""
    session_end: str = ""
    rest_end: str = ""


@dataclass
class UIConfig:
    """界面相关配置（目前只预留主题字段）"""
    theme: str = "light"


@dataclass
class AppConfig:
    time: TimeConfig = field(default_factory=TimeConfig)
    sounds: SoundConfig = field(default_factory=SoundConfig)
    ui: UIConfig = field(default_factory=UIConfig)


class ConfigManager:
    def __init__(self, path: str = CONFIG_FILE):
        self.path = path
        self.config = AppConfig()
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            time_defaults = asdict(TimeConfig())
            sound_defaults = asdict(SoundConfig())
            ui_defaults = asdict(UIConfig())

            time_data = {**time_defaults, **data.get("time", {})}
            sound_data = {**sound_defaults, **data.get("sounds", {})}
            ui_data = {**ui_defaults, **data.get("ui", {})}

            self.config.time = TimeConfig(**time_data)
            self.config.sounds = SoundConfig(**sound_data)
            self.config.ui = UIConfig(**ui_data)
        except Exception:
            # 配置损坏时重置
            self.config = AppConfig()
            self.save()

    def save(self) -> None:
        data = {
            "time": asdict(self.config.time),
            "sounds": asdict(self.config.sounds),
            "ui": asdict(self.config.ui),
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- 对外接口 ---

    def get_time_config(self) -> TimeConfig:
        return self.config.time

    def get_sound_config(self) -> SoundConfig:
        return self.config.sounds

    def get_ui_config(self) -> UIConfig:
        return self.config.ui

    def update_time_config(self, new_time: TimeConfig) -> None:
        self.config.time = new_time
        self.save()

    def update_sound_config(self, new_sound: SoundConfig) -> None:
        self.config.sounds = new_sound
        self.save()

    def update_ui_config(self, new_ui: UIConfig) -> None:
        self.config.ui = new_ui
        self.save()
