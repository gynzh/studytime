from __future__ import annotations

import sqlite3
from datetime import datetime, date
from typing import List, Tuple

DB_FILE = "study_stats.db"


class StatsManager:
    """负责记录每轮学习数据,并提供按日/月/年统计"""

    def __init__(self, path: str = DB_FILE):
        self.path = path
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                study_seconds INTEGER NOT NULL
            )
            """
        )
        self._conn.commit()

    def record_session(self, start_dt: datetime, end_dt: datetime, study_seconds: int):
        self._conn.execute(
            "INSERT INTO sessions(start_time, end_time, study_seconds) VALUES (?, ?, ?)",
            (int(start_dt.timestamp()), int(end_dt.timestamp()), int(study_seconds)),
        )
        self._conn.commit()

    def get_daily_total(self, day: date) -> Tuple[int, int]:
        """
        返回:当日完成轮数,总学习秒数

        修改逻辑:只要学习轮次的开始时间在当天,就计入当天统计
        这样可以避免跨天学习导致的统计混乱
        """
        start_ts = int(datetime(day.year, day.month, day.day, 0, 0, 0).timestamp())
        end_ts = int(datetime(day.year, day.month, day.day, 23, 59, 59).timestamp())
        cur = self._conn.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(study_seconds), 0)
            FROM sessions
            WHERE start_time >= ? AND start_time <= ?
            """,
            (start_ts, end_ts),
        )
        count, total = cur.fetchone()
        return int(count), int(total)

    def get_monthly_daily_totals(self, year: int, month: int) -> List[Tuple[int, int]]:
        """
        返回指定年/月中每天的学习总秒数 (day, seconds) 列表

        优化:使用单次数据库查询获取整月数据,提高效率
        """
        # 计算月份的第一天和最后一天
        from calendar import monthrange
        first_day = date(year, month, 1)
        last_day_num = monthrange(year, month)[1]
        last_day = date(year, month, last_day_num)

        start_ts = int(datetime(year, month, 1, 0, 0, 0).timestamp())
        end_ts = int(datetime(year, month, last_day_num, 23, 59, 59).timestamp())

        # 单次查询获取本月所有数据
        cur = self._conn.execute(
            """
            SELECT start_time, study_seconds
            FROM sessions
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time
            """,
            (start_ts, end_ts),
        )

        # 按日期分组统计
        daily_totals_dict = {}
        for start_time, study_seconds in cur.fetchall():
            dt = datetime.fromtimestamp(start_time)
            day_num = dt.day
            if day_num not in daily_totals_dict:
                daily_totals_dict[day_num] = 0
            daily_totals_dict[day_num] += study_seconds

        # 构建完整的日期列表(包括无数据的日期)
        result = []
        for d in range(1, last_day_num + 1):
            total = daily_totals_dict.get(d, 0)
            result.append((d, total))

        return result

    def get_yearly_monthly_totals(self, year: int) -> List[Tuple[int, int]]:
        """
        返回指定年中每个月的学习总秒数 (month, seconds) 列表

        优化:使用单次数据库查询获取全年数据,避免重复查询
        """
        start_ts = int(datetime(year, 1, 1, 0, 0, 0).timestamp())
        end_ts = int(datetime(year, 12, 31, 23, 59, 59).timestamp())

        # 单次查询获取全年所有数据
        cur = self._conn.execute(
            """
            SELECT start_time, study_seconds
            FROM sessions
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time
            """,
            (start_ts, end_ts),
        )

        # 按月份分组统计
        monthly_totals_dict = {}
        for start_time, study_seconds in cur.fetchall():
            dt = datetime.fromtimestamp(start_time)
            month_num = dt.month
            if month_num not in monthly_totals_dict:
                monthly_totals_dict[month_num] = 0
            monthly_totals_dict[month_num] += study_seconds

        # 构建完整的月份列表(包括无数据的月份)
        result = []
        for m in range(1, 13):
            total = monthly_totals_dict.get(m, 0)
            result.append((m, total))

        return result

    def close(self):
        self._conn.close()
