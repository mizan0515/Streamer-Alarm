#!/usr/bin/env python3
"""
Python 실행 환경 관리 유틸리티
PyInstaller 환경에서 올바른 Python 인터프리터를 찾기 위한 모듈
"""

import os
import sys
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
from ..utils.logger import logger

class PythonUtils:
    """Python 실행 환경 관리 유틸리티"""
    
    @staticmethod
    def is_executable_environment() -> bool:
        """PyInstaller로 빌드된 실행 파일 환경인지 확인"""
        return getattr(sys, 'frozen', False)
    
    @staticmethod
    def find_python_interpreter() -> str:
        """올바른 Python 인터프리터 경로 찾기"""
        try:
            if PythonUtils.is_executable_environment():
                logger.info("🔍 EXE 환경에서 Python 인터프리터 탐지")
                return PythonUtils._find_python_in_exe_environment()
            else:
                logger.info("🔍 일반 환경에서 Python 인터프리터 사용")
                return sys.executable
                
        except Exception as e:
            logger.error(f"💥 Python 인터프리터 탐지 실패: {e}")
            return sys.executable
    
    @staticmethod
    def _find_python_in_exe_environment() -> str:
        """EXE 환경에서 Python 인터프리터 경로 찾기"""
        try:
            # EXE 환경에서는 sys.executable을 그대로 사용
            # PyInstaller로 패키징된 EXE는 Python 런타임을 내장하고 있음
            logger.info(f"✅ EXE 환경에서 sys.executable 사용: {sys.executable}")
            return sys.executable
            
        except Exception as e:
            logger.error(f"💥 EXE 환경 Python 탐지 오류: {e}")
            return sys.executable
    
    @staticmethod
    def _find_python_from_environment() -> Optional[str]:
        """환경변수에서 Python 경로 찾기"""
        try:
            # 다양한 환경변수 확인
            env_vars = [
                'PYTHON_EXECUTABLE',
                'PYTHON_PATH', 
                'PYTHONEXE',
                'VIRTUAL_ENV'  # 가상환경의 경우
            ]
            
            for env_var in env_vars:
                env_value = os.environ.get(env_var)
                if env_value:
                    # VIRTUAL_ENV인 경우 Scripts/python.exe 추가
                    if env_var == 'VIRTUAL_ENV':
                        python_path = os.path.join(env_value, 'Scripts', 'python.exe')
                        if os.path.isfile(python_path):
                            return python_path
                    elif os.path.isfile(env_value):
                        return env_value
            
            return None
            
        except Exception as e:
            logger.debug(f"환경변수 Python 탐지 오류: {e}")
            return None
    
    @staticmethod
    def _get_common_python_paths() -> List[str]:
        """일반적인 Python 설치 경로들 반환"""
        try:
            paths = []
            
            # Windows 일반 경로들
            if os.name == 'nt':
                # Python Launcher를 통한 최신 버전 찾기
                try:
                    result = subprocess.run(['py', '-c', 'import sys; print(sys.executable)'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and result.stdout.strip():
                        py_path = result.stdout.strip()
                        if os.path.isfile(py_path):
                            paths.append(py_path)
                            logger.debug(f"Python Launcher로 발견: {py_path}")
                except:
                    pass
                
                # 일반적인 Windows Python 설치 경로들
                base_paths = [
                    os.path.expandvars(r'%LOCALAPPDATA%\Programs\Python'),
                    r'C:\Python3*',
                    r'C:\Program Files\Python*',
                    r'C:\Program Files (x86)\Python*',
                ]
                
                for base_path in base_paths:
                    if '*' in base_path:
                        # 와일드카드 경로 처리
                        import glob
                        for matched_path in glob.glob(base_path):
                            python_exe = os.path.join(matched_path, 'python.exe')
                            if os.path.isfile(python_exe):
                                paths.append(python_exe)
                    else:
                        # 버전별 경로 확인
                        for version in ['311', '312', '39', '310']:
                            python_exe = os.path.join(base_path, f'Python{version}', 'python.exe')
                            if os.path.isfile(python_exe):
                                paths.append(python_exe)
            
            # Linux/macOS 경로들
            else:
                unix_paths = [
                    '/usr/bin/python3',
                    '/usr/bin/python',
                    '/usr/local/bin/python3',
                    '/usr/local/bin/python',
                    '/opt/python/bin/python3',
                    os.path.expanduser('~/.pyenv/shims/python3'),
                ]
                for path in unix_paths:
                    if os.path.isfile(path):
                        paths.append(path)
            
            return paths
            
        except Exception as e:
            logger.debug(f"일반 Python 경로 탐지 오류: {e}")
            return []
    
    @staticmethod
    def _is_valid_python(python_path: str) -> bool:
        """Python 실행 파일이 유효한지 확인"""
        try:
            # 간단한 Python 명령 실행해서 확인
            result = subprocess.run([python_path, '-c', 'import sys; print(sys.version)'], 
                                  capture_output=True, text=True, timeout=5)
            
            is_valid = result.returncode == 0 and 'Python' in result.stdout
            if is_valid:
                version = result.stdout.strip().split()[0]
                logger.debug(f"유효한 Python 발견: {python_path} (버전: {version})")
            
            return is_valid
            
        except Exception:
            return False
    
    @staticmethod
    def setup_pythonpath_for_exe() -> Dict[str, str]:
        """EXE 환경에서 PYTHONPATH 설정"""
        try:
            env = os.environ.copy()
            
            if PythonUtils.is_executable_environment():
                # _MEIPASS 디렉토리를 PYTHONPATH에 추가
                if hasattr(sys, '_MEIPASS'):
                    meipass_path = sys._MEIPASS
                    current_pythonpath = env.get('PYTHONPATH', '')
                    
                    if current_pythonpath:
                        env['PYTHONPATH'] = f"{meipass_path}{os.pathsep}{current_pythonpath}"
                    else:
                        env['PYTHONPATH'] = meipass_path
                    
                    logger.debug(f"PYTHONPATH 설정: {env['PYTHONPATH']}")
                
                # EXE 디렉토리도 추가
                exe_dir = os.path.dirname(sys.executable)
                current_path = env.get('PATH', '')
                if exe_dir not in current_path:
                    env['PATH'] = f"{exe_dir}{os.pathsep}{current_path}"
            
            return env
            
        except Exception as e:
            logger.error(f"💥 PYTHONPATH 설정 오류: {e}")
            return os.environ.copy()

class PortUtils:
    """포트 관리 유틸리티"""
    
    @staticmethod
    def is_port_available(port: int, host: str = 'localhost') -> bool:
        """포트가 사용 가능한지 확인"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # 연결 실패면 포트가 사용 가능
                
        except Exception:
            return False
    
    @staticmethod
    def find_available_port(start_port: int = 8501, max_attempts: int = 10) -> int:
        """사용 가능한 포트 찾기"""
        try:
            for i in range(max_attempts):
                port = start_port + i
                if PortUtils.is_port_available(port):
                    logger.info(f"✅ 사용 가능한 포트 발견: {port}")
                    return port
            
            logger.warning(f"⚠️ {start_port}부터 {max_attempts}개 포트 모두 사용 중")
            return start_port  # 기본 포트 반환
            
        except Exception as e:
            logger.error(f"💥 포트 탐지 오류: {e}")
            return start_port
    
    @staticmethod
    def kill_process_using_port(port: int) -> bool:
        """특정 포트를 사용하는 프로세스 종료"""
        try:
            if os.name == 'nt':  # Windows
                cmd = f'netstat -ano | findstr :{port}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            try:
                                subprocess.run(f'taskkill /F /PID {pid}', shell=True, check=True)
                                logger.info(f"✅ 포트 {port} 사용 프로세스 (PID: {pid}) 종료됨")
                                return True
                            except:
                                continue
            else:  # Linux/macOS
                cmd = f'lsof -ti:{port}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        try:
                            subprocess.run(f'kill -9 {pid}', shell=True, check=True)
                            logger.info(f"✅ 포트 {port} 사용 프로세스 (PID: {pid}) 종료됨")
                            return True
                        except:
                            continue
            
            return False
            
        except Exception as e:
            logger.error(f"💥 포트 {port} 프로세스 종료 실패: {e}")
            return False

# 편의를 위한 함수들
def get_python_executable() -> str:
    """Python 실행 파일 경로 반환 (간단한 래퍼)"""
    return PythonUtils.find_python_interpreter()

def setup_environment() -> Dict[str, str]:
    """환경변수 설정 (간단한 래퍼)"""
    return PythonUtils.setup_pythonpath_for_exe()

def find_free_port(start_port: int = 8501) -> int:
    """사용 가능한 포트 찾기 (간단한 래퍼)"""
    return PortUtils.find_available_port(start_port)