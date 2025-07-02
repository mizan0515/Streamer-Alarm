#!/usr/bin/env python3
"""
Playwright 브라우저 경로 및 실행 관련 유틸리티
PyInstaller 환경에서 Chromium 브라우저 경로를 올바르게 찾기 위한 모듈
"""

import os
import sys
import platform
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from ..utils.logger import logger

class PlaywrightUtils:
    """Playwright 브라우저 관리 유틸리티"""
    
    @staticmethod
    def is_executable_environment() -> bool:
        """PyInstaller로 빌드된 실행 파일 환경인지 확인"""
        return getattr(sys, 'frozen', False)
    
    @staticmethod
    def get_chromium_executable_path() -> Optional[str]:
        """Chromium 브라우저 실행 파일 경로 찾기"""
        try:
            if PlaywrightUtils.is_executable_environment():
                logger.info("🔍 EXE 환경에서 Chromium 브라우저 경로 탐지 시작")
                return PlaywrightUtils._find_chromium_in_exe_environment()
            else:
                logger.info("🔍 일반 Python 환경에서 Chromium 브라우저 경로 탐지")
                return PlaywrightUtils._find_chromium_in_normal_environment()
                
        except Exception as e:
            logger.error(f"💥 Chromium 브라우저 경로 탐지 실패: {e}")
            return None
    
    @staticmethod
    def _find_chromium_in_exe_environment() -> Optional[str]:
        """EXE 환경에서 Chromium 브라우저 경로 찾기"""
        try:
            # 1순위: EXE와 같은 디렉토리의 playwright 폴더
            exe_dir = Path(sys.executable).parent
            exe_playwright_path = exe_dir / "playwright"
            
            logger.debug(f"📂 EXE 디렉토리 Playwright 경로 확인: {exe_playwright_path}")
            chromium_path = PlaywrightUtils._find_chromium_in_directory(exe_playwright_path)
            if chromium_path:
                logger.info(f"✅ EXE 디렉토리에서 Chromium 발견: {chromium_path}")
                return chromium_path
            
            # 2순위: _MEIPASS 임시 디렉토리 (PyInstaller)
            if hasattr(sys, '_MEIPASS'):
                meipass_playwright_path = Path(sys._MEIPASS) / "playwright"
                logger.debug(f"📂 _MEIPASS Playwright 경로 확인: {meipass_playwright_path}")
                chromium_path = PlaywrightUtils._find_chromium_in_directory(meipass_playwright_path)
                if chromium_path:
                    logger.info(f"✅ _MEIPASS에서 Chromium 발견: {chromium_path}")
                    return chromium_path
            
            # 3순위: 사용자 AppData의 Playwright 설치
            user_playwright_path = PlaywrightUtils._get_user_playwright_path()
            if user_playwright_path:
                logger.debug(f"📂 사용자 Playwright 경로 확인: {user_playwright_path}")
                chromium_path = PlaywrightUtils._find_chromium_in_directory(user_playwright_path)
                if chromium_path:
                    logger.info(f"✅ 사용자 디렉토리에서 Chromium 발견: {chromium_path}")
                    return chromium_path
            
            # 4순위: 시스템 전역 Playwright 설치
            system_paths = PlaywrightUtils._get_system_playwright_paths()
            for path in system_paths:
                logger.debug(f"📂 시스템 Playwright 경로 확인: {path}")
                chromium_path = PlaywrightUtils._find_chromium_in_directory(path)
                if chromium_path:
                    logger.info(f"✅ 시스템에서 Chromium 발견: {chromium_path}")
                    return chromium_path
            
            logger.warning("❌ EXE 환경에서 Chromium 브라우저를 찾을 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"💥 EXE 환경 Chromium 탐지 오류: {e}")
            return None
    
    @staticmethod
    def _find_chromium_in_normal_environment() -> Optional[str]:
        """일반 Python 환경에서 Chromium 브라우저 경로 찾기"""
        try:
            # 일반 환경에서는 Playwright가 자동으로 관리하므로 None 반환
            # (Playwright가 기본 경로를 사용하도록 함)
            
            # 하지만 검증을 위해 경로 확인
            user_playwright_path = PlaywrightUtils._get_user_playwright_path()
            if user_playwright_path:
                chromium_path = PlaywrightUtils._find_chromium_in_directory(user_playwright_path)
                if chromium_path:
                    logger.info(f"✅ 일반 환경에서 Chromium 확인됨: {chromium_path}")
                    # 일반 환경에서는 경로를 명시하지 않고 Playwright 기본값 사용
                    return None
            
            logger.info("📍 일반 환경에서는 Playwright 기본 경로 사용")
            return None
            
        except Exception as e:
            logger.error(f"💥 일반 환경 Chromium 확인 오류: {e}")
            return None
    
    @staticmethod
    def _find_chromium_in_directory(base_path: Path) -> Optional[str]:
        """지정된 디렉토리에서 Chromium 실행 파일 찾기"""
        try:
            if not base_path.exists():
                return None
            
            system = platform.system().lower()
            
            if system == "windows":
                # Windows에서 Chromium 실행 파일 패턴
                patterns = [
                    "**/chromium*/chrome.exe",
                    "**/chrome-win*/chrome.exe", 
                    "**/chrome.exe",
                    "**/chromium.exe"
                ]
            elif system == "linux":
                # Linux에서 Chromium 실행 파일 패턴
                patterns = [
                    "**/chromium*/chrome",
                    "**/chrome-linux*/chrome",
                    "**/chrome",
                    "**/chromium"
                ]
            elif system == "darwin":
                # macOS에서 Chromium 실행 파일 패턴
                patterns = [
                    "**/Chromium.app/Contents/MacOS/Chromium",
                    "**/Chrome.app/Contents/MacOS/Chrome"
                ]
            else:
                logger.warning(f"⚠️ 지원되지 않는 운영체제: {system}")
                return None
            
            # 패턴으로 실행 파일 검색
            for pattern in patterns:
                for chromium_exe in base_path.glob(pattern):
                    if chromium_exe.is_file():
                        logger.debug(f"🎯 Chromium 실행 파일 발견: {chromium_exe}")
                        return str(chromium_exe)
            
            return None
            
        except Exception as e:
            logger.debug(f"디렉토리 {base_path} 검색 중 오류: {e}")
            return None
    
    @staticmethod
    def _get_user_playwright_path() -> Optional[Path]:
        """사용자별 Playwright 설치 경로 반환"""
        try:
            system = platform.system().lower()
            
            if system == "windows":
                # Windows: %USERPROFILE%\AppData\Local\ms-playwright
                appdata = os.environ.get('LOCALAPPDATA')
                if appdata:
                    return Path(appdata) / "ms-playwright"
            elif system == "linux":
                # Linux: ~/.cache/ms-playwright
                home = os.environ.get('HOME')
                if home:
                    return Path(home) / ".cache" / "ms-playwright"
            elif system == "darwin":
                # macOS: ~/Library/Caches/ms-playwright
                home = os.environ.get('HOME')
                if home:
                    return Path(home) / "Library" / "Caches" / "ms-playwright"
            
            return None
            
        except Exception as e:
            logger.debug(f"사용자 Playwright 경로 탐지 오류: {e}")
            return None
    
    @staticmethod
    def _get_system_playwright_paths() -> list[Path]:
        """시스템 전역 Playwright 설치 경로들 반환"""
        try:
            system = platform.system().lower()
            paths = []
            
            if system == "windows":
                # Windows 시스템 경로들
                program_files = os.environ.get('PROGRAMFILES', r'C:\Program Files')
                program_files_x86 = os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)')
                
                paths.extend([
                    Path(program_files) / "Playwright",
                    Path(program_files_x86) / "Playwright",
                    Path(r"C:\playwright"),
                ])
                
            elif system == "linux":
                # Linux 시스템 경로들
                paths.extend([
                    Path("/usr/local/lib/playwright"),
                    Path("/opt/playwright"),
                    Path("/usr/share/playwright")
                ])
                
            elif system == "darwin":
                # macOS 시스템 경로들
                paths.extend([
                    Path("/usr/local/lib/playwright"),
                    Path("/opt/playwright"),
                    Path("/Applications/Playwright")
                ])
            
            return paths
            
        except Exception as e:
            logger.debug(f"시스템 Playwright 경로 탐지 오류: {e}")
            return []
    
    @staticmethod
    def get_launch_options(executable_path: Optional[str] = None) -> Dict[str, Any]:
        """Playwright 브라우저 실행 옵션 생성"""
        try:
            options = {
                "headless": False,
                "viewport": {"width": 1280, "height": 720},
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows", 
                    "--disable-renderer-backgrounding",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
            }
            
            # EXE 환경에서 실행 파일 경로가 지정된 경우
            if executable_path and PlaywrightUtils.is_executable_environment():
                logger.info(f"🎯 Chromium 실행 파일 경로 지정: {executable_path}")
                options["executable_path"] = executable_path
                
                # EXE 환경에서 추가 안정성 옵션
                options["args"].extend([
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu-sandbox",
                    "--disable-software-rasterizer"
                ])
            
            return options
            
        except Exception as e:
            logger.error(f"💥 브라우저 실행 옵션 생성 오류: {e}")
            return {
                "headless": False,
                "viewport": {"width": 1280, "height": 720}
            }
    
    @staticmethod
    def check_chromium_availability() -> bool:
        """Chromium 브라우저 사용 가능 여부 확인"""
        try:
            chromium_path = PlaywrightUtils.get_chromium_executable_path()
            
            if chromium_path and os.path.isfile(chromium_path):
                logger.info(f"✅ Chromium 브라우저 사용 가능: {chromium_path}")
                return True
            elif not PlaywrightUtils.is_executable_environment():
                # 일반 환경에서는 Playwright가 자동 관리
                logger.info("✅ 일반 환경에서 Playwright 자동 관리")
                return True
            else:
                logger.warning("❌ Chromium 브라우저를 찾을 수 없음")
                return False
                
        except Exception as e:
            logger.error(f"💥 Chromium 가용성 확인 오류: {e}")
            return False
    
    @staticmethod
    def install_chromium_if_missing():
        """Chromium이 없는 경우 설치 시도"""
        try:
            if not PlaywrightUtils.check_chromium_availability():
                logger.info("🔧 Chromium 브라우저 자동 설치 시도")
                
                # subprocess로 playwright install 실행
                import subprocess
                
                cmd = [sys.executable, "-m", "playwright", "install", "chromium"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logger.info("✅ Chromium 브라우저 설치 성공")
                    return True
                else:
                    logger.error(f"❌ Chromium 설치 실패: {result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"💥 Chromium 설치 시도 중 오류: {e}")
            return False

# 편의를 위한 함수들
def get_chromium_path() -> Optional[str]:
    """Chromium 브라우저 경로 반환 (간단한 래퍼)"""
    return PlaywrightUtils.get_chromium_executable_path()

def get_browser_launch_options(headless: bool = False) -> Dict[str, Any]:
    """브라우저 실행 옵션 반환 (간단한 래퍼)"""
    chromium_path = PlaywrightUtils.get_chromium_executable_path()
    options = PlaywrightUtils.get_launch_options(chromium_path)
    options["headless"] = headless
    return options

def is_chromium_available() -> bool:
    """Chromium 사용 가능 여부 확인 (간단한 래퍼)"""
    return PlaywrightUtils.check_chromium_availability()