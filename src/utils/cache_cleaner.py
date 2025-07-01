"""
브라우저 캐시 및 임시 파일 정리 유틸리티
"""

import os
import shutil
import glob
import asyncio
from pathlib import Path
from typing import Tuple
from .logger import logger


class CacheCleaner:
    """캐시 및 임시 파일 정리 클래스"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.browser_data_dir = self.data_dir / "browser_data"
        
        # 정리할 브라우저 캐시 디렉토리 목록 (중요한 쿠키/세션 데이터는 보존)
        self.cache_dirs = [
            "Default/Cache",
            "Default/GPUCache", 
            "Default/Code Cache",
            "Default/DawnGraphiteCache",
            "Default/DawnWebGPUCache",
            "ShaderCache",
            "GrShaderCache",
            "GraphiteDawnCache"
        ]
        
        # 정리할 임시 파일 패턴
        self.temp_file_patterns = [
            "*.tmp",
            "*_temp.json",
            "../logs/*.log.old"
        ]
    
    async def cleanup_browser_cache(self) -> Tuple[bool, int]:
        """
        브라우저 캐시 정리 (비동기)
        
        Returns:
            Tuple[bool, int]: (성공 여부, 정리된 바이트 수)
        """
        if not self.browser_data_dir.exists():
            logger.debug("브라우저 데이터 디렉토리가 없습니다.")
            return True, 0
        
        total_freed = 0
        success_count = 0
        total_count = len(self.cache_dirs)
        
        for cache_dir in self.cache_dirs:
            cache_path = self.browser_data_dir / cache_dir
            if cache_path.exists():
                try:
                    # 디렉토리 크기 계산
                    size_before = sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file())
                    
                    # 디렉토리 삭제 후 재생성
                    shutil.rmtree(cache_path)
                    cache_path.mkdir(parents=True, exist_ok=True)
                    
                    total_freed += size_before
                    success_count += 1
                    
                    logger.debug(f"브라우저 캐시 정리됨: {cache_dir} ({size_before // 1024 // 1024} MB)")
                    
                except Exception as e:
                    logger.warning(f"브라우저 캐시 정리 실패: {cache_dir} - {e}")
                    
                # 비동기 처리를 위한 잠시 대기
                await asyncio.sleep(0.01)
        
        logger.info(f"브라우저 캐시 정리 완료: {success_count}/{total_count} 성공, {total_freed // 1024 // 1024} MB 정리됨")
        return success_count == total_count, total_freed
    
    async def cleanup_temp_files(self) -> Tuple[bool, int]:
        """
        임시 파일 정리 (비동기)
        
        Returns:
            Tuple[bool, int]: (성공 여부, 삭제된 파일 수)
        """
        deleted_count = 0
        total_size = 0
        
        for pattern in self.temp_file_patterns:
            pattern_path = self.data_dir / pattern
            
            try:
                for file_path in glob.glob(str(pattern_path)):
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
                        total_size += file_size
                        logger.debug(f"임시 파일 삭제됨: {file_path}")
                        
                    except Exception as e:
                        logger.warning(f"임시 파일 삭제 실패: {file_path} - {e}")
                        
                    # 비동기 처리를 위한 잠시 대기
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.warning(f"임시 파일 패턴 처리 실패: {pattern} - {e}")
        
        if deleted_count > 0:
            logger.info(f"임시 파일 정리 완료: {deleted_count}개 파일, {total_size // 1024} KB 정리됨")
        
        return True, deleted_count
    
    async def cleanup_all(self) -> Tuple[bool, dict]:
        """
        모든 캐시 및 임시 파일 정리
        
        Returns:
            Tuple[bool, dict]: (전체 성공 여부, 정리 결과 정보)
        """
        logger.info("캐시 및 임시 파일 정리 시작")
        
        # 브라우저 캐시 정리
        cache_success, cache_freed = await self.cleanup_browser_cache()
        
        # 임시 파일 정리
        temp_success, temp_deleted = await self.cleanup_temp_files()
        
        result = {
            'cache_success': cache_success,
            'cache_freed_mb': cache_freed // 1024 // 1024,
            'temp_success': temp_success,
            'temp_deleted': temp_deleted,
            'total_success': cache_success and temp_success
        }
        
        if result['total_success']:
            logger.info(f"전체 정리 완료: 캐시 {result['cache_freed_mb']} MB, 임시파일 {result['temp_deleted']}개")
        else:
            logger.warning("일부 정리 작업에서 오류가 발생했습니다.")
        
        return result['total_success'], result


# 전역 인스턴스
cache_cleaner = CacheCleaner()