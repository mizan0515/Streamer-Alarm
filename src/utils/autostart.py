import os
import sys
import winreg
from typing import Optional
from ..utils.logger import logger

class AutoStartManager:
    def __init__(self):
        self.app_name = "StreamerAlarm"
        self.registry_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        
    def get_executable_path(self) -> str:
        """실행 파일 경로 가져오기"""
        if getattr(sys, 'frozen', False):
            # PyInstaller로 빌드된 실행파일인 경우
            return sys.executable
        else:
            # 개발 환경에서는 python 스크립트 경로
            script_path = os.path.abspath(sys.argv[0])
            python_path = sys.executable
            return f'"{python_path}" "{script_path}"'
    
    def is_autostart_enabled(self) -> bool:
        """자동 시작 설정 여부 확인"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_READ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, self.app_name)
                    return True
                except FileNotFoundError:
                    return False
        except Exception as e:
            logger.error(f"자동 시작 설정 확인 실패: {e}")
            return False
    
    def enable_autostart(self) -> bool:
        """자동 시작 설정 활성화"""
        try:
            executable_path = self.get_executable_path()
            
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, executable_path)
            
            logger.info(f"자동 시작 설정 활성화: {executable_path}")
            return True
            
        except Exception as e:
            logger.error(f"자동 시작 설정 활성화 실패: {e}")
            return False
    
    def disable_autostart(self) -> bool:
        """자동 시작 설정 비활성화"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, self.app_name)
                    logger.info("자동 시작 설정 비활성화")
                    return True
                except FileNotFoundError:
                    logger.info("자동 시작 설정이 이미 비활성화되어 있음")
                    return True
                    
        except Exception as e:
            logger.error(f"자동 시작 설정 비활성화 실패: {e}")
            return False
    
    def toggle_autostart(self) -> bool:
        """자동 시작 설정 토글"""
        if self.is_autostart_enabled():
            return self.disable_autostart()
        else:
            return self.enable_autostart()
    
    def get_current_registry_value(self) -> Optional[str]:
        """현재 레지스트리에 등록된 값 반환"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_key, 0, winreg.KEY_READ) as key:
                try:
                    value, _ = winreg.QueryValueEx(key, self.app_name)
                    return value
                except FileNotFoundError:
                    return None
        except Exception as e:
            logger.error(f"레지스트리 값 조회 실패: {e}")
            return None
    
    def update_autostart_path(self) -> bool:
        """자동 시작 경로 업데이트 (파일 위치가 변경된 경우)"""
        if not self.is_autostart_enabled():
            return True
        
        current_path = self.get_current_registry_value()
        new_path = self.get_executable_path()
        
        if current_path != new_path:
            logger.info(f"자동 시작 경로 업데이트: {current_path} -> {new_path}")
            return self.enable_autostart()
        
        return True

# 전역 자동 시작 관리자 인스턴스
autostart_manager = AutoStartManager()