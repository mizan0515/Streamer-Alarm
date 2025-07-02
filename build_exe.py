#!/usr/bin/env python3
"""
스트리머 알림 앱 EXE 빌드 스크립트
PyInstaller를 사용하여 Windows 실행 파일 생성
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def build_exe():
    """EXE 파일 빌드"""
    
    # 프로젝트 루트 디렉토리
    project_root = Path(__file__).parent
    
    # PyInstaller 명령어 구성
    cmd = [
        "pyinstaller",
        "--onefile",                    # 단일 실행 파일 생성
        "--windowed",                   # 콘솔 창 숨기기
        "--name=StreamerAlarm",         # 실행 파일 이름
        "--icon=assets/icon.ico",       # 아이콘 파일 (있다면)
        "--add-data=src;src",           # src 폴더 포함
        "--add-data=data;data",         # data 폴더 포함 (템플릿용)
        "--add-data=streamlit_run.py;.",# streamlit_run.py 포함
        "--hidden-import=streamlit",    # Streamlit 모듈 포함
        "--hidden-import=playwright",   # Playwright 모듈 포함
        "--hidden-import=win11toast",   # Windows 알림 모듈 포함
        "--hidden-import=pystray",      # 시스템 트레이 모듈 포함
        "--hidden-import=PIL",          # Pillow 모듈 포함
        "--hidden-import=feedparser",   # RSS 파서 모듈 포함
        "--hidden-import=httpx",        # HTTP 클라이언트 모듈 포함
        "--hidden-import=psutil",       # 시스템 유틸리티 모듈 포함
        "--clean",                      # 이전 빌드 정리
        "main.py"                       # 메인 스크립트
    ]
    
    print("🔨 EXE 파일 빌드 시작...")
    print(f"명령어: {' '.join(cmd)}")
    
    try:
        # PyInstaller 실행
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ 빌드 성공!")
        
        # 결과 파일 위치
        exe_path = project_root / "dist" / "StreamerAlarm.exe"
        if exe_path.exists():
            print(f"📦 생성된 EXE 파일: {exe_path}")
            print(f"📏 파일 크기: {exe_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ 빌드 실패!")
        print(f"오류: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False

def create_installer_script():
    """설치 스크립트 생성"""
    installer_content = '''@echo off
echo 🎯 스트리머 알림 앱 설치
echo.

REM 설치 디렉토리 생성
set INSTALL_DIR=%LOCALAPPDATA%\\StreamerAlarm
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM 실행 파일 복사
copy "StreamerAlarm.exe" "%INSTALL_DIR%\\"
if errorlevel 1 (
    echo ❌ 파일 복사 실패
    pause
    exit /b 1
)

REM 데이터 디렉토리 생성
if not exist "%INSTALL_DIR%\\data" mkdir "%INSTALL_DIR%\\data"

REM 바탕화면 바로가기 생성
set SHORTCUT_PATH=%USERPROFILE%\\Desktop\\스트리머 알림.lnk
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\StreamerAlarm.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Save()"

REM 시작 메뉴 등록
set START_MENU_DIR=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
copy "%USERPROFILE%\\Desktop\\스트리머 알림.lnk" "%START_MENU_DIR%\\"

echo ✅ 설치 완료!
echo 📂 설치 위치: %INSTALL_DIR%
echo 🖥️ 바탕화면 바로가기 생성됨
echo 📋 시작 메뉴에 등록됨
echo.
echo 설치된 앱을 실행하시겠습니까? (Y/N)
set /p CHOICE=
if /i "%CHOICE%"=="Y" start "" "%INSTALL_DIR%\\StreamerAlarm.exe"

pause
'''
    
    with open("installer.bat", "w", encoding="cp949") as f:
        f.write(installer_content)
    
    print("📋 설치 스크립트 생성: installer.bat")

def create_uninstaller_script():
    """제거 스크립트 생성"""
    uninstaller_content = '''@echo off
echo 🗑️ 스트리머 알림 앱 제거
echo.

set INSTALL_DIR=%LOCALAPPDATA%\\StreamerAlarm

REM 실행 중인 프로세스 종료
taskkill /f /im StreamerAlarm.exe 2>nul

REM 설치 디렉토리 삭제
if exist "%INSTALL_DIR%" (
    rmdir /s /q "%INSTALL_DIR%"
    echo ✅ 프로그램 파일 삭제됨
)

REM 바탕화면 바로가기 삭제
if exist "%USERPROFILE%\\Desktop\\스트리머 알림.lnk" (
    del "%USERPROFILE%\\Desktop\\스트리머 알림.lnk"
    echo ✅ 바탕화면 바로가기 삭제됨
)

REM 시작 메뉴에서 삭제
if exist "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\스트리머 알림.lnk" (
    del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\스트리머 알림.lnk"
    echo ✅ 시작 메뉴에서 삭제됨
)

echo.
echo ✅ 제거 완료!
pause
'''
    
    with open("uninstaller.bat", "w", encoding="cp949") as f:
        f.write(uninstaller_content)
    
    print("🗑️ 제거 스크립트 생성: uninstaller.bat")

def main():
    """메인 함수"""
    print("🚀 스트리머 알림 앱 빌드 도구")
    print("=" * 50)
    
    # EXE 빌드
    if build_exe():
        print("\n📦 추가 파일 생성 중...")
        create_installer_script()
        create_uninstaller_script()
        
        print("\n🎉 빌드 완료!")
        print("\n📋 생성된 파일들:")
        print("  • dist/StreamerAlarm.exe - 메인 실행 파일")
        print("  • installer.bat - 설치 스크립트")
        print("  • uninstaller.bat - 제거 스크립트")
        print("\n💡 사용 방법:")
        print("  1. dist/StreamerAlarm.exe를 직접 실행")
        print("  2. 또는 installer.bat으로 시스템에 설치")
        
    else:
        print("\n❌ 빌드 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main()