from __future__ import annotations

import sqlite3
from datetime import datetime, date
from typing import List, Tuple

DB_FILE = "study_stats.db"


class StatsManager:
    """负责记录每轮学习数据，并提供按日 / 月统计"""

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
        """返回：当日完成轮数，总学习秒数"""
        start_ts = int(datetime(day.year, day.month, day.day, 0, 0, 0).timestamp())
        end_ts = int(datetime(day.year, day.month, day.day, 23, 59, 59).timestamp())
        cur = self._conn.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(study_seconds), 0)
            FROM sessions
            WHERE start_time BETWEEN ? AND ?
            """,
            (start_ts, end_ts),
        )
        count, total = cur.fetchone()
        return int(count), int(total)

    def get_monthly_daily_totals(self, year: int, month: int) -> List[Tuple[int, int]]:
        """返回指定年/月中每天的学习总秒数 (day, seconds) 列表"""
        if month == 12:
            from datetime import date as DateType
            next_month = DateType(year + 1, 1, 1)
        else:
            from datetime import date as DateType
            next_month = DateType(year, month + 1, 1)
        first_day = date(year, month, 1)
        days = (next_month - first_day).days

        result = []
        for d in range(1, days + 1):
            day_date = date(year, month, d)
            _, total = self.get_daily_total(day_date)
            result.append((d, total))
        return result

    def close(self):
        self._conn.close()
