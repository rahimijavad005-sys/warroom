import sys
import threading
import torch
import feedparser
import requests
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QProgressBar, QAbstractItemView)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette
from transformers import pipeline

# تنظیمات منابع خبری استراتژیک
NEWS_SOURCES = [
    {"name": "SouthFront", "url": "https://southfront.press/feed/"},
    {"name": "ZeroHedge", "url": "https://feeds.feedburner.com/zerohedge/feed"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"name": "Defense One", "url": "https://www.defenseone.com/rss/all/"}
]

class AnalysisThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(list)

    def run(self):
        self.status.emit("در حال بررسی سخت‌افزار و لود مدل AI...")
        
        # تشخیص خودکار RTX 3050Ti یا هر GPU موجود
        device = 0 if torch.cuda.is_available() else -1
        gpu_name = torch.cuda.get_device_name(0) if device == 0 else "CPU"
        self.status.emit(f"در حال استفاده از: {gpu_name}")

        try:
            # مدل چندزبانه بهینه برای تحلیل احساسات و تنش
            classifier = pipeline("sentiment-analysis", 
                                  model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
                                  device=device)
        except Exception as e:
            self.status.emit(f"خطا در لود مدل: {str(e)}")
            return

        all_results = []
        total_steps = len(NEWS_SOURCES)

        for i, source in enumerate(NEWS_SOURCES):
            self.status.emit(f"در حال دریافت اخبار از: {source['name']}...")
            try:
                feed = feedparser.parse(source['url'])
                for entry in feed.entries[:7]:  # ۷ خبر برتر از هر منبع
                    text_to_analyze = f"{entry.title}. {getattr(entry, 'summary', '')}"
                    
                    # تحلیل توسط هوش مصنوعی
                    result = classifier(text_to_analyze[:512])[0] # محدودیت ۵۱۲ کاراکتر برای سرعت
                    label = result['label']
                    score = result['score']

                    # محاسبه امتیاز تنش (Tension Score)
                    tension = 10 # مقدار پایه
                    if label == 'negative':
                        tension = int(score * 100)
                    elif label == 'positive':
                        tension = int((1 - score) * 35)

                    all_results.append({
                        'title': entry.title,
                        'source': source['name'],
                        'tension': tension,
                        'status': "بحرانی" if tension > 75 else ("هشدار" if tension > 45 else "عادی"),
                        'link': entry.link
                    })
            except:
                continue
            
            self.progress.emit(int((i + 1) / total_steps * 100))

        # مرتب‌سازی بر اساس بیشترین تنش
        all_results.sort(key=lambda x: x['tension'], reverse=True)
        self.finished.emit(all_results)

class StrategicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Strategic Pulse Monitor v1.0")
        self.resize(1200, 800)
        self.init_ui()

    def init_ui(self):
        # تم تیره و نظامی (Military Dark Theme)
        self.setStyleSheet("""
            QMainWindow { background-color: #0b0f19; }
            QLabel { color: #94a3b8; font-weight: bold; }
            QPushButton { 
                background-color: #1e293b; color: #3b82f6; 
                border: 1px solid #3b82f6; padding: 10px; border-radius: 4px;
                font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #3b82f6; color: white; }
            QTableWidget { 
                background-color: #111827; color: #e2e8f0; 
                gridline-color: #1f2937; border: none; font-size: 13px;
            }
            QHeaderView::section { background-color: #1f2937; color: #94a3b8; border: none; padding: 8px; }
            QProgressBar { border: 1px solid #1f2937; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #2563eb; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # هدر برنامه
        header = QHBoxLayout()
        title = QLabel("سیستم تحلیل استراتژیک هوشمند (OSINT)")
        title.setStyleSheet("font-size: 20px; color: #f8fafc; font-family: 'Segoe UI';")
        header.addWidget(title)

        self.btn_run = QPushButton("شروع تحلیل وضعیت")
        self.btn_run.clicked.connect(self.run_analysis)
        header.addWidget(self.btn_run)
        layout.addLayout(header)

        # وضعیت و لودینگ
        self.status_lbl = QLabel("آماده به کار")
        layout.addWidget(self.status_lbl)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # جدول اطلاعات
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["عنوان خبر", "منبع استراتژیک", "امتیاز تنش", "وضعیت"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def run_analysis(self):
        self.btn_run.setEnabled(False)
        self.table.setRowCount(0)
        self.worker = AnalysisThread()
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status.connect(self.status_lbl.setText)
        self.worker.finished.connect(self.display_results)
        self.worker.start()

    def display_results(self, data):
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(item['title']))
            self.table.setItem(row, 1, QTableWidgetItem(item['source']))
            
            # رنگ‌بندی داینامیک تنش
            tension_val = item['tension']
            t_item = QTableWidgetItem(f"{tension_val}%")
            if tension_val > 75: t_item.setForeground(QColor("#ef4444")) # قرمز
            elif tension_val > 45: t_item.setForeground(QColor("#f59e0b")) # زرد
            else: t_item.setForeground(QColor("#10b981")) # سبز
            
            self.table.setItem(row, 2, t_item)
            self.table.setItem(row, 3, QTableWidgetItem(item['status']))
            
        self.btn_run.setEnabled(True)
        self.status_lbl.setText("تحلیل با موفقیت روی GPU انجام شد.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrategicApp()
    window.show()
    sys.exit(app.exec())
