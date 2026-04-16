import sys
import os
import threading
import torch
import feedparser
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from transformers import pipeline

# تنظیمات منابع خبری
SOURCES = [
    {"name": "SouthFront", "url": "https://southfront.press/feed/"},
    {"name": "ZeroHedge", "url": "https://feeds.feedburner.com/zerohedge/feed"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"}
]

class AIProcessor(QThread):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    data_signal = pyqtSignal(list)

    def run(self):
        self.status_signal.emit("Loading Neural Engine...")
        device = 0 if torch.cuda.is_available() else -1
        
        try:
            # استفاده از مدل چندزبانه برای پشتیبانی از فارسی و انگلیسی
            analyzer = pipeline("sentiment-analysis", 
                                model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
                                device=device)
        except Exception as e:
            self.status_signal.emit(f"AI Error: {str(e)}")
            return

        news_list = []
        for i, src in enumerate(SOURCES):
            self.status_signal.emit(f"Scanning {src['name']}...")
            try:
                feed = feedparser.parse(src['url'])
                for entry in feed.entries[:6]:
                    text = entry.title + " " + getattr(entry, 'summary', '')
                    result = analyzer(text[:512])[0]
                    
                    tension = 10
                    if result['label'] == 'negative':
                        tension = int(result['score'] * 100)
                    elif result['label'] == 'positive':
                        tension = int((1 - result['score']) * 40)

                    news_list.append({
                        'title': entry.title,
                        'source': src['name'],
                        'tension': tension,
                        'label': result['label']
                    })
            except:
                continue
            self.progress_signal.emit(int((i + 1) / len(SOURCES) * 100))
        
        news_list.sort(key=lambda x: x['tension'], reverse=True)
        self.data_signal.emit(news_list)

class ModernUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRATEGIC AI MONITOR v2.0")
        self.resize(1000, 700)
        self.set_style()
        self.init_widgets()

    def set_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0f172a; }
            QTableWidget { background-color: #1e293b; color: white; border: none; gridline-color: #334155; }
            QHeaderView::section { background-color: #334155; color: #94a3b8; border: none; padding: 10px; }
            QPushButton { background-color: #2563eb; color: white; border-radius: 5px; padding: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #1d4ed8; }
            QProgressBar { border: 1px solid #334155; border-radius: 5px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #2563eb; }
        """)

    def init_widgets(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.btn = QPushButton("RUN GLOBAL ANALYSIS")
        self.btn.clicked.connect(self.start_work)
        layout.addWidget(self.btn)

        self.pbar = QProgressBar()
        layout.addWidget(self.pbar)

        self.status_lbl = QLabel("System Ready")
        self.status_lbl.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.status_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["TITLE", "SOURCE", "TENSION", "SENTIMENT"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def start_work(self):
        self.btn.setEnabled(False)
        self.worker = AIProcessor()
        self.worker.status_signal.connect(self.status_lbl.setText)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.data_signal.connect(self.fill_table)
        self.worker.start()

    def fill_table(self, data):
        self.table.setRowCount(len(data))
        for r, item in enumerate(data):
            self.table.setItem(r, 0, QTableWidgetItem(item['title']))
            self.table.setItem(r, 1, QTableWidgetItem(item['source']))
            
            t_item = QTableWidgetItem(f"{item['tension']}%")
            if item['tension'] > 70: t_item.setForeground(QColor("#ef4444"))
            elif item['tension'] > 40: t_item.setForeground(QColor("#f59e0b"))
            else: t_item.setForeground(QColor("#10b981"))
            
            self.table.setItem(r, 2, t_item)
            self.table.setItem(r, 3, QTableWidgetItem(item['label']))
        
        self.btn.setEnabled(True)
        self.status_lbl.setText("Analysis Finished.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ModernUI()
    window.show()
    sys.exit(app.exec())
