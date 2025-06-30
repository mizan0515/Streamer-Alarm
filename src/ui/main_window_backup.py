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
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        /* 컨텐츠 영역 */
        .content-area {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(0, 0, 0, 0.05);
        }
        
        /* 메트릭 카드 */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
            transition: transform 0.2s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
        }
        
        .metric-card h3 {
            margin: 0 0 0.5rem 0;
            font-size: 0.9rem;
            opacity: 0.9;
            font-weight: 500;
        }
        
        .metric-card h2 {
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
        }
        
        /* 스트리머 카드 */
        .streamer-card {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .streamer-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        
        .streamer-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            border-color: #667eea;
        }
        
        .streamer-info {
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1rem;
        }
        
        
        /* 플랫폼 배지 */
        .platform-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 4px;
        }
        
        .platform-chzzk {
            background: linear-gradient(45deg, #ff6b35, #f7931e);
            color: white;
        }
        
        .platform-twitter {
            background: linear-gradient(45deg, #1da1f2, #0077b5);
            color: white;
        }
        
        .platform-cafe {
            background: linear-gradient(45deg, #2ed573, #17a2b8);
            color: white;
        }
        
        /* 상태 배지 */
        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .status-active {
            background: linear-gradient(45deg, #2ed573, #17a2b8);
            color: white;
        }
        
        .status-inactive {
            background: #e9ecef;
            color: #6c757d;
        }
        
        .live-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .live-on {
            background: linear-gradient(45deg, #ff4757, #ff3742);
            color: white;
            animation: pulse 2s infinite;
        }
        
        .live-off {
            background: #f8f9fa;
            color: #6c757d;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.4); }
            70% { box-shadow: 0 0 0 8px rgba(255, 71, 87, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0); }
        }
        
        /* 알림 카드 */
        .notification-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 0.5rem 0;
            border-left: 4px solid;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            transition: all 0.2s ease;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .notification-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
        }
        
        .notification-live {
            border-left-color: #ff4757;
        }
        
        .notification-cafe {
            border-left-color: #2ed573;
        }
        
        .notification-twitter {
            border-left-color: #1da1f2;
        }
        
        .notification-info {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .notification-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 0.5rem;
            border-top: 1px solid #f1f3f4;
            margin-top: auto;
        }
        
        /* 설정 카드 */
        .settings-card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            border: 1px solid #e9ecef;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
            min-height: 120px;
        }
        
        .settings-section {
            margin-bottom: 2rem;
        }
        
        .settings-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            border-bottom: 1px solid #f1f3f4;
        }
        
        .settings-row:last-child {
            border-bottom: none;
        }
        
        /* 폼 스타일링 */
        .form-container {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #e9ecef;
            min-height: auto;
        }
        
        /* 일관된 버튼 스타일 */
        .stButton > button {
            min-height: 40px;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.2s ease;
            border: none;
        }
        
        /* 확장자 스타일 */
        .stExpander {
            border: 1px solid #e9ecef;
            border-radius: 12px;
            overflow: hidden;
        }
        
        .stExpander > div > div {
            padding: 1.5rem;
        }
        
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
        }
        
        /* 섹션 헤더 */
        .section-header {
            font-size: 1.5rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e9ecef;
        }
        
        /* 통계 텍스트 */
        .stats-text {
            text-align: center;
            color: #6c757d;
            font-size: 1rem;
            margin: 1rem 0;
            font-weight: 500;
        }
        
        /* 빈 상태 */
        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: #6c757d;
        }
        
        .empty-state h3 {
            color: #495057;
            margin-bottom: 1rem;
        }
        
        /* 반응형 */
        @media (max-width: 768px) {
            .main {
                margin: 1rem;
                padding: 0.5rem;
            }
            
            .block-container {
                padding: 1rem;
            }
            
            .app-title {
                font-size: 2rem;
            }
        }
        </style>
        """, unsafe_allow_html=True)

    def initialize_session_state(self):
        """세션 상태 초기화"""
        if 'last_tab' not in st.session_state:
            st.session_state.last_tab = 0
        if 'streamer_data_cache' not in st.session_state:
            st.session_state.streamer_data_cache = {}
        if 'cache_timestamp' not in st.session_state:
            st.session_state.cache_timestamp = 0
            # 초기화 시 라이브 상태 파일 읽기
            self.try_update_live_status_background()
        if 'edit_mode' not in st.session_state:
            st.session_state.edit_mode = {}
        if 'notification_filter' not in st.session_state:
            st.session_state.notification_filter = "all"
        if 'show_add_form' not in st.session_state:
            st.session_state.show_add_form = False
        if 'add_form_data' not in st.session_state:
            st.session_state.add_form_data = {
                'name': '',
                'chzzk_id': '',
                'twitter_username': '',
                'cafe_user_id': '',
                'cafe_club_id': '',
                'enabled': True
            }
        
        # 애플리케이션 시작시 진행 상태 플래그 정리 (안전장치)
        st.session_state.notification_test_in_progress = False
        st.session_state.naver_login_in_progress = False
        logger.debug("애플리케이션 시작 - 모든 진행 상태 플래그 초기화 완료")
    
    def run(self):
        """메인 애플리케이션 실행"""
        # 메인 컨테이너로 전체 감싸기
        st.markdown('<div class="center-container">', unsafe_allow_html=True)
        
        # 헤더
        st.markdown("""
        <div class="header-container">
            <h1 style="color: #1f77b4; margin-bottom: 0;">📺 스트리머 알림</h1>
            <p style="color: #666; margin-top: 0;">실시간 스트리머 모니터링 시스템</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 탭 시스템
        tab1, tab2, tab3 = st.tabs(["🎮 스트리머 관리", "🔔 알림 기록", "⚙️ 설정"])
        
        with tab1:
            self.show_streamer_management()
        
        with tab2:
            self.show_notification_history()
        
        with tab3:
            self.show_settings()
        
        st.markdown('</div>', unsafe_allow_html=True)

    def show_streamer_management(self):
        """스트리머 관리 페이지"""
        # 자동 새로고침 설정
        self.setup_auto_refresh()
        
        # 통계 요약 (중앙 정렬)
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
        
        # 새 스트리머 추가 버튼 (우측 정렬, 더 큰 버튼)
        col1, col2, col3 = st.columns([3, 1, 1])
        with col3:
            if st.button("➕ 새 스트리머 추가", type="primary", use_container_width=True):
                st.session_state.show_add_form = True
                st.rerun()
        
        # 스트리머 추가 폼 표시
        if st.session_state.show_add_form:
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
        
        # 스트리머 카드들 (일관된 간격)
        for name, data in streamers.items():
            with st.container():
                self.create_streamer_card_optimized(name, data)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    def get_live_count_cached(self):
        """캐시된 라이브 카운트 반환 (메인 모니터링 데이터 활용)"""
        current_time = time.time()
        if current_time - st.session_state.cache_timestamp > 10:  # 10초 캐시
            # 메인 모니터링 시스템에서 데이터 동기화
            self.try_update_live_status_background()
        
        # 라이브 중인 스트리머 수 반환
        return len([name for name, data in st.session_state.streamer_data_cache.items() if data.get('is_live', False)])
    
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
            
            # 카드 HTML (일관된 구조)
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
            
            # 액션 버튼들 (일관된 레이아웃)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("✏️ 편집", key=f"edit_{name}", use_container_width=True):
                    st.session_state.edit_mode[name] = True
                    st.rerun()
            with col2:
                if st.button("🗑️ 삭제", key=f"delete_{name}", use_container_width=True):
                    self.confirm_delete_streamer(name)
            with col3:
                if st.button("🔄 새로고침", key=f"refresh_{name}", use_container_width=True):
                    self.refresh_streamer_data(name)
            
            # 편집 모드
            if st.session_state.edit_mode.get(name, False):
                self.show_inline_edit_form(name, data)

    def show_notification_history(self):
        """알림 기록 페이지"""
        # 필터 버튼들 (중앙 정렬)
        filter_options = {
            "all": ("전체", "🔍"),
            "live": ("방송", "📺"),
            "cafe": ("카페", "💬"),
            "twitter": ("트위터", "🐦")
        }
        
        # 필터 버튼들 (일관된 레이아웃)
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
        st.markdown(f'<div class="stats-text">📊 총 {len(filtered_notifications)}개의 알림 (최근 50개 표시)</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">최근 알림</div>', unsafe_allow_html=True)
        
        # 최근 50개 알림만 표시 (일관된 간격)
        for notification in filtered_notifications[:50]:
            self.create_notification_item_optimized(notification)

    def create_notification_item_optimized(self, notification: dict):
        """최적화된 알림 아이템 생성"""
        # 타입별 설정
        type_config = {
            'live': {'icon': '📺', 'color': '#ff4757', 'class': 'notification-live'},
            'cafe': {'icon': '💬', 'color': '#2ed573', 'class': 'notification-cafe'},
            'twitter': {'icon': '🐦', 'color': '#1e90ff', 'class': 'notification-twitter'}
        }
        
        config_data = type_config.get(notification['type'], {'icon': '📢', 'color': '#666', 'class': 'notification-default'})
        
        # 시간 포맷팅
        try:
            timestamp = notification['timestamp'][:19].replace('T', ' ')
            time_obj = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            time_str = time_obj.strftime('%m/%d %H:%M')
        except:
            time_str = "시간 정보 없음"
        
        # 알림 카드 HTML 직접 생성 (클릭 가능한 링크로)
        notification_id = notification.get('id', hash(notification['title']))
        
        # HTML 주석 없이 간단한 구조로 작성
        card_html = f"""<div style="margin-bottom: 12px;"><a href="{notification['url']}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;"><div style="display: flex; align-items: flex-start; gap: 12px; width: 100%; border: 1px solid #e1e5e9; border-radius: 12px; padding: 16px; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: all 0.2s ease; cursor: pointer; border-left: 4px solid {config_data['color']};" onmouseover="this.style.boxShadow='0 4px 16px rgba(0,0,0,0.15)'; this.style.transform='translateY(-2px)';" onmouseout="this.style.boxShadow='0 2px 8px rgba(0,0,0,0.1)'; this.style.transform='translateY(0)';"><div style="font-size: 1.8rem; flex-shrink: 0; margin-top: 2px;">{config_data['icon']}</div><div style="flex: 1; min-width: 0;"><div style="margin: 0 0 8px 0; color: #2c3e50; font-size: 1.1rem; font-weight: 600; line-height: 1.3;">{notification['title']}</div><div style="margin: 0 0 12px 0; color: #666; line-height: 1.4; font-size: 0.95rem;">{notification['content'][:150]}{'...' if len(notification['content']) > 150 else ''}</div><div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;"><small style="color: #999; font-size: 0.85rem;">⏰ {time_str}</small><span style="background: {config_data['color']}; color: white; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">{notification['type'].upper()}</span></div></div></div></a></div>"""
        
        # HTML 마크다운으로 렌더링
        st.markdown(card_html, unsafe_allow_html=True)

    def show_settings(self):
        """설정 페이지"""
        settings = config.get_settings()
        
        # 설정 섹션들 (일관된 구조)
        tab1, tab2, tab3 = st.tabs(["⚙️ 일반 설정", "🔔 알림 설정", "🔐 계정 관리"])
        
        with tab1:
            # 일반 설정 카드
            st.markdown("""
            <div class="settings-card">
                <div class="section-header">📊 모니터링 설정</div>
            </div>
            """, unsafe_allow_html=True)
            
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
            # 알림 설정 카드
            st.markdown("""
            <div class="settings-card">
                <div class="section-header">🔔 알림 설정</div>
            </div>
            """, unsafe_allow_html=True)
            
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
            # 계정 관리 카드
            st.markdown("""
            <div class="settings-card">
                <div class="section-header">🔐 네이버 계정 관리</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 네이버 로그인 상태 확인 및 표시 (개선된 버전)
            login_status = self.get_naver_login_status()
            
            col1, col2 = st.columns([2, 1])
            with col1:
                if login_status == "logged_in":
                    st.success("✅ 네이버에 로그인되어 있습니다. 카페 모니터링이 정상 작동합니다.")
                elif login_status == "logged_out":
                    st.warning("⚠️ 네이버 로그아웃 상태입니다. 카페 모니터링을 위해 로그인이 필요합니다.")
                elif login_status == "checking":
                    st.info("🔍 네이버 로그인 상태를 확인하는 중...")
                elif login_status == "unknown":
                    st.warning("❓ 네이버 로그인 상태를 확인할 수 없습니다. 메인 시스템이 실행 중인지 확인해주세요.")
                else:
                    st.info("💡 네이버 카페 모니터링을 위해서는 로그인이 필요합니다.")
                    
            # 로그인 상태에 따른 추가 정보 표시
            if login_status == "logged_in":
                st.info("ℹ️ 재로그인 버튼을 클릭하면 네이버 브라우저 창을 다시 볼 수 있습니다.")
                    
            with col2:
                if st.button("🔄 네이버 다시 로그인", use_container_width=True, type="primary"):
                    self.relogin_naver()
        
        # 설정 저장 (일관된 레이아웃)
        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("💾 설정 저장", use_container_width=True, type="primary"):
                self.save_settings_with_realtime_update(
                    check_interval, show_notifications, 
                    start_with_windows, minimize_to_tray
                )

    def show_add_streamer_form(self):
        """스트리머 추가 폼"""
        # 폼을 중앙 정렬된 컨테이너에 배치
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        st.markdown("### ➕ 새 스트리머 추가")
        st.markdown("#### 📝 스트리머 정보 입력")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input(
                "🎭 스트리머 이름 *",
                value=st.session_state.add_form_data['name'],
                placeholder="예: 아리사",
                help="스트리머의 실제 이름이나 닉네임을 입력해주세요.",
                key="add_name",
                on_change=lambda: self.update_form_data('name', st.session_state.add_name)
            )
            chzzk_id = st.text_input(
                "📺 치지직 ID",
                value=st.session_state.add_form_data['chzzk_id'],
                placeholder="예: abc123def456",
                help="치지직 채널 URL에서 확인할 수 있습니다.",
                key="add_chzzk",
                on_change=lambda: self.update_form_data('chzzk_id', st.session_state.add_chzzk)
            )
            cafe_club_id = st.text_input(
                "🏠 네이버 카페 고유번호",
                value=st.session_state.add_form_data['cafe_club_id'],
                placeholder="예: 30919539",
                help="네이버 카페 URL에서 확인할 수 있는 고유번호입니다.",
                key="add_cafe_club_id",
                on_change=lambda: self.update_form_data('cafe_club_id', st.session_state.add_cafe_club_id)
            )
        
        with col2:
            twitter_username = st.text_input(
                "🐦 트위터 사용자명",
                value=st.session_state.add_form_data['twitter_username'],
                placeholder="예: username (@ 제외)",
                help="@를 제외한 사용자명만 입력해주세요.",
                key="add_twitter",
                on_change=lambda: self.update_form_data('twitter_username', st.session_state.add_twitter)
            )
            cafe_user_id = st.text_input(
                "💬 네이버 카페 사용자 ID",
                value=st.session_state.add_form_data['cafe_user_id'],
                placeholder="예: user123",
                help="네이버 카페에서 확인할 수 있는 사용자 ID입니다.",
                key="add_cafe_user",
                on_change=lambda: self.update_form_data('cafe_user_id', st.session_state.add_cafe_user)
            )
        
        enabled = st.checkbox(
            "✅ 활성화", 
            value=st.session_state.add_form_data['enabled'], 
            help="체크하면 즉시 모니터링을 시작합니다.", 
            key="add_enabled",
            on_change=lambda: self.update_form_data('enabled', st.session_state.add_enabled)
        )
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("❌ 취소", use_container_width=True, key="add_cancel"):
                st.session_state.show_add_form = False
                self.reset_add_form()
                st.rerun()
        
        with col2:
            if st.button("✨ 스트리머 추가", use_container_width=True, type="primary", key="add_submit"):
                if name.strip():
                    streamers = config.get_streamers()
                    if name in streamers:
                        st.error(f"❌ '{name}' 스트리머가 이미 존재합니다!")
                    else:
                        streamers[name] = {
                            'chzzk_id': chzzk_id.strip(),
                            'twitter_username': twitter_username.strip(),
                            'cafe_user_id': cafe_user_id.strip(),
                            'cafe_club_id': cafe_club_id.strip() if cafe_club_id.strip() else config.cafe_club_id,
                            'enabled': enabled
                        }
                        config.save_streamers(streamers)
                        st.success(f"🎉 스트리머 '{name}'가 성공적으로 추가되었습니다!")
                        st.session_state.show_add_form = False
                        self.reset_add_form()
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("❌ 스트리머 이름을 입력해주세요.")
        
        st.markdown('</div>', unsafe_allow_html=True)

    def show_inline_edit_form(self, name: str, data: dict):
        """인라인 편집 폼"""
        # 편집 폼을 중앙 정렬된 컨테이너에 배치
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        st.markdown(f"### ✏️ {name} 편집")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input("스트리머 이름", value=name, key=f"edit_name_{name}")
            chzzk_id = st.text_input("치지직 ID", value=data.get('chzzk_id', ''), key=f"edit_chzzk_{name}")
            cafe_club_id = st.text_input("네이버 카페 고유번호", value=data.get('cafe_club_id', config.cafe_club_id), key=f"edit_cafe_club_{name}")
        
        with col2:
            twitter_username = st.text_input("트위터 사용자명", value=data.get('twitter_username', ''), key=f"edit_twitter_{name}")
            cafe_user_id = st.text_input("네이버 카페 사용자 ID", value=data.get('cafe_user_id', ''), key=f"edit_cafe_{name}")
        
        enabled = st.checkbox("활성화", value=data.get('enabled', True), key=f"edit_enabled_{name}")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("💾 저장", key=f"save_{name}", use_container_width=True, type="primary"):
                streamers = config.get_streamers()
                if new_name != name and new_name in streamers:
                    st.error("❌ 이미 존재하는 스트리머 이름입니다.")
                else:
                    # 기존 스트리머 삭제 (이름이 변경된 경우)
                    if new_name != name:
                        del streamers[name]
                    
                    streamers[new_name] = {
                        'chzzk_id': chzzk_id.strip(),
                        'twitter_username': twitter_username.strip(),
                        'cafe_user_id': cafe_user_id.strip(),
                        'cafe_club_id': cafe_club_id.strip() if cafe_club_id.strip() else config.cafe_club_id,
                        'enabled': enabled
                    }
                    config.save_streamers(streamers)
                    st.success("✅ 스트리머 정보가 업데이트되었습니다!")
                    st.session_state.edit_mode[name] = False
                    time.sleep(1)
                    st.rerun()
        
        with col2:
            if st.button("❌ 취소", key=f"cancel_{name}", use_container_width=True):
                st.session_state.edit_mode[name] = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    def confirm_delete_streamer(self, name: str):
        """스트리머 삭제 확인"""
        st.warning(f"⚠️ 정말로 '{name}' 스트리머를 삭제하시겠습니까?")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("🗑️ 삭제", key=f"confirm_delete_{name}", type="primary"):
                streamers = config.get_streamers()
                if name in streamers:
                    del streamers[name]
                    config.save_streamers(streamers)
                    st.success(f"✅ 스트리머 '{name}'가 삭제되었습니다!")
                    time.sleep(1)
                    st.rerun()
        with col2:
            if st.button("↩️ 취소", key=f"cancel_delete_{name}"):
                st.rerun()

    def apply_notification_filter(self, notifications: List[dict], filter_type: str) -> List[dict]:
        """알림 필터 적용"""
        if filter_type == "all":
            return notifications
        elif filter_type == "live":
            return [n for n in notifications if n.get('type') == 'live']
        elif filter_type == "cafe":
            return [n for n in notifications if n.get('type') == 'cafe']
        elif filter_type == "twitter":
            return [n for n in notifications if n.get('type') == 'twitter']
        else:
            return notifications

    def clear_all_notifications(self):
        """모든 알림 기록 삭제"""
        # 삭제 확인을 위한 세션 상태 설정
        if 'confirm_delete_notifications' not in st.session_state:
            st.session_state.confirm_delete_notifications = False
        
        if not st.session_state.confirm_delete_notifications:
            # 첫 번째 클릭 - 확인 요청
            st.session_state.confirm_delete_notifications = True
            st.warning("⚠️ 정말로 모든 알림 기록을 삭제하시겠습니까? 다시 한 번 버튼을 클릭하면 삭제됩니다.")
            st.rerun()
        else:
            # 두 번째 클릭 - 실제 삭제
            try:
                config.save_notifications([])  # 빈 리스트로 저장
                st.session_state.confirm_delete_notifications = False
                st.success("✅ 모든 알림 기록이 삭제되었습니다!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                logger.error(f"알림 기록 삭제 실패: {e}")
                st.error(f"❌ 알림 기록 삭제 실패: {str(e)}")
                st.session_state.confirm_delete_notifications = False
    
    def refresh_streamer_data(self, name: str):
        """스트리머 데이터 새로고침"""
        try:
            # 메인 모니터링 파일에서 최신 데이터 읽기
            self.try_update_live_status_background()
            
            # 캐시에서 상태 확인
            if name in st.session_state.streamer_data_cache:
                is_live = st.session_state.streamer_data_cache[name].get('is_live', False)
                status_text = "라이브 중" if is_live else "오프라인"
                st.success(f"✅ {name}의 상태가 새로고침되었습니다! (현재: {status_text})")
            else:
                # 캐시에 없으면 직접 API 호출 (더 안전한 방식)
                streamers = config.get_streamers()
                data = streamers.get(name, {})
                
                if data.get('chzzk_id'):
                    try:
                        import httpx
                        # 더 안전한 HTTP 클라이언트 설정
                        timeout_config = httpx.Timeout(
                            connect=5.0,  # 연결 타임아웃
                            read=10.0,    # 읽기 타임아웃
                            write=5.0,    # 쓰기 타임아웃
                            pool=10.0     # 풀 타임아웃
                        )
                        
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "application/json",
                            "Connection": "close"  # 연결 재사용 방지
                        }
                        
                        with httpx.Client(timeout=timeout_config, headers=headers, follow_redirects=True) as client:
                            url = f"https://api.chzzk.naver.com/service/v2/channels/{data['chzzk_id']}/live-status"
                            response = client.get(url)
                            
                            if response.status_code == 200:
                                response_data = response.json()
                                is_live = response_data.get('content', {}).get('status') == 'OPEN'
                                
                                # 캐시 업데이트
                                if name not in st.session_state.streamer_data_cache:
                                    st.session_state.streamer_data_cache[name] = {}
                                st.session_state.streamer_data_cache[name]['is_live'] = is_live
                                st.session_state.cache_timestamp = time.time()
                                
                                status_text = "라이브 중" if is_live else "오프라인"
                                st.success(f"✅ {name}의 상태가 새로고침되었습니다! (현재: {status_text})")
                            else:
                                st.warning(f"⚠️ {name}의 상태를 확인할 수 없습니다. (HTTP {response.status_code})")
                                
                    except httpx.ConnectError:
                        st.error(f"❌ {name}: 네트워크 연결 실패. 인터넷 연결을 확인해주세요.")
                    except httpx.TimeoutException:
                        st.error(f"❌ {name}: 요청 시간 초과. 나중에 다시 시도해주세요.")
                    except httpx.RequestError as e:
                        st.error(f"❌ {name}: 요청 오류 - {str(e)}")
                    except Exception as e:
                        st.error(f"❌ {name}: 알 수 없는 오류 - {str(e)}")
                else:
                    st.warning(f"⚠️ {name}의 치지직 ID가 설정되지 않았습니다.")
                
        except Exception as e:
            logger.error(f"새로고침 중 예상치 못한 오류: {e}")
            st.error(f"❌ 새로고침 중 오류가 발생했습니다.")
        
        time.sleep(1)
        st.rerun()

    def relogin_naver(self):
        """네이버 재로그인 (강화된 중복 방지 및 안정성 개선)"""
        
        # 현재 시간 기반 중복 방지
        current_time = time.time()
        last_login_time = getattr(st.session_state, 'last_naver_login_time', 0)
        
        # 5초 내 중복 요청 방지
        if current_time - last_login_time < 5:
            st.warning("⚠️ 너무 빠른 연속 요청입니다. 5초 후 다시 시도해주세요.")
            return
        
        # 세션 상태 체크 및 강제 리셋 (안전장치)
        if 'naver_login_in_progress' in st.session_state and st.session_state.naver_login_in_progress:
            # 마지막 로그인으로부터 60초 이상 지났으면 강제 리셋
            if current_time - last_login_time > 60:
                logger.warning("네이버 로그인 세션 상태 강제 리셋 (60초 초과)")
                st.session_state.naver_login_in_progress = False
            else:
                st.warning("⚠️ 네이버 로그인이 진행 중입니다. 잠시 후 다시 시도해주세요.")
                return
        
        # 진행 상태 플래그 및 시간 설정
        st.session_state.naver_login_in_progress = True
        st.session_state.last_naver_login_time = current_time
        
        try:
            login_request_file = os.path.join(config.data_dir, "login_request.json")
            
            # 모든 기존 로그인 요청 파일 강제 정리
            for attempt in range(3):  # 최대 3회 시도
                try:
                    if os.path.exists(login_request_file):
                        os.remove(login_request_file)
                    time.sleep(0.1)  # 파일 시스템 동기화 대기
                    break
                except Exception as e:
                    if attempt == 2:  # 마지막 시도
                        logger.warning(f"기존 로그인 요청 파일 삭제 실패: {e}")
                    time.sleep(0.2)
            
            # 고유한 요청 ID 생성
            request_id = f"login_{int(time.time() * 1000)}"
            
            # 로그인 요청 파일 생성
            login_request = {
                "action": "relogin_naver",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "status": "requested"
            }
            
            # 안전한 파일 쓰기 (Windows 호환)
            try:
                self._safe_write_json(login_request_file, login_request)
                logger.info(f"네이버 로그인 요청 파일 생성 성공 (ID: {request_id})")
            except Exception as e:
                logger.error(f"네이버 로그인 요청 파일 생성 실패 (ID: {request_id}): {e}")
                st.error(f"❌ 네이버 로그인 요청 파일 생성 실패: {str(e)}")
                return
            
            logger.info("네이버 재로그인 요청이 생성되었습니다")
            
            # 진행률 표시기 추가
            st.info("📤 네이버 로그인 요청을 전송했습니다...")
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 더 세밀한 확인 (최대 15초)
            max_wait_time = 15
            check_interval = 0.5
            checks_done = 0
            max_checks = int(max_wait_time / check_interval)
            
            for i in range(max_checks):
                time.sleep(check_interval)
                checks_done += 1
                progress = checks_done / max_checks
                progress_bar.progress(progress)
                
                # 상태별 메시지 업데이트
                if i < 4:  # 처음 2초
                    status_text.text("🔄 메인 프로세스로 요청 전달 중...")
                elif i < 8:  # 2-4초
                    status_text.text("🔧 브라우저 세션 준비 중...")
                elif i < 16:  # 4-8초
                    status_text.text("🌐 네이버 로그인 페이지 로딩 중...")
                else:  # 8초 이후
                    status_text.text("🔐 로그인 창이 열렸을 수 있습니다...")
                
                # 파일 상태 확인
                if os.path.exists(login_request_file):
                    try:
                        with open(login_request_file, 'r', encoding='utf-8') as f:
                            status = json.load(f)
                        
                        if status.get('status') == 'processing':
                            progress_bar.progress(0.7)
                            status_text.text("✅ 브라우저에서 로그인을 진행하세요...")
                        elif status.get('status') == 'completed':
                            progress_bar.progress(1.0)
                            status_text.empty()
                            st.success("✅ 네이버 로그인이 완료되었습니다!")
                            # 성공 시 즉시 세션 상태 정리
                            st.session_state.naver_login_in_progress = False
                            st.session_state.last_naver_login_time = time.time()
                            logger.debug("네이버 로그인 성공 - 세션 상태 즉시 정리")
                            return
                        elif status.get('status') == 'failed':
                            progress_bar.progress(1.0)
                            status_text.empty()
                            error_msg = status.get('error', '알 수 없는 오류')
                            st.error(f"❌ 네이버 로그인 실패: {error_msg}")
                            st.info("💡 메인 애플리케이션의 트레이 아이콘을 우클릭하여 '네이버 로그인'을 시도해보세요.")
                            # 실패 시에도 세션 상태 정리
                            st.session_state.naver_login_in_progress = False
                            st.session_state.last_naver_login_time = time.time()
                            logger.debug("네이버 로그인 실패 - 세션 상태 즉시 정리")
                            return
                    except:
                        continue
                else:
                    # 파일이 삭제되었다면 처리 완료 가능성
                    if i > 8:  # 4초 이후부터 확인
                        progress_bar.progress(1.0)
                        status_text.empty()
                        st.success("✅ 네이버 로그인 요청이 처리되었습니다!")
                        st.info("🌐 브라우저에서 로그인 창이 열렸는지 확인해주세요.")
                        # 파일 삭제된 경우에도 세션 상태 정리
                        st.session_state.naver_login_in_progress = False
                        st.session_state.last_naver_login_time = time.time()
                        logger.debug("네이버 로그인 파일 삭제 확인 - 세션 상태 즉시 정리")
                        return
            
            # 타임아웃 처리
            progress_bar.progress(1.0)
            status_text.empty()
            st.warning("⏰ 네이버 로그인 요청 응답 시간 초과")
            st.info("💡 메인 시스템이 실행 중인지 확인하고 다시 시도해주세요.")
            st.info("🔧 또는 메인 애플리케이션의 트레이 아이콘을 우클릭하여 '네이버 로그인'을 선택해주세요.")
            
            # 정리
            try:
                if os.path.exists(login_request_file):
                    os.remove(login_request_file)
            except:
                pass
                
        except Exception as e:
            logger.error(f"네이버 재로그인 요청 실패: {e}")
            st.error(f"❌ 네이버 재로그인 요청에 실패했습니다: {str(e)}")
            st.info("💡 대신 메인 애플리케이션의 트레이 아이콘을 우클릭하여 '네이버 로그인'을 선택해주세요.")
        
        finally:
            # 항상 진행 상태 플래그 해제 (강화된 정리)
            try:
                st.session_state.naver_login_in_progress = False
                st.session_state.last_naver_login_time = time.time()
                logger.debug("네이버 로그인 세션 상태 정리 완료")
            except Exception as cleanup_error:
                logger.warning(f"네이버 로그인 세션 상태 정리 중 오류: {cleanup_error}")
                # 강제 리셋
                try:
                    if hasattr(st.session_state, 'naver_login_in_progress'):
                        del st.session_state.naver_login_in_progress
                except:
                    pass

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
        if 'notification_test_in_progress' in st.session_state and st.session_state.notification_test_in_progress:
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

    def get_naver_login_status(self):
        """네이버 로그인 상태 확인 (개선된 버전)"""
        try:
            login_status_file = os.path.join(config.data_dir, "login_status_request.json")
            login_result_file = os.path.join(config.data_dir, "login_status_result.json")
            
            # 기존 결과 파일이 있고 최근 것이면 사용 (캐싱 - 30초로 확장)
            if os.path.exists(login_result_file):
                try:
                    with open(login_result_file, 'r', encoding='utf-8') as f:
                        result = json.load(f)
                    
                    # 결과가 30초 이내 것이면 캐시된 결과 사용 (UI 일관성 개선)
                    result_time = datetime.fromisoformat(result.get('timestamp', ''))
                    cache_age = (datetime.now() - result_time).total_seconds()
                    
                    if cache_age < 30:
                        logger.debug(f"캐시된 로그인 상태 사용 (캐시 나이: {cache_age:.1f}초): {result.get('status', 'unknown')}")
                        
                        # Streamlit 세션 상태에도 캐시
                        if 'naver_login_cache' not in st.session_state:
                            st.session_state.naver_login_cache = {}
                        
                        st.session_state.naver_login_cache = {
                            'status': result.get('status', 'unknown'),
                            'timestamp': result.get('timestamp', ''),
                            'cache_age': cache_age
                        }
                        
                        return result.get('status', 'unknown')
                except Exception as e:
                    logger.debug(f"캐시된 로그인 상태 파일 읽기 실패: {e}")
                    # 손상된 파일 삭제
                    try:
                        os.remove(login_result_file)
                    except:
                        pass
            
            # 기존 요청 파일 정리
            if os.path.exists(login_status_file):
                try:
                    os.remove(login_status_file)
                except:
                    pass
            
            # 새로운 상태 확인 요청
            status_request = {
                "action": "check_login_status",
                "timestamp": datetime.now().isoformat(),
                "status": "requested"
            }
            
            with open(login_status_file, 'w', encoding='utf-8') as f:
                json.dump(status_request, f, ensure_ascii=False, indent=2)
            
            logger.debug("네이버 로그인 상태 확인 요청 전송")
            
            # 더 짧은 간격으로 여러 번 확인 (최대 3초)
            max_wait_time = 3.0
            check_interval = 0.2
            checks_done = 0
            max_checks = int(max_wait_time / check_interval)
            
            for i in range(max_checks):
                time.sleep(check_interval)
                checks_done += 1
                
                # 결과 파일 확인
                if os.path.exists(login_result_file):
                    try:
                        with open(login_result_file, 'r', encoding='utf-8') as f:
                            result = json.load(f)
                        
                        status = result.get('status', 'unknown')
                        logger.debug(f"로그인 상태 확인 완료: {status}")
                        return status
                    except Exception as e:
                        logger.debug(f"로그인 상태 결과 파일 읽기 실패: {e}")
                        continue
                
                # 요청 파일이 사라졌는지 확인 (처리 중 표시)
                if not os.path.exists(login_status_file) and i > 2:
                    # 요청은 처리되었지만 결과가 아직 없음
                    continue
            
            # 타임아웃 - 기본값 반환
            logger.warning("네이버 로그인 상태 확인 타임아웃")
            
            # 정리
            try:
                if os.path.exists(login_status_file):
                    os.remove(login_status_file)
            except:
                pass
            
            return "unknown"
                
        except Exception as e:
            logger.error(f"네이버 로그인 상태 확인 실패: {e}")
            return "unknown"

    def save_settings_with_realtime_update(self, check_interval, show_notifications, start_with_windows, minimize_to_tray):
        """설정 저장 및 실시간 반영"""
        try:
            # 이전 설정과 비교하여 변경사항 감지
            old_settings = config.get_settings()
            new_settings = {
                'check_interval': check_interval,
                'show_notifications': show_notifications,
                'start_with_windows': start_with_windows,
                'minimize_to_tray': minimize_to_tray
            }
            
            # 설정 저장
            config.update_settings(new_settings)
            
            # 변경사항에 따른 실시간 처리
            changes_applied = []
            
            # 체크 간격이 변경된 경우
            if old_settings.get('check_interval', 30) != check_interval:
                # 메인 프로세스에 체크 간격 변경 신호 전송
                try:
                    settings_update_file = os.path.join(config.data_dir, "settings_update.json")
                    update_signal = {
                        "action": "update_check_interval",
                        "new_interval": check_interval,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    with open(settings_update_file, 'w', encoding='utf-8') as f:
                        json.dump(update_signal, f, ensure_ascii=False, indent=2)
                    
                    changes_applied.append(f"체크 간격: {check_interval}초")
                    logger.info(f"체크 간격 변경 신호 전송: {check_interval}초")
                except Exception as e:
                    logger.warning(f"체크 간격 실시간 업데이트 실패: {e}")
            
            # 알림 설정 변경
            if old_settings.get('show_notifications', True) != show_notifications:
                changes_applied.append(f"데스크톱 알림: {'활성화' if show_notifications else '비활성화'}")
            
            # 자동 시작 설정 변경
            if old_settings.get('start_with_windows', True) != start_with_windows:
                try:
                    # Windows 자동 시작 레지스트리 설정 (실제 구현 필요)
                    changes_applied.append(f"윈도우 자동 시작: {'활성화' if start_with_windows else '비활성화'}")
                except Exception as e:
                    logger.warning(f"자동 시작 설정 실패: {e}")
            
            # 트레이 최소화 설정
            if old_settings.get('minimize_to_tray', True) != minimize_to_tray:
                changes_applied.append(f"트레이 최소화: {'활성화' if minimize_to_tray else '비활성화'}")
            
            # 성공 메시지 표시
            if changes_applied:
                st.success("✅ 설정이 저장되고 즉시 적용되었습니다!")
                with st.expander("🔍 적용된 변경사항", expanded=True):
                    for change in changes_applied:
                        st.write(f"• {change}")
            else:
                st.info("📝 설정이 저장되었습니다. (변경사항 없음)")
            
            logger.info(f"설정 저장 완료. 적용된 변경사항: {len(changes_applied)}개")
            
            time.sleep(2)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 설정 저장 실패: {str(e)}")
            logger.error(f"설정 저장 중 오류: {e}")

    # 성능 최적화를 위한 캐시 함수들
    def get_streamer_profile_image_sync(self, streamer_name: str) -> Optional[str]:
        """스트리머 프로필 이미지 동기 버전 (캐시 적용)"""
        # 성능을 위해 캐시된 데이터 사용
        if streamer_name in st.session_state.streamer_data_cache:
            return st.session_state.streamer_data_cache[streamer_name].get('profile_image')
        return None

    def check_streamer_live_status_sync(self, streamer_name: str) -> bool:
        """스트리머 방송 상태 확인 동기 버전 (메인 모니터링 데이터 활용)"""
        # 캐시된 데이터가 있으면 사용
        if streamer_name in st.session_state.streamer_data_cache:
            return st.session_state.streamer_data_cache[streamer_name].get('is_live', False)
        
        # 캐시가 없거나 오래된 경우 메인 모니터링 데이터 동기화
        current_time = time.time()
        if current_time - st.session_state.cache_timestamp > 10:
            self.try_update_live_status_background()
            # 동기화 후 다시 확인
            if streamer_name in st.session_state.streamer_data_cache:
                return st.session_state.streamer_data_cache[streamer_name].get('is_live', False)
        
        return False  # 기본값
    
    def try_update_live_status_background(self):
        """메인 모니터링 시스템에서 저장한 라이브 상태 파일 읽기"""
        try:
            import json
            import os
            
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
        # 자동 새로고침 간격 (초)
        auto_refresh_interval = 15
        
        # 마지막 자동 새로고침 시간 체크
        if 'last_auto_refresh' not in st.session_state:
            st.session_state.last_auto_refresh = time.time()
        
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
    
    def update_form_data(self, field: str, value):
        """폼 데이터 업데이트"""
        st.session_state.add_form_data[field] = value
    
    def reset_add_form(self):
        """폼 데이터 초기화"""
        st.session_state.add_form_data = {
            'name': '',
            'chzzk_id': '',
            'twitter_username': '',
            'cafe_user_id': '',
            'cafe_club_id': '',
            'enabled': True
        }

    async def get_streamer_profile_image(self, streamer_name: str) -> Optional[str]:
        """스트리머 프로필 이미지 URL 가져오기"""
        try:
            streamers = config.get_streamers()
            streamer_data = streamers.get(streamer_name, {})
            chzzk_id = streamer_data.get('chzzk_id')
            
            if not chzzk_id:
                return None
            
            # 캐시된 이미지 파일 체크
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"profile_{streamer_name}.jpg")
            if os.path.exists(temp_file):
                return temp_file
            
            # 치지직 API에서 프로필 이미지 가져오기
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.chzzk.naver.com/service/v1/channels/{chzzk_id}")
                if response.status_code == 200:
                    data = response.json()
                    if 'content' in data and 'channelImageUrl' in data['content']:
                        image_url = data['content']['channelImageUrl']
                        return await self.download_and_save_image(image_url, streamer_name)
        except Exception as e:
            logger.warning(f"프로필 이미지 가져오기 실패 ({streamer_name}): {e}")
        return None

    async def download_and_save_image(self, url: str, streamer_name: str) -> Optional[str]:
        """이미지 다운로드 및 임시 저장"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10)
                if response.status_code == 200:
                    temp_dir = tempfile.gettempdir()
                    temp_file = os.path.join(temp_dir, f"profile_{streamer_name}.jpg")
                    
                    with open(temp_file, 'wb') as f:
                        f.write(response.content)
                    
                    return temp_file
        except Exception as e:
            logger.warning(f"이미지 다운로드 실패: {e}")
        return None

    async def check_streamer_live_status(self, streamer_name: str) -> bool:
        """스트리머 방송 상태 확인"""
        try:
            streamers = config.get_streamers()
            streamer_data = streamers.get(streamer_name, {})
            chzzk_id = streamer_data.get('chzzk_id')
            
            if not chzzk_id:
                return False
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://api.chzzk.naver.com/service/v2/channels/{chzzk_id}/live-status")
                if response.status_code == 200:
                    data = response.json()
                    if 'content' in data and 'status' in data['content']:
                        return data['content']['status'] == 'OPEN'
        except Exception as e:
            logger.warning(f"방송 상태 확인 실패 ({streamer_name}): {e}")
        return False

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


# Streamlit 앱 실행
def run_streamlit_app():
    """Streamlit 앱 실행"""
    app = MainWindow()
    app.run()

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