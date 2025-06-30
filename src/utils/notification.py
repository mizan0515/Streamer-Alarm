import webbrowser
from win11toast import toast
from PIL import Image
import os
import tempfile
from typing import Optional
from ..utils.logger import logger
from .http_client import get_image_client

class NotificationManager:
    @staticmethod
    async def download_profile_image(url: str) -> Optional[str]:
        """프로필 이미지를 다운로드하고 임시 파일 경로 반환"""
        try:
            client = await get_image_client()
            response = await client.get(url)  # ← 들여쓰기 수정
            if response.status_code == 200:   # ← 들여쓰기 수정
                # 임시 파일 생성
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"profile_{hash(url)}.jpg")

                # 이미지 저장 및 크기 조정
                with open(temp_file, 'wb') as f:
                    f.write(response.content)

                # 이미지 크기 조정 (알림에 적합한 크기로)
                try:
                    with Image.open(temp_file) as img:
                        # RGBA를 RGB로 변환 (JPEG 호환성)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background

                        img = img.resize((80, 80), Image.Resampling.LANCZOS)
                        img.save(temp_file, "JPEG", quality=85)
                    return temp_file
                except Exception as e:
                    logger.warning(f"이미지 크기 조정 실패: {e}")
                    return temp_file
        except Exception as e:
            logger.error(f"프로필 이미지 다운로드 실패: {e}")
        return None
    
    @staticmethod
    def show_notification(title: str, message: str, url: str, image_path: Optional[str] = None):
        """win11toast를 사용한 간단한 클릭 가능 알림"""
        try:
            # win11toast의 on_click 매개변수 사용 (URL 직접 지정)
            toast(
                title,
                message,
                icon=image_path,
                duration="long",
                on_click=url  # URL 문자열 직접 지정 - 클릭 시 기본 브라우저에서 열림
            )
            logger.info(f"win11toast 알림 표시: {title} - {message}")
            
        except Exception as e:
            logger.warning(f"win11toast 실패: {e}, webbrowser로 폴백")
            try:
                # 간단한 toast (클릭 기능 없음)
                toast(
                    title,
                    f"{message}\n\n클릭해도 열리지 않습니다. 수동으로 URL을 열어주세요.",
                    icon=image_path,
                    duration="long"
                )
                logger.info(f"간단한 toast 알림 표시: {title} - {message}")
                
                # URL을 클립보드에 복사
                import subprocess
                try:
                    subprocess.run(['clip'], input=url.encode('utf-8'), check=True, 
                                 creationflags=subprocess.CREATE_NO_WINDOW)
                    logger.info(f"URL 클립보드 복사: {url}")
                except:
                    pass
                
            except Exception as e2:
                logger.error(f"모든 알림 방식 실패: {e2}")
                # 최후 수단: 직접 브라우저 열기
                try:
                    webbrowser.open(url)
                    logger.info(f"직접 브라우저 열기: {url}")
                except:
                    logger.info(f"알림 완전 실패, 수동으로 URL 열기: {url}")
                    print(f"[알림] {title}: {message}")
                    print(f"URL: {url}")
    
    @staticmethod
    async def show_live_notification(streamer_name: str, stream_title: str, chzzk_id: str, profile_image_url: Optional[str] = None):
        """방송 시작 알림"""
        title = f"{streamer_name} 방송 시작!"
        message = stream_title or "방송을 시작했습니다!"
        url = f"https://chzzk.naver.com/live/{chzzk_id}"
        
        image_path = None
        if profile_image_url:
            image_path = await NotificationManager.download_profile_image(profile_image_url)
        
        NotificationManager.show_notification(title, message, url, image_path)
    
    @staticmethod
    async def show_cafe_notification(streamer_name: str, post_title: str, post_url: str, profile_image_url: Optional[str] = None):
        """카페 새 글 알림"""
        title = f"{streamer_name} 카페 새 글"
        message = post_title
        
        image_path = None
        if profile_image_url:
            image_path = await NotificationManager.download_profile_image(profile_image_url)
        
        NotificationManager.show_notification(title, message, post_url, image_path)
    
    @staticmethod
    async def show_twitter_notification(streamer_name: str, tweet_content: str, tweet_url: str, profile_image_url: Optional[str] = None):
        """트위터 새 글 알림"""
        title = f"{streamer_name} 새 트윗"
        message = tweet_content[:100] + "..." if len(tweet_content) > 100 else tweet_content
        
        image_path = None
        if profile_image_url:
            image_path = await NotificationManager.download_profile_image(profile_image_url)
        
        NotificationManager.show_notification(title, message, tweet_url, image_path)