"""
누락된 알림 복구 시스템
앱이 꺼져있던 동안 발생한 새 글들을 감지하고 알림을 발송하는 시스템
"""

import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Any, Optional, Tuple
from urllib.parse import urlparse
from ..config import config
from ..utils.logger import logger
from ..utils.notification import NotificationManager


class MissedNotificationRecovery:
    def __init__(self):
        self.recovery_file = os.path.join(config.data_dir, "recovery_state.json")
        self.is_recovering = False
        self.recovery_delay = 2  # 알림 간 지연시간 (초)
        self.max_recovery_items = 50  # 한번에 복구할 최대 항목 수
        self.max_notification_records = 2000  # 최대 알림 기록 분석 수 (성능 고려)
        self.network_retry_count = 3  # 네트워크 재시도 횟수
        self.partial_recovery_threshold = 0.3  # 부분 성공 임계값 (30%)
        
    async def recover_missed_notifications(self) -> Dict[str, int]:
        """
        누락된 알림을 복구합니다. (엣지케이스 대응 강화)
        
        Returns:
            Dict[str, int]: 복구된 알림 수 {'cafe': 3, 'twitter': 2}
        """
        # 동시 실행 방지 (엣지케이스 1)
        if self.is_recovering:
            logger.warning("⚠️ 알림 복구가 이미 진행 중입니다 - 중복 실행 방지")
            return {}
            
        # 복구 상태 lock 파일로 추가 보호
        lock_file = os.path.join(config.data_dir, "recovery_lock.tmp")
        if os.path.exists(lock_file):
            try:
                # 락 파일이 10분 이상 오래되면 강제 해제
                import time
                if time.time() - os.path.getmtime(lock_file) > 600:
                    os.remove(lock_file)
                    logger.warning("⚠️ 오래된 복구 락 파일 강제 해제 (10분 초과)")
                else:
                    logger.warning("⚠️ 다른 복구 프로세스가 진행 중입니다")
                    return {}
            except Exception as e:
                logger.debug(f"락 파일 확인 실패: {e}")
        
        self.is_recovering = True
        recovery_stats = {'cafe': 0, 'twitter': 0, 'errors': 0, 'partial_success': False}
        
        try:
            # 복구 시작 락 파일 생성
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            
            logger.info("🔄 누락된 알림 복구 시작 (엣지케이스 대응 강화)")
            
            # 현재 확인 가능한 모든 글 수집 (네트워크 재시도 포함)
            current_items = await self._collect_current_items_with_retry()
            total_items = len(current_items['cafe']) + len(current_items['twitter'])
            
            if total_items == 0:
                logger.warning("⚠️ 현재 확인 가능한 항목이 없습니다 (네트워크 문제 가능)")
                return recovery_stats
            
            logger.info(f"📊 현재 확인 가능한 항목: 카페 {len(current_items['cafe'])}개, 트위터 {len(current_items['twitter'])}개")
            
            # 기존 알림 기록 안전하게 로드 (손상 대응)
            existing_records = self._get_existing_notification_records_safe()
            logger.info(f"📋 기존 알림 기록: {len(existing_records)}개")
            
            # URL ID 추출 테스트 및 디버깅 정보 (중복 알림 문제 해결 확인)
            self._debug_url_extraction_status(current_items, existing_records)
            
            # 누락된 항목들 식별
            missed_items = self._identify_missed_items(current_items, existing_records)
            total_missed = sum(len(items) for items in missed_items.values())
            
            # 중복 감지 성공 여부 확인 (핵심 수정 사항)
            if len(existing_records) > 0 and total_missed == (len(current_items['cafe']) + len(current_items['twitter'])):
                logger.error("🚨 중복 감지 실패! 모든 현재 항목이 '누락'으로 잘못 식별되었습니다")
                logger.error("이는 URL ID 추출 로직 문제이거나 고유 키 생성 방식 불일치를 의미합니다")
                
                # 긴급 진단 실행
                self._emergency_duplicate_detection_diagnosis(current_items, existing_records)
                
                # 안전 모드: 대량 중복 알림 방지
                if total_missed > 20:
                    logger.warning("⚠️ 안전 모드 활성화: 20개 이상의 중복 가능성 있는 알림 차단")
                    return {'cafe': 0, 'twitter': 0, 'errors': 1, 'safety_mode_activated': True}
            
            if total_missed == 0:
                logger.info("✅ 누락된 알림이 없습니다")
                return recovery_stats
            
            logger.info(f"📢 누락된 알림 발견: 카페 {len(missed_items['cafe'])}개, 트위터 {len(missed_items['twitter'])}개")
            
            # 대량 알림 처리 시 사용자 안내 및 확인
            if total_missed > 20:
                await self._show_bulk_recovery_notification(total_missed)
                # 대량인 경우 처리 속도 조절
                self.recovery_delay = max(3, min(10, total_missed // 10))
                logger.info(f"대량 복구로 인한 지연 시간 조정: {self.recovery_delay}초")
            
            # 누락된 알림들을 순차적으로 발송 (에러 추적 포함)
            total_processed = 0
            total_successful = 0
            
            for item_type in ['cafe', 'twitter']:
                items = missed_items[item_type]
                if not items:
                    continue
                    
                # 항목 수 제한 (성능 고려)
                original_count = len(items)
                if len(items) > self.max_recovery_items:
                    logger.warning(f"⚠️ {item_type} 항목이 {len(items)}개로 너무 많습니다. {self.max_recovery_items}개로 제한합니다.")
                    items = items[:self.max_recovery_items]
                
                recovery_count, error_count = await self._send_missed_notifications_with_error_tracking(item_type, items)
                recovery_stats[item_type] = recovery_count
                recovery_stats['errors'] += error_count
                
                total_processed += len(items)
                total_successful += recovery_count
                
                logger.info(f"✅ {item_type} 알림 복구: {recovery_count}/{len(items)}개 성공 (원본 {original_count}개)")
            
            # 부분 성공 판별
            success_rate = total_successful / total_processed if total_processed > 0 else 0
            if success_rate < self.partial_recovery_threshold:
                recovery_stats['partial_success'] = True
                logger.warning(f"⚠️ 부분 성공: {success_rate:.1%} ({total_successful}/{total_processed})")
            else:
                logger.info(f"✅ 복구 성공률: {success_rate:.1%} ({total_successful}/{total_processed})")
            
            # 복구 완료 통계 로깅
            total_recovered = recovery_stats['cafe'] + recovery_stats['twitter']
            logger.info(f"🎉 누락 알림 복구 완료: 총 {total_recovered}개 (카페: {recovery_stats['cafe']}, 트위터: {recovery_stats['twitter']}, 오류: {recovery_stats['errors']}개)")
            
            return recovery_stats
            
        except Exception as e:
            logger.error(f"❌ 누락 알림 복구 중 치명적 오류: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")
            recovery_stats['errors'] = recovery_stats.get('errors', 0) + 1
            return recovery_stats
        finally:
            self.is_recovering = False
            # 락 파일 정리
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except Exception as e:
                logger.debug(f"락 파일 정리 실패: {e}")
    
    async def _collect_current_items_with_retry(self) -> Dict[str, List[Dict[str, Any]]]:
        """현재 확인 가능한 모든 카페글과 트위터글을 수집합니다 (재시도 포함)"""
        current_items = {'cafe': [], 'twitter': []}
        
        # 각 타입별로 여러 번 시도
        for attempt in range(self.network_retry_count):
            try:
                # 카페 글 수집 (재시도)
                if not current_items['cafe']:
                    cafe_items = await self._collect_cafe_items()
                    if cafe_items:
                        current_items['cafe'] = cafe_items
                        logger.debug(f"카페 글 수집 성공 ({attempt + 1}번째 시도)")
                
                # 트위터 글 수집 (재시도)
                if not current_items['twitter']:
                    twitter_items = await self._collect_twitter_items()
                    if twitter_items:
                        current_items['twitter'] = twitter_items
                        logger.debug(f"트위터 글 수집 성공 ({attempt + 1}번째 시도)")
                
                # 둘 다 성공하면 중단
                if current_items['cafe'] or current_items['twitter']:
                    break
                    
                # 재시도 전 대기
                if attempt < self.network_retry_count - 1:
                    await asyncio.sleep(2 ** attempt)  # 지수 백오프
                    
            except Exception as e:
                logger.warning(f"글 수집 시도 {attempt + 1} 실패: {e}")
                if attempt < self.network_retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return current_items
    
    async def _collect_current_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """현재 확인 가능한 모든 카페글과 트위터글을 수집합니다 (기존 메서드)"""
        current_items = {'cafe': [], 'twitter': []}
        
        try:
            # 카페 글 수집
            cafe_items = await self._collect_cafe_items()
            current_items['cafe'] = cafe_items
            
            # 트위터 글 수집  
            twitter_items = await self._collect_twitter_items()
            current_items['twitter'] = twitter_items
            
        except Exception as e:
            logger.error(f"현재 항목 수집 중 오류: {e}")
        
        return current_items
    
    async def _collect_cafe_items(self) -> List[Dict[str, Any]]:
        """모든 활성 스트리머의 카페 글을 수집합니다"""
        cafe_items = []
        
        try:
            from ..browser.naver_session import naver_session
            
            # 로그인 상태가 아니면 건너뜀
            if not naver_session.is_logged_in:
                logger.debug("네이버 로그인 상태가 아니므로 카페 글 수집을 건너뜁니다")
                return []
            
            streamers = config.get_streamers()
            active_cafe_streamers = {
                name: data for name, data in streamers.items()
                if data.get('enabled', True) and data.get('cafe_user_id')
            }
            
            for name, data in active_cafe_streamers.items():
                try:
                    club_id = data.get('cafe_club_id', config.cafe_club_id)
                    user_id = data['cafe_user_id']
                    
                    # 카페 게시물 가져오기 (타임아웃 단축)
                    posts = await asyncio.wait_for(
                        naver_session.get_cafe_posts(club_id, user_id),
                        timeout=10.0
                    )
                    
                    if posts:
                        for post in posts:
                            cafe_items.append({
                                'streamer_name': name,
                                'id': post['id'],
                                'title': post['title'],
                                'url': post['url'],
                                'date': post['date'],
                                'type': 'cafe',
                                'unique_key': f"cafe_{name}_{post['id']}"
                            })
                        logger.debug(f"{name} 카페: {len(posts)}개 글 수집")
                    
                    # 요청 간 지연
                    await asyncio.sleep(0.5)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"{name} 카페 글 수집 타임아웃")
                except Exception as e:
                    logger.warning(f"{name} 카페 글 수집 실패: {e}")
                    
        except Exception as e:
            logger.error(f"카페 글 수집 중 오류: {e}")
        
        return cafe_items
    
    async def _collect_twitter_items(self) -> List[Dict[str, Any]]:
        """모든 활성 스트리머의 트위터 글을 수집합니다"""
        twitter_items = []
        
        try:
            from ..monitors.twitter_monitor import twitter_monitor
            
            streamers = config.get_streamers()
            active_twitter_streamers = {
                name: data for name, data in streamers.items()
                if data.get('enabled', True) and data.get('twitter_username')
            }
            
            for name, data in active_twitter_streamers.items():
                try:
                    username = data['twitter_username']
                    
                    # RSS 피드에서 트윗 가져오기 (타임아웃 단축)
                    tweets = await asyncio.wait_for(
                        twitter_monitor.get_tweets_from_rss(username),
                        timeout=15.0
                    )
                    
                    if tweets:
                        for tweet in tweets:
                            twitter_items.append({
                                'streamer_name': name,
                                'id': tweet['id'],
                                'title': tweet['title'],
                                'url': tweet['url'],
                                'published': tweet['published'],
                                'type': 'twitter',
                                'unique_key': f"twitter_{name}_{tweet['id']}"
                            })
                        logger.debug(f"{name} 트위터: {len(tweets)}개 트윗 수집")
                    
                    # 요청 간 지연
                    await asyncio.sleep(0.5)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"{name} 트위터 글 수집 타임아웃")
                except Exception as e:
                    logger.warning(f"{name} 트위터 글 수집 실패: {e}")
                    
        except Exception as e:
            logger.error(f"트위터 글 수집 중 오류: {e}")
        
        return twitter_items
    
    def _get_existing_notification_records(self) -> Set[str]:
        """기존 알림 기록에서 고유 키들을 추출합니다"""
        existing_keys = set()
        
        try:
            notifications = config.get_notifications()
            
            for notification in notifications:
                # 기존 알림에서 고유 키 생성
                noti_type = notification.get('type', '')
                streamer_name = notification.get('streamer_name', '')
                
                if noti_type in ['cafe', 'twitter'] and streamer_name:
                    # URL에서 ID 추출 시도
                    url = notification.get('url', '')
                    extracted_id = self._extract_id_from_url(url, noti_type)
                    
                    if extracted_id:
                        unique_key = f"{noti_type}_{streamer_name}_{extracted_id}"
                        existing_keys.add(unique_key)
            
            logger.debug(f"기존 알림에서 {len(existing_keys)}개 고유 키 추출")
            
        except Exception as e:
            logger.error(f"기존 알림 기록 분석 중 오류: {e}")
        
        return existing_keys
    
    def _get_existing_notification_records_safe(self) -> Set[str]:
        """기존 알림 기록을 안전하게 로드합니다 (손상된 데이터 대응)"""
        try:
            # 기존 메서드 호출
            return self._get_existing_notification_records()
        except Exception as e:
            logger.error(f"알림 기록 로드 실패, 백업 방법 시도: {e}")
            
            try:
                # 직접 파일에서 읽기 시도
                notification_file = os.path.join(config.data_dir, "notifications.json")
                if os.path.exists(notification_file):
                    with open(notification_file, 'r', encoding='utf-8') as f:
                        raw_data = f.read().strip()
                    
                    if raw_data:
                        import json
                        notifications = json.loads(raw_data)
                        
                        existing_keys = set()
                        for notification in notifications:
                            noti_type = notification.get('type', '')
                            streamer_name = notification.get('streamer_name', '')
                            
                            if noti_type in ['cafe', 'twitter'] and streamer_name:
                                url = notification.get('url', '')
                                extracted_id = self._extract_id_from_url(url, noti_type)
                                
                                if extracted_id:
                                    unique_key = f"{noti_type}_{streamer_name}_{extracted_id}"
                                    existing_keys.add(unique_key)
                        
                        logger.info(f"백업 방법으로 {len(existing_keys)}개 기록 복구")
                        return existing_keys
                        
            except Exception as backup_error:
                logger.warning(f"백업 로드도 실패: {backup_error}")
            
            # 모든 방법 실패 시 빈 집합 반환
            logger.warning("기존 알림 기록을 불러올 수 없어 빈 상태로 시작")
            return set()
    
    def _extract_id_from_url(self, url: str, content_type: str) -> Optional[str]:
        """URL에서 고유 ID를 추출합니다 (다양한 URL 형식 지원)"""
        try:
            if content_type == 'cafe':
                # 카페 URL 패턴 1: https://cafe.naver.com/ArticleRead.nhn?clubid=30919539&articleid=107499
                if 'articleid=' in url:
                    import re
                    match = re.search(r'articleid=([0-9]+)', url)
                    if match:
                        return match.group(1)
                
                # 카페 URL 패턴 2: https://cafe.naver.com/ca-fe/cafes/30919539/articles/123456?fromList=true
                if 'articles/' in url:
                    parts = url.split('articles/')
                    if len(parts) > 1:
                        article_id = parts[1].split('?')[0].split('/')[0]
                        return article_id
                        
            elif content_type == 'twitter':
                # 트위터 URL: https://nitter.instance/username/status/1234567890
                if '/status/' in url:
                    parts = url.split('/status/')
                    if len(parts) > 1:
                        status_id = parts[1].split('?')[0].split('/')[0].split('#')[0]
                        return status_id
                        
        except Exception as e:
            logger.debug(f"URL ID 추출 실패 ({content_type}): {e}")
        
        return None
    
    def _identify_missed_items(self, current_items: Dict[str, List[Dict]], existing_records: Set[str]) -> Dict[str, List[Dict]]:
        """현재 항목과 기존 기록을 비교하여 누락된 항목들을 식별합니다"""
        missed_items = {'cafe': [], 'twitter': []}
        
        for item_type in ['cafe', 'twitter']:
            items = current_items[item_type]
            
            for item in items:
                unique_key = item['unique_key']
                
                # 기존 기록에 없는 항목이면 누락된 것으로 판단
                if unique_key not in existing_records:
                    # 시간 필터링: 너무 오래된 글은 제외 (7일 이내)
                    if self._is_recent_item(item):
                        missed_items[item_type].append(item)
                    else:
                        logger.debug(f"오래된 항목 제외: {unique_key}")
        
        # 시간순으로 정렬 (오래된 것부터)
        for item_type in missed_items:
            missed_items[item_type].sort(key=lambda x: self._get_item_timestamp(x))
        
        return missed_items
    
    def _is_recent_item(self, item: Dict[str, Any]) -> bool:
        """항목이 최근 7일 이내의 것인지 확인합니다"""
        try:
            item_time = self._get_item_timestamp(item)
            if item_time:
                cutoff_time = datetime.now() - timedelta(days=7)
                return item_time > cutoff_time
        except Exception as e:
            logger.debug(f"시간 필터링 오류: {e}")
        
        # 시간 판단이 불가능한 경우 포함
        return True
    
    def _get_item_timestamp(self, item: Dict[str, Any]) -> Optional[datetime]:
        """항목의 타임스탬프를 추출합니다"""
        try:
            if item['type'] == 'cafe':
                date_str = item.get('date', '')
                # 카페 날짜 형식 처리
                if ':' in date_str and '.' not in date_str:
                    # "15:30" 형식 (오늘)
                    today = datetime.now().date()
                    time_parts = date_str.split(':')
                    if len(time_parts) == 2:
                        hour, minute = int(time_parts[0]), int(time_parts[1])
                        return datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                elif '.' in date_str:
                    # "2025.07.02." 형식
                    date_clean = date_str.rstrip('.')
                    return datetime.strptime(date_clean, '%Y.%m.%d')
                    
            elif item['type'] == 'twitter':
                published = item.get('published', '')
                if published:
                    # RSS 날짜 형식 파싱
                    from email.utils import parsedate_to_datetime
                    return parsedate_to_datetime(published)
                    
        except Exception as e:
            logger.debug(f"타임스탬프 추출 실패: {e}")
        
        return None
    
    async def _send_missed_notifications(self, item_type: str, items: List[Dict[str, Any]]) -> int:
        """누락된 알림들을 순차적으로 발송합니다"""
        sent_count = 0
        
        try:
            for i, item in enumerate(items):
                try:
                    success = await self._send_single_notification(item)
                    if success:
                        sent_count += 1
                        logger.debug(f"{item_type} 알림 발송 완료: {item['title'][:30]}...")
                    else:
                        logger.warning(f"{item_type} 알림 발송 실패: {item['title'][:30]}...")
                    
                    # 마지막 항목이 아니면 지연
                    if i < len(items) - 1:
                        await asyncio.sleep(self.recovery_delay)
                        
                except Exception as e:
                    logger.error(f"개별 알림 발송 오류: {e}")
                    
        except Exception as e:
            logger.error(f"{item_type} 알림 발송 중 오류: {e}")
        
        return sent_count
    
    async def _send_missed_notifications_with_error_tracking(self, item_type: str, items: List[Dict[str, Any]]) -> Tuple[int, int]:
        """누락된 알림들을 순차적으로 발송합니다 (에러 추적 포함)"""
        sent_count = 0
        error_count = 0
        
        try:
            for i, item in enumerate(items):
                try:
                    success = await self._send_single_notification(item)
                    if success:
                        sent_count += 1
                        logger.debug(f"{item_type} 알림 발송 완료: {item['title'][:30]}...")
                    else:
                        error_count += 1
                        logger.warning(f"{item_type} 알림 발송 실패: {item['title'][:30]}...")
                    
                    # 마지막 항목이 아니면 지연
                    if i < len(items) - 1:
                        await asyncio.sleep(self.recovery_delay)
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"개별 알림 발송 오류: {e}")
                    
                    # 심각한 오류가 연속으로 발생하면 잠시 대기 후 계속
                    if error_count > 0 and error_count % 5 == 0:
                        logger.warning(f"연속 오류 {error_count}개 발생, 5초 대기 후 계속")
                        await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"{item_type} 알림 발송 중 치명적 오류: {e}")
            error_count += 1
        
        return sent_count, error_count
    
    async def _send_single_notification(self, item: Dict[str, Any]) -> bool:
        """단일 알림을 발송하고 기록에 추가합니다 (프로필 이미지 매칭 오류 수정)"""
        try:
            streamer_name = item['streamer_name']
            item_type = item['type']
            title = item['title']
            url = item['url']
            
            logger.debug(f"📢 {item_type} 알림 발송 시작: {streamer_name} - {title[:30]}...")
            
            # 프로필 이미지 가져오기 (스트리머 이름 검증 강화)
            profile_image_url = await self._get_streamer_profile_image_safe(streamer_name)
            
            # 알림 발송
            if item_type == 'cafe':
                await NotificationManager.show_cafe_notification(
                    streamer_name, title, url, profile_image_url
                )
                notification_title = f"{streamer_name} 카페 새 글"
            else:  # twitter
                await NotificationManager.show_twitter_notification(
                    streamer_name, title, url, profile_image_url
                )
                notification_title = f"{streamer_name} 새 트윗"
            
            logger.debug(f"✅ {item_type} 알림 발송 완료: {streamer_name} (프로필: {'있음' if profile_image_url else '없음'})")
            
            # 알림 기록에 추가
            config.add_notification(
                streamer_name=streamer_name,
                notification_type=item_type,
                title=notification_title,
                content=title,
                url=url
            )
            
            return True
            
        except Exception as e:
            logger.error(f"단일 알림 발송 실패 ({item.get('streamer_name', 'unknown')}): {e}")
            import traceback
            logger.debug(f"알림 발송 오류 상세:\n{traceback.format_exc()}")
            return False
    
    async def _get_streamer_profile_image(self, streamer_name: str) -> Optional[str]:
        """스트리머 프로필 이미지 URL을 가져옵니다"""
        try:
            streamers = config.get_streamers()
            streamer_data = streamers.get(streamer_name, {})
            chzzk_id = streamer_data.get('chzzk_id')
            
            if not chzzk_id:
                return None
            
            from ..monitors.chzzk_monitor import chzzk_monitor
            return await chzzk_monitor.get_channel_profile_image(chzzk_id)
            
        except Exception as e:
            logger.warning(f"프로필 이미지 가져오기 실패 ({streamer_name}): {e}")
            return None
    
    async def _get_streamer_profile_image_safe(self, streamer_name: str) -> Optional[str]:
        """스트리머 프로필 이미지 URL을 안전하게 가져옵니다 (매칭 오류 방지)"""
        try:
            # 스트리머 이름 검증
            if not streamer_name or not isinstance(streamer_name, str):
                logger.warning(f"⚠️ 잘못된 스트리머 이름: {streamer_name} (타입: {type(streamer_name)})")
                return None
            
            # 스트리머 데이터 가져오기
            streamers = config.get_streamers()
            if not streamers:
                logger.warning("⚠️ 스트리머 데이터를 불러올 수 없습니다")
                return None
            
            # 정확한 스트리머 이름 매칭 확인
            if streamer_name not in streamers:
                logger.warning(f"⚠️ 스트리머 '{streamer_name}' 설정을 찾을 수 없습니다")
                logger.debug(f"사용 가능한 스트리머: {list(streamers.keys())}")
                return None
            
            streamer_data = streamers[streamer_name]
            chzzk_id = streamer_data.get('chzzk_id')
            
            if not chzzk_id:
                logger.debug(f"스트리머 '{streamer_name}'의 CHZZK ID가 없습니다")
                return None
            
            logger.debug(f"🖼️ 프로필 이미지 요청: {streamer_name} (CHZZK ID: {chzzk_id})")
            
            # CHZZK 모니터를 통해 프로필 이미지 가져오기
            from ..monitors.chzzk_monitor import chzzk_monitor
            
            # 타임아웃을 적용하여 무한 대기 방지
            profile_url = await asyncio.wait_for(
                chzzk_monitor.get_channel_profile_image(chzzk_id),
                timeout=10.0
            )
            
            if profile_url:
                logger.debug(f"✅ 프로필 이미지 취득 성공: {streamer_name}")
            else:
                logger.debug(f"⚠️ 프로필 이미지 없음: {streamer_name}")
            
            return profile_url
            
        except asyncio.TimeoutError:
            logger.warning(f"⏰ 프로필 이미지 가져오기 타임아웃 ({streamer_name})")
            return None
        except Exception as e:
            logger.warning(f"💥 프로필 이미지 가져오기 실패 ({streamer_name}): {e}")
            import traceback
            logger.debug(f"프로필 이미지 오류 상세 ({streamer_name}):\n{traceback.format_exc()}")
            return None
    
    async def _show_bulk_recovery_notification(self, total_count: int):
        """대량 복구 시작을 알리는 시스템 알림"""
        try:
            title = "📢 누락 알림 복구 중"
            message = f"앱이 꺼져있던 동안 발생한 {total_count}개의 새 글을 발견했습니다.\n순차적으로 알림을 발송합니다."
            
            NotificationManager.show_notification(title, message)
            logger.info(f"대량 복구 시작 알림 발송: {total_count}개 항목")
            
        except Exception as e:
            logger.error(f"대량 복구 알림 발송 실패: {e}")


    async def test_twitter_notification_recovery(self) -> Dict[str, Any]:
        """
        트위터 알림 복구 시스템 테스트 및 검증
        
        Returns:
            Dict[str, Any]: 테스트 결과 {'success': bool, 'details': dict}
        """
        test_results = {
            'success': False,
            'twitter_collection': False,
            'id_extraction': False,
            'notification_records': False,
            'comparison_logic': False,
            'details': {}
        }
        
        try:
            logger.info("🧪 트위터 알림 복구 시스템 테스트 시작")
            
            # 1. 트위터 데이터 수집 테스트
            try:
                twitter_items = await self._collect_twitter_items()
                test_results['twitter_collection'] = len(twitter_items) > 0
                test_results['details']['twitter_items_count'] = len(twitter_items)
                logger.info(f"✅ 트위터 데이터 수집: {len(twitter_items)}개 수집")
                
                # 2. ID 추출 테스트
                id_extraction_success = 0
                for item in twitter_items[:5]:  # 처음 5개만 테스트
                    extracted_id = self._extract_id_from_url(item['url'], 'twitter')
                    if extracted_id:
                        id_extraction_success += 1
                
                test_results['id_extraction'] = id_extraction_success > 0
                test_results['details']['id_extraction_count'] = id_extraction_success
                logger.info(f"✅ ID 추출: {id_extraction_success}/5개 성공")
                
            except Exception as e:
                logger.error(f"❌ 트위터 데이터 수집 테스트 실패: {e}")
                test_results['details']['twitter_error'] = str(e)
            
            # 3. 알림 기록 로드 테스트
            try:
                existing_records = self._get_existing_notification_records_safe()
                test_results['notification_records'] = True
                test_results['details']['existing_records_count'] = len(existing_records)
                logger.info(f"✅ 알림 기록 로드: {len(existing_records)}개 기록")
            except Exception as e:
                logger.error(f"❌ 알림 기록 로드 테스트 실패: {e}")
                test_results['details']['records_error'] = str(e)
            
            # 4. 비교 로직 테스트
            try:
                if test_results['twitter_collection'] and test_results['notification_records']:
                    current_items = {'cafe': [], 'twitter': twitter_items}
                    missed_items = self._identify_missed_items(current_items, existing_records)
                    test_results['comparison_logic'] = True
                    test_results['details']['missed_twitter'] = len(missed_items['twitter'])
                    logger.info(f"✅ 비교 로직: {len(missed_items['twitter'])}개 누락 트윗 식별")
            except Exception as e:
                logger.error(f"❌ 비교 로직 테스트 실패: {e}")
                test_results['details']['comparison_error'] = str(e)
            
            # 전체 성공 여부 판단
            test_results['success'] = all([
                test_results['twitter_collection'],
                test_results['id_extraction'],
                test_results['notification_records'],
                test_results['comparison_logic']
            ])
            
            if test_results['success']:
                logger.info("🎉 트위터 알림 복구 시스템 테스트 완전 성공")
            else:
                logger.warning("⚠️ 트위터 알림 복구 시스템 테스트 부분 실패")
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ 트위터 알림 복구 테스트 중 치명적 오류: {e}")
            test_results['details']['fatal_error'] = str(e)
            return test_results


    def test_url_id_extraction_fix(self) -> Dict[str, Any]:
        """URL ID 추출 로직 수정 테스트"""
        test_results = {
            'success': False,
            'cafe_articleread_pattern': False,
            'cafe_articles_pattern': False,
            'twitter_pattern': False,
            'edge_cases': False,
            'real_data_test': False,
            'details': {}
        }
        
        try:
            logger.info("🧪 URL ID 추출 로직 수정 테스트 시작")
            
            # 카페 URL 패턴 1 테스트 (실제 사용되는 형식)
            cafe_url_1 = "https://cafe.naver.com/ArticleRead.nhn?clubid=30919539&articleid=107499"
            id_1 = self._extract_id_from_url(cafe_url_1, 'cafe')
            test_results['cafe_articleread_pattern'] = (id_1 == '107499')
            test_results['details']['cafe_articleread_result'] = id_1
            logger.info(f"카페 URL 패턴 1: {id_1} (예상: 107499)")
            
            # 카페 URL 패턴 2 테스트 (기존 예상 형식)
            cafe_url_2 = "https://cafe.naver.com/ca-fe/cafes/30919539/articles/123456?fromList=true"
            id_2 = self._extract_id_from_url(cafe_url_2, 'cafe')
            test_results['cafe_articles_pattern'] = (id_2 == '123456')
            test_results['details']['cafe_articles_result'] = id_2
            logger.info(f"카페 URL 패턴 2: {id_2} (예상: 123456)")
            
            # 트위터 URL 테스트
            twitter_url = "https://nitter.instance/username/status/1234567890"
            id_3 = self._extract_id_from_url(twitter_url, 'twitter')
            test_results['twitter_pattern'] = (id_3 == '1234567890')
            test_results['details']['twitter_result'] = id_3
            logger.info(f"트위터 URL: {id_3} (예상: 1234567890)")
            
            # 엣지 케이스 테스트
            edge_cases = [
                ("", 'cafe'),  # 빈 URL
                ("invalid-url", 'cafe'),  # 잘못된 URL
                ("https://cafe.naver.com/ArticleRead.nhn?clubid=abc&articleid=xyz", 'cafe'),  # 비숫자 ID
                ("https://cafe.naver.com/ArticleRead.nhn", 'cafe'),  # articleid 없음
            ]
            
            edge_success = 0
            for url, content_type in edge_cases:
                result = self._extract_id_from_url(url, content_type)
                if result is None:  # 엣지 케이스는 None을 반환해야 함
                    edge_success += 1
            
            test_results['edge_cases'] = (edge_success == len(edge_cases))
            test_results['details']['edge_cases_passed'] = f"{edge_success}/{len(edge_cases)}"
            logger.info(f"엣지 케이스: {edge_success}/{len(edge_cases)} 통과")
            
            # 실제 데이터로 테스트
            try:
                existing_records = self._get_existing_notification_records_safe()
                test_results['real_data_test'] = len(existing_records) > 0
                test_results['details']['extracted_records_count'] = len(existing_records)
                logger.info(f"실제 데이터 테스트: {len(existing_records)}개 기록에서 고유 키 추출")
            except Exception as e:
                logger.warning(f"실제 데이터 테스트 실패: {e}")
                test_results['details']['real_data_error'] = str(e)
            
            # 전체 성공 여부
            test_results['success'] = all([
                test_results['cafe_articleread_pattern'],
                test_results['cafe_articles_pattern'], 
                test_results['twitter_pattern'],
                test_results['edge_cases'],
                test_results['real_data_test']
            ])
            
            if test_results['success']:
                logger.info("🎉 URL ID 추출 로직 수정 테스트 완전 성공")
            else:
                logger.warning("⚠️ URL ID 추출 로직 수정 테스트 부분 실패")
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ URL ID 추출 테스트 중 오류: {e}")
            test_results['details']['test_error'] = str(e)
            return test_results
    
    def _debug_url_extraction_status(self, current_items: Dict[str, List[Dict]], existing_records: Set[str]):
        """URL ID 추출 상태 디버깅 정보 출력 (중복 알림 문제 진단용)"""
        try:
            logger.info("🔍 URL ID 추출 상태 디버깅")
            
            # 현재 항목들의 ID 추출 성공률 체크
            for item_type in ['cafe', 'twitter']:
                items = current_items[item_type]
                if not items:
                    continue
                    
                extraction_success = 0
                for item in items[:5]:  # 처음 5개만 샘플링
                    url = item.get('url', '')
                    extracted_id = self._extract_id_from_url(url, item_type)
                    if extracted_id:
                        extraction_success += 1
                        logger.debug(f"{item_type} URL 샘플: {url[:50]}... → ID: {extracted_id}")
                    else:
                        logger.warning(f"❌ {item_type} ID 추출 실패: {url[:50]}...")
                
                success_rate = extraction_success / min(len(items), 5)
                logger.info(f"{item_type} ID 추출 성공률: {success_rate:.1%} ({extraction_success}/{min(len(items), 5)})")
            
            # 기존 기록에서 고유 키 생성 성공률 체크
            if existing_records:
                logger.info(f"기존 알림 기록에서 {len(existing_records)}개 고유 키 생성 성공")
                
                # 샘플 기존 기록 출력
                sample_keys = list(existing_records)[:3]
                for key in sample_keys:
                    logger.debug(f"기존 고유 키 샘플: {key}")
            else:
                logger.warning("⚠️ 기존 알림 기록에서 고유 키를 추출하지 못했습니다 - 모든 항목이 '누락'으로 처리됩니다")
                
        except Exception as e:
            logger.debug(f"디버깅 정보 출력 중 오류: {e}")
    
    def _emergency_duplicate_detection_diagnosis(self, current_items: Dict[str, List[Dict]], existing_records: Set[str]):
        """중복 감지 실패 시 긴급 진단 실행"""
        try:
            logger.error("🚨 긴급 진단: 중복 감지 로직 분석")
            
            # 현재 항목 샘플 분석
            for item_type in ['cafe', 'twitter']:
                items = current_items[item_type]
                if items:
                    sample_item = items[0]
                    url = sample_item.get('url', '')
                    streamer_name = sample_item.get('streamer_name', '')
                    
                    # 고유 키 생성 과정 추적
                    extracted_id = self._extract_id_from_url(url, item_type)
                    if extracted_id:
                        unique_key = f"{item_type}_{streamer_name}_{extracted_id}"
                        is_in_existing = unique_key in existing_records
                        
                        logger.error(f"{item_type} 샘플 분석:")
                        logger.error(f"  URL: {url}")
                        logger.error(f"  추출된 ID: {extracted_id}")
                        logger.error(f"  생성된 고유 키: {unique_key}")
                        logger.error(f"  기존 기록에 존재: {is_in_existing}")
                        
                        if not is_in_existing:
                            # 유사한 키 검색
                            similar_keys = [key for key in existing_records if extracted_id in key or streamer_name in key]
                            if similar_keys:
                                logger.error(f"  유사한 기존 키들: {similar_keys[:3]}")
                    else:
                        logger.error(f"{item_type} ID 추출 완전 실패: {url}")
            
            # 기존 기록 샘플 분석
            if existing_records:
                sample_keys = list(existing_records)[:3]
                logger.error(f"기존 기록 샘플: {sample_keys}")
                
        except Exception as e:
            logger.error(f"긴급 진단 중 오류: {e}")
    
    def force_reset_notification_tracking(self) -> bool:
        """강제로 알림 추적을 초기화합니다 (중복 알림 해결을 위한 극단적 방법)"""
        try:
            logger.warning("⚠️ 강제 알림 추적 초기화 실행")
            
            # 현재 실행 중인 모니터들의 상태 초기화
            try:
                from ..monitors.cafe_monitor import cafe_monitor
                from ..monitors.twitter_monitor import twitter_monitor
                
                # 카페 모니터 초기화
                if hasattr(cafe_monitor, 'last_post_ids'):
                    cafe_monitor.last_post_ids.clear()
                    logger.info("카페 모니터 last_post_ids 초기화")
                
                if hasattr(cafe_monitor, 'first_check'):
                    cafe_monitor.first_check = True
                    logger.info("카페 모니터 first_check 플래그 리셋")
                
                # 트위터 모니터 초기화
                if hasattr(twitter_monitor, 'last_tweet_ids'):
                    twitter_monitor.last_tweet_ids.clear()
                    logger.info("트위터 모니터 last_tweet_ids 초기화")
                
                if hasattr(twitter_monitor, 'first_check'):
                    twitter_monitor.first_check = True
                    logger.info("트위터 모니터 first_check 플래그 리셋")
                
                logger.info("✅ 모니터 상태 초기화 완료")
                return True
                
            except Exception as e:
                logger.error(f"모니터 상태 초기화 실패: {e}")
                return False
                
        except Exception as e:
            logger.error(f"강제 알림 추적 초기화 실패: {e}")
            return False


# 전역 인스턴스
missed_notification_recovery = MissedNotificationRecovery()