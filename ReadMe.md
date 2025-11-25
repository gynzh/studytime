# 专注学习计时器（PySide6）

一个桌面端的小巧学习计时工具：支持学习 / 休息倒计时、随机微休提醒、学习统计图表，以及可选浅色 / 深色主题界面。使用 Python + PySide6 开发，数据本地存储，无需联网。

---

## 功能特性

- 🕒 **学习计时**
  - 可配置学习总时长、收尾提醒时间。
  - 自动切换到休息倒计时，休息结束后可一键开始下一轮。

- 😴 **休息 & 微休**
  - 支持配置休息时长。
  - 在学习阶段，根据「微休最小/最大间隔」随机给出微休提醒（不打断计时）。:contentReference[oaicite:4]{index=4}  

- 🔔 **多种提示音**
  - 微休提示、收尾提示、学习结束、休息结束均可设置独立音效。
  - 若未设置音效文件，默认使用系统 beep。:contentReference[oaicite:5]{index=5}  

- 📊 **学习统计**
  - 记录每轮学习开始/结束时间与学习时长（保存在 `study_stats.db`）。:contentReference[oaicite:6]{index=6}  
  - 提供日 / 月 / 年三种统计视图，支持图表展示学习时长分布与总结。:contentReference[oaicite:7]{index=7}  

- 🎨 **主题切换**
  - 在「设置」窗口中可选择 **浅色主题** / **深色主题**。
  - 主计时条和统计窗口会使用相同主题风格（下次打开统计窗口时生效，或在设置保存后实时刷新）。

- 🧷 **悬浮胶囊窗口**
  - 无边框、总在最前的小胶囊窗口，显示倒计时。
  - 支持左键拖动、右键弹出菜单（开始 / 暂停 / 结束 / 设置 / 查看统计 / 退出）。:contentReference[oaicite:8]{index=8}  

---

## 环境要求

- Python 3.9+
- 依赖库：
  - `PySide6`
  - `matplotlib`（用于统计图表）

安装依赖：

```bash
pip install PySide6 matplotlib



打包命令：pyinstaller --noconsole --onefile --name StudyTimer --icon=StudyTimer.ico mian.py

git使用教程：

cd "D:\桌面\typora文件\StudyTimer"

git status                # 看看改了哪些文件
git add 修改的文件 或 git add .
git commit -m "说明本次改了什么"
git push                  # 推到 GitHub