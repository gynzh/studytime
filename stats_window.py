from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QDateEdit,
    QComboBox,
    QSpinBox,
    QStackedWidget,
)

from stats_manager import StatsManager

import matplotlib
import matplotlib.pyplot as plt  # noqa: F401  # 保留以兼容外部可能的引用
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# 设置中文字体和负号显示
# 增加 DejaVu Sans 作为兜底, 避免部分符号缺字形
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Arial Unicode MS",
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=7, height=4.5, dpi=100):
        # 稍微缩小默认尺寸,使整体窗口更加紧凑
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        # 默认使用浅色背景, 之后由 StatsWindow 里的 _apply_chart_theme 统一调整
        self.fig.patch.set_facecolor("#f8fafc")
        self.ax.set_facecolor("#ffffff")


class StatsWindow(QDialog):
    """
    学习统计窗口, 支持日/月/年三种视图.
    颜色主题通过构造函数传入的 style_mode 控制, 建议从 config.json 中读取:

        ui_cfg = config_manager.get_ui_config()
        StatsWindow(stats_manager, style_mode=ui_cfg.theme)
        # ui.theme: "light" 或 "dark"
    """

    def __init__(self, stats_manager: StatsManager, style_mode: str = "light", parent=None):
        super().__init__(parent)
        self.setWindowTitle("学习统计")
        # 窗口略小一点
        self.resize(760, 540)

        self.stats_manager = stats_manager

        self.current_date = date.today()
        self.view_mode = "day"   # day, month, year
        self.style_mode = style_mode if style_mode in ("light", "dark") else "light"

        # UI 元素占位
        self.control_widget: QWidget | None = None
        self.nav_container: QWidget | None = None
        self.date_card: QWidget | None = None
        self.canvas_container: QWidget | None = None

        self.view_combo: QComboBox | None = None
        self.btn_today: QPushButton | None = None

        self.date_edit: QDateEdit | None = None
        self.spin_month_year: QSpinBox | None = None
        self.combo_month: QComboBox | None = None
        self.spin_year: QSpinBox | None = None

        self.nav_stack: QStackedWidget | None = None
        self.date_label: QLabel | None = None
        self.summary_label: QLabel | None = None
        self.canvas: MplCanvas | None = None

        # 一些标签引用, 用于切换风格时统一设置
        self._view_label: QLabel | None = None
        self._lbl_day: QLabel | None = None
        self._lbl_month: QLabel | None = None
        self._lbl_year: QLabel | None = None

        self._init_ui()
        self._update_nav_controls_for_mode()
        self._apply_style(self.style_mode)
        self.update_view()

    # ======================== UI 初始化 ========================

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(14, 14, 14, 14)

        # ---------- 顶部控制区域 ----------
        control_widget = QWidget()
        self.control_widget = control_widget

        control_layout = QHBoxLayout(control_widget)
        # 间距稍微调小一点, 让控件更紧凑
        control_layout.setSpacing(8)
        control_layout.setContentsMargins(10, 8, 10, 8)

        # 左侧: 统计视图 + 下拉选择
        view_label = QLabel("📊 统计视图")
        self._view_label = view_label

        self.view_combo = QComboBox()
        self.view_combo.addItem("日统计", "day")
        self.view_combo.addItem("月统计", "month")
        self.view_combo.addItem("年统计", "year")
        self.view_combo.setCurrentIndex(0)
        # 限制宽度, 避免过长
        self.view_combo.setFixedWidth(90)

        control_layout.addWidget(view_label)
        control_layout.addWidget(self.view_combo)
        control_layout.addSpacing(8)

        # 中间: 日期导航(使用 QStackedWidget)
        nav_container = QWidget()
        self.nav_container = nav_container
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.nav_stack = QStackedWidget()

        # ---- 日视图: QDateEdit + 日历弹出 ----
        day_page = QWidget()
        day_layout = QHBoxLayout(day_page)
        day_layout.setContentsMargins(0, 0, 0, 0)
        day_layout.setSpacing(4)

        lbl_day = QLabel("日期:")
        self._lbl_day = lbl_day

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        # 控件宽度适当收紧, 避免在日统计视图中占用过多空间
        self.date_edit.setFixedWidth(130)

        day_layout.addWidget(lbl_day)
        day_layout.addWidget(self.date_edit)

        # ---- 月视图: 年份 + 月份下拉 ----
        month_page = QWidget()
        month_layout = QHBoxLayout(month_page)
        month_layout.setContentsMargins(0, 0, 0, 0)
        month_layout.setSpacing(4)

        lbl_month = QLabel("月份:")
        self._lbl_month = lbl_month

        self.spin_month_year = QSpinBox()
        self.spin_month_year.setRange(2000, 2100)
        self.spin_month_year.setValue(self.current_date.year)
        self.spin_month_year.setSuffix(" 年")
        # 年份控件固定宽度, 避免显得过长
        self.spin_month_year.setFixedWidth(100)

        self.combo_month = QComboBox()
        for m in range(1, 13):
            self.combo_month.addItem(f"{m}月", m)
        self.combo_month.setCurrentIndex(self.current_date.month - 1)
        # 月份下拉控件也限制宽度
        self.combo_month.setFixedWidth(90)

        month_layout.addWidget(lbl_month)
        month_layout.addWidget(self.spin_month_year)
        month_layout.addWidget(self.combo_month)

        # ---- 年视图: 仅年份 ----
        year_page = QWidget()
        year_layout = QHBoxLayout(year_page)
        year_layout.setContentsMargins(0, 0, 0, 0)
        year_layout.setSpacing(4)

        lbl_year = QLabel("年份:")
        self._lbl_year = lbl_year

        self.spin_year = QSpinBox()
        self.spin_year.setRange(2000, 2100)
        self.spin_year.setValue(self.current_date.year)
        self.spin_year.setSuffix(" 年")
        # 年度视图的年份控件同样限制宽度
        self.spin_year.setFixedWidth(100)

        year_layout.addWidget(lbl_year)
        year_layout.addWidget(self.spin_year)

        self.nav_stack.addWidget(day_page)    # index 0
        self.nav_stack.addWidget(month_page)  # index 1
        self.nav_stack.addWidget(year_page)   # index 2

        nav_layout.addWidget(self.nav_stack)
        control_layout.addWidget(nav_container, stretch=1)

        # 右侧: “回到今天” 按钮
        self.btn_today = QPushButton("回到今天")
        # 右侧按钮也限定一个合适宽度, 避免占太大空间
        self.btn_today.setFixedWidth(90)
        control_layout.addWidget(self.btn_today, alignment=Qt.AlignRight)

        main_layout.addWidget(control_widget)

        # ---------- 当前日期显示卡片 ----------
        date_card = QWidget()
        self.date_card = date_card
        date_layout = QHBoxLayout(date_card)
        date_layout.setContentsMargins(10, 8, 10, 8)

        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        date_layout.addWidget(self.date_label)

        main_layout.addWidget(date_card)

        # ---------- 图表画布容器 ----------
        canvas_container = QWidget()
        self.canvas_container = canvas_container
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(10, 8, 10, 8)

        self.canvas = MplCanvas(self, width=6.8, height=3.8, dpi=100)
        canvas_layout.addWidget(self.canvas)
        main_layout.addWidget(canvas_container, stretch=1)

        # ---------- 统计摘要卡片 ----------
        self.summary_label = QLabel()
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setWordWrap(True)
        main_layout.addWidget(self.summary_label)

        # 信号连接
        self.view_combo.currentIndexChanged.connect(self._on_view_changed)
        self.btn_today.clicked.connect(self._go_today)

        self.date_edit.dateChanged.connect(self._on_day_date_changed)
        self.spin_month_year.valueChanged.connect(self._on_month_year_changed)
        self.combo_month.currentIndexChanged.connect(self._on_month_year_changed)
        self.spin_year.valueChanged.connect(self._on_year_changed)

    # ======================== 风格相关 ========================

    def _apply_style(self, mode: str):
        """根据 style_mode 应用两套完整的 UI 风格"""

        # 整体背景 + 日历控件
        if mode == "light":
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #f8fafc;
                }

                QCalendarWidget QWidget {
                    background-color: #ffffff;
                    color: #0f172a;
                    font-size: 12px;
                }
                QCalendarWidget QAbstractItemView {
                    background-color: #ffffff;
                    color: #0f172a;
                    selection-background-color: #3b82f6;
                    selection-color: #ffffff;
                    font-size: 12px;
                }
                QCalendarWidget QToolButton {
                    color: #0f172a;
                    font-weight: 600;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QDialog {
                    background-color: #020617;
                }

                QCalendarWidget QWidget {
                    background-color: #020617;
                    color: #e5e7eb;
                    font-size: 12px;
                }
                QCalendarWidget QAbstractItemView {
                    background-color: #020617;
                    color: #e5e7eb;
                    selection-background-color: #1d4ed8;
                    selection-color: #f9fafb;
                    font-size: 12px;
                }
                QCalendarWidget QToolButton {
                    color: #e5e7eb;
                    font-weight: 600;
                }
                """
            )

        # 顶部控制卡片
        if self.control_widget is not None:
            if mode == "light":
                self.control_widget.setStyleSheet(
                    """
                    QWidget {
                        background-color: #ffffff;
                        border-radius: 10px;
                        border: 1px solid #e2e8f0;
                    }
                    """
                )
            else:
                self.control_widget.setStyleSheet(
                    """
                    QWidget {
                        background-color: #0f172a;
                        border-radius: 10px;
                        border: 1px solid #1f2937;
                    }
                    """
                )

        # “统计视图” 标签
        if isinstance(self._view_label, QLabel):
            if mode == "light":
                self._view_label.setStyleSheet(
                    """
                    QLabel {
                        font-weight: 600;
                        font-size: 13px;
                        color: #1e293b;
                    }
                    """
                )
            else:
                self._view_label.setStyleSheet(
                    """
                    QLabel {
                        font-weight: 600;
                        font-size: 13px;
                        color: #e5e7eb;
                    }
                    """
                )

        # 日期说明标签
        for lbl_attr in ("_lbl_day", "_lbl_month", "_lbl_year"):
            lbl = getattr(self, lbl_attr, None)
            if isinstance(lbl, QLabel):
                if mode == "light":
                    lbl.setStyleSheet(
                        """
                        QLabel {
                            font-size: 12px;
                            color: #0f172a;
                        }
                        """
                    )
                else:
                    lbl.setStyleSheet(
                        """
                        QLabel {
                            font-size: 12px;
                            color: #e5e7eb;
                        }
                        """
                    )

        # “回到今天”按钮
        if self.btn_today is not None:
            if mode == "light":
                nav_style = """
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #60a5fa,
                            stop: 1 #3b82f6
                        );
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 12px;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #3b82f6,
                            stop: 1 #2563eb
                        );
                    }
                    QPushButton:pressed {
                        background: #1d4ed8;
                    }
                """
            else:
                nav_style = """
                    QPushButton {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #2563eb,
                            stop: 1 #1d4ed8
                        );
                        color: #f9fafb;
                        border: none;
                        border-radius: 8px;
                        padding: 6px 12px;
                        font-size: 12px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 0, y2: 1,
                            stop: 0 #1d4ed8,
                            stop: 1 #1e40af
                        );
                    }
                    QPushButton:pressed {
                        background: #1d4ed8;
                    }
                """
            self.btn_today.setStyleSheet(nav_style)

        # 下拉框 / 日期 / 年份控件样式 (视图下拉 + 日期控件下拉) 统一
        selector_light = """
            QDateEdit, QSpinBox, QComboBox {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: 500;
                color: #0f172a;
            }
            QDateEdit:hover, QSpinBox:hover, QComboBox:hover {
                border-color: #60a5fa;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #0f172a;
                selection-background-color: #e5e7eb;
                selection-color: #0f172a;
                font-size: 12px;
            }
        """
        selector_dark = """
            QDateEdit, QSpinBox, QComboBox {
                background-color: #020617;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                font-weight: 500;
                color: #e5e7eb;
            }
            QDateEdit:hover, QSpinBox:hover, QComboBox:hover {
                border-color: #3b82f6;
            }
            QComboBox QAbstractItemView {
                background-color: #020617;
                color: #e5e7eb;
                selection-background-color: #1d4ed8;
                selection-color: #f9fafb;
                font-size: 12px;
            }
        """
        selector_style = selector_light if mode == "light" else selector_dark

        for w in (self.view_combo, self.date_edit, self.spin_month_year, self.combo_month, self.spin_year):
            if w is not None:
                w.setStyleSheet(selector_style)

        # 当前日期标题卡片
        if self.date_card is not None and self.date_label is not None:
            if mode == "light":
                self.date_card.setStyleSheet(
                    """
                    QWidget {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 #3b82f6,
                            stop: 1 #2563eb
                        );
                        border-radius: 10px;
                        padding: 6px;
                    }
                    """
                )
                self.date_label.setStyleSheet(
                    """
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #ffffff;
                        padding: 2px;
                    }
                    """
                )
            else:
                self.date_card.setStyleSheet(
                    """
                    QWidget {
                        background: qlineargradient(
                            x1: 0, y1: 0, x2: 1, y2: 0,
                            stop: 0 #0f172a,
                            stop: 1 #1f2937
                        );
                        border-radius: 10px;
                        padding: 6px;
                    }
                    """
                )
                self.date_label.setStyleSheet(
                    """
                    QLabel {
                        font-size: 16px;
                        font-weight: bold;
                        color: #e5e7eb;
                        padding: 2px;
                    }
                    """
                )

        # 图表画布容器
        if self.canvas_container is not None:
            if mode == "light":
                self.canvas_container.setStyleSheet(
                    """
                    QWidget {
                        background-color: #ffffff;
                        border-radius: 10px;
                        border: 1px solid #e2e8f0;
                    }
                    """
                )
            else:
                self.canvas_container.setStyleSheet(
                    """
                    QWidget {
                        background-color: #020617;
                        border-radius: 10px;
                        border: 1px solid #1f2937;
                    }
                    """
                )

        # 摘要卡片
        if self.summary_label is not None:
            if mode == "light":
                self.summary_label.setStyleSheet(
                    """
                    QLabel {
                        background-color: #ffffff;
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 13px;
                        color: #475569;
                        border: 1px solid #e2e8f0;
                        line-height: 1.6;
                    }
                    """
                )
            else:
                self.summary_label.setStyleSheet(
                    """
                    QLabel {
                        background-color: #0f172a;
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 13px;
                        color: #e5e7eb;
                        border: 1px solid #1f2937;
                        line-height: 1.6;
                    }
                    """
                )

        # 图表背景主题
        self._apply_chart_theme()

    def _apply_chart_theme(self):
        """根据 style_mode 调整 Matplotlib 画布背景"""
        if self.canvas is None:
            return

        if self.style_mode == "light":
            self.canvas.fig.patch.set_facecolor("#f8fafc")
            self.canvas.ax.set_facecolor("#ffffff")
        else:
            self.canvas.fig.patch.set_facecolor("#020617")
            self.canvas.ax.set_facecolor("#020617")

    # ======================== 顶部控制逻辑 ========================

    def _update_nav_controls_for_mode(self):
        """根据当前视图类型和 current_date, 同步顶部日期选择控件"""
        if self.nav_stack is None:
            return
        if self.view_mode == "day":
            self.nav_stack.setCurrentIndex(0)
            qd = QDate(self.current_date.year, self.current_date.month, self.current_date.day)
            if self.date_edit is not None:
                self.date_edit.setDate(qd)
        elif self.view_mode == "month":
            self.nav_stack.setCurrentIndex(1)
            if self.spin_month_year is not None:
                self.spin_month_year.setValue(self.current_date.year)
            if self.combo_month is not None:
                self.combo_month.setCurrentIndex(self.current_date.month - 1)
        else:  # year
            self.nav_stack.setCurrentIndex(2)
            if self.spin_year is not None:
                self.spin_year.setValue(self.current_date.year)

    def _on_view_changed(self, index: int):
        if self.view_combo is None:
            return
        mode = self.view_combo.itemData(index) or "day"
        if mode not in ("day", "month", "year"):
            mode = "day"
        self.view_mode = mode
        self._update_nav_controls_for_mode()
        self.update_view()

    def _on_day_date_changed(self, qdate: QDate):
        if self.view_mode != "day":
            return
        self.current_date = date(qdate.year(), qdate.month(), qdate.day())
        self.update_view()

    def _on_month_year_changed(self, *args):
        if self.view_mode != "month":
            return
        if self.spin_month_year is None or self.combo_month is None:
            return
        year = self.spin_month_year.value()
        month = self.combo_month.currentData() or (self.combo_month.currentIndex() + 1)
        self.current_date = date(year, int(month), 1)
        self.update_view()

    def _on_year_changed(self, value: int):
        if self.view_mode != "year":
            return
        self.current_date = date(value, 1, 1)
        self.update_view()

    def _go_today(self):
        """根据当前视图, 回到今天/本月/本年"""
        today = date.today()
        if self.view_mode == "day":
            self.current_date = today
        elif self.view_mode == "month":
            self.current_date = date(today.year, today.month, 1)
        else:  # year
            self.current_date = date(today.year, 1, 1)
        self._update_nav_controls_for_mode()
        self.update_view()

    # ======================== 视图展示 ========================

    def update_view(self):
        if self.view_mode == "day":
            self._show_day_view()
        elif self.view_mode == "month":
            self._show_month_view()
        else:
            self._show_year_view()

    def _show_day_view(self):
        """显示单日学习统计"""
        if self.canvas is None or self.date_label is None or self.summary_label is None:
            return

        count, total_seconds = self.stats_manager.get_daily_total(self.current_date)
        hours = total_seconds / 3600.0

        self.date_label.setText(f"📅 {self.current_date.strftime('%Y年%m月%d日')}")

        self.canvas.ax.clear()
        self._apply_chart_theme()
        self.canvas.ax.axis("off")
        self.canvas.ax.set_xlim(0, 10)
        self.canvas.ax.set_ylim(0, 10)

        # 绘制渐变背景卡片
        from matplotlib.patches import FancyBboxPatch, Circle

        if self.style_mode == "light":
            card_face = "#3b82f6"
            card_edge = "#2563eb"
            text_main = "#ffffff"
            circle_color = "#ffffff"
        else:
            card_face = "#1d4ed8"
            card_edge = "#1d4ed8"
            text_main = "#e5e7eb"
            circle_color = "#e5e7eb"

        card = FancyBboxPatch(
            (0.7, 1.8),
            8.6,
            6.8,
            boxstyle="round,pad=0.3",
            facecolor=card_face,
            edgecolor=card_edge,
            linewidth=2,
            alpha=0.95,
        )
        self.canvas.ax.add_patch(card)

        circle1 = Circle((1.4, 7.6), 0.7, color=circle_color, alpha=0.15)
        circle2 = Circle((8.7, 2.6), 1.0, color=circle_color, alpha=0.1)
        self.canvas.ax.add_patch(circle1)
        self.canvas.ax.add_patch(circle2)

        # 显示学习时长 (字体稍微小一点)
        self.canvas.ax.text(
            5,
            6.0,
            f"{hours:.1f}",
            ha="center",
            va="center",
            fontsize=60,
            fontweight="bold",
            color=text_main,
        )

        self.canvas.ax.text(
            5,
            4.1,
            "小时",
            ha="center",
            va="center",
            fontsize=20,
            color=text_main,
            alpha=0.95,
            fontweight="600",
        )

        # 分割线
        self.canvas.ax.plot(
            [2.6, 7.4],
            [3.4, 3.4],
            color=text_main,
            alpha=0.3,
            linewidth=2,
        )

        self.canvas.ax.text(
            5,
            2.6,
            f"完成 {count} 个学习轮次",
            ha="center",
            va="center",
            fontsize=13,
            color=text_main,
            alpha=0.9,
            fontweight="500",
        )

        self.canvas.fig.tight_layout(pad=0.4)
        self.canvas.draw()

        # 摘要
        if count > 0:
            avg_per_session = total_seconds / count
            self.summary_label.setText(
                f"<b>📊 今日学习总结</b><br>"
                f"共完成 <b style='color:#3b82f6'>{count}</b> 个学习轮次，"
                f"总计 <b style='color:#3b82f6'>{hours:.1f}</b> 小时；"
                f"平均每轮 <b style='color:#3b82f6'>{avg_per_session / 60:.0f}</b> 分钟"
            )
        else:
            self.summary_label.setText(
                "<b>📊 今日学习总结</b><br>"
                "今日还没有学习记录，开始你的学习之旅吧！💪"
            )

    def _show_month_view(self):
        """显示月度学习统计"""
        if self.canvas is None or self.date_label is None or self.summary_label is None:
            return

        year = self.current_date.year
        month = self.current_date.month

        self.date_label.setText(f"📆 {year}年{month}月")

        daily_totals = self.stats_manager.get_monthly_daily_totals(year, month)
        days = [d for d, _ in daily_totals]
        hours = [sec / 3600.0 for _, sec in daily_totals]

        self.canvas.ax.clear()
        self._apply_chart_theme()

        if days and max(hours) > 0:
            max_hour = max(hours)
            colors = []
            for h in hours:
                if h == 0:
                    colors.append("#e2e8f0" if self.style_mode == "light" else "#1f2937")
                elif h >= max_hour * 0.7:
                    colors.append("#3b82f6")
                elif h >= max_hour * 0.4:
                    colors.append("#60a5fa")
                else:
                    colors.append("#93c5fd")

            bars = self.canvas.ax.bar(
                days,
                hours,
                color=colors,
                alpha=0.9,
                edgecolor="#2563eb",
                linewidth=1.5,
                width=0.8,
            )

            label_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"
            for bar, h in zip(bars, hours):
                if h > 0:
                    height = bar.get_height()
                    self.canvas.ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{h:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color=label_color,
                        fontweight="600",
                    )

            avg_hour = sum(hours) / len(hours)
            if avg_hour > 0:
                self.canvas.ax.axhline(
                    y=avg_hour,
                    color="#ef4444",
                    linestyle="--",
                    linewidth=2,
                    alpha=0.6,
                    label=f"日均: {avg_hour:.1f}h",
                )

                # 根据主题选择图例文字颜色
                legend_label_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"

                legend = self.canvas.ax.legend(
                    loc="upper right",
                    bbox_to_anchor=(0.98, 0.98),  # 放在坐标轴内部右上角，稍微往里缩一点
                    framealpha=0.9,
                    fontsize=9,
                    facecolor="#ffffff" if self.style_mode == "light" else "#020617",
                    edgecolor="#cbd5e1" if self.style_mode == "light" else "#1f2937",
                )

                # 设置图例文字颜色，适配深色/浅色主题
                for text in legend.get_texts():
                    text.set_color(legend_label_color)

            axis_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"
            spine_color = "#cbd5e1" if self.style_mode == "light" else "#1f2937"
            grid_color = "#e5e7eb" if self.style_mode == "light" else "#1f2937"
            tick_color = "#64748b" if self.style_mode == "light" else "#e5e7eb"

            self.canvas.ax.set_xlabel("日期", fontsize=11, fontweight="bold", color=axis_color)
            self.canvas.ax.set_ylabel("学习时长 (小时)", fontsize=11, fontweight="bold", color=axis_color)
            self.canvas.ax.set_title(
                f"{year}年{month}月学习时间分布",
                fontsize=13,
                fontweight="bold",
                pad=12,
                color=axis_color,
            )

            self.canvas.ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=1, color=grid_color)
            self.canvas.ax.set_axisbelow(True)

            self.canvas.ax.spines["top"].set_visible(False)
            self.canvas.ax.spines["right"].set_visible(False)
            self.canvas.ax.spines["left"].set_color(spine_color)
            self.canvas.ax.spines["bottom"].set_color(spine_color)

            self.canvas.ax.tick_params(colors=tick_color, labelsize=8)
        else:
            msg_color = "#94a3b8" if self.style_mode == "light" else "#e5e7eb"
            self.canvas.ax.text(
                0.5,
                0.5,
                "本月暂无学习记录",
                ha="center",
                va="center",
                fontsize=16,
                color=msg_color,
                fontweight="600",
                transform=self.canvas.ax.transAxes,
            )
            self.canvas.ax.axis("off")

        self.canvas.fig.tight_layout(pad=0.8)
        self.canvas.draw()

        total_seconds = sum(sec for _, sec in daily_totals)
        days_with_data = sum(1 for _, sec in daily_totals if sec > 0)
        avg_seconds = total_seconds / len(daily_totals) if daily_totals else 0

        self.summary_label.setText(
            f"<b>📊 {year}年{month}月学习总结</b><br>"
            f"总学习 <b style='color:#3b82f6'>{total_seconds / 3600:.1f}</b> 小时，"
            f"日均 <b style='color:#3b82f6'>{avg_seconds / 3600:.1f}</b> 小时；"
            f"活跃 <b style='color:#3b82f6'>{days_with_data}</b> 天，"
            f"学习率 <b style='color:#3b82f6'>{(days_with_data / len(daily_totals) * 100) if daily_totals else 0:.0f}%</b>"
        )

    def _show_year_view(self):
        """显示年度学习统计"""
        if self.canvas is None or self.date_label is None or self.summary_label is None:
            return

        year = self.current_date.year
        self.date_label.setText(f"📈 {year}年度统计")

        monthly_totals = self.stats_manager.get_yearly_monthly_totals(year)
        months = [m for m, _ in monthly_totals]
        hours = [sec / 3600.0 for _, sec in monthly_totals]

        self.canvas.ax.clear()
        self._apply_chart_theme()

        if months and max(hours) > 0:
            avg_hour = sum(hours) / 12
            colors = ["#3b82f6" if h >= avg_hour else "#93c5fd" for h in hours]

            bars = self.canvas.ax.bar(
                months,
                hours,
                color=colors,
                alpha=0.9,
                edgecolor="#2563eb",
                linewidth=2,
                width=0.75,
            )

            label_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"
            for bar, h in zip(bars, hours):
                if h > 0:
                    height = bar.get_height()
                    self.canvas.ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{h:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                        fontweight="bold",
                        color=label_color,
                    )

            if avg_hour > 0:
                self.canvas.ax.axhline(
                    y=avg_hour,
                    color="#ef4444",
                    linestyle="--",
                    linewidth=2.2,
                    alpha=0.7,
                    label=f"月均: {avg_hour:.1f}h",
                )

                legend_label_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"

                legend = self.canvas.ax.legend(
                    loc="upper right",
                    bbox_to_anchor=(0.98, 0.98),
                    framealpha=0.95,
                    fontsize=9,
                    facecolor="#ffffff" if self.style_mode == "light" else "#020617",
                    edgecolor="#cbd5e1" if self.style_mode == "light" else "#1f2937",
                )

                for text in legend.get_texts():
                    text.set_color(legend_label_color)

            axis_color = "#1e293b" if self.style_mode == "light" else "#e5e7eb"
            spine_color = "#cbd5e1" if self.style_mode == "light" else "#1f2937"
            grid_color = "#e5e7eb" if self.style_mode == "light" else "#1f2937"
            tick_color = "#64748b" if self.style_mode == "light" else "#e5e7eb"

            self.canvas.ax.set_xlabel("月份", fontsize=11, fontweight="bold", color=axis_color)
            self.canvas.ax.set_ylabel("学习时长 (小时)", fontsize=11, fontweight="bold", color=axis_color)
            self.canvas.ax.set_title(
                f"{year}年度学习时间统计",
                fontsize=13,
                fontweight="bold",
                pad=12,
                color=axis_color,
            )

            self.canvas.ax.set_xticks(months)
            self.canvas.ax.set_xticklabels([f"{m}月" for m in months])

            self.canvas.ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=1, color=grid_color)
            self.canvas.ax.set_axisbelow(True)

            self.canvas.ax.spines["top"].set_visible(False)
            self.canvas.ax.spines["right"].set_visible(False)
            self.canvas.ax.spines["left"].set_color(spine_color)
            self.canvas.ax.spines["bottom"].set_color(spine_color)

            self.canvas.ax.tick_params(colors=tick_color, labelsize=8)
        else:
            msg_color = "#94a3b8" if self.style_mode == "light" else "#e5e7eb"
            self.canvas.ax.text(
                0.5,
                0.5,
                "本年暂无学习记录",
                ha="center",
                va="center",
                fontsize=16,
                color=msg_color,
                fontweight="600",
                transform=self.canvas.ax.transAxes,
            )
            self.canvas.ax.axis("off")

        self.canvas.fig.tight_layout(pad=0.8)
        self.canvas.draw()

        total_seconds = sum(sec for _, sec in monthly_totals)
        months_with_data = sum(1 for _, sec in monthly_totals if sec > 0)
        avg_seconds = total_seconds / 12 if total_seconds > 0 else 0
        max_month_hours = max(hours)
        max_month_idx = hours.index(max_month_hours) + 1 if max_month_hours > 0 else 0

        self.summary_label.setText(
            f"<b>📊 {year}年度学习总结</b><br>"
            f"全年总学习 <b style='color:#3b82f6'>{total_seconds / 3600:.1f}</b> 小时，"
            f"月均 <b style='color:#3b82f6'>{avg_seconds / 3600:.1f}</b> 小时；"
            f"活跃 <b style='color:#3b82f6'>{months_with_data}</b> 个月，"
            f"最高峰在 <b style='color:#3b82f6'>{max_month_idx}月</b> "
            f"({max_month_hours:.1f}小时)"
        )
