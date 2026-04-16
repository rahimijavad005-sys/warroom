name: Build Military AI EXE

on: [push]

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install torch --index-url https://download.pytorch.org/whl/cpu
          pip install PyQt6 transformers feedparser beautifulsoup4 requests pyinstaller
      - name: Create EXE
        run: |
          pyinstaller --noconfirm --onefile --windowed --name "MilitaryAI_Monitor" main.py
      - name: Upload result
        uses: actions/upload-artifact@v3
        with:
          name: AI_Monitor_v1
          path: dist/MilitaryAI_Monitor.exe
