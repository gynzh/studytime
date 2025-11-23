from __future__ import annotations

import random
from enum import Enum, auto

from PySide6.QtCore import QObject, QTimer, Signal

from config_manager import TimeConfig


class TimerState(Enum):
    IDLE = auto()
    STUDYING = auto()
    RESTING = auto()
    PAUSED = auto()


class TimerController(QObject):
    """统一管理学习 / 休息计时逻辑"""

    stateChanged = Signal(object)          # TimerState
    studyProgress = Signal(int, int)      # elapsed, total (seconds)
    restProgress = Signal(int, int)
    microBreakHint = Signal(int)          # 第几次微休
    wrapupHint = Signal()
    sessionEnd = Signal()
    restEnd = Signal()

    def __init__(self, time_config: TimeConfig, parent: QObject = None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

        self.time_config = time_config
        self.state = TimerState.IDLE
        self._last_active_state: TimerState | None = None

        self.study_elapsed = 0
        self.rest_elapsed = 0
        self._next_micro_break_target = 0
        self._micro_break_count = 0
        self._wrapup_triggered = False

        self._recalculate_micro_break_target()

    def update_time_config(self, time_config: TimeConfig):
        self.time_config = time_config
        if self.state == TimerState.IDLE:
            self._reset_counters()

    def start_study(self):
        self._reset_counters()
        self.state = TimerState.STUDYING
        self.stateChanged.emit(self.state)
        self._timer.start()

    def start_rest(self):
        self.rest_elapsed = 0
        self.state = TimerState.RESTING
        self.stateChanged.emit(self.state)
        if not self._timer.isActive():
            self._timer.start()

    def pause(self):
        if self.state in (TimerState.STUDYING, TimerState.RESTING):
            self._last_active_state = self.state
            self.state = TimerState.PAUSED
            self.stateChanged.emit(self.state)
            self._timer.stop()

    def resume(self):
        if self.state == TimerState.PAUSED and self._last_active_state:
            self.state = self._last_active_state
            self.stateChanged.emit(self.state)
            self._timer.start()

    def stop(self):
        self._timer.stop()
        self.state = TimerState.IDLE
        self.stateChanged.emit(self.state)

    def _reset_counters(self):
        self.study_elapsed = 0
        self.rest_elapsed = 0
        self._micro_break_count = 0
        self._wrapup_triggered = False
        self._recalculate_micro_break_target()

    def _recalculate_micro_break_target(self):
        """生成下一次微休提示时间点(相对于当前 study_elapsed)"""
        interval_min = self.time_config.micro_break_interval_min * 60
        interval_max = self.time_config.micro_break_interval_max * 60
        if interval_max <= 0 or interval_max < interval_min:
            self._next_micro_break_target = 0
            return
        base = self.study_elapsed
        delta = random.randint(interval_min, interval_max)
        target = base + delta
        if target >= self.time_config.wrapup_time * 60:
            self._next_micro_break_target = 0
        else:
            self._next_micro_break_target = target

    def _on_tick(self):
        if self.state == TimerState.STUDYING:
            self.study_elapsed += 1
            total = self.time_config.study_duration * 60
            self.studyProgress.emit(self.study_elapsed, total)

            # 微休提示:不暂停倒计时
            if self._next_micro_break_target and self.study_elapsed >= self._next_micro_break_target:
                self._micro_break_count += 1
                self.microBreakHint.emit(self._micro_break_count)
                self._recalculate_micro_break_target()

            # 收尾提示:不暂停倒计时
            if (not self._wrapup_triggered and
                    self.study_elapsed >= self.time_config.wrapup_time * 60):
                self._wrapup_triggered = True
                self.wrapupHint.emit()

            # 学习结束
            if self.study_elapsed >= total:
                self._timer.stop()
                self.sessionEnd.emit()

        elif self.state == TimerState.RESTING:
            self.rest_elapsed += 1
            total = self.time_config.rest_duration * 60
            self.restProgress.emit(self.rest_elapsed, total)
            if self.rest_elapsed >= total:
                self._timer.stop()
                self.restEnd.emit()
