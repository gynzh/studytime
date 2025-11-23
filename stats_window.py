from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QDateEdit

from stats_manager import StatsManager

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# 关键：设置全局中文字体 & 解决负号显示问题
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
matplotlib.rcParams["axes.unicode_minus"] = False

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots()
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout()


class StatsWindow(QDialog):
    """显示按月汇总的学习时间柱状图"""

    def __init__(self, stats_manager: StatsManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("学习统计")
        self.resize(600, 400)
        self.stats_manager = stats_manager

        layout = QVBoxLayout(self)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setDisplayFormat("yyyy-MM")
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.update_view)

        self.canvas = MplCanvas(self)
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.date_edit)
        layout.addWidget(self.canvas)
        layout.addWidget(self.summary_label)

        self.update_view()

    def update_view(self):
        qd = self.date_edit.date()
        year = qd.year()
        month = qd.month()

        daily_totals = self.stats_manager.get_monthly_daily_totals(year, month)
        days = [d for d, _ in daily_totals]
        hours = [sec / 3600.0 for _, sec in daily_totals]

        self.canvas.ax.clear()
        if days:
            self.canvas.ax.bar(days, hours)
            self.canvas.ax.set_xlabel("日")
            self.canvas.ax.set_ylabel("学习时间（小时）")
            self.canvas.ax.set_title(f"{year}年{month}月学习时间分布")
        self.canvas.fig.tight_layout()
        self.canvas.draw()

        total_seconds = sum(sec for _, sec in daily_totals)
        days_in_month = len(daily_totals)
        avg_seconds = total_seconds / days_in_month if days_in_month else 0

        self.summary_label.setText(
            f"{year}年{month}月 总学习 {total_seconds / 3600:.1f} 小时，"
            f"日均 {avg_seconds / 3600:.1f} 小时"
        )
