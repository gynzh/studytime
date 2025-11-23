from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from config_manager import ConfigManager
from sound_manager import SoundManager
from stats_manager import StatsManager
from timer_controller import TimerController
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    config_manager = ConfigManager()
    stats_manager = StatsManager()
    time_config = config_manager.get_time_config()
    sound_config = config_manager.get_sound_config()

    timer_controller = TimerController(time_config)
    sound_manager = SoundManager(sound_config)

    window = MainWindow(
        config_manager=config_manager,
        stats_manager=stats_manager,
        sound_manager=sound_manager,
        timer_controller=timer_controller,
    )
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
