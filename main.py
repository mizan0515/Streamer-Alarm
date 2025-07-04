#!/usr/bin/env python3
"""
스트리머 알림 - Streamlit 버전
"""

import asyncio
import threading
import signal
import sys
import os
import subprocess
import webbrowser
import json
import time
import tempfile
import psutil
from typing import Optional
from datetime import datetime
import pystray
from PIL import Image, ImageDraw
from src.monitors.chzzk_monitor import chzzk_monitor
from src.monitors.twitter_monitor import twitter_monitor
from src.monitors.cafe_monitor import cafe_monitor
from src.utils.logger import logger
from src.config import config
from src.utils.cache_cleaner import cache_cleaner
from src.utils.http_client import close_all_clients


class StreamerAlarmApp:
    def __init__(self):
        self.tray_icon: Optional[pystray.Icon] = None
        self.streamlit_process: Optional[subprocess.Popen] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cache_cleanup_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_running = False
        self.last_cache_cleanup = 0
        self.lock_file_path = os.path.join(tempfile.gettempdir(), "streamer_alarm.lock")
        self.last_monitoring_time = time.time()
        self.sleep_detection_threshold = 120  # 2분 이상 간격이면 절전모드로 감지
    
    def is_already_running(self) -> bool:
        """다른 인스턴스가 이미 실행 중인지 확인"""
        try:
            if os.path.exists(self.lock_file_path):
                with open(self.lock_file_path, 'r') as f:
                    pid = int(f.read().strip())
                
                # PID가 유효한지 확인
                if psutil.pid_exists(pid):
                    try:
                        process = psutil.Process(pid)
                        # 프로세스 이름이 StreamerAlarm인지 확인
                        if 'StreamerAlarm' in process.name() or 'python' in process.name():
                            logger.warning(f"애플리케이션이 이미 실행 중입니다 (PID: {pid})")
                            return True
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # 유효하지 않은 PID인 경우 락 파일 삭제
                os.remove(self.lock_file_path)
            
            return False
            
        except Exception as e:
            logger.debug(f"중복 실행 체크 중 오류 (무시됨): {e}")
            return False
    
    def create_lock_file(self) -> bool:
        """락 파일 생성"""
        try:
            with open(self.lock_file_path, 'w') as f:
                f.write(str(os.getpid()))
            logger.debug(f"락 파일 생성: {self.lock_file_path}")
            return True
        except Exception as e:
            logger.error(f"락 파일 생성 실패: {e}")
            return False
    
    def remove_lock_file(self):
        """락 파일 제거"""
        try:
            if os.path.exists(self.lock_file_path):
                os.remove(self.lock_file_path)
                logger.debug("락 파일 제거됨")
        except Exception as e:
            logger.debug(f"락 파일 제거 중 오류 (무시됨): {e}")
        
    def create_tray_icon(self) -> Image.Image:
        """시스템 트레이 아이콘 생성"""
        image = Image.new('RGB', (64, 64), color='red')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 20), "📺", fill='black')
        return image
    
    def start_streamlit_server(self):
        """Streamlit 서버 시작"""
        try:
            # 프로젝트 루트 디렉토리 확정 (main.py가 있는 디렉토리)
            project_root = os.path.dirname(os.path.abspath(__file__))
            streamlit_script = os.path.join(project_root, "streamlit_run.py")
            
            # PyInstaller 환경에서 실행 시 절대 경로 사용
            if getattr(sys, 'frozen', False):
                # PyInstaller로 빌드된 실행 파일인 경우
                project_root = os.path.dirname(sys.executable)
                streamlit_script = os.path.join(sys._MEIPASS, "streamlit_run.py")
                python_executable = sys.executable
            else:
                # 일반 Python 스크립트 실행인 경우
                python_executable = sys.executable
            
            # Streamlit 실행
            cmd = [
                python_executable, "-m", "streamlit", "run", 
                streamlit_script,
                "--server.port=8501",
                "--server.headless=true",
                "--server.address=localhost",
                "--browser.gatherUsageStats=false"
            ]
            
            # PyInstaller 환경에서는 창 숨김 옵션 추가
            creation_flags = 0
            if getattr(sys, 'frozen', False):
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            self.streamlit_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_root,
                creationflags=creation_flags
            )
            
            logger.info("Streamlit 서버가 시작되었습니다 (http://localhost:8501)")
            return True
            
        except Exception as e:
            logger.error(f"Streamlit 서버 시작 실패: {e}")
            return False
    
    def stop_streamlit_server(self):
        """Streamlit 서버 중지"""
        if self.streamlit_process:
            try:
                self.streamlit_process.terminate()
                self.streamlit_process.wait(timeout=5)
                logger.info("Streamlit 서버가 중지되었습니다")
            except subprocess.TimeoutExpired:
                self.streamlit_process.kill()
                logger.warning("Streamlit 서버를 강제 종료했습니다")
            except Exception as e:
                logger.error(f"Streamlit 서버 중지 중 오류: {e}")
            finally:
                self.streamlit_process = None
    
    def open_web_interface(self, icon=None, item=None):
        """웹 인터페이스 열기"""
        # 미사용 매개변수 처리
        _ = icon, item
        
        try:
            webbrowser.open("http://localhost:8501")
            logger.info("웹 인터페이스를 열었습니다")
        except Exception as e:
            logger.error(f"웹 인터페이스 열기 실패: {e}")
    
    def show_status(self, icon=None, item=None):
        """상태 표시"""
        # 미사용 매개변수 처리
        _ = icon, item
        
        streamers = config.get_streamers()
        active_count = sum(1 for data in streamers.values() if data.get('enabled', True))
        
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()  # 메인 윈도우 숨기기
        
        status_msg = f"""스트리머 알림 상태

등록된 스트리머: {len(streamers)}개
활성 스트리머: {active_count}개
모니터링 상태: {'실행중' if self.is_running else '중지됨'}

웹 인터페이스: http://localhost:8501"""
        
        messagebox.showinfo("스트리머 알림 상태", status_msg)
        root.destroy()
    
    def quit_app(self, icon=None, item=None):
        """애플리케이션 종료"""
        # 미사용 매개변수 처리
        _ = icon, item
        
        logger.info("애플리케이션 종료 중...")
        self.is_running = False
        
        # 모니터링 태스크 취소
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        
        # 캐시 정리 태스크 취소
        if self.cache_cleanup_task and not self.cache_cleanup_task.done():
            self.cache_cleanup_task.cancel()
        
        # Streamlit 서버 중지
        self.stop_streamlit_server()
        
        # 트레이 아이콘 제거
        if self.tray_icon:
            self.tray_icon.stop()
        
        # 락 파일 제거
        self.remove_lock_file()
        
        # 이벤트 루프 중지
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        sys.exit(0)
    
    def create_tray_menu(self):
        """트레이 메뉴 생성"""
        return pystray.Menu(
            pystray.MenuItem("웹 인터페이스 열기", self.open_web_interface, default=True),
            pystray.MenuItem("상태 보기", self.show_status),
            pystray.MenuItem("네이버 로그인", self.naver_login),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self.quit_app)
        )
    
    def naver_login(self, icon=None, item=None):
        """네이버 로그인"""
        # 미사용 매개변수 처리
        _ = icon, item
        
        try:
            from src.browser.naver_session import naver_session
            import threading
            
            def run_login():
                try:
                    import asyncio
                    logger.info("네이버 로그인 스레드 시작")
                    
                    # 새 이벤트 루프 생성 (기존 루프와 충돌 방지)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # 시스템 트레이에서 로그인 버튼을 클릭한 경우 항상 브라우저 창을 표시
                        logger.info("시스템 트레이에서 네이버 로그인 요청 - 브라우저 창을 표시합니다.")
                        
                        # 타임아웃 적용
                        try:
                            login_task = naver_session.login(force_visible=True)
                            result = loop.run_until_complete(asyncio.wait_for(login_task, timeout=30.0))
                            logger.info(f"시스템 트레이 로그인 완료, 결과: {result}")
                        except asyncio.TimeoutError:
                            logger.error("시스템 트레이 네이버 로그인 타임아웃 (30초)")
                            result = False
                        
                        if result:
                            logger.info("네이버 로그인 성공")
                        else:
                            logger.warning("네이버 로그인 실패 또는 취소됨")
                            
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"네이버 로그인 스레드 오류: {e}")
            
            login_thread = threading.Thread(target=run_login, daemon=True)
            login_thread.start()
            logger.info("네이버 로그인 요청됨")
            
        except Exception as e:
            logger.error(f"네이버 로그인 시작 실패: {e}")
    
    def setup_tray_icon(self):
        """시스템 트레이 아이콘 설정"""
        try:
            image = self.create_tray_icon()
            menu = self.create_tray_menu()
            
            self.tray_icon = pystray.Icon(
                "streamer_alarm",
                image,
                "스트리머 알림",
                menu
            )
            
            # 별도 스레드에서 트레이 아이콘 실행
            tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            tray_thread.start()
            
            logger.info("시스템 트레이 아이콘이 생성되었습니다")
            return True
            
        except Exception as e:
            logger.error(f"트레이 아이콘 생성 실패: {e}")
            return False
    
    async def monitor_all_platforms(self):
        """모든 플랫폼 모니터링 - UI 신호 처리 빈도 개선 및 절전모드 복구 감지"""
        first_run = True
        current_interval = config.get_settings().get('check_interval', 30)
        last_monitoring_time = asyncio.get_event_loop().time()
        
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                
                # 절전모드 복구 감지 (실제 시간과 마지막 모니터링 시간 비교)
                actual_time = time.time()
                time_gap = actual_time - self.last_monitoring_time
                
                if time_gap > self.sleep_detection_threshold:
                    logger.warning(f"⚠️ 절전모드 복구 감지: {time_gap:.1f}초 간격 ({time_gap/60:.1f}분)")
                    
                    # 절전모드 복구 후 누락 알림 복구 실행
                    try:
                        await self.recover_missed_notifications(startup=False, sleep_recovery=True)
                    except Exception as recovery_error:
                        logger.error(f"절전모드 복구 후 누락 알림 복구 실패: {recovery_error}")
                
                # UI 신호는 항상 확인 (응답성 향상)
                await self.check_ui_signals()
                
                # 모니터링은 설정된 간격에 따라 실행
                if current_time - last_monitoring_time >= current_interval:
                    # 병렬로 모든 모니터링 실행
                    await asyncio.gather(
                        chzzk_monitor.check_all_streamers(),
                        twitter_monitor.check_all_streamers(),
                        cafe_monitor.check_all_streamers(),
                        return_exceptions=True
                    )
                    
                    last_monitoring_time = current_time
                    self.last_monitoring_time = actual_time  # 실제 시간 업데이트
                    
                    # 첫 번째 실행 후 first_check 완료 표시
                    if first_run:
                        # 10초 후에 첫 번째 체크 완료 표시
                        await asyncio.sleep(10)
                        cafe_monitor.mark_first_check_complete()
                        twitter_monitor.mark_first_check_complete()
                        logger.info("첫 번째 모니터링 체크 완료 - 이제 새 알림을 감지합니다")
                        first_run = False
                
                # 현재 설정된 간격 가져오기 (실시간 반영)
                new_interval = config.get_settings().get('check_interval', 30)
                if new_interval != current_interval:
                    current_interval = new_interval
                    logger.info(f"모니터링 간격이 {current_interval}초로 변경되었습니다")
                
                # UI 신호 처리를 위해 짧은 간격으로 대기 (2초)
                await asyncio.sleep(2)
                
            except asyncio.CancelledError:
                logger.info("모니터링이 취소되었습니다")
                break
            except Exception as e:
                logger.error(f"모니터링 중 오류 발생: {e}")
                await asyncio.sleep(5)  # 오류 발생 시 짧은 지연 후 재시도
    
    async def async_main(self):
        """비동기 메인 함수"""
        logger.info("스트리머 알림 애플리케이션 시작")
        
        try:
            # 네이버 세션 초기화 (백그라운드에서)
            await self.initialize_naver_session()
            
            # 누락된 알림 복구 (앱 시작 시)
            await self.recover_missed_notifications(startup=True)
            
            # 모니터링 시작
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self.monitor_all_platforms())
            
            # 캐시 정리 태스크 시작
            self.cache_cleanup_task = asyncio.create_task(self.periodic_cache_cleanup())
            
            # 프로그램이 종료될 때까지 대기
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단되었습니다")
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
        finally:
            self.is_running = False
            if self.monitoring_task and not self.monitoring_task.done():
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            
            # 캐시 정리 태스크 취소
            if self.cache_cleanup_task and not self.cache_cleanup_task.done():
                self.cache_cleanup_task.cancel()
                try:
                    await self.cache_cleanup_task
                except asyncio.CancelledError:
                    pass
    
    def run(self):
        """애플리케이션 실행"""
        # 중복 실행 체크
        if self.is_already_running():
            logger.error("애플리케이션이 이미 실행 중입니다. 종료합니다.")
            return
        
        # 락 파일 생성
        if not self.create_lock_file():
            logger.error("락 파일 생성에 실패했습니다. 종료합니다.")
            return
        
        # 신호 핸들러 설정
        def signal_handler(signum, frame):
            # 미사용 매개변수 처리
            _ = frame
            logger.info(f"신호 {signum} 수신, 종료 중...")
            self.quit_app()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Streamlit 서버 시작
        if not self.start_streamlit_server():
            logger.error("Streamlit 서버를 시작할 수 없습니다")
            return
        
        # 시스템 트레이 아이콘 설정
        if not self.setup_tray_icon():
            logger.error("시스템 트레이 아이콘을 생성할 수 없습니다")
            self.stop_streamlit_server()
            return
        
        # 웹 인터페이스 자동 열기 (첫 실행시)
        import time
        time.sleep(3)  # Streamlit 서버가 완전히 시작될 때까지 대기
        self.open_web_interface()
        
        # 이벤트 루프 실행
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.async_main())
        except KeyboardInterrupt:
            logger.info("키보드 인터럽트로 종료")
        finally:
            if self.loop:
                try:
                    # 남은 태스크들 정리
                    pending = asyncio.all_tasks(self.loop)
                    for task in pending:
                        task.cancel()
                    
                    if pending:
                        self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        
                except Exception as e:
                    logger.error(f"이벤트 루프 정리 중 오류: {e}")
                finally:
                    self.loop.close()
            
            self.stop_streamlit_server()
            self.remove_lock_file()

    async def initialize_naver_session(self):
        """네이버 세션 초기화"""
        try:
            from src.browser.naver_session import naver_session
            
            logger.info("네이버 세션 초기화 시작")
            
            # 저장된 세션 로드 시도
            if await naver_session.load_session():
                logger.info("저장된 네이버 세션 로드 성공")
                return True
            
            logger.info("저장된 세션이 없거나 유효하지 않음")
            return False
            
        except Exception as e:
            logger.warning(f"네이버 세션 초기화 실패: {e}")
            return False

    async def recover_missed_notifications(self, startup=False, sleep_recovery=False):
        """누락된 알림 복구"""
        try:
            from src.utils.missed_notification_recovery import missed_notification_recovery
            
            if startup:
                logger.info("📢 앱 시작 시 누락된 알림 복구 시작")
            elif sleep_recovery:
                logger.info("🛌 절전모드 복구 후 누락된 알림 복구 시작")
            else:
                logger.info("📢 수동 요청으로 누락된 알림 복구 시작")
            
            # 복구 프로세스 실행 (타임아웃 적용)
            recovery_stats = await asyncio.wait_for(
                missed_notification_recovery.recover_missed_notifications(),
                timeout=300.0  # 5분 타임아웃
            )
            
            total_recovered = sum(recovery_stats.values())
            if total_recovered > 0:
                logger.info(f"✅ 누락 알림 복구 완료: 총 {total_recovered}개 (카페: {recovery_stats.get('cafe', 0)}, 트위터: {recovery_stats.get('twitter', 0)})")
                
                # 복구 완료 시스템 알림
                from src.utils.notification import NotificationManager
                if startup:
                    NotificationManager.show_notification(
                        "📢 알림 복구 완료",
                        f"앱이 꺼져있던 동안 놓친 {total_recovered}개의 알림을 복구했습니다."
                    )
                elif sleep_recovery:
                    NotificationManager.show_notification(
                        "🛌 절전모드 복구 완료",
                        f"절전모드 동안 놓친 {total_recovered}개의 알림을 복구했습니다."
                    )
                else:
                    NotificationManager.show_notification(
                        "📢 수동 알림 복구 완료",
                        f"수동 요청으로 {total_recovered}개의 누락된 알림을 복구했습니다."
                    )
            else:
                logger.info("✅ 누락된 알림이 없습니다")
                
        except asyncio.TimeoutError:
            logger.error("❌ 누락 알림 복구 타임아웃 (5분)")
        except Exception as e:
            logger.error(f"❌ 누락 알림 복구 실패: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")

    async def check_ui_signals(self):
        """UI로부터의 신호 확인 및 처리"""
        try:
            # 로그인 요청 확인
            login_request_file = os.path.join(config.data_dir, "login_request.json")
            if os.path.exists(login_request_file):
                logger.debug(f"📋 UI 로그인 요청 파일 발견: {login_request_file}")
                try:
                    with open(login_request_file, 'r', encoding='utf-8') as f:
                        request_data = json.load(f)
                    
                    logger.debug(f"📄 요청 데이터: {request_data}")
                    
                    if request_data.get('action') == 'relogin_naver' and request_data.get('status') == 'requested':
                        request_id = request_data.get('request_id', 'unknown')
                        source = request_data.get('source', 'unknown')
                        logger.info(f"🎯 UI로부터 네이버 재로그인 요청 수신 (ID: {request_id}, Source: {source})")
                        
                        # 즉시 처리 중 상태로 변경 (중복 처리 방지)
                        request_data['status'] = 'processing'
                        request_data['processing_started'] = datetime.now().isoformat()
                        
                        # 안전한 파일 쓰기
                        self._safe_write_json(login_request_file, request_data)
                        logger.debug(f"📝 요청 상태를 'processing'으로 업데이트 (ID: {request_id})")
                        
                        # 네이버 로그인 실행 (별도 스레드에서)
                        login_thread = threading.Thread(target=self.handle_naver_login_request, args=(request_data,), daemon=True)
                        login_thread.start()
                        logger.info(f"🚀 로그인 처리 스레드 시작됨 (ID: {request_id})")
                        
                    else:
                        logger.debug(f"📋 요청이 처리 조건에 맞지 않음: action={request_data.get('action')}, status={request_data.get('status')}")
                        
                except Exception as e:
                    logger.warning(f"💥 로그인 요청 처리 실패: {e}")
                    import traceback
                    logger.debug(f"요청 처리 오류 스택트레이스:\n{traceback.format_exc()}")
                    # 오류 발생 시 요청 파일 삭제
                    try:
                        os.remove(login_request_file)
                        logger.debug("🗑️ 오류 발생으로 요청 파일 삭제")
                    except:
                        pass
            
            # 설정 업데이트 신호 확인
            settings_update_file = os.path.join(config.data_dir, "settings_update.json")
            if os.path.exists(settings_update_file):
                try:
                    with open(settings_update_file, 'r', encoding='utf-8') as f:
                        update_data = json.load(f)
                    
                    if update_data.get('action') == 'update_check_interval':
                        new_interval = update_data.get('new_interval', 30)
                        logger.info(f"UI로부터 체크 간격 변경 요청: {new_interval}초")
                        
                        # 설정 파일 업데이트는 이미 UI에서 완료됨
                        # 메인 프로세스는 다음 루프에서 새 설정을 읽어옴
                        
                        # 신호 파일 삭제
                        os.remove(settings_update_file)
                        
                except Exception as e:
                    logger.warning(f"설정 업데이트 신호 처리 실패: {e}")
                    try:
                        os.remove(settings_update_file)
                    except:
                        pass
            
            # 알림 테스트 요청 확인
            notification_test_file = os.path.join(config.data_dir, "notification_test.json")
            if os.path.exists(notification_test_file):
                try:
                    with open(notification_test_file, 'r', encoding='utf-8') as f:
                        test_data = json.load(f)
                    
                    if test_data.get('action') == 'test_notification' and test_data.get('status') == 'requested':
                        test_id = test_data.get('test_id', 'unknown')
                        logger.info(f"UI로부터 알림 테스트 요청 수신 (ID: {test_id})")
                        
                        # 즉시 처리 중 상태로 변경 (중복 처리 방지)
                        test_data['status'] = 'processing'
                        test_data['processing_started'] = datetime.now().isoformat()
                        
                        # 안전한 파일 쓰기
                        self._safe_write_json(notification_test_file, test_data)
                        
                        # 알림 테스트 실행 (별도 스레드에서)
                        threading.Thread(target=self.handle_notification_test_request, args=(test_data.copy(),), daemon=True).start()
                        
                except Exception as e:
                    logger.warning(f"알림 테스트 요청 처리 실패: {e}")
                    try:
                        os.remove(notification_test_file)
                    except:
                        pass
            
            # 누락 알림 복구 요청 처리
            missed_recovery_file = os.path.join(config.data_dir, "missed_recovery_request.json")
            if os.path.exists(missed_recovery_file):
                try:
                    with open(missed_recovery_file, 'r', encoding='utf-8') as f:
                        recovery_data = json.load(f)
                    
                    if recovery_data.get('action') == 'recover_missed_notifications' and recovery_data.get('status') == 'requested':
                        recovery_id = recovery_data.get('timestamp', 'unknown')
                        source = recovery_data.get('source', 'unknown')
                        logger.info(f"UI로부터 누락 알림 복구 요청 수신 (ID: {recovery_id}, Source: {source})")
                        
                        # 즉시 처리 중 상태로 변경
                        recovery_data['status'] = 'processing'
                        recovery_data['processing_started'] = datetime.now().isoformat()
                        
                        self._safe_write_json(missed_recovery_file, recovery_data)
                        
                        # 누락 알림 복구 실행 (별도 스레드에서)
                        recovery_thread = threading.Thread(target=self.handle_missed_recovery_request, args=(recovery_data,), daemon=True)
                        recovery_thread.start()
                        logger.info(f"누락 알림 복구 처리 스레드 시작됨 (ID: {recovery_id})")
                        
                except Exception as e:
                    logger.warning(f"누락 알림 복구 요청 처리 실패: {e}")
                    try:
                        os.remove(missed_recovery_file)
                    except:
                        pass
            
                        
        except Exception as e:
            logger.debug(f"UI 신호 확인 중 오류 (무시됨): {e}")
    
    async def periodic_cache_cleanup(self):
        """주기적 캐시 정리 (설정 파일 기반)"""
        cache_cleanup_interval = config.get_settings().get('cache_cleanup_interval', 3600)  # 기본 1시간
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # 캐시 정리 간격 확인
                if current_time - self.last_cache_cleanup >= cache_cleanup_interval:
                    logger.info("주기적 캐시 정리 시작")
                    
                    try:
                        # 비동기 캐시 정리 실행
                        success, result = await cache_cleaner.cleanup_all()
                        
                        if success:
                            logger.info(f"캐시 정리 완료: 브라우저 캐시 {result['cache_freed_mb']}MB, 임시파일 {result['temp_deleted']}개")
                        else:
                            logger.warning("일부 캐시 정리 작업에서 오류 발생")
                            
                        self.last_cache_cleanup = current_time
                        
                    except Exception as cleanup_error:
                        logger.error(f"캐시 정리 중 오류: {cleanup_error}")
                        # 오류 발생 시에도 타이머 업데이트 (무한 재시도 방지)
                        self.last_cache_cleanup = current_time
                
                # 10분마다 캐시 정리 필요 여부 확인
                await asyncio.sleep(600)
                
            except asyncio.CancelledError:
                logger.info("캐시 정리 태스크가 취소되었습니다")
                break
            except Exception as e:
                logger.error(f"캐시 정리 태스크 중 오류: {e}")
                await asyncio.sleep(300)  # 오류 발생 시 5분 후 재시도
    
    def handle_naver_login_request(self, request_data):
        """네이버 로그인 요청 처리 (별도 스레드) - 개선된 버전"""
        login_request_file = os.path.join(config.data_dir, "login_request.json")
        request_id = request_data.get('request_id', 'unknown')
        
        logger.info(f"네이버 로그인 요청 처리 시작 (ID: {request_id})")
        
        try:
            from src.browser.naver_session import naver_session
            
            # 처리 시작 상태로 업데이트 (이미 매개변수로 받은 데이터 사용)
            try:
                request_data['status'] = 'processing'
                request_data['processing_started'] = datetime.now().isoformat()
                
                with open(login_request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"로그인 요청 상태를 processing으로 업데이트 (ID: {request_id})")
            except Exception as e:
                logger.warning(f"로그인 요청 상태 업데이트 실패 (ID: {request_id}): {e}")
            
            # 새 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 요청 소스 확인
                request_source = request_data.get('source', 'unknown')
                logger.info(f"🔍 네이버 로그인 요청 소스: {request_source}")
                logger.info("🚀 시스템 트레이와 동일한 방식으로 처리 시작")
                logger.info("🎯 로그인 상태 확인 건너뛰고 즉시 브라우저 창 표시")
                
                try:
                    login_start_time = time.time()
                    logger.info("🌐 force_visible=True로 네이버 로그인 호출 시작")
                    logger.debug(f"naver_session 인스턴스: {naver_session}")
                    
                    # 헤드리스 모드 해제하여 로그인 창 표시 (타임아웃 적용)
                    login_task = naver_session.login(force_visible=True)
                    result = loop.run_until_complete(asyncio.wait_for(login_task, timeout=30.0))
                    
                    login_duration = time.time() - login_start_time
                    logger.info(f"🌐 네이버 로그인 호출 완료: {result} (소요시간: {login_duration:.2f}초)")
                    
                except asyncio.TimeoutError:
                    login_duration = time.time() - login_start_time
                    logger.error(f"⏰ 네이버 로그인 호출 타임아웃 (30초, 실제: {login_duration:.2f}초)")
                    result = False
                except Exception as e:
                    login_duration = time.time() - login_start_time
                    logger.error(f"💥 네이버 로그인 처리 중 오류: {e} (소요시간: {login_duration:.2f}초)")
                    import traceback
                    logger.debug(f"로그인 오류 스택트레이스:\n{traceback.format_exc()}")
                    result = False
                
                # 결과에 따른 상태 업데이트
                try:
                    if result:
                        logger.info("✅ 네이버 로그인 성공 - 세션 사용 검증 시작")
                        
                        # 로그인 성공 후 즉시 카페 접근 테스트
                        cafe_test_result = loop.run_until_complete(
                            self._test_cafe_session_access(loop, naver_session, request_id)
                        )
                        
                        request_data['status'] = 'completed'
                        request_data['completed_at'] = datetime.now().isoformat()
                        request_data['message'] = '로그인 성공'
                        request_data['cafe_test_result'] = cafe_test_result
                    else:
                        logger.warning("❌ 네이버 로그인 실패 또는 취소됨")
                        request_data['status'] = 'failed'
                        request_data['failed_at'] = datetime.now().isoformat()
                        request_data['error'] = '로그인 실패 또는 사용자 취소'
                    
                    with open(login_request_file, 'w', encoding='utf-8') as f:
                        json.dump(request_data, f, ensure_ascii=False, indent=2)
                    
                    # 5초 후 파일 정리
                    def cleanup():
                        import time
                        time.sleep(5)
                        try:
                            if os.path.exists(login_request_file):
                                os.remove(login_request_file)
                        except:
                            pass
                    
                    threading.Thread(target=cleanup, daemon=True).start()
                    
                except Exception as e:
                    logger.warning(f"로그인 결과 파일 업데이트 실패: {e}")
                    
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"네이버 로그인 스레드 오류 (ID: {request_id}): {e}")
            import traceback
            logger.error(f"네이버 로그인 스레드 오류 상세 (ID: {request_id}):\n{traceback.format_exc()}")
            
            # 오류 상태로 업데이트 (매개변수로 받은 데이터 사용)
            try:
                request_data['status'] = 'failed'
                request_data['failed_at'] = datetime.now().isoformat()
                request_data['error'] = f'로그인 스레드 오류: {str(e)}'
                
                with open(login_request_file, 'w', encoding='utf-8') as f:
                    json.dump(request_data, f, ensure_ascii=False, indent=2)
                    
                logger.info(f"로그인 요청 실패 상태로 업데이트 완료 (ID: {request_id})")
                    
                # 3초 후 파일 삭제
                def cleanup():
                    import time
                    time.sleep(3)
                    try:
                        if os.path.exists(login_request_file):
                            os.remove(login_request_file)
                    except:
                        pass
                
                threading.Thread(target=cleanup, daemon=True).start()
                
            except:
                # 최후 수단으로 파일 삭제
                try:
                    os.remove(login_request_file)
                except:
                    pass
    
    async def _test_cafe_session_access(self, loop, naver_session, request_id):
        """로그인 후 카페 세션 접근 테스트"""
        test_start = time.time()
        logger.info(f"🧪 카페 세션 접근 테스트 시작 (ID: {request_id})")
        
        try:
            # 기본 스트리머 설정에서 카페 ID가 있는 스트리머 찾기
            streamers = config.get_streamers()
            test_streamer = None
            test_cafe_id = None
            test_user_id = None
            
            logger.debug("카페 모니터링 가능한 스트리머 검색 중...")
            for name, data in streamers.items():
                if data.get('enabled', True) and data.get('cafe_user_id'):
                    test_streamer = name
                    test_cafe_id = data.get('cafe_club_id', config.cafe_club_id)
                    test_user_id = data['cafe_user_id']
                    logger.debug(f"테스트 대상 선정: {test_streamer} (cafe_id: {test_cafe_id}, user_id: {test_user_id})")
                    break
            
            if not test_streamer:
                logger.warning("❌ 카페 모니터링 설정된 스트리머 없음 - 세션 테스트 건너뜀")
                return {
                    "success": False,
                    "reason": "no_cafe_streamers",
                    "message": "카페 모니터링 설정된 스트리머 없음"
                }
            
            logger.info(f"🎯 카페 접근 테스트 대상: {test_streamer}")
            
            # 카페 접근 테스트 실행
            try:
                cafe_test_start = time.time()
                logger.debug("naver_session.get_cafe_posts() 호출 시작...")
                
                # asyncio 루프에서 실행
                posts = loop.run_until_complete(
                    asyncio.wait_for(
                        naver_session.get_cafe_posts(test_cafe_id, test_user_id),
                        timeout=10.0
                    )
                )
                
                cafe_test_time = time.time() - cafe_test_start
                
                if posts is not None:
                    posts_count = len(posts) if isinstance(posts, list) else 0
                    logger.info(f"✅ 카페 접근 성공: {posts_count}개 게시물 조회 (소요시간: {cafe_test_time:.2f}초)")
                    
                    # 게시물 정보 상세 로깅
                    if posts_count > 0:
                        latest_post = posts[0]
                        logger.debug(f"최신 게시물: {latest_post.get('title', 'N/A')[:30]}...")
                    
                    test_result = {
                        "success": True,
                        "posts_count": posts_count,
                        "test_duration": cafe_test_time,
                        "streamer": test_streamer,
                        "message": f"카페 접근 성공 ({posts_count}개 게시물)"
                    }
                else:
                    logger.warning(f"⚠️ 카페 접근 실패: None 반환 (소요시간: {cafe_test_time:.2f}초)")
                    test_result = {
                        "success": False,
                        "reason": "posts_none",
                        "test_duration": cafe_test_time,
                        "streamer": test_streamer,
                        "message": "카페 게시물 조회 실패 (None 반환)"
                    }
                    
            except asyncio.TimeoutError:
                cafe_test_time = time.time() - cafe_test_start
                logger.error(f"⏰ 카페 접근 테스트 타임아웃 (10초, 실제: {cafe_test_time:.2f}초)")
                test_result = {
                    "success": False,
                    "reason": "timeout",
                    "test_duration": cafe_test_time,
                    "streamer": test_streamer,
                    "message": "카페 접근 타임아웃"
                }
            except Exception as cafe_error:
                cafe_test_time = time.time() - cafe_test_start
                logger.error(f"💥 카페 접근 테스트 오류: {cafe_error} (소요시간: {cafe_test_time:.2f}초)")
                test_result = {
                    "success": False,
                    "reason": "error",
                    "error": str(cafe_error),
                    "test_duration": cafe_test_time,
                    "streamer": test_streamer,
                    "message": f"카페 접근 오류: {str(cafe_error)}"
                }
            
            total_test_time = time.time() - test_start
            test_result["total_duration"] = total_test_time
            
            logger.info(f"🧪 카페 세션 접근 테스트 완료: {test_result['success']} (총 소요시간: {total_test_time:.2f}초)")
            return test_result
            
        except Exception as e:
            total_test_time = time.time() - test_start
            logger.error(f"💥 카페 세션 테스트 전체 실패: {e} (소요시간: {total_test_time:.2f}초)")
            return {
                "success": False,
                "reason": "test_error",
                "error": str(e),
                "total_duration": total_test_time,
                "message": f"세션 테스트 실패: {str(e)}"
            }

    def handle_notification_test_request(self, test_data):
        """알림 테스트 요청 처리 (별도 스레드) - 개선된 버전"""
        notification_test_file = os.path.join(config.data_dir, "notification_test.json")
        test_id = test_data.get('test_id', 'unknown')
        
        try:
            from src.utils.notification import NotificationManager
            
            # 중복 처리 방지 - 이미 완료된 테스트인지 확인
            if test_data.get('status') in ['completed', 'failed']:
                logger.warning(f"이미 처리된 알림 테스트 요청 무시 (ID: {test_id})")
                return
            
            title = test_data.get('title', '🔔 테스트 알림')
            message = test_data.get('message', '알림 테스트입니다!')
            url = test_data.get('url', 'https://github.com/anthropics/claude-code')
            
            logger.info(f"알림 테스트 시작 (ID: {test_id})")
            
            # NotificationManager를 사용하여 실제 알림 발송
            try:
                NotificationManager.show_notification(title, message, url)
                logger.info(f"알림 발송 성공 (ID: {test_id})")
                
                # 성공 상태로 파일 업데이트
                test_data['status'] = 'completed'
                test_data['completed_at'] = datetime.now().isoformat()
                test_data['notification_sent'] = True
                test_data['success_message'] = '데스크톱 알림이 성공적으로 발송되었습니다.'
                
            except Exception as notification_error:
                logger.error(f"알림 발송 실패 (ID: {test_id}): {notification_error}")
                
                # 실패 상태로 파일 업데이트  
                test_data['status'] = 'failed'
                test_data['failed_at'] = datetime.now().isoformat()
                test_data['notification_sent'] = False
                test_data['error'] = f'알림 발송 실패: {str(notification_error)}'
            
            # 안전한 파일 쓰기 (성공/실패 무관하게 실행)
            try:
                self._safe_write_json(notification_test_file, test_data)
                logger.info(f"알림 테스트 상태 파일 업데이트 완료 (ID: {test_id}, 상태: {test_data['status']})")
            except Exception as file_error:
                logger.error(f"알림 테스트 상태 파일 쓰기 실패 (ID: {test_id}): {file_error}")
                # 파일 쓰기 실패 시 직접 쓰기 재시도
                try:
                    with open(notification_test_file, 'w', encoding='utf-8') as f:
                        json.dump(test_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"알림 테스트 상태 파일 직접 쓰기 성공 (ID: {test_id})")
                except Exception as direct_write_error:
                    logger.error(f"알림 테스트 상태 파일 직접 쓰기도 실패 (ID: {test_id}): {direct_write_error}")
            
            logger.info(f"알림 테스트 처리 완료 - NotificationManager 사용 (ID: {test_id})")
            
            # 3초 후 파일 삭제 (UI 응답성 개선)
            def cleanup():
                import time
                time.sleep(3)
                try:
                    if os.path.exists(notification_test_file):
                        os.remove(notification_test_file)
                        logger.debug(f"알림 테스트 결과 파일 정리 완료 (ID: {test_id})")
                except:
                    pass
            
            threading.Thread(target=cleanup, daemon=True).start()
            
        except Exception as e:
            logger.error(f"알림 테스트 처리 중 오류: {e}")
            
            # 실패 상태로 파일 업데이트
            try:
                notification_test_file = os.path.join(config.data_dir, "notification_test.json")
                test_data['status'] = 'failed'
                test_data['error'] = str(e)
                test_data['failed_at'] = datetime.now().isoformat()
                
                with open(notification_test_file, 'w', encoding='utf-8') as f:
                    json.dump(test_data, f, ensure_ascii=False, indent=2)
                    
                # 5초 후 파일 삭제
                def cleanup():
                    import time
                    time.sleep(5)
                    try:
                        if os.path.exists(notification_test_file):
                            os.remove(notification_test_file)
                    except:
                        pass
                
                threading.Thread(target=cleanup, daemon=True).start()
                
            except:
                # 파일 처리도 실패한 경우 그냥 삭제
                try:
                    notification_test_file = os.path.join(config.data_dir, "notification_test.json")
                    os.remove(notification_test_file)
                except:
                    pass


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

    def handle_missed_recovery_request(self, recovery_data):
        """누락 알림 복구 요청 처리 (별도 스레드)"""
        missed_recovery_file = os.path.join(config.data_dir, "missed_recovery_request.json")
        recovery_id = recovery_data.get('timestamp', 'unknown')
        
        try:
            logger.info(f"누락 알림 복구 요청 처리 시작 (ID: {recovery_id})")
            
            # 새 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                from src.utils.missed_notification_recovery import missed_notification_recovery
                
                # 복구 프로세스 실행
                recovery_stats = loop.run_until_complete(
                    asyncio.wait_for(
                        missed_notification_recovery.recover_missed_notifications(),
                        timeout=300.0  # 5분 타임아웃
                    )
                )
                
                total_recovered = sum(recovery_stats.values())
                
                logger.info(f"누락 알림 복구 완료: 총 {total_recovered}개 (카페: {recovery_stats.get('cafe', 0)}, 트위터: {recovery_stats.get('twitter', 0)})")
                
                # 복구 완료 시스템 알림
                if total_recovered > 0:
                    from src.utils.notification import NotificationManager
                    NotificationManager.show_notification(
                        "📢 알림 복구 완료",
                        f"수동 요청으로 {total_recovered}개의 누락된 알림을 복구했습니다."
                    )
                
            except asyncio.TimeoutError:
                logger.error(f"누락 알림 복구 타임아웃 (5분) - ID: {recovery_id}")
            except Exception as recovery_error:
                logger.error(f"누락 알림 복구 중 오류: {recovery_error}")
            finally:
                loop.close()
            
            # 요청 파일 삭제
            try:
                os.remove(missed_recovery_file)
                logger.debug(f"누락 알림 복구 요청 파일 삭제: {recovery_id}")
            except:
                pass
                
        except Exception as e:
            logger.error(f"누락 알림 복구 처리 중 전체 오류: {e}")
            # 오류 발생 시 요청 파일 정리
            try:
                os.remove(missed_recovery_file)
            except:
                pass


def main():
    """메인 함수"""
    try:
        app = StreamerAlarmApp()
        app.run()
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # PyInstaller로 빌드된 실행 파일에서 multiprocessing 문제 방지
    import multiprocessing
    multiprocessing.freeze_support()
    main()