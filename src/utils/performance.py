"""
성능 최적화 유틸리티
"""
import asyncio
import time
import functools
import threading
from typing import Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from .logger import logger

class PerformanceManager:
    """성능 관리 클래스"""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="perf_")
    
    def measure_time(self, func_name: str = None):
        """함수 실행 시간 측정 데코레이터"""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                name = func_name or f"{func.__module__}.{func.__name__}"
                start_time = time.perf_counter()
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.perf_counter() - start_time
                    self._record_metric(name, elapsed)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                name = func_name or f"{func.__module__}.{func.__name__}"
                start_time = time.perf_counter()
                
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    elapsed = time.perf_counter() - start_time
                    self._record_metric(name, elapsed)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def _record_metric(self, name: str, elapsed_time: float):
        """성능 메트릭 기록"""
        if name not in self.metrics:
            self.metrics[name] = {
                'count': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0,
                'avg_time': 0.0
            }
        
        metric = self.metrics[name]
        metric['count'] += 1
        metric['total_time'] += elapsed_time
        metric['min_time'] = min(metric['min_time'], elapsed_time)
        metric['max_time'] = max(metric['max_time'], elapsed_time)
        metric['avg_time'] = metric['total_time'] / metric['count']
        
        # 느린 함수 경고 (1초 이상)
        if elapsed_time > 1.0:
            logger.warning(f"느린 함수 실행: {name} - {elapsed_time:.3f}초")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        return dict(self.metrics)
    
    def reset_metrics(self):
        """메트릭 초기화"""
        self.metrics.clear()
        logger.info("성능 메트릭 초기화 완료")
    
    async def run_in_thread(self, func: Callable, *args, **kwargs):
        """CPU 집약적 작업을 별도 스레드에서 실행"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    def log_performance_summary(self):
        """성능 요약 로깅"""
        if not self.metrics:
            return
        
        logger.info("=== 성능 요약 ===")
        for name, metric in self.metrics.items():
            logger.info(f"{name}: 호출 {metric['count']}회, "
                       f"평균 {metric['avg_time']:.3f}초, "
                       f"최대 {metric['max_time']:.3f}초")
    
    def cleanup(self):
        """리소스 정리"""
        self.thread_pool.shutdown(wait=True)
        logger.info("성능 관리자 정리 완료")

class AsyncCache:
    """비동기 캐시"""
    
    def __init__(self, max_size: int = 100, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        async with self._lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # TTL 체크
                if time.time() - entry['timestamp'] < self.ttl:
                    return entry['value']
                else:
                    # 만료된 항목 제거
                    del self.cache[key]
            
            return None
    
    async def set(self, key: str, value: Any):
        """캐시에 값 저장"""
        async with self._lock:
            # 크기 제한 체크
            if len(self.cache) >= self.max_size:
                # 가장 오래된 항목 제거
                oldest_key = min(self.cache.keys(), 
                               key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            self.cache[key] = {
                'value': value,
                'timestamp': time.time()
            }
    
    async def clear(self):
        """캐시 초기화"""
        async with self._lock:
            self.cache.clear()
    
    def cache_decorator(self, key_func: Callable = None):
        """캐시 데코레이터"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # 키 생성
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
                # 캐시에서 조회
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # 함수 실행 및 캐시 저장
                result = await func(*args, **kwargs)
                await self.set(cache_key, result)
                return result
            
            return wrapper
        return decorator

class BatchProcessor:
    """배치 처리기"""
    
    def __init__(self, batch_size: int = 10, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    async def add_item(self, item: Any):
        """아이템을 배치 큐에 추가"""
        await self.queue.put(item)
    
    async def start_processing(self, processor_func: Callable):
        """배치 처리 시작"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._process_batches(processor_func))
    
    async def _process_batches(self, processor_func: Callable):
        """배치 처리 루프"""
        batch = []
        last_flush = time.time()
        
        while self.running:
            try:
                # 배치 크기나 시간 간격에 따라 플러시
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush >= self.flush_interval)
                )
                
                if should_flush:
                    if batch:
                        await processor_func(batch.copy())
                        batch.clear()
                        last_flush = current_time
                
                # 새 아이템 추가
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                    batch.append(item)
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"배치 처리 오류: {e}")
                await asyncio.sleep(1)
    
    async def stop_processing(self):
        """배치 처리 중지"""
        self.running = False
        if self._task:
            await self._task

# 전역 인스턴스
performance_manager = PerformanceManager()
global_cache = AsyncCache(max_size=200, ttl=600.0)  # 10분 TTL