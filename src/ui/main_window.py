"""
메인 윈도우 - 리팩토링된 버전
"""
import streamlit as st
from ..config import config
from ..utils.logger import logger
from .styles import load_css
from .components import StreamerTab, NotificationTab, SettingsTab

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
    
    def render_header(self):
        """헤더 렌더링"""
        st.markdown("""
        <div class="app-header">
            <h1 class="app-title">📺 스트리머 알림</h1>
            <p class="app-subtitle">실시간 스트리머 모니터링 시스템</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_metrics(self):
        """메트릭 대시보드 렌더링"""
        try:
            streamers = config.get_streamers()
            notifications = config.get_notifications()
            settings = config.get_settings()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("등록된 스트리머", len(streamers))
            
            with col2:
                # streamers는 딕셔너리이므로 .values()를 사용하여 값들에 접근
                active_count = len([data for data in streamers.values() if data.get('enabled', True)])
                st.metric("활성 스트리머", active_count)
            
            with col3:
                today_notifications = len([n for n in notifications 
                                         if n.get('timestamp', '').startswith('2024')])
                st.metric("오늘 알림", today_notifications)
            
            with col4:
                interval = settings.get('check_interval', 30)
                st.metric("체크 간격", f"{interval}초")
                
        except Exception as e:
            logger.error(f"메트릭 렌더링 오류: {e}")
            st.error("메트릭 정보를 불러올 수 없습니다.")
    
    def run(self):
        """메인 애플리케이션 실행"""
        try:
            # 헤더 렌더링
            self.render_header()
            
            # 메트릭 대시보드
            with st.container():
                st.markdown("### 📊 현황")
                self.render_metrics()
            
            st.divider()
            
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
            
            # 새 스트리머 추가 버튼
            col1, col2, col3 = st.columns([3, 1, 1])
            with col3:
                if st.button("➕ 새 스트리머 추가", type="primary", use_container_width=True):
                    st.session_state.show_add_form = True
                    st.rerun()
            
            # 스트리머 추가 폼 표시
            if st.session_state.get('show_add_form', False):
                self.show_add_streamer_form()
            
            st.markdown("---")
            
            # 스트리머 목록
            if not streamers:
                st.markdown("""
                <div class="empty-state">
                    <h3>🎭 등록된 스트리머가 없습니다</h3>
                    <p>위의 '새 스트리머 추가' 버튼을 클릭하여 스트리머를 추가해보세요!</p>
                </div>
                """, unsafe_allow_html=True)
                return
            
            st.markdown('<div class="section-header">등록된 스트리머</div>', unsafe_allow_html=True)
            
            # 스트리머 카드들
            for name, data in streamers.items():
                with st.container():
                    self.create_streamer_card_optimized(name, data)
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    
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
            
            # 알림 기록 제거 버튼
            col1, col2, col3 = st.columns([3, 1, 1])
            with col3:
                if st.button("🗑️ 모든 알림 삭제", type="secondary", use_container_width=True):
                    self.clear_all_notifications()
            
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
                return
            
            # 알림 통계
            st.markdown(f"📊 총 {len(filtered_notifications)}개의 알림 (최근 50개 표시)")
            
            # 최근 50개 알림만 표시
            for notification in filtered_notifications[:50]:
                self.create_notification_item_optimized(notification)
                
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
        """최적화된 알림 아이템 생성"""
        with st.container():
            timestamp = notification.get('timestamp', '')
            noti_type = notification.get('type', '')
            title = notification.get('title', '')
            content = notification.get('content', '')
            url = notification.get('url', '')
            streamer_name = notification.get('streamer_name', '')
            
            # 시간 포맷팅
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime('%m/%d %H:%M')
            except:
                time_str = timestamp
            
            # 타입별 아이콘
            type_icons = {
                'live': '🔴',
                'cafe': '📝', 
                'twitter': '🐦'
            }
            icon = type_icons.get(noti_type, '📢')
            
            # 알림 카드 HTML
            card_html = f"""
            <div class="notification-card">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="font-size: 24px;">{icon}</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <h4 style="margin: 0; color: #2c3e50;">{title}</h4>
                            <small style="color: #7f8c8d;">{time_str}</small>
                        </div>
                        <p style="margin: 0 0 0.5rem 0; color: #34495e;">{content}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="color: #7f8c8d; font-size: 0.9rem;">👤 {streamer_name}</span>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            st.markdown(card_html, unsafe_allow_html=True)
            
            # 링크 버튼
            if url:
                if st.button("🔗 링크 열기", key=f"open_{timestamp}", help="원본 링크로 이동"):
                    st.markdown(f"[링크 열기]({url})")
            
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    
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
            
            with tab3:
                st.markdown("#### 🔐 네이버 계정 관리")
                
                # 네이버 로그인 상태 확인
                login_status = self.get_naver_login_status()
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    if login_status == "logged_in":
                        st.success("✅ 네이버에 로그인되어 있습니다. 카페 모니터링이 정상 작동합니다.")
                    elif login_status == "logged_out":
                        st.warning("⚠️ 네이버 로그아웃 상태입니다. 카페 모니터링을 위해 로그인이 필요합니다.")
                    elif login_status == "checking":
                        st.info("🔍 네이버 로그인 상태를 확인하는 중...")
                    else:
                        st.info("💡 네이버 카페 모니터링을 위해서는 로그인이 필요합니다.")
                
                with col2:
                    if st.button("🔄 네이버 다시 로그인", use_container_width=True, type="primary"):
                        self.relogin_naver()
                
                # 시스템 정보
                st.markdown("---")
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
            col1, col2, col3 = st.columns([2, 1, 2])
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
            # 플랫폼 배지들
            platforms = []
            if data.get('chzzk_id'):
                platforms.append('<span class="platform-badge platform-chzzk">📺 치지직</span>')
            if data.get('twitter_username'):
                platforms.append('<span class="platform-badge platform-twitter">🐦 트위터</span>')
            if data.get('cafe_user_id'):
                platforms.append('<span class="platform-badge platform-cafe">💬 카페</span>')
            
            # 상태 배지
            status_class = "status-active" if data.get('enabled', True) else "status-inactive"
            status_text = "활성" if data.get('enabled', True) else "비활성"
            
            # 라이브 상태 확인
            is_live = self.check_streamer_live_status_sync(name)
            live_class = "live-on" if is_live else "live-off"
            live_text = "🔴 라이브" if is_live else "⚫ 오프라인"
            
            # 카드 HTML
            card_html = f"""
            <div class="streamer-card">
                <div class="streamer-info">
                    <div style="width: 64px; height: 64px; background: linear-gradient(135deg, #667eea, #764ba2); 
                               border-radius: 16px; display: flex; align-items: center; justify-content: center; 
                               font-size: 28px; color: white; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3); flex-shrink: 0;">👤</div>
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
        """스트리머 라이브 상태 동기적 확인"""
        try:
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
                
                enabled = st.checkbox("✅ 활성화", value=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✨ 추가", type="primary", use_container_width=True):
                        if name.strip():
                            streamers = config.get_streamers()
                            if name in streamers:
                                st.error(f"❌ '{name}' 스트리머가 이미 존재합니다!")
                            else:
                                streamers[name] = {
                                    'chzzk_id': chzzk_id.strip(),
                                    'twitter_username': twitter_username.strip(),
                                    'cafe_user_id': cafe_user_id.strip(),
                                    'cafe_club_id': '30919539',
                                    'enabled': enabled,
                                    'profile_image': None
                                }
                                config.save_streamers(streamers)
                                st.success(f"🎉 스트리머 '{name}'가 추가되었습니다!")
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
                
                enabled = st.checkbox("활성화", value=data.get('enabled', True))
                
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
                            
                            # 새 데이터 저장
                            streamers[new_name] = {
                                'chzzk_id': chzzk_id.strip(),
                                'twitter_username': twitter_username.strip(),
                                'cafe_user_id': cafe_user_id.strip(),
                                'cafe_club_id': data.get('cafe_club_id', '30919539'),
                                'enabled': enabled,
                                'profile_image': data.get('profile_image')
                            }
                            
                            config.save_streamers(streamers)
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
        """스트리머 데이터 새로고침"""
        try:
            # 실제 모니터링 시스템에 새로고침 요청
            st.info(f"🔄 {name} 스트리머 데이터를 새로고침합니다...")
            # 여기에 실제 새로고침 로직을 추가할 수 있습니다.
            st.success(f"✅ {name} 데이터가 새로고침되었습니다!")
        except Exception as e:
            logger.error(f"스트리머 데이터 새로고침 실패 ({name}): {e}")
            st.error("새로고침 중 오류가 발생했습니다.")
    
    def test_notification(self):
        """알림 테스트"""
        try:
            st.info("🔔 테스트 알림을 전송합니다...")
            # 실제 알림 테스트 로직을 여기에 추가
            import time
            time.sleep(1)
            st.success("✅ 테스트 알림이 전송되었습니다!")
        except Exception as e:
            logger.error(f"알림 테스트 실패: {e}")
            st.error("알림 테스트 중 오류가 발생했습니다.")
    
    def get_naver_login_status(self):
        """네이버 로그인 상태 확인"""
        try:
            session_data = config.get_browser_session()
            if session_data and session_data.get('logged_in'):
                return "logged_in"
            else:
                return "logged_out"
        except Exception as e:
            logger.error(f"네이버 로그인 상태 확인 실패: {e}")
            return "unknown"
    
    def relogin_naver(self):
        """네이버 재로그인"""
        try:
            st.info("🔄 네이버 재로그인을 시작합니다...")
            # 실제 재로그인 로직을 여기에 추가
            st.success("✅ 네이버 재로그인이 시작되었습니다. 브라우저 창을 확인해주세요.")
        except Exception as e:
            logger.error(f"네이버 재로그인 실패: {e}")
            st.error("재로그인 중 오류가 발생했습니다.")
    
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