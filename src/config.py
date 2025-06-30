import json
import os
from typing import Dict, Any, Optional
from datetime import datetime

class Config:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.streamers_file = os.path.join(self.data_dir, "streamers.json")
        self.notifications_file = os.path.join(self.data_dir, "notifications.json")
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.browser_session_file = os.path.join(self.data_dir, "browser_session.json")
        
        self._load_config()
    
    def _load_config(self):
        self.default_streamers = {
            "아리사": {
                "chzzk_id": "4de764d9dad3b25602284be6db3ac647",
                "twitter_username": "Aesther_Arisa",
                "cafe_user_id": "cuEWXUyMqKzQGLwr3RwrXw",
                "cafe_club_id": "30919539",
                "enabled": True,
                "profile_image": None
            },
            "카린": {
                "chzzk_id": "32fb866e323242b770cdc790f991a6f6",
                "twitter_username": "aesther_karin",
                "cafe_user_id": "0eMme44p-arwLgz3wMo-3w",
                "cafe_club_id": "30919539",
                "enabled": True,
                "profile_image": None
            },
            "엘리": {
                "chzzk_id": "475313e6c26639d5763628313b4c130e",
                "twitter_username": "Bestwizardellie",
                "cafe_user_id": "blKmz6tKug60_5B_A_UNQA",
                "cafe_club_id": "30919539",
                "enabled": True,
                "profile_image": None
            },
            "에리스": {
                "chzzk_id": "17d8605fc37fb5ef49f5f67ae786fe4e",
                "twitter_username": "Aesther_Eris",
                "cafe_user_id": "7DjwjhrCoMP8DCw1623w3w",
                "cafe_club_id": "30919539",
                "enabled": True,
                "profile_image": None
            },
            "소풍왔니": {
                "chzzk_id": "089185efc29a8fbe14ea294dc85f9661",
                "twitter_username": "gomgomdru",
                "cafe_user_id": "GO7tGTwhLKbT-wGtJXyH3A",
                "cafe_club_id": "30288368",
                "enabled": True,
                "profile_image": None
            },
            "아라하시 타비": {
                "chzzk_id": "a6c4ddb09cdb160478996007bff35296",
                "twitter_username": "ArahashiTabi",
                "cafe_user_id": "3BcOWMiN3wPomGVkb8D_Nw",
                "cafe_club_id": "29424353",
                "enabled": True,
                "profile_image": None
            }
        }
        
        self.cafe_club_id = "30919539"
        self.nitter_instances = [
            "https://nitter.dashy.a3x.dn.nyx.im",
            "https://nitter.net",
            "https://nitter.it"
        ]
        
        self.default_settings = {
            "check_interval": 30,  # seconds
            "start_with_windows": True,
            "show_notifications": True,
            "notification_sound": True,
            "minimize_to_tray": True,
            "last_login_check": None,
            "theme": "dark"
        }
    
    def get_streamers(self) -> Dict[str, Any]:
        if os.path.exists(self.streamers_file):
            with open(self.streamers_file, 'r', encoding='utf-8') as f:
                streamers = json.load(f)
                # 기존 데이터에 cafe_club_id가 없는 경우 추가 (마이그레이션)
                updated = False
                for name, data in streamers.items():
                    if 'cafe_club_id' not in data and 'cafe_user_id' in data and data['cafe_user_id']:
                        data['cafe_club_id'] = self.cafe_club_id
                        updated = True
                
                # 업데이트된 경우 파일에 저장
                if updated:
                    self.save_streamers(streamers)
                
                return streamers
        else:
            self.save_streamers(self.default_streamers)
            return self.default_streamers
    
    def save_streamers(self, streamers: Dict[str, Any]):
        with open(self.streamers_file, 'w', encoding='utf-8') as f:
            json.dump(streamers, f, ensure_ascii=False, indent=2)
    
    def get_notifications(self) -> list:
        if os.path.exists(self.notifications_file):
            with open(self.notifications_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def save_notifications(self, notifications: list):
        with open(self.notifications_file, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
    
    def add_notification(self, streamer_name: str, notification_type: str, title: str, content: str, url: str):
        notifications = self.get_notifications()
        notification = {
            "id": len(notifications) + 1,
            "streamer_name": streamer_name,
            "type": notification_type,  # 'live', 'cafe', 'twitter'
            "title": title,
            "content": content,
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "read": False
        }
        notifications.insert(0, notification)  # 최신순으로 정렬
        
        # 최대 1000개까지만 저장 (메모리 관리)
        if len(notifications) > 1000:
            notifications = notifications[:1000]
        
        self.save_notifications(notifications)
        return notification
    
    def get_settings(self) -> Dict[str, Any]:
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # 기본 설정과 병합
                return {**self.default_settings, **settings}
        else:
            self.save_settings(self.default_settings)
            return self.default_settings
    
    def save_settings(self, settings: Dict[str, Any]):
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """설정 업데이트"""
        current_settings = self.get_settings()
        current_settings.update(new_settings)
        self.save_settings(current_settings)
    
    def get_browser_session(self) -> Optional[Dict[str, Any]]:
        if os.path.exists(self.browser_session_file):
            with open(self.browser_session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_browser_session(self, session_data: Dict[str, Any]):
        with open(self.browser_session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

# 전역 설정 인스턴스
config = Config()