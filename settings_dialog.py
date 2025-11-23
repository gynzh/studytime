from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QSpinBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QWidget,
)

from config_manager import ConfigManager, TimeConfig, SoundConfig


class SettingsDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.config_manager = config_manager
        self._init_ui()
        self._load_from_config()

    def _init_ui(self):
        layout = QFormLayout(self)

        self.spin_study = QSpinBox()
        self.spin_study.setRange(10, 300)
        self.spin_study.setSuffix(" 分钟")

        self.spin_wrapup = QSpinBox()
        self.spin_wrapup.setRange(1, 300)
        self.spin_wrapup.setSuffix(" 分钟")

        self.spin_rest = QSpinBox()
        self.spin_rest.setRange(1, 120)
        self.spin_rest.setSuffix(" 分钟")

        self.spin_micro_min = QSpinBox()
        self.spin_micro_min.setRange(1, 60)
        self.spin_micro_min.setSuffix(" 分钟")

        self.spin_micro_max = QSpinBox()
        self.spin_micro_max.setRange(1, 60)
        self.spin_micro_max.setSuffix(" 分钟")

        self.spin_micro_dur = QSpinBox()
        self.spin_micro_dur.setRange(1, 300)
        self.spin_micro_dur.setSuffix(" 秒")

        layout.addRow("学习总时长：", self.spin_study)
        layout.addRow("收尾提示时间：", self.spin_wrapup)
        layout.addRow("休息时长：", self.spin_rest)
        layout.addRow("微休间隔最小：", self.spin_micro_min)
        layout.addRow("微休间隔最大：", self.spin_micro_max)
        layout.addRow("微休建议时长：", self.spin_micro_dur)

        # 音效路径
        self.edit_micro_sound, btn_micro = self._create_sound_selector()
        self.edit_wrapup_sound, btn_wrapup = self._create_sound_selector()
        self.edit_session_end_sound, btn_session_end = self._create_sound_selector()
        self.edit_rest_end_sound, btn_rest_end = self._create_sound_selector()

        layout.addRow("微休提示音：", self._wrap_with_button(self.edit_micro_sound, btn_micro))
        layout.addRow("收尾提示音：", self._wrap_with_button(self.edit_wrapup_sound, btn_wrapup))
        layout.addRow("学习结束提示音：", self._wrap_with_button(self.edit_session_end_sound, btn_session_end))
        layout.addRow("休息结束提示音：", self._wrap_with_button(self.edit_rest_end_sound, btn_rest_end))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)

    def _create_sound_selector(self):
        edit = QLineEdit()
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda: self._choose_sound_file(edit))
        return edit, btn

    def _wrap_with_button(self, line_edit: QLineEdit, button: QPushButton):
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(line_edit)
        h.addWidget(button)
        return container

    def _choose_sound_file(self, edit: QLineEdit):
        """
        选择音频文件：
        - 如果当前编辑框里已有路径，则以该路径所在目录为初始目录；
        - 否则在 Windows 上默认跳转到 C:\\Windows\\Media（如果存在）；
        - 其他情况则让 Qt 使用默认目录。
        """
        initial_dir = ""

        current_text = edit.text().strip()
        if current_text:
            if os.path.isfile(current_text):
                initial_dir = os.path.dirname(current_text)
            elif os.path.isdir(current_text):
                initial_dir = current_text

        if not initial_dir:
            # Windows 下优先使用系统媒体目录
            windows_media = r"C:\Windows\Media"
            if os.path.isdir(windows_media):
                initial_dir = windows_media

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            initial_dir,
            "音频文件 (*.wav *.mp3 *.ogg);;所有文件 (*)",
        )
        if path:
            edit.setText(path)

    def _load_from_config(self):
        time_cfg = self.config_manager.get_time_config()
        sound_cfg = self.config_manager.get_sound_config()

        self.spin_study.setValue(time_cfg.study_duration)
        self.spin_wrapup.setValue(time_cfg.wrapup_time)
        self.spin_rest.setValue(time_cfg.rest_duration)
        self.spin_micro_min.setValue(time_cfg.micro_break_interval_min)
        self.spin_micro_max.setValue(time_cfg.micro_break_interval_max)
        self.spin_micro_dur.setValue(time_cfg.micro_break_duration)

        self.edit_micro_sound.setText(sound_cfg.micro_break)
        self.edit_wrapup_sound.setText(sound_cfg.wrapup)
        self.edit_session_end_sound.setText(sound_cfg.session_end)
        self.edit_rest_end_sound.setText(sound_cfg.rest_end)

    def accept(self):
        time_cfg = TimeConfig(
            study_duration=self.spin_study.value(),
            wrapup_time=self.spin_wrapup.value(),
            rest_duration=self.spin_rest.value(),
            micro_break_interval_min=self.spin_micro_min.value(),
            micro_break_interval_max=self.spin_micro_max.value(),
            micro_break_duration=self.spin_micro_dur.value(),
        )

        sound_cfg = SoundConfig(
            micro_break=self.edit_micro_sound.text(),
            wrapup=self.edit_wrapup_sound.text(),
            session_end=self.edit_session_end_sound.text(),
            rest_end=self.edit_rest_end_sound.text(),
        )

        self.config_manager.update_time_config(time_cfg)
        self.config_manager.update_sound_config(sound_cfg)
        super().accept()
