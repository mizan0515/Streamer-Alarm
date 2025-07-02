#!/usr/bin/env python3
"""
간단한 EXE 빌드 스크립트
PyInstaller를 직접 호출하여 EXE 파일 생성
"""

import subprocess
import sys
import os
from pathlib import Path

def build_simple_exe():
    """간단한 EXE 빌드"""
    
    print("🔨 간단한 EXE 빌드 시작...")
    
    # PyInstaller 명령어
    cmd = [
        "pyinstaller",
        "--onefile",                    # 단일 파일
        "--windowed",                   # 콘솔 숨김
        "--name=StreamerAlarm",         # 파일명
        "--clean",                      # 이전 빌드 정리
        
        # 필수 모듈들 명시적 포함
        "--hidden-import=streamlit",
        "--hidden-import=streamlit.web.cli", 
        "--hidden-import=streamlit.web.server.server",
        "--hidden-import=playwright",
        "--hidden-import=win11toast",
        "--hidden-import=pystray",
        "--hidden-import=PIL",
        "--hidden-import=feedparser",
        "--hidden-import=httpx",
        "--hidden-import=psutil",
        
        # 소스 폴더 포함
        "--add-data=src;src",
        "--add-data=streamlit_run.py;.",
        
        # 아이콘 (있다면)
        "--icon=assets/icon.ico" if os.path.exists("assets/icon.ico") else "",
        
        # 메인 스크립트
        "main.py"
    ]
    
    # 빈 문자열 제거
    cmd = [arg for arg in cmd if arg]
    
    print(f"실행 명령어: {' '.join(cmd)}")
    
    try:
        # PyInstaller 실행
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ 빌드 성공!")
        
        # 결과 확인
        exe_path = Path("dist/StreamerAlarm.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / 1024 / 1024
            print(f"📦 생성된 파일: {exe_path}")
            print(f"📏 파일 크기: {size_mb:.1f} MB")
            return True
        else:
            print("❌ EXE 파일을 찾을 수 없습니다.")
            return False
            
    except subprocess.CalledProcessError as e:
        print("❌ 빌드 실패!")
        print(f"오류 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 스트리머 알림 앱 - 간단 빌드")
    print("=" * 50)
    
    # 현재 디렉토리 확인
    if not Path("main.py").exists():
        print("❌ main.py 파일을 찾을 수 없습니다.")
        print("💡 프로젝트 루트 디렉토리에서 실행해주세요.")
        return False
    
    # 빌드 실행
    success = build_simple_exe()
    
    if success:
        print("\n🎉 빌드 완료!")
        print("\n📋 사용 방법:")
        print("  • dist/StreamerAlarm.exe를 더블클릭하여 실행")
        print("  • 시스템 트레이에 아이콘이 나타납니다")
        print("  • 트레이 아이콘 우클릭 → '웹 인터페이스 열기'")
        
        # 실행 확인
        choice = input("\n빌드된 앱을 실행해보시겠습니까? (y/N): ")
        if choice.lower() == 'y':
            exe_path = Path("dist/StreamerAlarm.exe")
            if exe_path.exists():
                import subprocess
                subprocess.Popen([str(exe_path)])
                print("🚀 앱이 실행되었습니다!")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)