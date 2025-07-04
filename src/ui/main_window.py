"""
메인 윈도우 - 리팩토링된 버전
"""
import streamlit as st
import time
import json
import os
import webbrowser
import asyncio
from datetime import datetime
from typing import Optional
from ..config import config
from ..utils.logger import logger
from .styles import load_css

class MainWindow:
    def __init__(self):
        self.setup_page_config()
        self.initialize_session_state()
        
    def setup_page_config(self):
        """페이지 기본 설정"""
        st.set_page_config(
            page_title="스트리머 알림",
            page_icon="📺",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # CSS 로드
        load_css()
    
    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.refresh_counter = 0
            logger.debug("세션 상태 초기화 완료")
            
            # 초기화 시 프로필 이미지 스캔 실행
            self.scan_existing_profile_images()
            
            # 기존 스트리머들에 알림 설정 추가 (마이그레이션)
            self.migrate_notification_settings()
        
        # 라이브 상태 관리를 위한 세션 상태 초기화
        if 'streamer_data_cache' not in st.session_state:
            st.session_state.streamer_data_cache = {}
        if 'cache_timestamp' not in st.session_state:
            st.session_state.cache_timestamp = 0
            # 초기화 시 라이브 상태 파일 읽기
            self.try_update_live_status_background()
        if 'last_auto_refresh' not in st.session_state:
            st.session_state.last_auto_refresh = 0
    
    def render_header(self):
        """헤더 렌더링"""
        st.markdown("""
        <div class="app-header">
            <h1 class="app-title">📺 스트리머 알림</h1>
            <p class="app-subtitle">실시간 스트리머 모니터링 시스템</p>
        </div>
        """, unsafe_allow_html=True)
    
    def try_update_live_status_background(self):
        """메인 모니터링 시스템에서 저장한 라이브 상태 파일 읽기"""
        try:
            import json
            import os
            import time
            
            # 라이브 상태 파일 경로
            live_status_file = os.path.join(config.data_dir, "live_status.json")
            
            if os.path.exists(live_status_file):
                with open(live_status_file, 'r', encoding='utf-8') as f:
                    live_status_data = json.load(f)
                
                # 데이터를 세션 캐시에 업데이트
                for streamer_name, status_info in live_status_data.items():
                    if streamer_name not in st.session_state.streamer_data_cache:
                        st.session_state.streamer_data_cache[streamer_name] = {}
                    
                    st.session_state.streamer_data_cache[streamer_name]['is_live'] = status_info.get('is_live', False)
                    st.session_state.streamer_data_cache[streamer_name]['title'] = status_info.get('title', '')
                    st.session_state.streamer_data_cache[streamer_name]['url'] = status_info.get('url', '')
                
                # 타임스탬프 업데이트
                st.session_state.cache_timestamp = time.time()
                logger.debug(f"UI 라이브 상태 파일 업데이트: {len(live_status_data)}개 스트리머")
            else:
                logger.debug("라이브 상태 파일이 아직 생성되지 않음")
                
        except Exception as e:
            logger.debug(f"라이브 상태 파일 읽기 실패: {e}")
    
    def setup_auto_refresh(self):
        """자동 새로고침 설정"""
        import time
        
        # 자동 새로고침 간격 (초)
        auto_refresh_interval = 15
        
        current_time = time.time()
        time_since_refresh = current_time - st.session_state.last_auto_refresh
        
        # 15초마다 자동 새로고침
        if time_since_refresh >= auto_refresh_interval:
            st.session_state.last_auto_refresh = current_time
            # 라이브 상태 파일 다시 읽기
            self.try_update_live_status_background()
            logger.debug("UI 자동 새로고침 실행")
            st.rerun()
        
        # 남은 시간 표시 (선택사항 - 우측 상단에 작은 텍스트)
        remaining_time = auto_refresh_interval - int(time_since_refresh)
        if remaining_time > 0:
            st.markdown(f'<div style="position: fixed; top: 10px; right: 10px; background: rgba(0,0,0,0.7); color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; z-index: 999;">🔄 {remaining_time}초 후 업데이트</div>', unsafe_allow_html=True)
    
    def get_live_count_cached(self):
        """캐시된 라이브 카운트 반환 (메인 모니터링 데이터 활용)"""
        import time
        
        current_time = time.time()
        if current_time - st.session_state.cache_timestamp > 10:  # 10초 캐시
            # 메인 모니터링 시스템에서 데이터 동기화
            self.try_update_live_status_background()
        
        # 라이브 중인 스트리머 수 반환
        return len([name for name, data in st.session_state.streamer_data_cache.items() if data.get('is_live', False)])
    
    
    def display_cached_profile_image(self, profile_url: str, width: int = 64):
        """캐시된 프로필 이미지 표시"""
        try:
            # st.image에 자체 캐싱 기능이 있어서 별도 캐시 불필요
            st.image(profile_url, width=width)
        except Exception as e:
            logger.debug(f"프로필 이미지 로드 실패: {e}")
            # 기본 아바타로 폴백 
            avatar_size = width if width else 64
            st.markdown(f'<div style="width: {avatar_size}px; height: {avatar_size}px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: {avatar_size//2}px; color: white; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">👤</div>', unsafe_allow_html=True)

    
    def url_to_base64_sync(self, image_url: str) -> str:
        """URL 이미지를 Base64로 변환 (동기 버전, 크기 최적화)"""
        try:
            import requests
            import base64
            from PIL import Image
            import io
            
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                # 이미지 크기 최적화 (UI 표시용으로 리사이즈)
                try:
                    # PIL로 이미지 로드 및 리사이즈
                    with Image.open(io.BytesIO(response.content)) as img:
                        # RGBA를 RGB로 변환
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        
                        # 80x80으로 리사이즈 (UI 표시용)
                        img = img.resize((80, 80), Image.Resampling.LANCZOS)
                        
                        # 최적화된 JPEG로 저장
                        output = io.BytesIO()
                        img.save(output, format='JPEG', quality=75, optimize=True)
                        return base64.b64encode(output.getvalue()).decode('utf-8')
                
                except Exception as e:
                    logger.debug(f"이미지 최적화 실패, 원본 사용: {e}")
                    # 최적화 실패 시 원본 사용
                    return base64.b64encode(response.content).decode('utf-8')
            else:
                logger.debug(f"이미지 다운로드 실패: {response.status_code}")
                return ''
        except Exception as e:
            logger.debug(f"URL to Base64 변환 실패: {e}")
            return ''
    
    
    def cleanup_old_cache_files(self):
        """사용하지 않는 프로필 캐시 파일들 정리"""
        try:
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            
            # profile_로 시작하는 캐시 파일들 찾기
            cache_files = []
            try:
                cache_files = [f for f in os.listdir(temp_dir) if f.startswith('profile_') and f.endswith('.jpg')]
            except Exception as e:
                logger.debug(f"임시 디렉토리 스캔 실패: {e}")
                return
            
            if cache_files:
                logger.info(f"기존 프로필 캐시 파일 {len(cache_files)}개 정리 중...")
                deleted_count = 0
                
                for cache_file in cache_files:
                    try:
                        file_path = os.path.join(temp_dir, cache_file)
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"캐시 파일 삭제: {cache_file}")
                    except Exception as e:
                        logger.warning(f"캐시 파일 삭제 실패 ({cache_file}): {e}")
                
                logger.info(f"프로필 캐시 파일 {deleted_count}개 정리 완료")
        except Exception as e:
            logger.warning(f"캐시 파일 정리 오류: {e}")
    
    def scan_existing_profile_images(self):
        """더 이상 필요 없는 함수 - URL 직접 사용으로 변경됨"""
        # URL 방식으로 변경되어 캐시 파일 정리만 수행
        self.cleanup_old_cache_files()
            
    # 더 이상 사용하지 않는 함수 (URL 직접 사용으로 변경)
    # def get_cached_profile_image_path(self, profile_url: str) -> str:
    
    
    
    def run(self):
        """메인 애플리케이션 실행"""
        try:
            # 헤더 렌더링
            self.render_header()
            
            
            # 탭 시스템
            tab1, tab2, tab3 = st.tabs(["🎮 스트리머 관리", "🔔 알림 기록", "⚙️ 설정"])
            
            with tab1:
                self.show_streamer_management()
            
            with tab2:
                self.show_notification_history()
            
            with tab3:
                self.show_settings()
                
        except Exception as e:
            logger.error(f"메인 윈도우 실행 오류: {e}")
            st.error(f"❌ 애플리케이션 실행 중 오류가 발생했습니다: {e}")
    
    def show_streamer_management(self):
        """스트리머 관리 페이지"""
        try:
            # 자동 새로고침 설정
            self.setup_auto_refresh()
            
            # 통계 요약
            streamers = config.get_streamers()
            total_streamers = len(streamers)
            active_streamers = sum(1 for data in streamers.values() if data.get('enabled', True))
            
            # 메트릭 카드들
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown('<div class="metric-card"><h3>전체 스트리머</h3><h2>' + str(total_streamers) + '</h2></div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card"><h3>활성 상태</h3><h2>' + str(active_streamers) + '</h2></div>', unsafe_allow_html=True)
            with col3:
                live_count = self.get_live_count_cached()
                st.markdown('<div class="metric-card"><h3>라이브 중</h3><h2>' + str(live_count) + '</h2></div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            
            # 스트리머 목록
            if not streamers:
                st.markdown("""
                <div class="empty-state">
                    <h3>🎭 등록된 스트리머가 없습니다</h3>
                    <p>아래 '새 스트리머 추가' 버튼을 클릭하여 스트리머를 추가해보세요!</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 빈 상태에서도 추가 버튼 표시
                _, col2, _ = st.columns([2, 1, 2])
                with col2:
                    if st.button("➕ 새 스트리머 추가", type="primary", use_container_width=True, key="empty_add_btn"):
                        st.session_state.show_add_form = True
                        st.rerun()
                
                # 스트리머 추가 폼 표시
                if st.session_state.get('show_add_form', False):
                    self.show_add_streamer_form()
                return
            
            st.markdown('<div class="section-header">등록된 스트리머</div>', unsafe_allow_html=True)
            
            # 스트리머 카드들
            for name, data in streamers.items():
                with st.container():
                    self.create_streamer_card_optimized(name, data)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            
            # 새 스트리머 추가 버튼 (최하단)
            st.markdown("---")
            _, col2, _ = st.columns([2, 1, 2])
            with col2:
                if st.button("➕ 새 스트리머 추가", type="primary", use_container_width=True):
                    st.session_state.show_add_form = True
                    st.rerun()
            
            # 스트리머 추가 폼 표시
            if st.session_state.get('show_add_form', False):
                self.show_add_streamer_form()
                    
        except Exception as e:
            logger.error(f"스트리머 관리 페이지 오류: {e}")
            st.error("스트리머 관리 페이지를 불러올 수 없습니다.")
    
    def show_notification_history(self):
        """알림 기록 페이지"""
        try:
            # 필터 초기화
            if 'notification_filter' not in st.session_state:
                st.session_state.notification_filter = "all"
            
            # 필터 버튼들
            filter_options = {
                "all": ("전체", "🔍"),
                "live": ("방송", "📺"),
                "cafe": ("카페", "💬"),
                "twitter": ("트위터", "🐦")
            }
            
            col1, col2, col3, col4 = st.columns(4)
            cols = [col1, col2, col3, col4]
            
            for i, (filter_key, (label, icon)) in enumerate(filter_options.items()):
                with cols[i]:
                    button_type = "primary" if st.session_state.notification_filter == filter_key else "secondary"
                    if st.button(f"{icon} {label}", key=f"filter_{filter_key}", use_container_width=True, type=button_type):
                        st.session_state.notification_filter = filter_key
                        st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("---")
            
            # 알림 목록 표시
            notifications = config.get_notifications()
            filtered_notifications = self.apply_notification_filter(notifications, st.session_state.notification_filter)
            
            if not filtered_notifications:
                st.markdown("""
                <div class="empty-state">
                    <h3>📭 표시할 알림이 없습니다</h3>
                    <p>선택한 필터에 해당하는 알림이 없습니다.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 빈 상태에서도 전체 알림이 있으면 삭제 버튼 표시
                all_notifications = config.get_notifications()
                if all_notifications:
                    st.markdown("---")
                    col1, col2, col3 = st.columns([2, 1, 2])
                    with col2:
                        if st.button("🗑️ 모든 알림 삭제", type="secondary", use_container_width=True, key="empty_delete_btn"):
                            self.clear_all_notifications()
                return
            
            # 알림 통계
            st.markdown(f"📊 총 {len(filtered_notifications)}개의 알림 (최근 50개 표시)")
            
            # 최근 50개 알림만 표시
            for notification in filtered_notifications[:50]:
                self.create_notification_item_optimized(notification)
            
            # 모든 알림 삭제 버튼 (최하단)
            if filtered_notifications:  # 알림이 있을 때만 표시
                st.markdown("---")
                col1, col2, col3 = st.columns([2, 1, 2])
                with col2:
                    if st.button("🗑️ 모든 알림 삭제", type="secondary", use_container_width=True):
                        self.clear_all_notifications()
                
        except Exception as e:
            logger.error(f"알림 기록 페이지 오류: {e}")
            st.error("알림 기록을 불러올 수 없습니다.")
    
    def apply_notification_filter(self, notifications, filter_type: str):
        """알림 필터링"""
        if filter_type == "all":
            return sorted(notifications, key=lambda x: x.get('timestamp', ''), reverse=True)
        else:
            filtered = [n for n in notifications if n.get('type') == filter_type]
            return sorted(filtered, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def create_notification_item_optimized(self, notification: dict):
        """최적화된 알림 아이템 생성 - 백업 파일 방식 적용"""
        import html
        from datetime import datetime
        
        # 타입별 설정 (라이브: 붉은색, 트위터: 푸른색 구분)
        type_config = {
            'live': {'icon': '📺', 'color': '#ef4444', 'class': 'notification-live'},
            'cafe': {'icon': '💬', 'color': '#10b981', 'class': 'notification-cafe'},
            'twitter': {'icon': '🐦', 'color': '#06b6d4', 'class': 'notification-twitter'}
        }
        
        # 안전한 데이터 추출 및 이스케이프 처리
        noti_type = notification.get('type', '')
        title = html.escape(str(notification.get('title', ''))) if notification.get('title') else '제목 없음'
        content = html.escape(str(notification.get('content', ''))) if notification.get('content') else '내용 없음'
        url = notification.get('url', '')
        streamer_name = html.escape(str(notification.get('streamer_name', ''))) if notification.get('streamer_name') else ''
        
        config_data = type_config.get(noti_type, {'icon': '📢', 'color': '#6366f1', 'class': 'notification-default'})
        
        # 시간 포맷팅
        try:
            timestamp = notification.get('timestamp', '')
            if 'T' in str(timestamp):
                timestamp_clean = str(timestamp)[:19].replace('T', ' ')
                time_obj = datetime.strptime(timestamp_clean, '%Y-%m-%d %H:%M:%S')
                time_str = time_obj.strftime('%m/%d %H:%M')
            else:
                time_str = "시간 정보 없음"
        except:
            time_str = "시간 정보 없음"
        
        # URL 검증 및 안전 처리
        safe_url = '#'
        if url and isinstance(url, str):
            url = url.strip()
            if url.startswith(('http://', 'https://')):
                if not url.lower().startswith(('javascript:', 'data:', 'vbscript:')):
                    safe_url = html.escape(url)
        
        # 내용 길이 제한 및 안전 처리
        content_preview = content[:150] + ('...' if len(content) > 150 else '') if content != '내용 없음' else content
        
        # 프로필 이미지 처리
        profile_image_html = ''
        if streamer_name:
            # 스트리머 데이터에서 프로필 이미지 찾기
            streamers = config.get_streamers()
            streamer_data = streamers.get(streamer_name, {})
            profile_url = streamer_data.get('profile_image')
            
            if profile_url:
                # 프로필 이미지가 있는 경우 Base64 변환하여 HTML에 삽입
                base64_data = self.url_to_base64_sync(profile_url)
                if base64_data:
                    profile_image_html = f'<img src="data:image/jpeg;base64,{base64_data}" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; object-fit: cover; border: 2px solid {config_data["color"]};">'
                else:
                    # Base64 변환 실패 시 기본 아바타
                    profile_image_html = f'<div style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; background: linear-gradient(135deg, {config_data["color"]}, {config_data["color"]}88); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: white; border: 2px solid {config_data["color"]};">👤</div>'
            else:
                # 기본 아바타
                profile_image_html = f'<div style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; background: linear-gradient(135deg, {config_data["color"]}, {config_data["color"]}88); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: white; border: 2px solid {config_data["color"]};">👤</div>'
        
        # 기존 HTML 카드 형태로 복원 (클릭 가능, 왼쪽 색깔 줄 포함)
        card_html = f'<div style="margin-bottom: 12px;"><a href="{safe_url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;"><div style="display: flex; align-items: flex-start; gap: 12px; width: 100%; border: 1px solid #e1e5e9; border-radius: 12px; padding: 16px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: all 0.2s ease; cursor: pointer; border-left: 4px solid {config_data["color"]};" onmouseover="this.style.boxShadow=\'0 4px 16px rgba(0,0,0,0.15)\'; this.style.transform=\'translateY(-2px)\';" onmouseout="this.style.boxShadow=\'0 2px 8px rgba(0,0,0,0.1)\'; this.style.transform=\'translateY(0)\';" ><div style="display: flex; align-items: center; margin-bottom: 8px;">{profile_image_html}<div style="font-size: 1.8rem; margin-right: 8px;">{config_data["icon"]}</div></div><div style="flex: 1; min-width: 0;"><div style="margin: 0 0 8px 0; color: #2c3e50; font-size: 1.1rem; font-weight: 600; line-height: 1.3;">{title}</div><div style="margin: 0 0 12px 0; color: #666; line-height: 1.4; font-size: 0.95rem;">{content_preview}</div><div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;"><small style="color: #999; font-size: 0.85rem;">⏰ {time_str}</small><div style="display: flex; align-items: center; gap: 8px;">{f"<span style=\"color: #999; font-size: 0.85rem;\">👤 {streamer_name}</span>" if streamer_name else ""}<span style="background: {config_data["color"]}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">{noti_type.upper() if noti_type else "UNKNOWN"}</span></div></div></div></div></a></div>'
        
        # HTML 마크다운으로 렌더링
        st.markdown(card_html, unsafe_allow_html=True)
    
    def clear_all_notifications(self):
        """모든 알림 삭제"""
        if st.session_state.get('confirm_clear_notifications', False):
            config.save_notifications([])
            st.success("🗑️ 모든 알림이 삭제되었습니다.")
            st.session_state.confirm_clear_notifications = False
            st.rerun()
        else:
            st.session_state.confirm_clear_notifications = True
            st.warning("⚠️ 모든 알림을 정말 삭제하시겠습니까? 삭제 버튼을 다시 클릭하세요.")
            st.rerun()
    
    def show_settings(self):
        """설정 페이지"""
        try:
            settings = config.get_settings()
            
            # 설정 섹션들
            tab1, tab2, tab3 = st.tabs(["⚙️ 일반 설정", "🔔 알림 설정", "🔐 계정 관리"])
            
            with tab1:
                st.markdown("#### 📊 모니터링 설정")
                
                col1, col2 = st.columns(2)
                with col1:
                    check_interval = st.slider(
                        "체크 간격 (초)",
                        min_value=10,
                        max_value=300,
                        value=settings.get('check_interval', 30),
                        step=5,
                        help="스트리머 상태를 확인하는 간격을 설정합니다."
                    )
                
                with col2:
                    st.markdown("#### 📱 시스템 설정")
                    start_with_windows = st.checkbox(
                        "윈도우 시작 시 자동 실행",
                        value=settings.get('start_with_windows', True)
                    )
                    minimize_to_tray = st.checkbox(
                        "창 닫기 시 트레이로 최소화",
                        value=settings.get('minimize_to_tray', True)
                    )
            
            with tab2:
                st.markdown("#### 🔔 알림 설정")
                
                col1, col2 = st.columns(2)
                with col1:
                    show_notifications = st.checkbox(
                        "데스크톱 알림 표시",
                        value=settings.get('show_notifications', True),
                        help="새로운 방송이나 게시글이 올라올 때 알림을 표시합니다."
                    )
                
                with col2:
                    # 알림 테스트 버튼
                    if st.button("🔔 알림 테스트", use_container_width=True):
                        self.test_notification()
                
                # 누락 알림 복구 버튼
                st.markdown("#### 📢 누락 알림 복구")
                col3, col4 = st.columns(2)
                with col3:
                    st.info("앱이 꺼져있던 동안 놓친 카페글이나 트위터글의 알림을 복구합니다.")
                with col4:
                    if st.button("🔄 누락 알림 복구", use_container_width=True, type="secondary"):
                        self.recover_missed_notifications()
            
            with tab3:
                # 시스템 정보
                st.markdown("#### 📋 시스템 정보")
                
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    streamers = config.get_streamers()
                    notifications = config.get_notifications()
                    st.write(f"**등록된 스트리머**: {len(streamers)}명")
                    st.write(f"**알림 기록**: {len(notifications)}개")
                
                with info_col2:
                    st.write(f"**설정 파일**: `data/settings.json`")
                    st.write(f"**로그 디렉토리**: `logs/`")
                    
                    # 캐시 정리 버튼
                    if st.button("🧹 캐시 정리"):
                        st.info("브라우저 캐시를 정리합니다...")
            
            # 설정 저장
            st.markdown("---")
            _, col2, _ = st.columns([2, 1, 2])
            with col2:
                if st.button("💾 설정 저장", use_container_width=True, type="primary"):
                    self.save_settings_with_realtime_update(
                        check_interval, show_notifications, 
                        start_with_windows, minimize_to_tray
                    )
                    
        except Exception as e:
            logger.error(f"설정 페이지 오류: {e}")
            st.error("설정 페이지를 불러올 수 없습니다.")
    
    def setup_auto_refresh(self):
        """자동 새로고침 설정"""
        if st.session_state.get('auto_refresh', False):
            st.rerun()
    
    def get_live_count_cached(self):
        """캐시된 라이브 카운트 반환"""
        try:
            # 라이브 상태 파일에서 데이터 읽기
            import os
            import json
            live_status_file = os.path.join(config.data_dir, "live_status.json")
            
            if os.path.exists(live_status_file):
                with open(live_status_file, 'r', encoding='utf-8') as f:
                    live_data = json.load(f)
                    return len([name for name, data in live_data.items() if data.get('is_live', False)])
            return 0
        except Exception as e:
            logger.warning(f"라이브 카운트 조회 실패: {e}")
            return 0
    
    def create_streamer_card_optimized(self, name: str, data: dict):
        """최적화된 스트리머 카드 생성"""
        with st.container():
            # 개별 알림 설정 상태 확인 (먼저 정의)
            notifications = data.get('notifications', {})
            chzzk_enabled = notifications.get('chzzk', True)
            twitter_enabled = notifications.get('twitter', True)
            cafe_enabled = notifications.get('cafe', True)
            
            # 플랫폼 배지들 (알림 상태 반영)
            platforms = []
            if data.get('chzzk_id'):
                chzzk_class = 'platform-badge platform-chzzk' + ('' if chzzk_enabled else ' disabled')
                platforms.append(f'<span class="{chzzk_class}">📺 치지직</span>')
            if data.get('twitter_username'):
                twitter_class = 'platform-badge platform-twitter' + ('' if twitter_enabled else ' disabled')
                platforms.append(f'<span class="{twitter_class}">🐦 트위터</span>')
            if data.get('cafe_user_id'):
                cafe_class = 'platform-badge platform-cafe' + ('' if cafe_enabled else ' disabled')
                platforms.append(f'<span class="{cafe_class}">💬 카페</span>')
            
            # 상태 배지
            status_class = "status-active" if data.get('enabled', True) else "status-inactive"
            status_text = "활성" if data.get('enabled', True) else "비활성"
            
            # 라이브 상태 확인
            is_live = self.check_streamer_live_status_sync(name)
            live_class = "live-on" if is_live else "live-off"
            live_text = "🔴 라이브" if is_live else "⚫ 오프라인"
            
            # 프로필 이미지 처리
            profile_url = data.get('profile_image')
            profile_content = ''
            
            if profile_url:
                # 프로필 이미지가 있는 경우 Base64 변환하여 HTML에 삽입
                base64_data = self.url_to_base64_sync(profile_url)
                if base64_data:
                    profile_content = f'<img src="data:image/jpeg;base64,{base64_data}" style="width: 64px; height: 64px; border-radius: 16px; object-fit: cover; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);">'
                else:
                    # Base64 변환 실패 시 기본 아바타
                    profile_content = '<div style="width: 64px; height: 64px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; color: white; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); flex-shrink: 0;">👤</div>'
            else:
                # 기본 아바타
                profile_content = '<div style="width: 64px; height: 64px; background: linear-gradient(135deg, #667eea, #764ba2); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; color: white; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); flex-shrink: 0;">👤</div>'
            
            # 알림 상태는 이제 플랫폼 배지 색상으로 표현됨
            
            # 기존 HTML 카드 형태로 복원 (알림 상태 포함)
            card_html = f"""
            <div class="streamer-card">
                <div class="streamer-info">
                    {profile_content}
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #2c3e50; font-size: 1.3rem; font-weight: 600;">{name}</h3>
                        <div style="margin-bottom: 0.8rem;">
                            {"".join(platforms) if platforms else '<span style="color: #999; font-size: 0.9rem;">플랫폼 미설정</span>'}
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                            <span class="status-badge {status_class}">{status_text}</span>
                            <span class="live-badge {live_class}">{live_text}</span>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            # 액션 버튼들
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ 편집", key=f"edit_{name}", use_container_width=True):
                    st.session_state[f'edit_mode_{name}'] = True
                    st.rerun()
            with col2:
                if st.button("🗑️ 삭제", key=f"delete_{name}", use_container_width=True):
                    self.confirm_delete_streamer(name)
            with col3:
                if st.button("🔄 새로고침", key=f"refresh_{name}", use_container_width=True):
                    self.refresh_streamer_data(name)
            
            # 편집 모드
            if st.session_state.get(f'edit_mode_{name}', False):
                self.show_inline_edit_form(name, data)
    
    def check_streamer_live_status_sync(self, name: str):
        """스트리머 라이브 상태 동기적 확인 (캐시 기반)"""
        try:
            # 세션 캐시에서 라이브 상태 확인
            if name in st.session_state.streamer_data_cache:
                return st.session_state.streamer_data_cache[name].get('is_live', False)
            
            # 캐시에 데이터가 없으면 파일에서 직접 읽기 (폴백)
            import os
            import json
            live_status_file = os.path.join(config.data_dir, "live_status.json")
            
            if os.path.exists(live_status_file):
                with open(live_status_file, 'r', encoding='utf-8') as f:
                    live_data = json.load(f)
                    return live_data.get(name, {}).get('is_live', False)
            return False
        except Exception as e:
            logger.warning(f"{name} 라이브 상태 확인 실패: {e}")
            return False
    
    def show_add_streamer_form(self):
        """스트리머 추가 폼"""
        with st.container():
            st.markdown("### ➕ 새 스트리머 추가")
            
            with st.form("add_streamer_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("🎭 스트리머 이름 *", placeholder="예: 아리사")
                    chzzk_id = st.text_input("📺 치지직 ID", placeholder="예: abc123def456")
                
                with col2:
                    twitter_username = st.text_input("🐦 트위터 사용자명", placeholder="예: username")
                    cafe_user_id = st.text_input("💬 네이버 카페 사용자 ID", placeholder="예: user123")
                    cafe_club_id = st.text_input("🏢 카페 클럽 ID", placeholder="예: 30919539")
                
                enabled = st.checkbox("✅ 활성화", value=True)
                
                # 개별 알림 설정
                st.markdown("**🔔 알림 설정**")
                notif_col1, notif_col2, notif_col3 = st.columns(3)
                
                with notif_col1:
                    chzzk_notifications = st.checkbox("📺 스트리밍 알림", value=True, key="add_chzzk_notif")
                with notif_col2:
                    twitter_notifications = st.checkbox("🐦 트위터 알림", value=True, key="add_twitter_notif")
                with notif_col3:
                    cafe_notifications = st.checkbox("💬 카페 알림", value=True, key="add_cafe_notif")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✨ 추가", type="primary", use_container_width=True):
                        if name.strip():
                            streamers = config.get_streamers()
                            if name in streamers:
                                st.error(f"❌ '{name}' 스트리머가 이미 존재합니다!")
                            else:
                                # 프로필 이미지 URL 가져오기
                                profile_image_url = None
                                if chzzk_id.strip():
                                    with st.spinner("🔄 프로필 이미지를 가져오는 중..."):
                                        profile_image_url = self.get_chzzk_profile_image_sync(chzzk_id.strip())
                                
                                streamers[name] = {
                                    'chzzk_id': chzzk_id.strip(),
                                    'twitter_username': twitter_username.strip(),
                                    'cafe_user_id': cafe_user_id.strip(),
                                    'cafe_club_id': cafe_club_id.strip(),
                                    'enabled': enabled,
                                    'profile_image': profile_image_url,
                                    'notifications': {
                                        'chzzk': chzzk_notifications,
                                        'twitter': twitter_notifications,
                                        'cafe': cafe_notifications
                                    }
                                }
                                config.save_streamers(streamers)
                                
                                if profile_image_url:
                                    st.success(f"🎉 스트리머 '{name}'가 추가되었습니다! (프로필 이미지 포함)")
                                else:
                                    st.success(f"🎉 스트리머 '{name}'가 추가되었습니다!")
                                    if chzzk_id.strip():
                                        st.info("💡 프로필 이미지는 백그라운드에서 자동으로 업데이트됩니다.")
                                
                                st.session_state.show_add_form = False
                                st.rerun()
                        else:
                            st.error("❌ 스트리머 이름을 입력해주세요.")
                
                with col2:
                    if st.form_submit_button("❌ 취소", use_container_width=True):
                        st.session_state.show_add_form = False
                        st.rerun()
    
    def show_inline_edit_form(self, name: str, data: dict):
        """인라인 편집 폼"""
        with st.container():
            st.markdown(f"### ✏️ {name} 편집")
            
            with st.form(f"edit_form_{name}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_name = st.text_input("스트리머 이름", value=name)
                    chzzk_id = st.text_input("치지직 ID", value=data.get('chzzk_id', ''))
                
                with col2:
                    twitter_username = st.text_input("트위터 사용자명", value=data.get('twitter_username', ''))
                    cafe_user_id = st.text_input("카페 사용자 ID", value=data.get('cafe_user_id', ''))
                    cafe_club_id = st.text_input("카페 클럽 ID", value=data.get('cafe_club_id', ''))
                
                enabled = st.checkbox("활성화", value=data.get('enabled', True))
                
                # 개별 알림 설정
                st.markdown("---")
                st.markdown("**🔔 알림 세부 설정**")
                st.caption("플랫폼별 알림을 개별적으로 켜고 끌 수 있습니다.")
                
                current_notifications = data.get('notifications', {'chzzk': True, 'twitter': True, 'cafe': True})
                
                notif_col1, notif_col2, notif_col3 = st.columns(3)
                
                with notif_col1:
                    if data.get('chzzk_id'):
                        edit_chzzk_notifications = st.checkbox("📺 스트리밍 알림", value=current_notifications.get('chzzk', True), key=f"edit_chzzk_notif_{name}")
                    else:
                        edit_chzzk_notifications = False
                        st.caption("📺 CHZZK ID 없음")
                        
                with notif_col2:
                    if data.get('twitter_username'):
                        edit_twitter_notifications = st.checkbox("🐦 트위터 알림", value=current_notifications.get('twitter', True), key=f"edit_twitter_notif_{name}")
                    else:
                        edit_twitter_notifications = False
                        st.caption("🐦 트위터 ID 없음")
                        
                with notif_col3:
                    if data.get('cafe_user_id'):
                        edit_cafe_notifications = st.checkbox("💬 카페 알림", value=current_notifications.get('cafe', True), key=f"edit_cafe_notif_{name}")
                    else:
                        edit_cafe_notifications = False
                        st.caption("💬 카페 ID 없음")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 저장", type="primary", use_container_width=True):
                        streamers = config.get_streamers()
                        
                        # 이름이 변경된 경우
                        if new_name != name and new_name in streamers:
                            st.error(f"❌ '{new_name}' 이름이 이미 존재합니다!")
                        else:
                            # 기존 항목 삭제 (이름 변경 시)
                            if new_name != name:
                                del streamers[name]
                            
                            # 프로필 이미지 업데이트 확인
                            current_profile = data.get('profile_image')
                            updated_profile = current_profile
                            
                            # CHZZK ID가 변경되었거나 기존 프로필이 없을 경우 새로 가져오기
                            if chzzk_id.strip() and (chzzk_id.strip() != data.get('chzzk_id') or not current_profile):
                                with st.spinner("🔄 프로필 이미지 업데이트 중..."):
                                    new_profile = self.get_chzzk_profile_image_sync(chzzk_id.strip())
                                    if new_profile:
                                        updated_profile = new_profile
                            
                            # 새 데이터 저장
                            streamers[new_name] = {
                                'chzzk_id': chzzk_id.strip(),
                                'twitter_username': twitter_username.strip(),
                                'cafe_user_id': cafe_user_id.strip(),
                                'cafe_club_id': cafe_club_id.strip(),
                                'enabled': enabled,
                                'profile_image': updated_profile,
                                'notifications': {
                                    'chzzk': edit_chzzk_notifications,
                                    'twitter': edit_twitter_notifications,
                                    'cafe': edit_cafe_notifications
                                }
                            }
                            
                            config.save_streamers(streamers)
                            
                            if updated_profile != current_profile and updated_profile:
                                st.success(f"✅ {new_name} 정보가 저장되었습니다! (프로필 이미지 업데이트 포함)")
                            else:
                                st.success(f"✅ {new_name} 정보가 저장되었습니다!")
                            
                            st.session_state[f'edit_mode_{name}'] = False
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("❌ 취소", use_container_width=True):
                        st.session_state[f'edit_mode_{name}'] = False
                        st.rerun()
    
    def confirm_delete_streamer(self, name: str):
        """스트리머 삭제 확인"""
        if st.session_state.get(f'confirm_delete_{name}', False):
            streamers = config.get_streamers()
            if name in streamers:
                del streamers[name]
                config.save_streamers(streamers)
                st.success(f"🗑️ {name} 스트리머가 삭제되었습니다.")
                st.session_state[f'confirm_delete_{name}'] = False
                st.rerun()
        else:
            st.session_state[f'confirm_delete_{name}'] = True
            st.warning(f"⚠️ '{name}' 스트리머를 정말 삭제하시겠습니까? 삭제 버튼을 다시 클릭하세요.")
            st.rerun()
    
    def refresh_streamer_data(self, name: str):
        """스트리머 데이터 새로고침 (완료 후 메시지 자동 제거)"""
        import time
        
        try:
            # 새로고침 시작 메시지 표시
            refresh_placeholder = st.empty()
            refresh_placeholder.info(f"🔄 {name} 스트리머 데이터를 새로고침합니다...")
            
            # 실제 새로고침 로직 (시뮬레이션)
            time.sleep(1)  # 시뮬레이션용 대기
            
            # 라이브 상태 업데이트
            self.try_update_live_status_background()
            
            # 프로필 이미지 업데이트는 백그라운드에서 자동 처리됨
            
            # 성공 메시지 표시
            refresh_placeholder.success(f"✅ {name} 데이터가 새로고침되었습니다!")
            
            # 2초 후 메시지 제거
            time.sleep(2)
            refresh_placeholder.empty()
            
        except Exception as e:
            logger.error(f"스트리머 데이터 새로고침 실패 ({name}): {e}")
            refresh_placeholder.error("새로고침 중 오류가 발생했습니다.")
            time.sleep(3)
            refresh_placeholder.empty()
    
    def test_notification(self):
        """알림 테스트 기능 - 강화된 중복 방지 및 안정성 개선"""
        
        # 현재 시간 기반 중복 방지 (더 안정적)
        current_time = time.time()
        last_test_time = getattr(st.session_state, 'last_notification_test_time', 0)
        
        # 3초 내 중복 요청 방지
        if current_time - last_test_time < 3:
            st.warning("⚠️ 너무 빠른 연속 요청입니다. 3초 후 다시 시도해주세요.")
            return
        
        # 세션 상태 체크 및 강제 리셋 (안전장치)
        if getattr(st.session_state, 'notification_test_in_progress', False):
            # 마지막 테스트로부터 30초 이상 지났으면 강제 리셋
            if current_time - last_test_time > 30:
                logger.warning("알림 테스트 세션 상태 강제 리셋 (30초 초과)")
                st.session_state.notification_test_in_progress = False
            else:
                st.warning("⚠️ 알림 테스트가 진행 중입니다. 잠시 후 다시 시도해주세요.")
                return
        
        # 진행 상태 플래그 및 시간 설정
        st.session_state.notification_test_in_progress = True
        st.session_state.last_notification_test_time = current_time
        
        try:
            # 테스트 알림 요청을 메인 프로세스에 전송
            notification_test_file = os.path.join(config.data_dir, "notification_test.json")
            
            # 모든 기존 알림 테스트 파일 강제 정리 (큐 누적 방지)
            for attempt in range(3):  # 최대 3회 시도
                try:
                    if os.path.exists(notification_test_file):
                        os.remove(notification_test_file)
                    time.sleep(0.1)  # 파일 시스템 동기화 대기
                    break
                except Exception as e:
                    if attempt == 2:  # 마지막 시도
                        logger.warning(f"기존 알림 테스트 파일 삭제 실패: {e}")
                    time.sleep(0.2)
            
            # 고유한 테스트 ID 생성 (중복 방지)
            test_id = f"test_{int(time.time() * 1000)}"
            
            test_request = {
                "action": "test_notification",
                "test_id": test_id,
                "timestamp": datetime.now().isoformat(),
                "title": "🔔 스트리머 알림 테스트",
                "message": "알림이 정상적으로 작동합니다! 🎉",
                "url": "https://github.com/anthropics/claude-code",
                "status": "requested"
            }
            
            # 안전한 파일 쓰기 (Windows 호환)
            try:
                self._safe_write_json(notification_test_file, test_request)
                logger.info(f"알림 테스트 요청 파일 생성 성공 (ID: {test_id})")
            except Exception as e:
                logger.error(f"알림 테스트 요청 파일 생성 실패 (ID: {test_id}): {e}")
                st.error(f"❌ 알림 테스트 파일 생성 실패: {str(e)}")
                return
            
            # 즉시 피드백
            st.info("📤 알림 테스트 요청을 전송했습니다...")
            logger.info(f"알림 테스트 요청이 메인 프로세스에 전송됨 (ID: {test_id})")
            
            # 진행률 표시기 추가
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 응답 시간 증가 (최대 12초) - 알림 전송 안정성 개선
            max_wait_time = 12
            check_interval = 0.2
            checks_done = 0
            max_checks = int(max_wait_time / check_interval)
            
            for i in range(max_checks):
                time.sleep(check_interval)
                checks_done += 1
                progress = checks_done / max_checks
                progress_bar.progress(progress)
                
                # 상태별 메시지 업데이트 (타이밍 조정)
                if i < 5:  # 처음 1초
                    status_text.text("🔄 메인 프로세스로 요청 전달 중...")
                elif i < 15:  # 1-3초
                    status_text.text("⚙️ 알림 시스템 준비 중...")
                elif i < 35:  # 3-7초
                    status_text.text("📱 데스크톱 알림 발송 중...")
                else:  # 7초 이후
                    status_text.text("⏳ 알림 전송 완료 확인 중...")
                
                # 파일 상태 확인
                try:
                    if os.path.exists(notification_test_file):
                        with open(notification_test_file, 'r', encoding='utf-8') as f:
                            result = json.load(f)
                        
                        # 테스트 ID 일치 확인 (다른 요청의 결과가 아님을 보장)
                        if result.get('test_id') == test_id:
                            if result.get('status') == 'completed':
                                progress_bar.progress(1.0)
                                status_text.empty()
                                
                                # 성공 메시지 개선 (알림 클릭과 무관함을 명시)
                                success_msg = result.get('success_message', '데스크톱 알림이 성공적으로 발송되었습니다.')
                                st.success(f"✅ 알림 테스트 완료! {success_msg}")
                                st.info("💡 데스크톱 알림을 확인하세요. 알림을 클릭하지 않아도 테스트는 성공적으로 완료되었습니다.")
                                
                                try:
                                    os.remove(notification_test_file)
                                except:
                                    pass
                                # 성공 시 즉시 세션 상태 정리
                                st.session_state.notification_test_in_progress = False
                                st.session_state.last_notification_test_time = time.time()
                                logger.debug("알림 테스트 성공 - 세션 상태 즉시 정리")
                                return
                            elif result.get('status') == 'failed':
                                progress_bar.progress(1.0)
                                status_text.empty()
                                error_msg = result.get('error', '알 수 없는 오류')
                                st.warning(f"⚠️ 알림 테스트 실패: {error_msg}")
                                st.info("💡 메인 시스템의 알림 설정을 확인해주세요.")
                                try:
                                    os.remove(notification_test_file)
                                except:
                                    pass
                                # 실패 시에도 세션 상태 정리
                                st.session_state.notification_test_in_progress = False
                                st.session_state.last_notification_test_time = time.time()
                                logger.debug("알림 테스트 실패 - 세션 상태 즉시 정리")
                                return
                    else:
                        # 파일이 삭제되었다면 처리 완료로 간주 (6초 이후부터 확인)
                        if i > 30:  # 30 * 0.2초 = 6초 후부터
                            progress_bar.progress(1.0)
                            status_text.empty()
                            st.success("✅ 알림 테스트가 처리되었습니다! 데스크톱에서 알림을 확인하세요.")
                            st.info("💡 알림이 정상적으로 전송되었습니다. 알림을 클릭하지 않아도 테스트는 성공입니다.")
                            # 파일 삭제된 경우에도 세션 상태 정리
                            st.session_state.notification_test_in_progress = False
                            st.session_state.last_notification_test_time = time.time()
                            logger.debug("알림 테스트 파일 삭제 확인 - 세션 상태 즉시 정리")
                            return
                except:
                    continue
            
            # 타임아웃 처리 - 더 친화적인 메시지
            progress_bar.progress(1.0)
            status_text.empty()
            st.warning("⏰ 알림 테스트 완료 확인 지연")
            st.info("💡 알림이 전송되었을 가능성이 높습니다. 데스크톱 알림을 확인해보세요.")
            st.info("🔧 지속적으로 문제가 발생하면 메인 시스템이 실행 중인지 확인해주세요.")
            
            # 정리
            try:
                if os.path.exists(notification_test_file):
                    os.remove(notification_test_file)
            except:
                pass
                
        except Exception as e:
            st.error(f"❌ 알림 테스트 요청 실패: {str(e)}")
            logger.error(f"알림 테스트 요청 중 오류: {e}")
            
            # 폴백: 간단한 브라우저 알림
            st.info("💡 대신 간단한 테스트를 위해 GitHub 페이지를 열겠습니다.")
            webbrowser.open("https://github.com/anthropics/claude-code")
        
        finally:
            # 항상 진행 상태 플래그 해제 (강화된 정리)
            try:
                st.session_state.notification_test_in_progress = False
                st.session_state.last_notification_test_time = time.time()
                logger.debug("알림 테스트 세션 상태 정리 완료")
            except Exception as cleanup_error:
                logger.warning(f"세션 상태 정리 중 오류: {cleanup_error}")
                # 강제 리셋
                try:
                    if hasattr(st.session_state, 'notification_test_in_progress'):
                        del st.session_state.notification_test_in_progress
                except:
                    pass
    
    def recover_missed_notifications(self):
        """누락된 알림 복구 (UI에서 수동 실행)"""
        try:
            # 복구 요청 파일 생성
            recovery_request_file = os.path.join(config.data_dir, "missed_recovery_request.json")
            
            # 중복 요청 방지
            if os.path.exists(recovery_request_file):
                st.warning("⚠️ 누락 알림 복구가 이미 진행 중입니다.")
                return
            
            # 요청 파일 생성
            request_data = {
                "action": "recover_missed_notifications",
                "timestamp": datetime.now().isoformat(),
                "source": "ui_manual",
                "status": "requested"
            }
            
            with open(recovery_request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)
            
            st.success("✅ 누락 알림 복구를 시작했습니다. 백그라운드에서 처리 중이며 완료되면 알림으로 안내됩니다.")
            logger.info("UI에서 누락 알림 복구 요청됨")
            
            # 3초 후 자동으로 페이지 새로고침
            time.sleep(3)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 누락 알림 복구 요청 중 오류: {str(e)}")
            logger.error(f"UI 누락 알림 복구 요청 실패: {e}")
    
    def save_settings_with_realtime_update(self, check_interval, show_notifications, start_with_windows, minimize_to_tray):
        """실시간 설정 저장"""
        try:
            new_settings = {
                'check_interval': check_interval,
                'show_notifications': show_notifications,
                'start_with_windows': start_with_windows,
                'minimize_to_tray': minimize_to_tray
            }
            
            # 기존 설정과 병합
            current_settings = config.get_settings()
            current_settings.update(new_settings)
            
            config.save_settings(current_settings)
            st.success("✅ 설정이 저장되었습니다!")
            
            # 실시간 업데이트 알림
            if check_interval != current_settings.get('check_interval', 30):
                st.info("ℹ️ 체크 간격 변경사항은 다음 체크 주기부터 적용됩니다.")
                
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            st.error("설정 저장 중 오류가 발생했습니다.")
    
    def _safe_write_json(self, file_path: str, data: dict):
        """Windows에서 안전한 JSON 파일 쓰기"""
        import uuid
        import shutil
        
        # 고유한 임시 파일명 생성
        temp_file = f"{file_path}.{uuid.uuid4().hex[:8]}.tmp"
        
        try:
            # 기존 파일이 있으면 강제 삭제
            for attempt in range(5):  # 최대 5회 시도
                try:
                    if os.path.exists(file_path):
                        os.chmod(file_path, 0o777)  # 권한 변경
                        os.remove(file_path)
                    break
                except (PermissionError, OSError) as e:
                    if attempt == 4:  # 마지막 시도
                        logger.warning(f"기존 파일 삭제 실패: {e}")
                    time.sleep(0.1 * (attempt + 1))  # 점진적 대기
            
            # 임시 파일에 데이터 쓰기
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 원본 파일로 복사 (rename 대신 copy 사용)
            shutil.copy2(temp_file, file_path)
            
            logger.debug(f"안전한 파일 쓰기 완료: {file_path}")
            
        except Exception as e:
            logger.error(f"안전한 파일 쓰기 실패 ({file_path}): {e}")
            # 직접 쓰기 시도 (폴백)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.debug(f"직접 파일 쓰기 완료: {file_path}")
            except Exception as e2:
                logger.error(f"직접 파일 쓰기도 실패 ({file_path}): {e2}")
                raise e2
        finally:
            # 임시 파일 정리
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
    
    def get_chzzk_profile_image_sync(self, chzzk_id: str) -> Optional[str]:
        """치지직 프로필 이미지 URL 가져오기 (동기적 버전)"""
        try:
            import httpx
            
            # 비동기 버전을 동기적으로 실행
            return asyncio.run(self._get_chzzk_profile_image_async(chzzk_id))
        except Exception as e:
            logger.warning(f"CHZZK 프로필 이미지 가져오기 실패 ({chzzk_id}): {e}")
            return None
    
    async def _get_chzzk_profile_image_async(self, chzzk_id: str) -> Optional[str]:
        """치지직 프로필 이미지 URL 가져오기 (비동기 버전)"""
        try:
            import httpx
            
            # CHZZK 채널 정보 API 호출
            url = f"https://api.chzzk.naver.com/service/v1/channels/{chzzk_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('content', {})
                    
                    # 프로필 이미지 URL 추출
                    profile_image_url = content.get('channelImageUrl')
                    if profile_image_url:
                        logger.debug(f"CHZZK 프로필 이미지 URL 획득: {profile_image_url}")
                        return profile_image_url
                    else:
                        logger.debug(f"CHZZK 채널 {chzzk_id}에 프로필 이미지가 없습니다.")
                else:
                    logger.warning(f"CHZZK API 응답 오류: {response.status_code}")
                    
        except Exception as e:
            logger.warning(f"CHZZK 프로필 이미지 API 호출 실패 ({chzzk_id}): {e}")
        
        return None
    
    # update_notification_setting 함수 제거 - 이제 편집 모드에서만 관리
    
    def migrate_notification_settings(self):
        """기존 스트리머들에 알림 설정 추가 (마이그레이션)"""
        try:
            streamers = config.get_streamers()
            updated = False
            
            for name, data in streamers.items():
                if 'notifications' not in data:
                    # 기본값으로 모든 알림 활성화
                    data['notifications'] = {
                        'chzzk': True,
                        'twitter': True,
                        'cafe': True
                    }
                    updated = True
                    logger.debug(f"{name} 스트리머에 알림 설정 추가")
            
            if updated:
                config.save_streamers(streamers)
                logger.info("스트리머 알림 설정 마이그레이션 완료")
                
        except Exception as e:
            logger.error(f"알림 설정 마이그레이션 실패: {e}")

def run_streamlit_app():
    """Streamlit 앱 실행 함수 (하위 호환성)"""
    main()

def main():
    """메인 함수"""
    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        st.error(f"❌ 애플리케이션 실행 중 오류가 발생했습니다: {e}")
        logger.error(f"UI 실행 오류: {e}")

if __name__ == "__main__":
    main()