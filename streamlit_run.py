#!/usr/bin/env python3
"""
Streamlit 앱 실행 스크립트
"""

import os
import sys

# 프로젝트 루트 디렉토리를 sys.path에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Streamlit 앱 실행  
def main():
    from src.ui.main_window import run_streamlit_app
    run_streamlit_app()

if __name__ == "__main__":
    main()