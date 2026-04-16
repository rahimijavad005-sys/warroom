import sys
import torch
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from playwright.sync_api import sync_playwright
from transformers import pipeline

# لیست سایت‌هایی که باید مثل مرورگر به آن‌ها سر بزنیم
SOURCES = [
    {"name": "SouthFront", "url": "https://southfront.press/"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/tag/military/"},
    {"name": "Defense News", "url": "https://www.defensenews.com/"}
]

class BrowserWorker(QThread):
    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    data_signal = pyqtSignal(list)

    def run(self):
        self.status_signal.emit("در حال لود موتور مرورگر و هوش مصنوعی...")
        
        # تشخیص گرافیک RTX 3050Ti
        device = 0 if torch.cuda.is_available() else -1
        try:
            analyzer = pipeline("sentiment-analysis", 
                                model="lxyuan/distilbert-base-multilingual-cased-sentiments-student", 
                                device=device)
        except:
            analyzer = None

        results = []
        
        # استفاده از Playwright برای رفتار کاملاً مشابه مرورگر
        with sync_playwright() as p:
            self.status_signal.emit("مرورگر در حال آماده‌سازی (User-Agent: Chrome)...")
            browser = p.chromium.launch(headless=True) # مرورگر در پس‌زمینه کار می‌کند
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            for i, src in enumerate(SOURCES):
                try:
                    self.status_signal.emit(f"مرورگر در حال بازدید از: {src['name']}")
                    # شبیه‌سازی ورود واقعی به سایت
                    page.goto(src['url'], wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(2000) # وقفه انسانی

                    # استخراج تیترها از متن صفحه (DOM)
                    # اینجا تیترهای h1 تا h3 که معمولاً اخبار هستند را می‌گیریم
                    elements = page.locator("h1, h2, h3").all_inner_texts()
                    
                    count = 0
                    for text in elements:
                        if len(text.strip()) > 25 and count < 5:
                            tension = 10
                            if analyzer:
                                res = analyzer(text[:512])[0]
                                if res['label'] == 'negative':
                                    tension = int(res['score'] * 100)
                                else:
                                    tension = int((1 - res['score']) * 30)

                            results.append({
                                'title': text.strip(),
                                'source': src['name'],
                                'tension': tension,
                                'status': "بحرانی" if tension > 75 else "عادی"
                            })
                            count += 1
                except Exception as e:
                    print(f"Error visiting {src['name']}: {e}")
                
                self.progress_signal.emit(int((i + 1) / len(SOURCES) * 100))

            browser.close()
        
        results.sort(key=lambda x: x['tension'], reverse=True)
        self.data_signal.emit(results)

class StrategicApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI STRATEGIC OSINT - BROWSER ENGINE v3.0")
        self.resize(1100, 750)
        self.setup_ui()

    def setup_ui(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #020617; }
            QTableWidget { background-color: #0f172a; color: #f8fafc; border: 1px solid #1e293b; gridline-color: #1e293b; }
            QHeaderView::section { background-color: #1e293b; color: #94a3b8; padding: 10px; border: none; }
            QPushButton { background-color: #3b82f6; color: white; border-radius: 4px; padding: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #2563eb; }
            QProgressBar { border: 1px solid #1e293b; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #3b82f6; }
        """)

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)

        self.btn = QPushButton("شروع اسکن شبکه (Browser Emulation)")
        self.btn.clicked.connect(self.run_engine)
        layout.addWidget(self.btn)

        self.pbar = QProgressBar()
        layout.addWidget(self.pbar)

        self.status_lbl = QLabel("سیستم آماده تحلیل شبکه")
        self.status_lbl.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(self.status_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["تیتر استخراج شده", "منبع", "سطح تنش", "وضعیت"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

    def run_engine(self):
        self.btn.setEnabled(False)
        self.table.setRowCount(0)
        self.worker = BrowserWorker()
        self.worker.status_signal.connect(self.status_lbl.setText)
        self.worker.progress_signal.connect(self.pbar.setValue)
        self.worker.data_signal.connect(self.display_data)
        self.worker.start()

    def display_data(self, data):
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(item['title']))
            self.table.setItem(row, 1, QTableWidgetItem(item['source']))
            
            t_val = item['tension']
            t_item = QTableWidgetItem(f"{t_val}%")
            if t_val > 75: t_item.setForeground(QColor("#ef4444"))
            elif t_val > 45: t_item.setForeground(QColor("#f59e0b"))
            else: t_item.setForeground(QColor("#10b981"))
            
            self.table.setItem(row, 2, t_item)
            self.table.setItem(row, 3, QTableWidgetItem(item['status']))
            
        self.btn.setEnabled(True)
        self.status_lbl.setText("اسکن با موفقیت به پایان رسید.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StrategicApp()
    window.show()
    sys.exit(app.exec())
