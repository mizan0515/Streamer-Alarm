"""
메모리 최적화 유틸리티
"""
import gc
import asyncio
import psutil
import os
from typing import Dict, Any
from .logger import logger

class MemoryManager:
    """메모리 사용량 관리"""
    
    @staticmethod
    def get_memory_usage() -> Dict[str, Any]:
        """현재 메모리 사용량 반환"""
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'rss': memory_info.rss,  # 물리 메모리 (bytes)
                'vms': memory_info.vms,  # 가상 메모리 (bytes)
                'percent': process.memory_percent(),  # 시스템 대비 비율
                'rss_mb': round(memory_info.rss / 1024 / 1024, 2),
                'vms_mb': round(memory_info.vms / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.warning(f"메모리 사용량 조회 실패: {e}")
            return {}
    
    @staticmethod
    def force_garbage_collection():
        """강제 가비지 컬렉션"""
        collected = gc.collect()
        logger.debug(f"가비지 컬렉션 완료: {collected}개 객체 정리")
        return collected
    
    @staticmethod
    def get_memory_stats() -> Dict[str, Any]:
        """상세 메모리 통계"""
        try:
            # 가비지 컬렉션 통계
            gc_stats = {f"gen_{i}": gc.get_count()[i] for i in range(3)}
            
            # 프로세스 메모리 정보
            memory_usage = MemoryManager.get_memory_usage()
            
            # 시스템 메모리 정보
            system_memory = psutil.virtual_memory()
            
            return {
                'process': memory_usage,
                'garbage_collection': gc_stats,
                'system': {
                    'total_gb': round(system_memory.total / 1024 / 1024 / 1024, 2),
                    'available_gb': round(system_memory.available / 1024 / 1024 / 1024, 2),
                    'percent_used': system_memory.percent
                }
            }
        except Exception as e:
            logger.warning(f"메모리 통계 조회 실패: {e}")
            return {}
    
    @staticmethod
    async def periodic_cleanup(interval: int = 300):
        """주기적 메모리 정리 (5분마다)"""
        while True:
            try:
                await asyncio.sleep(interval)
                
                # 메모리 사용량 체크
                usage = MemoryManager.get_memory_usage()
                memory_mb = usage.get('rss_mb', 0)
                
                # 100MB 이상 사용 시 가비지 컬렉션
                if memory_mb > 100:
                    collected = MemoryManager.force_garbage_collection()
                    logger.info(f"메모리 정리 수행: {memory_mb:.1f}MB 사용중, {collected}개 객체 정리")
                
                # 200MB 이상 사용 시 경고
                if memory_mb > 200:
                    logger.warning(f"높은 메모리 사용량: {memory_mb:.1f}MB")
                    
            except Exception as e:
                logger.error(f"주기적 메모리 정리 실패: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도

class ResourceMonitor:
    """리소스 모니터링"""
    
    @staticmethod
    def get_system_resources() -> Dict[str, Any]:
        """시스템 리소스 현황"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory': {
                    'total_gb': round(memory.total / 1024 / 1024 / 1024, 2),
                    'used_gb': round(memory.used / 1024 / 1024 / 1024, 2),
                    'percent': memory.percent
                },
                'disk': {
                    'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                    'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                    'percent': round((disk.used / disk.total) * 100, 1)
                }
            }
        except Exception as e:
            logger.warning(f"시스템 리소스 조회 실패: {e}")
            return {}
    
    @staticmethod
    def log_resource_usage():
        """리소스 사용량 로깅"""
        try:
            resources = ResourceMonitor.get_system_resources()
            memory_stats = MemoryManager.get_memory_stats()
            
            logger.info(f"시스템 리소스 - CPU: {resources.get('cpu_percent', 0):.1f}%, "
                       f"메모리: {resources.get('memory', {}).get('percent', 0):.1f}%, "
                       f"프로세스 메모리: {memory_stats.get('process', {}).get('rss_mb', 0):.1f}MB")
                       
        except Exception as e:
            logger.warning(f"리소스 사용량 로깅 실패: {e}")

# 전역 인스턴스
memory_manager = MemoryManager()
resource_monitor = ResourceMonitor()