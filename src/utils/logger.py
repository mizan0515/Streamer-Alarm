import logging
import os
import glob
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

def cleanup_old_logs(log_dir: str, days: int = 7):
    """오래된 로그 파일 정리"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        pattern = os.path.join(log_dir, "streamer_alarm_*.log*")
        
        for log_file in glob.glob(pattern):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                if file_time < cutoff_date:
                    os.remove(log_file)
                    print(f"오래된 로그 파일 삭제: {log_file}")
            except Exception:
                pass  # 개별 파일 삭제 실패는 무시
    except Exception:
        pass  # 로그 정리 실패는 무시

def setup_logger(name: str = "streamer_alarm", level: int = logging.INFO) -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # 로그 디렉토리 생성
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 로테이팅 파일 핸들러 (10MB 제한, 최대 3개 파일 유지)
    log_file = os.path.join(log_dir, f"streamer_alarm_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    
    # 오래된 로그 파일 정리 (7일 이상)
    cleanup_old_logs(log_dir)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    
    # 포매터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 기본 로거 인스턴스
logger = setup_logger()