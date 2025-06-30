"""
UI 스타일 유틸리티 모듈
"""
import os
import streamlit as st

def load_css():
    """CSS 파일 로드"""
    css_file = os.path.join(os.path.dirname(__file__), "styles.css")
    try:
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # 폴백 스타일
        st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .main {
            max-width: 1000px;
            margin: 0 auto;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        </style>
        """, unsafe_allow_html=True)

def get_platform_badge_html(platform: str) -> str:
    """플랫폼 배지 HTML 생성"""
    platform_styles = {
        "chzzk": "background: #00d564; color: white;",
        "twitter": "background: #1da1f2; color: white;", 
        "cafe": "background: #03c75a; color: white;"
    }
    
    style = platform_styles.get(platform.lower(), "background: #6c757d; color: white;")
    display_name = {
        "chzzk": "치지직",
        "twitter": "X(트위터)",
        "cafe": "카페"
    }.get(platform.lower(), platform)
    
    return f'<span class="platform-badge" style="{style}">{display_name}</span>'

def get_status_indicator_html(is_online: bool, text: str = None) -> str:
    """상태 인디케이터 HTML 생성"""
    if is_online:
        status_class = "online"
        icon = "🟢"
        text = text or "온라인"
    else:
        status_class = "offline"
        icon = "🔴"
        text = text or "오프라인"
    
    return f'<span class="status-indicator {status_class}">{icon} {text}</span>'

def get_metric_card_html(title: str, value: str, subtitle: str = None) -> str:
    """메트릭 카드 HTML 생성"""
    subtitle_html = f"<p style='margin: 0; font-size: 0.8rem; opacity: 0.8;'>{subtitle}</p>" if subtitle else ""
    return f"""
    <div class="metric-card">
        <h3>{title}</h3>
        <h2>{value}</h2>
        {subtitle_html}
    </div>
    """

def get_streamer_card_html(streamer_name: str, platforms: list, status: str = "offline") -> str:
    """스트리머 카드 HTML 생성"""
    platform_badges = "".join([get_platform_badge_html(p) for p in platforms])
    status_indicator = get_status_indicator_html(status == "online")
    
    return f"""
    <div class="streamer-card">
        <div class="streamer-info">
            <div>
                <h3 style="margin: 0 0 0.5rem 0; font-size: 1.2rem; font-weight: 600;">{streamer_name}</h3>
                <div style="margin-bottom: 0.5rem;">{platform_badges}</div>
                {status_indicator}
            </div>
        </div>
    </div>
    """