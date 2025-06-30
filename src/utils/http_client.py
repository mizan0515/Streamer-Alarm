"""
최적화된 HTTP 클라이언트 유틸리티
"""
import httpx
import asyncio
from typing import Optional, Dict, Any
from .logger import logger

class HttpClientManager:
    """HTTP 클라이언트 매니저 - 싱글톤 패턴"""
    
    _instance: Optional['HttpClientManager'] = None
    _clients: Dict[str, httpx.AsyncClient] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_client(cls, client_type: str = "default") -> httpx.AsyncClient:
        """클라이언트 타입별 HTTP 클라이언트 반환"""
        if client_type not in cls._clients or cls._clients[client_type].is_closed:
            cls._clients[client_type] = await cls._create_client(client_type)
        return cls._clients[client_type]
    
    @classmethod
    async def _create_client(cls, client_type: str) -> httpx.AsyncClient:
        """클라이언트 타입별 HTTP 클라이언트 생성"""
        common_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if client_type == "chzzk":
            return httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0
                ),
                headers=common_headers,
                http2=True  # HTTP/2 지원
            )
        
        elif client_type == "twitter":
            return httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=5.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=60.0
                ),
                headers=common_headers,
                follow_redirects=True
            )
        
        elif client_type == "image":
            return httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    max_connections=10,
                    keepalive_expiry=30.0
                ),
                headers=common_headers
            )
        
        else:  # default
            return httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(
                    max_keepalive_connections=8,
                    max_connections=15,
                    keepalive_expiry=30.0
                ),
                headers=common_headers
            )
    
    @classmethod
    async def close_all(cls):
        """모든 HTTP 클라이언트 정리"""
        for client_type, client in cls._clients.items():
            try:
                if not client.is_closed:
                    await client.aclose()
                    logger.debug(f"HTTP 클라이언트 정리: {client_type}")
            except Exception as e:
                logger.warning(f"HTTP 클라이언트 정리 실패 ({client_type}): {e}")
        
        cls._clients.clear()
        logger.info("모든 HTTP 클라이언트 정리 완료")
    
    @classmethod
    async def health_check(cls) -> Dict[str, bool]:
        """모든 클라이언트 상태 확인"""
        status = {}
        for client_type, client in cls._clients.items():
            try:
                status[client_type] = not client.is_closed
            except:
                status[client_type] = False
        return status

# 전역 매니저 인스턴스
http_manager = HttpClientManager()

# 편의 함수들
async def get_chzzk_client() -> httpx.AsyncClient:
    """치지직 API용 클라이언트"""
    return await http_manager.get_client("chzzk")

async def get_twitter_client() -> httpx.AsyncClient:
    """트위터/RSS용 클라이언트"""
    return await http_manager.get_client("twitter")

async def get_image_client() -> httpx.AsyncClient:
    """이미지 다운로드용 클라이언트"""
    return await http_manager.get_client("image")

async def get_default_client() -> httpx.AsyncClient:
    """기본 클라이언트"""
    return await http_manager.get_client("default")

async def close_all_clients():
    """모든 클라이언트 정리"""
    await http_manager.close_all()