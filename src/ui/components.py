"""
UI 컴포넌트 모듈
"""
import streamlit as st
import json
from typing import Dict, List, Optional
from datetime import datetime
from ..config import config
from ..utils.logger import logger
from .styles import get_platform_badge_html, get_status_indicator_html, get_metric_card_html

class StreamerTab:
    """스트리머 관리 탭"""
    
    @staticmethod
    def render():
        st.markdown("### 📺 등록된 스트리머")
        
        streamers = config.get_streamers()
        
        if not streamers:
            st.info("등록된 스트리머가 없습니다.")
            return
        
        # 스트리머 목록 표시 - streamers는 딕셔너리이므로 .items()로 접근
        for i, (name, streamer_data) in enumerate(streamers.items()):
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{name}**")  # 딕셔너리의 키가 스트리머 이름
                    platforms = []
                    if streamer_data.get('chzzk_id'):
                        platforms.append('chzzk')
                    if streamer_data.get('twitter_username'):
                        platforms.append('twitter')
                    if streamer_data.get('cafe_user_id'):
                        platforms.append('cafe')
                    
                    if platforms:
                        badges_html = "".join([get_platform_badge_html(p) for p in platforms])
                        st.markdown(badges_html, unsafe_allow_html=True)
                
                with col2:
                    if streamer_data.get('chzzk_id'):
                        st.write(f"치지직: {streamer_data['chzzk_id']}")
                
                with col3:
                    if streamer_data.get('twitter_username'):
                        st.write(f"X: @{streamer_data['twitter_username']}")
                
                with col4:
                    if st.button("편집", key=f"edit_{i}"):
                        st.session_state[f'editing_{i}'] = True
                        st.session_state[f'editing_name_{i}'] = name  # 편집할 스트리머 이름 저장
                
                # 편집 모드
                if st.session_state.get(f'editing_{i}', False):
                    StreamerTab._render_edit_form(i, name, streamer_data)
                
                st.divider()
        
        # 새 스트리머 추가
        if st.button("➕ 새 스트리머 추가"):
            st.session_state['adding_new'] = True
        
        if st.session_state.get('adding_new', False):
            StreamerTab._render_add_form()
    
    @staticmethod
    def _render_edit_form(index: int, original_name: str, streamer_data: Dict):
        """스트리머 편집 폼"""
        with st.form(f"edit_streamer_{index}"):
            st.write("### ✏️ 스트리머 정보 편집")
            
            name = st.text_input("이름", value=original_name)
            chzzk_id = st.text_input("치지직 채널 ID", value=streamer_data.get('chzzk_id', ''))
            twitter_username = st.text_input("X(트위터) 사용자명", value=streamer_data.get('twitter_username', ''))
            cafe_user_id = st.text_input("네이버 카페 사용자 ID", value=streamer_data.get('cafe_user_id', ''))
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("💾 저장"):
                    StreamerTab._update_streamer(original_name, name, {
                        'chzzk_id': chzzk_id,
                        'twitter_username': twitter_username,
                        'cafe_user_id': cafe_user_id,
                        'enabled': streamer_data.get('enabled', True),
                        'cafe_club_id': streamer_data.get('cafe_club_id', '30919539'),
                        'profile_image': streamer_data.get('profile_image')
                    })
                    st.session_state[f'editing_{index}'] = False
                    st.rerun()
            
            with col2:
                if st.form_submit_button("❌ 취소"):
                    st.session_state[f'editing_{index}'] = False
                    st.rerun()
    
    @staticmethod
    def _render_add_form():
        """새 스트리머 추가 폼"""
        with st.form("add_streamer"):
            st.write("### ➕ 새 스트리머 추가")
            
            name = st.text_input("이름*")
            chzzk_id = st.text_input("치지직 채널 ID")
            twitter_username = st.text_input("X(트위터) 사용자명")
            cafe_user_id = st.text_input("네이버 카페 사용자 ID")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.form_submit_button("➕ 추가"):
                    if name:
                        StreamerTab._add_streamer(name, {
                            'chzzk_id': chzzk_id,
                            'twitter_username': twitter_username,
                            'cafe_user_id': cafe_user_id
                        })
                        st.session_state['adding_new'] = False
                        st.success(f"✅ {name} 스트리머가 추가되었습니다!")
                        st.rerun()
                    else:
                        st.error("이름을 입력해주세요!")
            
            with col2:
                if st.form_submit_button("❌ 취소"):
                    st.session_state['adding_new'] = False
                    st.rerun()
    
    @staticmethod
    def _update_streamer(original_name: str, new_name: str, data: Dict):
        """스트리머 정보 업데이트"""
        try:
            streamers = config.get_streamers()
            
            # 이름이 변경된 경우 기존 항목 삭제하고 새로 추가
            if original_name != new_name:
                if original_name in streamers:
                    del streamers[original_name]
                streamers[new_name] = data
            else:
                # 이름이 같은 경우 데이터만 업데이트
                if original_name in streamers:
                    streamers[original_name].update(data)
            
            config.save_streamers(streamers)
            logger.info(f"스트리머 정보 업데이트: {original_name} -> {new_name}")
        except Exception as e:
            logger.error(f"스트리머 정보 업데이트 실패: {e}")
            st.error("저장 중 오류가 발생했습니다.")
    
    @staticmethod
    def _add_streamer(name: str, data: Dict):
        """새 스트리머 추가"""
        try:
            streamers = config.get_streamers()
            streamers[name] = {
                'chzzk_id': data.get('chzzk_id', ''),
                'twitter_username': data.get('twitter_username', ''),
                'cafe_user_id': data.get('cafe_user_id', ''),
                'cafe_club_id': '30919539',
                'enabled': True,
                'profile_image': None
            }
            config.save_streamers(streamers)
            logger.info(f"새 스트리머 추가: {name}")
        except Exception as e:
            logger.error(f"스트리머 추가 실패: {e}")
            st.error("추가 중 오류가 발생했습니다.")


class NotificationTab:
    """알림 기록 탭"""
    
    @staticmethod
    def render():
        st.markdown("### 📋 알림 기록")
        
        notifications = config.get_notifications()
        
        if not notifications:
            st.info("알림 기록이 없습니다.")
            return
        
        # 최신 순으로 정렬
        notifications = sorted(notifications, key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 페이지네이션
        items_per_page = 20
        total_pages = (len(notifications) + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            page = st.selectbox("페이지", range(1, total_pages + 1)) - 1
        else:
            page = 0
        
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_notifications = notifications[start_idx:end_idx]
        
        # 통계 정보
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("전체 알림", len(notifications))
        
        with col2:
            live_count = len([n for n in notifications if n.get('type') == 'live'])
            st.metric("방송 알림", live_count)
        
        with col3:
            cafe_count = len([n for n in notifications if n.get('type') == 'cafe'])
            st.metric("카페 알림", cafe_count)
        
        with col4:
            twitter_count = len([n for n in notifications if n.get('type') == 'twitter'])
            st.metric("트위터 알림", twitter_count)
        
        st.divider()
        
        # 알림 목록
        for notification in page_notifications:
            NotificationTab._render_notification_item(notification)
        
        # 전체 삭제 버튼
        if notifications:
            st.divider()
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("🗑️ 전체 삭제", type="secondary"):
                    if st.session_state.get('confirm_delete_all', False):
                        config.clear_notifications()
                        st.success("모든 알림이 삭제되었습니다.")
                        st.rerun()
                    else:
                        st.session_state['confirm_delete_all'] = True
                        st.warning("한 번 더 클릭하면 모든 알림이 삭제됩니다.")
    
    @staticmethod
    def _render_notification_item(notification: Dict):
        """개별 알림 아이템 렌더링"""
        timestamp = notification.get('timestamp', '')
        noti_type = notification.get('type', '')
        streamer = notification.get('streamer', '')
        title = notification.get('title', '')
        url = notification.get('url', '')
        
        # 시간 포맷팅
        try:
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
        
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 2, 4, 1])
            
            with col1:
                st.write(f"**{time_str}**")
            
            with col2:
                st.write(f"{icon} {streamer}")
            
            with col3:
                if url:
                    st.markdown(f"[{title}]({url})")
                else:
                    st.write(title)
            
            with col4:
                if url:
                    if st.button("🔗", key=f"open_{timestamp}", help="링크 열기"):
                        st.write(f"링크: {url}")
            
            st.divider()


class SettingsTab:
    """설정 탭"""
    
    @staticmethod
    def render():
        st.markdown("### ⚙️ 설정")
        
        settings = config.get_settings()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 모니터링 설정")
            
            check_interval = st.number_input(
                "체크 간격 (초)",
                min_value=10,
                max_value=300,
                value=settings.get('check_interval', 30),
                step=5
            )
            
            enable_notifications = st.checkbox(
                "알림 표시",
                value=settings.get('enable_notifications', True)
            )
            
            minimize_to_tray = st.checkbox(
                "트레이로 최소화",
                value=settings.get('minimize_to_tray', True)
            )
            
            autostart = st.checkbox(
                "윈도우 시작시 자동 실행",
                value=settings.get('autostart', False)
            )
        
        with col2:
            st.markdown("#### 🔐 네이버 로그인")
            
            session_data = config.get_browser_session()
            if session_data.get('logged_in'):
                st.success("✅ 로그인됨")
                if st.button("로그아웃"):
                    config.clear_browser_session()
                    st.success("로그아웃되었습니다.")
                    st.rerun()
            else:
                st.warning("❌ 로그인 필요")
                if st.button("네이버 로그인"):
                    st.info("메인 앱에서 브라우저가 열립니다.")
        
        # 설정 저장
        if st.button("💾 설정 저장", type="primary"):
            new_settings = {
                'check_interval': check_interval,
                'enable_notifications': enable_notifications,
                'minimize_to_tray': minimize_to_tray,
                'autostart': autostart
            }
            config.save_settings(new_settings)
            st.success("✅ 설정이 저장되었습니다!")
        
        st.divider()
        
        # 시스템 정보
        st.markdown("#### 📋 시스템 정보")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**설정 파일**: `data/settings.json`")
            st.write(f"**로그 디렉토리**: `logs/`")
            st.write(f"**브라우저 데이터**: `data/browser_data/`")
        
        with info_col2:
            streamers = config.get_streamers()
            notifications = config.get_notifications()
            st.write(f"**등록된 스트리머**: {len(streamers)}명")
            st.write(f"**알림 기록**: {len(notifications)}개")
            
            # 캐시 정리 버튼
            if st.button("🧹 캐시 정리"):
                st.info("브라우저 캐시를 정리합니다...")
                # 여기에 캐시 정리 로직 추가 가능