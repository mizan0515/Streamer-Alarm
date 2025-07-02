import asyncio
import httpx
import feedparser
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from ..config import config
from ..utils.logger import logger
from ..utils.notification import NotificationManager

class TwitterMonitor:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/rss+xml, application/xml, text/xml, */*",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            },
            follow_redirects=True
        )
        self.running = False
        self.last_tweet_ids: Dict[str, Set[str]] = {}  # 스트리머별 마지막 트윗 ID들
        self.first_check = True
        
    async def start_monitoring(self):
        """모니터링 시작"""
        if self.running:
            return
            
        self.running = True
        logger.info("트위터/X RSS 모니터링 시작")
        
        while self.running:
            try:
                await self.check_all_streamers()
                
                # 설정된 간격만큼 대기
                settings = config.get_settings()
                interval = settings.get('check_interval', 30)
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"트위터 모니터링 중 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 대기
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.running = False
        logger.info("트위터/X RSS 모니터링 중지")
    
    async def check_all_streamers(self):
        """모든 스트리머의 트위터 확인"""
        streamers = config.get_streamers()
        
        # 트위터 사용자명이 있는 활성화된 스트리머들만 체크
        active_streamers = {
            name: data for name, data in streamers.items() 
            if data.get('enabled', True) and data.get('twitter_username')
        }
        
        if not active_streamers:
            return
        
        # 순차적으로 스트리머 체크 (429 오류 방지)
        for name, data in active_streamers.items():
            try:
                await self.check_streamer_tweets(name, data['twitter_username'])
                # 각 스트리머 체크 사이에 1초 지연 (429 오류 방지)
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"{name} 트위터 확인 중 오류: {e}")
    
    async def check_streamer_tweets(self, streamer_name: str, username: str):
        """특정 스트리머의 트위터 RSS 확인"""
        for instance_url in config.nitter_instances:
            try:
                rss_url = f"{instance_url}/{username}/rss"
                logger.debug(f"{streamer_name} RSS 요청: {rss_url}")
                
                response = await self.client.get(rss_url)
                logger.debug(f"{streamer_name} RSS 응답: {response.status_code}")
                
                if response.status_code != 200:
                    logger.warning(f"RSS 요청 실패 ({instance_url}): {response.status_code}")
                    continue
                
                # RSS 파싱
                try:
                    feed = feedparser.parse(response.text)
                    logger.debug(f"{streamer_name} 파싱 결과: entries={len(feed.entries)}")
                    
                    # 파싱 실패시 바이트로 재시도
                    if not feed.entries and response.content:
                        feed = feedparser.parse(response.content)
                        logger.debug(f"{streamer_name} 바이트 재파싱: entries={len(feed.entries)}")
                    
                except Exception as parse_error:
                    logger.error(f"{streamer_name} RSS 파싱 오류: {parse_error}")
                    continue
                
                if hasattr(feed, 'bozo') and feed.bozo and not feed.entries:
                    logger.warning(f"{streamer_name} RSS 파싱 경고: {getattr(feed, 'bozo_exception', 'unknown error')}")
                    continue
                
                if not feed.entries:
                    logger.warning(f"{streamer_name} RSS 피드에 항목이 없습니다 ({instance_url})")
                    continue
                
                logger.info(f"{streamer_name} RSS 피드에서 {len(feed.entries)}개 항목 발견 ({instance_url})")
                
                # 트윗 처리
                await self.process_tweets(streamer_name, username, feed.entries, instance_url)
                return  # 성공하면 다른 인스턴스 시도하지 않음
                
            except Exception as e:
                logger.error(f"{streamer_name} RSS 확인 실패 ({instance_url}): {e}", exc_info=True)
                continue
        
        logger.error(f"{streamer_name} 모든 Nitter 인스턴스에서 RSS 확인 실패")
    
    async def process_tweets(self, streamer_name: str, username: str, entries: List, instance_url: str):
        """트윗 항목들 처리"""
        try:
            # 현재 트윗 ID들 추출
            current_tweet_ids = set()
            tweets_data = []
            
            for entry in entries:
                # 트윗 ID 추출 (링크에서)
                tweet_id = self.extract_tweet_id(entry.link)
                if tweet_id:
                    current_tweet_ids.add(tweet_id)
                    tweets_data.append({
                        'id': tweet_id,
                        'title': entry.title,
                        'content': entry.summary,
                        'link': entry.link,
                        'published': entry.published_parsed
                    })
            
            # 이전 트윗 ID들 가져오기
            previous_tweet_ids = self.last_tweet_ids.get(streamer_name, set())
            
            # 첫 번째 체크인 경우, 현재 트윗들을 기준으로 설정 (알림 발송하지 않음)
            if self.first_check or not previous_tweet_ids:
                self.last_tweet_ids[streamer_name] = current_tweet_ids
                logger.info(f"{streamer_name} 트위터 기준 트윗 {len(current_tweet_ids)}개 설정 (첫 체크 - 알림 없음)")
                return
            
            # 새 트윗 찾기
            new_tweet_ids = current_tweet_ids - previous_tweet_ids
            
            if new_tweet_ids:
                logger.info(f"{streamer_name} 새 트윗 {len(new_tweet_ids)}개 발견")
                
                # 새 트윗들에 대해 알림 발송
                for tweet in tweets_data:
                    if tweet['id'] in new_tweet_ids:
                        await self.send_new_tweet_notification(streamer_name, username, tweet)
                
                # 마지막 트윗 ID들 업데이트
                self.last_tweet_ids[streamer_name] = current_tweet_ids
            
            logger.debug(f"{streamer_name} 트위터 확인 완료 ({instance_url})")
            
        except Exception as e:
            logger.error(f"{streamer_name} 트윗 처리 실패: {e}")
    
    def extract_tweet_id(self, link: str) -> Optional[str]:
        """트위터 링크에서 트윗 ID 추출"""
        try:
            # 다양한 형태의 링크에서 ID 추출
            # 예: https://nitter.instance/username/status/1234567890
            if '/status/' in link:
                return link.split('/status/')[-1].split('?')[0].split('#')[0]
            return None
        except:
            return None
    
    async def send_new_tweet_notification(self, streamer_name: str, username: str, tweet: dict):
        """새 트윗 알림 발송"""
        try:
            # X(트위터) 실제 링크로 변환
            twitter_url = f"https://x.com/{username}/status/{tweet['id']}"
            
            # 프로필 이미지 URL 가져오기 (치지직에서)
            profile_image_url = await self.get_streamer_profile_image(streamer_name)
            
            # 트윗 내용 정리 (HTML 태그 제거)
            content = self.clean_tweet_content(tweet['content'])
            
            # 알림 표시
            await NotificationManager.show_twitter_notification(
                streamer_name,
                content,
                twitter_url,
                profile_image_url
            )
            
            # 알림 기록 저장
            config.add_notification(
                streamer_name=streamer_name,
                notification_type='twitter',
                title=f"{streamer_name} 새 트윗",
                content=content,
                url=twitter_url
            )
            
            logger.info(f"{streamer_name} 새 트윗 알림 발송: {content[:50]}...")
            
        except Exception as e:
            logger.error(f"트윗 알림 발송 실패: {e}")
    
    def clean_tweet_content(self, content: str) -> str:
        """트윗 내용에서 HTML 태그 제거 및 정리"""
        try:
            import re
            
            # HTML 태그 제거
            content = re.sub(r'<[^>]+>', '', content)
            
            # HTML 엔티티 디코딩
            import html
            content = html.unescape(content)
            
            # 줄바꿈 정리
            content = content.replace('\n', ' ').strip()
            
            # 길이 제한
            if len(content) > 200:
                content = content[:200] + "..."
            
            return content
            
        except Exception as e:
            logger.warning(f"트윗 내용 정리 실패: {e}")
            return content[:100] + "..." if len(content) > 100 else content
    
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
        username = streamer_data.get('twitter_username')
        
        if not username:
            return False
        
        await self.check_streamer_tweets(streamer_name, username)
        return True
    
    def mark_first_check_complete(self):
        """첫 번째 체크 완료 표시"""
        self.first_check = False
    
    async def reset_streamer_tweets(self, streamer_name: str):
        """특정 스트리머의 트윗 기준 초기화"""
        if streamer_name in self.last_tweet_ids:
            del self.last_tweet_ids[streamer_name]
            logger.info(f"{streamer_name} 트위터 트윗 기준 초기화")
    
    def get_streamer_tweet_count(self, streamer_name: str) -> int:
        """특정 스트리머의 추적 중인 트윗 수"""
        return len(self.last_tweet_ids.get(streamer_name, set()))
    
    async def get_tweets_from_rss(self, username: str) -> List[Dict[str, Any]]:
        """특정 사용자의 RSS에서 트윗 목록을 가져옵니다 (누락 알림 복구용)"""
        tweets = []
        
        for instance_url in config.nitter_instances:
            try:
                rss_url = f"{instance_url}/{username}/rss"
                response = await self.client.get(rss_url)
                
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.text)
                if not feed.entries and response.content:
                    feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    continue
                
                for entry in feed.entries:
                    tweet_id = self.extract_tweet_id(entry.link)
                    if tweet_id:
                        tweets.append({
                            'id': tweet_id,
                            'title': entry.title,
                            'url': f"https://x.com/{username}/status/{tweet_id}",
                            'published': getattr(entry, 'published', ''),
                            'content': entry.summary if hasattr(entry, 'summary') else entry.title
                        })
                
                return tweets  # 성공하면 첫 번째 인스턴스 결과 반환
                
            except Exception as e:
                logger.debug(f"RSS 가져오기 실패 ({instance_url}): {e}")
                continue
        
        return tweets
    
    async def test_nitter_instances(self) -> Dict[str, bool]:
        """Nitter 인스턴스들 테스트"""
        results = {}
        
        for instance_url in config.nitter_instances:
            try:
                test_url = f"{instance_url}/twitter/rss"  # 테스트용 URL
                response = await self.client.get(test_url, timeout=5)
                results[instance_url] = response.status_code == 200
                
            except Exception as e:
                logger.debug(f"Nitter 인스턴스 테스트 실패 ({instance_url}): {e}")
                results[instance_url] = False
        
        return results
    
    async def close(self):
        """리소스 정리"""
        self.stop_monitoring()
        await self.client.aclose()
        logger.info("트위터 모니터 리소스 정리 완료")

# 전역 트위터 모니터 인스턴스
twitter_monitor = TwitterMonitor()