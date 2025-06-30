#!/usr/bin/env python3
"""
브라우저 캐시 및 임시 파일 정리 스크립트
"""

import os
import shutil
import glob
from pathlib import Path

def cleanup_browser_cache():
    """브라우저 캐시 정리"""
    browser_data_dir = Path("data/browser_data")
    
    if not browser_data_dir.exists():
        print("브라우저 데이터 디렉토리가 없습니다.")
        return
    
    # 정리할 디렉토리 목록 (중요한 쿠키/세션 데이터는 보존)
    cache_dirs = [
        "Default/Cache",
        "Default/GPUCache", 
        "Default/Code Cache",
        "Default/DawnGraphiteCache",
        "Default/DawnWebGPUCache",
        "ShaderCache",
        "GrShaderCache",
        "GraphiteDawnCache"
    ]
    
    total_freed = 0
    
    for cache_dir in cache_dirs:
        cache_path = browser_data_dir / cache_dir
        if cache_path.exists():
            try:
                size_before = sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file())
                shutil.rmtree(cache_path)
                cache_path.mkdir(parents=True, exist_ok=True)
                total_freed += size_before
                print(f"✅ {cache_dir} 정리됨 ({size_before // 1024 // 1024} MB)")
            except Exception as e:
                print(f"❌ {cache_dir} 정리 실패: {e}")
    
    print(f"\n🧹 총 {total_freed // 1024 // 1024} MB 정리됨")

def cleanup_temp_files():
    """임시 파일 정리"""
    patterns = [
        "data/*.tmp",
        "data/*_temp.json",
        "logs/*.log.old"
    ]
    
    for pattern in patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"🗑️ 임시 파일 삭제: {file_path}")
            except Exception as e:
                print(f"❌ 임시 파일 삭제 실패 {file_path}: {e}")

if __name__ == "__main__":
    print("🧹 캐시 및 임시 파일 정리 시작...")
    cleanup_browser_cache()
    cleanup_temp_files()
    print("✅ 정리 완료!")