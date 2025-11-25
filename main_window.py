from __future__ import annotations

from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont, QScreen, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from config_manager import ConfigManager
from stats_manager import StatsManager
from sound_manager import SoundManager
from timer_controller import TimerController, TimerState
from settings_dialog import SettingsDialog
from stats_window import StatsWindow


class MainWindow(QMainWindow):
    def __init__(
            self,
            config_manager: ConfigManager,
            stats_manager: StatsManager,
            sound_manager: SoundManager,
            timer_controller: TimerController,
            parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # 无边框窗口,删除标题栏和关闭按钮
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        # 允许窗口背景透明,去掉圆角外面那四个黑色直角
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 拖动相关状态
        self._dragging = False
        self._drag_pos = QPoint()

        self.config_manager = config_manager
        self.stats_manager = stats_manager
        self.sound_manager = sound_manager
        self.timer_controller = timer_controller

        self.current_session_start: Optional[datetime] = None
        self.stats_window: Optional[StatsWindow] = None

        self._init_ui()
        self._connect_signals()
        self._update_state_ui(self.timer_controller.state)

        # 窗口显示后定位到右上角
        QApplication.instance().processEvents()
        self._position_window_top_right()

    def _position_window_top_right(self) -> None:
        """将窗口定位到屏幕右上角偏下一点"""
        screen: QScreen = QApplication.primaryScreen()
        if screen is None:
            return

        screen_geometry = screen.availableGeometry()
        window_width = self.width()
        window_height = self.height()

        # 右上角位置:右边距45像素,上边距60像素
        x = screen_geometry.right() - window_width - 45
        y = screen_geometry.top() + 60

        self.move(QPoint(x, y))

    def _init_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("TimerBar")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)

        self.label_time = QLabel("00:00")
        self.label_time.setObjectName("TimeLabel")
        font_time = QFont()
        font_time.setPointSize(20)
        font_time.setBold(True)
        self.label_time.setFont(font_time)
        self.label_time.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label_time)
        self.setCentralWidget(central)

        self._apply_theme()
        # 根据时间文本自动调整窗口大小,让胶囊刚好包住时间
        self._update_window_size_for_text(self.label_time.text())

    def _apply_theme(self) -> None:
        """根据配置中的 ui.theme 应用浅色/深色主题"""
        ui_cfg = self.config_manager.get_ui_config()
        theme = getattr(ui_cfg, "theme", "light")

        if theme == "dark":
            # 深色胶囊样式
            self.setStyleSheet(
                """
                QMainWindow {
                    background-color: transparent;
                }

                QWidget#TimerBar {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0   #020617,
                        stop: 0.35 #0f172a,
                        stop: 0.7 #1f2937,
                        stop: 1   #1d4ed8
                    );
                    border-radius: 12px;
                    border: 1px solid #1d4ed8;
                }

                QLabel#TimeLabel {
                    color: #e5e7eb;
                    font-weight: 600;
                    letter-spacing: 1px;
                }
                """
            )
        else:
            # 默认浅色蓝色胶囊样式
            self.setStyleSheet(
                """
                QMainWindow {
                    background-color: transparent;
                }

                QWidget#TimerBar {
                    background: qlineargradient(
                        x1: 0, y1: 0, x2: 1, y2: 0,
                        stop: 0   #0f172a,
                        stop: 0.25 #1d4ed8,
                        stop: 0.6 #2563eb,
                        stop: 1   #38bdf8
                    );
                    border-radius: 12px;
                    border: 1px solid #60a5fa;
                }

                QLabel#TimeLabel {
                    color: white;
                    font-weight: 600;
                    letter-spacing: 1px;
                }
                """
            )

    def _update_window_size_for_text(self, text: str) -> None:
        """
        根据当前时间文本计算合适的窗口大小,让蓝色背景刚好包住文字。
        额外留出少量边框空间,避免看起来过于拥挤。
        """
        fm = self.label_time.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        text_height = fm.height()

        central = self.centralWidget()
        if central is None:
            return
        layout = central.layout()
        if layout is None:
            return
        margins = layout.contentsMargins()

        width = text_width + margins.left() + margins.right() + 4  # 4像素缓冲
        height = text_height + margins.top() + margins.bottom() + 4

        self.setFixedSize(width, height)

    def _set_time_text(self, text: str) -> None:
        """统一设置时间文本并自动调整窗口大小"""
        self.label_time.setText(text)
        self._update_window_size_for_text(text)

    def _connect_signals(self) -> None:
        self.timer_controller.stateChanged.connect(self._update_state_ui)
        self.timer_controller.studyProgress.connect(self._on_study_progress)
        self.timer_controller.restProgress.connect(self._on_rest_progress)
        self.timer_controller.microBreakHint.connect(self._on_micro_break)
        self.timer_controller.wrapupHint.connect(self._on_wrapup)
        self.timer_controller.sessionEnd.connect(self._on_session_end)
        self.timer_controller.restEnd.connect(self._on_rest_end)

    @staticmethod
    def _format_seconds(seconds: int) -> str:
        seconds = max(int(seconds), 0)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"

    def _update_state_ui(self, state: TimerState) -> None:
        if state == TimerState.IDLE:
            self._set_time_text("00:00")

    def start_new_session(self) -> None:
        self.current_session_start = datetime.now()
        self.timer_controller.start_study()

    def _on_start_triggered(self) -> None:
        if self.timer_controller.state == TimerState.IDLE:
            self.start_new_session()
        else:
            ret = QMessageBox.question(
                self,
                "重新开始",
                "当前已有进行中的轮次,确定要重新开始吗?当前轮不会计入统计。",
            )
            if ret == QMessageBox.Yes:
                self.timer_controller.stop()
                self.start_new_session()

    def _on_pause_triggered(self) -> None:
        if self.timer_controller.state in (TimerState.STUDYING, TimerState.RESTING):
            self.timer_controller.pause()
        elif self.timer_controller.state == TimerState.PAUSED:
            self.timer_controller.resume()

    def _on_stop_triggered(self) -> None:
        if self.timer_controller.state in (
                TimerState.STUDYING,
                TimerState.RESTING,
                TimerState.PAUSED,
        ):
            ret = QMessageBox.question(
                self,
                "结束当前轮",
                "确定要结束当前轮吗?当前学习数据将不会计入统计。",
            )
            if ret == QMessageBox.Yes:
                self.timer_controller.stop()
                self.current_session_start = None

    def _on_study_progress(self, elapsed: int, total: int) -> None:
        remaining = max(total - elapsed, 0)
        self._set_time_text(self._format_seconds(remaining))

    def _on_rest_progress(self, elapsed: int, total: int) -> None:
        remaining = max(total - elapsed, 0)
        self._set_time_text(self._format_seconds(remaining))

    def _on_micro_break(self, count: int) -> None:
        """微休提示:仅播放声音,不弹窗,不暂停"""
        self.sound_manager.play_micro_break()

    def _on_wrapup(self) -> None:
        """收尾提示:仅播放声音,不弹窗,不暂停"""
        self.sound_manager.play_wrapup()

    def _on_session_end(self) -> None:
        # 记录本轮学习统计
        end_dt = datetime.now()
        study_seconds = self.timer_controller.study_elapsed
        if self.current_session_start is not None:
            self.stats_manager.record_session(
                self.current_session_start, end_dt, study_seconds
            )
            self.current_session_start = None

        self.sound_manager.play_session_end()

        msg = QMessageBox(self)
        msg.setWindowTitle("本轮学习结束")
        msg.setText("本轮学习已结束,要不要休息一下?")
        btn_relax = msg.addButton("放松一下(休息20分钟)", QMessageBox.AcceptRole)
        msg.addButton("溜了,我有别的事", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_relax)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_relax:
            self.timer_controller.start_rest()
        else:
            self.timer_controller.stop()

    def _on_rest_end(self) -> None:
        self.sound_manager.play_rest_end()
        msg = QMessageBox(self)
        msg.setWindowTitle("休息结束")
        msg.setText("休息时间到啦,开始下一轮学习吗?")
        btn_start = msg.addButton("开始下一轮", QMessageBox.AcceptRole)
        msg.addButton("今天先到这儿", QMessageBox.RejectRole)
        msg.setDefaultButton(btn_start)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == btn_start:
            self.start_new_session()
        else:
            self.timer_controller.stop()

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.config_manager, self)
        if dlg.exec():
            self.timer_controller.update_time_config(
                self.config_manager.get_time_config()
            )
            self.sound_manager.update_config(
                self.config_manager.get_sound_config()
            )

            # 更新主窗口主题
            self._apply_theme()

            # 如果统计窗口已经打开, 同步切换其主题
            if self.stats_window is not None:
                ui_cfg = self.config_manager.get_ui_config()
                style_mode = ui_cfg.theme if ui_cfg.theme in ("light", "dark") else "light"
                self.stats_window.style_mode = style_mode
                # _apply_style / update_view 虽为内部方法, 这里直接调用以实现实时刷新
                self.stats_window._apply_style(style_mode)
                self.stats_window.update_view()

    def open_stats(self) -> None:
        if self.stats_window is None:
            ui_cfg = self.config_manager.get_ui_config()
            style_mode = ui_cfg.theme if ui_cfg.theme in ("light", "dark") else "light"
            self.stats_window = StatsWindow(
                self.stats_manager,
                style_mode=style_mode,
                parent=self,
            )
        self.stats_window.show()
        self.stats_window.raise_()
        self.stats_window.activateWindow()

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        menu = QMenu(self)

        action_start = menu.addAction("开始")
        action_pause = menu.addAction("暂停/继续")
        action_stop = menu.addAction("结束本轮")
        menu.addSeparator()
        action_settings = menu.addAction("首选项...")
        action_stats = menu.addAction("查看统计")
        menu.addSeparator()
        action_quit = menu.addAction("退出程序")

        selected = menu.exec(event.globalPos())
        if selected is None:
            return

        if selected == action_start:
            self._on_start_triggered()
        elif selected == action_pause:
            self._on_pause_triggered()
        elif selected == action_stop:
            self._on_stop_triggered()
        elif selected == action_settings:
            self.open_settings()
        elif selected == action_stats:
            self.open_stats()
        elif selected == action_quit:
            app = QApplication.instance()
            if app is not None:
                app.quit()

    # ---------- 鼠标拖动窗口相关 ----------

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._dragging = True
            # 记录鼠标相对窗口左上角的偏移
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if self._dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)
