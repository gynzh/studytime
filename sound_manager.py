from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication

from config_manager import SoundConfig


class SoundManager(QObject):
    """统一管理各类提示音"""

    def __init__(self, sound_config: SoundConfig, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._sound_config = sound_config

        self.micro_break_effect = QSoundEffect(self)
        self.wrapup_effect = QSoundEffect(self)
        self.session_end_effect = QSoundEffect(self)
        self.rest_end_effect = QSoundEffect(self)

        self._init_effects()

    def _setup_effect(self, effect: QSoundEffect, path: str):
        if path and os.path.exists(path):
            effect.setSource(QUrl.fromLocalFile(path))
            effect.setLoopCount(1)
            effect.setVolume(0.9)
        else:
            # 置空：后续用 beep 代替
            effect.setSource(QUrl())

    def _init_effects(self):
        self._setup_effect(self.micro_break_effect, self._sound_config.micro_break)
        self._setup_effect(self.wrapup_effect, self._sound_config.wrapup)
        self._setup_effect(self.session_end_effect, self._sound_config.session_end)
        self._setup_effect(self.rest_end_effect, self._sound_config.rest_end)

    def update_config(self, sound_config: SoundConfig):
        self._sound_config = sound_config
        self._init_effects()

    def _play_or_beep(self, effect: QSoundEffect):
        if effect.source().isEmpty():
            QApplication.beep()
        else:
            effect.play()

    def play_micro_break(self):
        self._play_or_beep(self.micro_break_effect)

    def play_wrapup(self):
        self._play_or_beep(self.wrapup_effect)

    def play_session_end(self):
        self._play_or_beep(self.session_end_effect)

    def play_rest_end(self):
        self._play_or_beep(self.rest_end_effect)
