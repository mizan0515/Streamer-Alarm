import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from ..config import config
from ..utils.logger import logger
from ..utils.notification import NotificationManager
from ..browser.naver_session import naver_session

class CafeMonitor:
    def __init__(self):
        self.running = False
        self.last_post_ids: Dict[str, Set[str]] = {}  # 스트리머별 마지막 게시물 ID들
        self.first_check = True
        
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.running:
            return
            
        self.running = True
        logger.info("네이버 카페 모니터링 시작")
        
        # 네이버 로그인 확인
        login_attempts = 0
        max_attempts = 3
        
        while login_attempts < max_attempts and self.running:
            try:
                # 세션 로드 또는 로그인 상태 확인
                session_loaded = await naver_session.load_session()
                if session_loaded:
                    logger.info("네이버 세션 로드 성공")
                    break
                
                # 세션이 없으면 로그인 상태 확인
                if await naver_session.check_login_status():
                    logger.info("네이버 로그인 상태 확인됨")
                    # 헤드리스 모드가 아닌 경우 강제로 전환
                    if not naver_session.headless_mode:
                        logger.info("카페 모니터링을 위해 헤드리스 모드로 전환")
                        await naver_session.save_session()  # 세션 저장 후 전환
                        await naver_session.close_browser()
                        await naver_session.start_browser(headless=True)
                        if not await naver_session.restore_session_and_check_login():
                            logger.warning("헤드리스 모드 전환 후 로그인 상태 확인 실패")
                            login_attempts += 1
                            await asyncio.sleep(30)
                            continue
                    break
                
                # 로그인이 필요한 경우 자동 로그인 시도 (첫 번째 시도에서만)
                if login_attempts == 0:
                    logger.info("네이버 로그인이 필요합니다. 자동 로그인을 시도합니다.")
                    if await naver_session.login():
                        logger.info("네이버 자동 로그인 성공")
                        break
                    else:
                        logger.warning("네이버 자동 로그인 실패")
                
                login_attempts += 1
                logger.info(f"네이버 로그인 대기 중... ({login_attempts}/{max_attempts})")
                await asyncio.sleep(30)  # 30초 대기
                
            except Exception as e:
                logger.error(f"네이버 로그인 확인 실패: {e}")
                login_attempts += 1
                await asyncio.sleep(30)
        
        if login_attempts >= max_attempts:
            logger.warning("네이버 로그인 시간 초과. 카페 모니터링을 건너뜁니다.")
            # 완전히 중지하지 않고 카페 모니터링만 비활성화
            return
        
        while self.running:
            try:
                await self.check_all_streamers()
                
                # 설정된 간격만큼 대기
                settings = config.get_settings()
                interval = settings.get('check_interval', 30)
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"카페 모니터링 중 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        logger.info("네이버 카페 모니터링 중지")
    
    async def ensure_login(self) -> bool:
        """네이버 로그인 상태 확인 및 로그인"""
        try:
            # 세션 복원 시도
            if await naver_session.load_session():
                return True
            
            # 로그인 필요
            logger.info("네이버 로그인이 필요합니다.")
            return await naver_session.login()
            
        except Exception as e:
            logger.error(f"네이버 로그인 확인 실패: {e}")
            return False
    
    async def check_all_streamers(self):
        """모든 스트리머의 카페 게시물 확인"""
        streamers = config.get_streamers()
        
        # 카페 사용자 ID가 있는 활성화된 스트리머들만 체크
        active_streamers = {
            name: data for name, data in streamers.items() 
            if data.get('enabled', True) and data.get('cafe_user_id')
        }
        
        if not active_streamers:
            return
        
        for name, data in active_streamers.items():
            try:
                # 스트리머별 카페 고유번호 사용 (기본값: config.cafe_club_id)
                club_id = data.get('cafe_club_id', config.cafe_club_id)
                await self.check_streamer_posts(name, club_id, data['cafe_user_id'])
                # 각 스트리머 체크 사이에 약간의 지연
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.debug(f"{name} 카페 게시물 확인 실패 (일시적): {e}")
    
    async def check_streamer_posts(self, streamer_name: str, club_id: str, user_id: str):
        """특정 스트리머의 카페 게시물 확인"""
        try:
            # 네이버 세션 유효성 확인 (부드럽게 처리)
            if not naver_session.page or not naver_session.browser:
                logger.debug(f"{streamer_name} 네이버 브라우저 세션이 없음 - 건너뜀")
                return
            
            # 캐시된 로그인 상태만 확인 (실시간 확인 제거로 성능 개선)
            if not naver_session.is_logged_in:
                logger.debug(f"{streamer_name} 네이버 로그인 상태 아님 (캐시됨) - 건너뜀")
                return
            
            # 게시물 목록 가져오기
            posts = await naver_session.get_cafe_posts(club_id, user_id)
            
            if not posts:
                logger.debug(f"{streamer_name} 카페 게시물을 가져올 수 없습니다.")
                return
            
            # 현재 게시물 ID들
            current_post_ids = {post['id'] for post in posts}
            
            # 이전 게시물 ID들 가져오기
            previous_post_ids = self.last_post_ids.get(streamer_name, set())
            
            # 첫 번째 체크인 경우, 현재 게시물들을 기준으로 설정 (알림 발송하지 않음)
            if self.first_check or not previous_post_ids:
                self.last_post_ids[streamer_name] = current_post_ids
                logger.info(f"{streamer_name} 카페 기준 게시물 {len(current_post_ids)}개 설정 (첫 체크 - 알림 없음)")
                return
            
            # 새 게시물 찾기
            new_post_ids = current_post_ids - previous_post_ids
            
            if new_post_ids:
                logger.info(f"{streamer_name} 새 카페 게시물 {len(new_post_ids)}개 발견")
                
                # 새 게시물들에 대해 알림 발송
                for post in posts:
                    if post['id'] in new_post_ids:
                        # 개별 알림 설정 확인
                        streamers = config.get_streamers()
                        streamer_data = streamers.get(streamer_name, {})
                        
                        if not streamer_data.get('notifications', {}).get('cafe', True):
                            logger.debug(f"{streamer_name} 카페 알림이 비활성화됨")
                            continue
                            
                        await self.send_new_post_notification(streamer_name, post)
                
                # 마지막 게시물 ID들 업데이트
                self.last_post_ids[streamer_name] = current_post_ids
            
        except Exception as e:
            logger.error(f"{streamer_name} 카페 게시물 확인 실패: {e}")
    
    async def send_new_post_notification(self, streamer_name: str, post: dict):
        """새 게시물 알림 발송"""
        try:
            # 프로필 이미지 URL 가져오기 (치지직에서)
            profile_image_url = await self.get_streamer_profile_image(streamer_name)
            
            # 알림 표시
            await NotificationManager.show_cafe_notification(
                streamer_name,
                post['title'],
                post['url'],
                profile_image_url
            )
            
            # 알림 기록 저장
            config.add_notification(
                streamer_name=streamer_name,
                notification_type='cafe',
                title=f"{streamer_name} 카페 새 글",
                content=post['title'],
                url=post['url']
            )
            
            logger.info(f"{streamer_name} 카페 새 게시물 알림 발송: {post['title']}")
            
        except Exception as e:
            logger.error(f"카페 게시물 알림 발송 실패: {e}")
    
    async def get_streamer_profile_image(self, streamer_name: str) -> Optional[str]:
        """스트리머 프로필 이미지 URL 가져오기 (치지직에서)"""
        try:
            streamers = config.get_streamers()
            streamer_data = streamers.get(streamer_name, {})
            chzzk_id = streamer_data.get('chzzk_id')
            
            if not chzzk_id:
                return None
            
            # 치지직 모니터에서 프로필 이미지 가져오기
            from .chzzk_monitor import chzzk_monitor
            return await chzzk_monitor.get_channel_profile_image(chzzk_id)
            
        except Exception as e:
            logger.warning(f"프로필 이미지 가져오기 실패 ({streamer_name}): {e}")
            return None
    
    async def force_check_streamer(self, streamer_name: str) -> bool:
        """특정 스트리머 강제 체크"""
        streamers = config.get_streamers()
        if streamer_name not in streamers:
            return False
        
        streamer_data = streamers[streamer_name]
        cafe_user_id = streamer_data.get('cafe_user_id')
        
        if not cafe_user_id:
            return False
        
        if not await self.ensure_login():
            return False
        
        # 스트리머별 카페 고유번호 사용 (기본값: config.cafe_club_id)
        club_id = streamer_data.get('cafe_club_id', config.cafe_club_id)
        await self.check_streamer_posts(streamer_name, club_id, cafe_user_id)
        return True
    
    def mark_first_check_complete(self):
        """첫 번째 체크 완료 표시"""
        self.first_check = False
    
    async def reset_streamer_posts(self, streamer_name: str):
        """특정 스트리머의 게시물 기준 초기화"""
        if streamer_name in self.last_post_ids:
            del self.last_post_ids[streamer_name]
            logger.info(f"{streamer_name} 카페 게시물 기준 초기화")
    
    def get_streamer_post_count(self, streamer_name: str) -> int:
        """특정 스트리머의 추적 중인 게시물 수"""
        return len(self.last_post_ids.get(streamer_name, set()))
    
    def is_post_within_24_hours(self, date_str: str) -> bool:
        """게시물이 24시간 내에 작성되었는지 확인"""
        try:
            if not date_str:
                return False
            
            now = datetime.now()
            
            # "15:50" 형식 (오늘)
            if ':' in date_str and '.' not in date_str:
                return True  # 시:분 형식은 오늘 게시물
            
            # "2025.06.28." 형식
            if '.' in date_str:
                # 마지막 점 제거
                date_str = date_str.rstrip('.')
                try:
                    post_date = datetime.strptime(date_str, '%Y.%m.%d')
                    # 오늘 날짜와 비교
                    today = now.date()
                    yesterday = today - timedelta(days=1)
                    
                    return post_date.date() >= yesterday
                except ValueError:
                    logger.warning(f"날짜 파싱 실패: {date_str}")
                    return False
            
            return False
            
        except Exception as e:
            logger.warning(f"날짜 확인 중 오류: {e}")
            return False

# 전역 카페 모니터 인스턴스
cafe_monitor = CafeMonitor()