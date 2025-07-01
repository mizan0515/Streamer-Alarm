import asyncio
import json
import os
from typing import Dict, Any, Optional, Tuple
from ..config import config
from ..utils.logger import logger
from ..utils.notification import NotificationManager
from ..utils.http_client import get_chzzk_client

class ChzzkMonitor:
    def __init__(self):
        self.stream_status: Dict[str, Dict[str, Any]] = {}
        self.running = False
        
        # 라이브 상태 파일 경로 설정
        self.live_status_file = os.path.join(config.data_dir, "live_status.json")
        
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.running:
            return
            
        self.running = True
        logger.info("치지직 모니터링 시작")
        
        while self.running:
            try:
                await self.check_all_streamers()
                
                # 설정된 간격만큼 대기
                settings = config.get_settings()
                interval = settings.get('check_interval', 30)
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"치지직 모니터링 중 오류: {e}")
                await asyncio.sleep(30)  # 오류 시 30초 대기
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        logger.info("치지직 모니터링 중지")
    
    async def check_all_streamers(self):
        """모든 스트리머 상태 확인"""
        streamers = config.get_streamers()
        
        # 활성화된 스트리머들만 체크
        active_streamers = {
            name: data for name, data in streamers.items() 
            if data.get('enabled', True) and data.get('chzzk_id')
        }
        
        if not active_streamers:
            return
        
        # 병렬로 모든 스트리머 체크
        tasks = [
            self.check_streamer_status(name, data['chzzk_id'])
            for name, data in active_streamers.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 처리
        for i, (name, data) in enumerate(active_streamers.items()):
            if i < len(results) and not isinstance(results[i], Exception):
                is_live, title = results[i]
                await self.handle_status_change(name, data, is_live, title)
        
        # 라이브 상태를 파일로 저장 (UI에서 사용)
        self.save_live_status_to_file()
    
    async def check_streamer_status(self, streamer_name: str, chzzk_id: str) -> Tuple[bool, Optional[str]]:
        """개별 스트리머 상태 확인"""
        try:
            url = f"https://api.chzzk.naver.com/polling/v2/channels/{chzzk_id}/live-status"
            client = await get_chzzk_client()
            response = await client.get(url)
            
            logger.debug(f"📡 {streamer_name} 치지직 API 응답: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', {})
                
                if content:
                    status = content.get('status')
                    title = content.get('liveTitle', '')
                    
                    is_live = status == 'OPEN'
                    
                    if is_live:
                        logger.info(f"🔴 {streamer_name} 방송 중! 상태: {status}, 제목: {title}")
                    else:
                        logger.debug(f"⚫ {streamer_name} 방송 종료. 상태: {status}")
                    
                    return is_live, title
                else:
                    logger.warning(f"⚠️ {streamer_name} 치지직 응답에 content가 없습니다.")
                    return False, None
            else:
                logger.error(f"❌ {streamer_name} 치지직 API 응답 오류: {response.status_code}")
                return False, None
                
        except Exception as e:
            logger.error(f"❌ {streamer_name} 치지직 상태 확인 실패: {e}")
            return False, None
    
    async def handle_status_change(self, streamer_name: str, streamer_data: dict, is_live: bool, title: Optional[str]):
        """스트리머 상태 변경 처리"""
        try:
            chzzk_id = streamer_data['chzzk_id']
            
            # 이전 상태 가져오기
            prev_status = self.stream_status.get(streamer_name, {})
            was_live = prev_status.get('is_live', False)
            
            # 상태 업데이트
            from datetime import datetime
            self.stream_status[streamer_name] = {
                'is_live': is_live,
                'title': title or '',
                'chzzk_id': chzzk_id,
                'last_check': asyncio.get_event_loop().time(),
                'last_updated': datetime.now().isoformat()
            }
            
            # 방송 시작 알림 (이전에 방송 중이 아니었고, 현재 방송 중인 경우)
            if is_live and not was_live:
                logger.info(f"🎉 {streamer_name} 방송 시작 알림 발송: {title}")
                
                # 프로필 이미지 URL 가져오기
                profile_image_url = await self.get_channel_profile_image(chzzk_id)
                
                # 스트리머 데이터에 프로필 이미지 URL 저장
                if profile_image_url:
                    await self.update_streamer_profile_image(streamer_name, profile_image_url)
                
                # 알림 표시
                await NotificationManager.show_live_notification(
                    streamer_name, 
                    title or "방송을 시작했습니다!", 
                    chzzk_id,
                    profile_image_url
                )
                
                # 알림 기록 저장
                config.add_notification(
                    streamer_name=streamer_name,
                    notification_type='live',
                    title=f"{streamer_name} 방송 시작!",
                    content=title or "방송을 시작했습니다!",
                    url=f"https://chzzk.naver.com/live/{chzzk_id}"
                )
            
            # 방송 종료 로깅 (방송 중이었고, 현재 방송 중이 아닌 경우)
            elif was_live and not is_live:
                logger.info(f"📺 {streamer_name} 방송 종료")
                
        except Exception as e:
            logger.error(f"상태 변경 처리 실패 ({streamer_name}): {e}")
    
    async def get_channel_profile_image(self, chzzk_id: str) -> Optional[str]:
        """채널 프로필 이미지 URL 가져오기"""
        try:
            # 채널 정보 API 호출
            url = f"https://api.chzzk.naver.com/service/v1/channels/{chzzk_id}"
            client = await get_chzzk_client()
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('content', {})
                
                # 프로필 이미지 URL 추출
                profile_image_url = content.get('channelImageUrl')
                if profile_image_url:
                    logger.debug(f"프로필 이미지 URL 획득: {profile_image_url}")
                    return profile_image_url
                    
        except Exception as e:
            logger.warning(f"프로필 이미지 URL 획득 실패 ({chzzk_id}): {e}")
        
        return None
    
    async def update_streamer_profile_image(self, streamer_name: str, profile_image_url: str):
        """스트리머 데이터에 프로필 이미지 URL 업데이트"""
        try:
            streamers = config.get_streamers()
            if streamer_name in streamers:
                # 현재 저장된 프로필 이미지 URL과 다른 경우에만 업데이트
                current_url = streamers[streamer_name].get('profile_image')
                if current_url != profile_image_url:
                    streamers[streamer_name]['profile_image'] = profile_image_url
                    config._save_streamers(streamers)
                    logger.debug(f"{streamer_name} 프로필 이미지 URL 업데이트: {profile_image_url}")
        except Exception as e:
            logger.warning(f"{streamer_name} 프로필 이미지 URL 업데이트 실패: {e}")
    
    async def get_streamer_status(self, streamer_name: str) -> Optional[Dict[str, Any]]:
        """특정 스트리머의 현재 상태 반환"""
        return self.stream_status.get(streamer_name)
    
    async def force_check_streamer(self, streamer_name: str) -> bool:
        """특정 스트리머 강제 체크"""
        streamers = config.get_streamers()
        if streamer_name not in streamers:
            return False
        
        streamer_data = streamers[streamer_name]
        chzzk_id = streamer_data.get('chzzk_id')
        
        if not chzzk_id:
            return False
        
        is_live, title = await self.check_streamer_status(streamer_name, chzzk_id)
        await self.handle_status_change(streamer_name, streamer_data, is_live, title)
        
        return True
    
    def save_live_status_to_file(self):
        """라이브 상태를 파일로 저장 (UI에서 사용)"""
        try:
            # 현재 스트리머들의 라이브 상태 수집
            live_status_data = {}
            for streamer_name, status_info in self.stream_status.items():
                live_status_data[streamer_name] = {
                    'is_live': status_info.get('is_live', False),
                    'title': status_info.get('title', ''),
                    'last_updated': status_info.get('last_updated', ''),
                    'url': f"https://chzzk.naver.com/live/{status_info.get('chzzk_id', '')}" if status_info.get('chzzk_id') else ''
                }
            
            # 파일로 저장
            with open(self.live_status_file, 'w', encoding='utf-8') as f:
                json.dump(live_status_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"라이브 상태를 파일로 저장: {len(live_status_data)}개 스트리머")
            
        except Exception as e:
            logger.warning(f"라이브 상태 파일 저장 실패: {e}")
    
    async def close(self):
        """리소스 정리"""
        self.stop_monitoring()
        logger.info("치지직 모니터 리소스 정리 완료")

# 전역 모니터 인스턴스
chzzk_monitor = ChzzkMonitor()