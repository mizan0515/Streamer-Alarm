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
from typing import Optional
from datetime import datetime
import pystray
from PIL import Image, ImageDraw
from src.monitors.chzzk_monitor import chzzk_monitor
from src.monitors.twitter_monitor import twitter_monitor
from src.monitors.cafe_monitor import cafe_monitor
from src.utils.logger import logger
from src.config import config
from src.utils.performance import performance_manager
from src.utils.memory import memory_manager, resource_monitor
from src.utils.http_client import close_all_clients


class StreamerAlarmApp:
    def __init__(self):
        self.tray_icon: Optional[pystray.Icon] = None
        self.streamlit_process: Optional[subprocess.Popen] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.is_running = False
        
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
            # Streamlit 실행
            cmd = [
                sys.executable, "-m", "streamlit", "run", 
                "streamlit_run.py",
                "--server.port=8501",
                "--server.headless=true",
                "--server.address=localhost",
                "--browser.gatherUsageStats=false"
            ]
            
            self.streamlit_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
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
        
        # Streamlit 서버 중지
        self.stop_streamlit_server()
        
        # 트레이 아이콘 제거
        if self.tray_icon:
            self.tray_icon.stop()
        
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
        """모든 플랫폼 모니터링 - UI 신호 처리 빈도 개선"""
        first_run = True
        current_interval = config.get_settings().get('check_interval', 30)
        last_monitoring_time = asyncio.get_event_loop().time()
        
        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                
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
            
            # 모니터링 시작
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self.monitor_all_platforms())
            
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
    
    def run(self):
        """애플리케이션 실행"""
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

    async def check_ui_signals(self):
        """UI로부터의 신호 확인 및 처리"""
        try:
            # 로그인 요청 확인
            login_request_file = os.path.join(config.data_dir, "login_request.json")
            if os.path.exists(login_request_file):
                try:
                    with open(login_request_file, 'r', encoding='utf-8') as f:
                        request_data = json.load(f)
                    
                    if request_data.get('action') == 'relogin_naver' and request_data.get('status') == 'requested':
                        request_id = request_data.get('request_id', 'unknown')
                        logger.info(f"UI로부터 네이버 재로그인 요청 수신 (ID: {request_id})")
                        
                        # 즉시 처리 중 상태로 변경 (중복 처리 방지)
                        request_data['status'] = 'processing'
                        request_data['processing_started'] = datetime.now().isoformat()
                        
                        # 안전한 파일 쓰기
                        self._safe_write_json(login_request_file, request_data)
                        
                        # 네이버 로그인 실행 (별도 스레드에서)
                        threading.Thread(target=self.handle_naver_login_request, args=(request_data,), daemon=True).start()
                        
                except Exception as e:
                    logger.warning(f"로그인 요청 처리 실패: {e}")
                    # 오류 발생 시 요청 파일 삭제
                    try:
                        os.remove(login_request_file)
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
            
            # 로그인 상태 확인 요청 처리
            login_status_file = os.path.join(config.data_dir, "login_status_request.json")
            if os.path.exists(login_status_file):
                try:
                    with open(login_status_file, 'r', encoding='utf-8') as f:
                        status_data = json.load(f)
                    
                    if status_data.get('action') == 'check_login_status' and status_data.get('status') == 'requested':
                        logger.info("UI로부터 로그인 상태 확인 요청 수신")
                        
                        # 로그인 상태 확인 실행 (별도 스레드에서)
                        threading.Thread(target=self.handle_login_status_request, args=(status_data,), daemon=True).start()
                        
                        # 요청 파일 삭제
                        os.remove(login_status_file)
                        
                except Exception as e:
                    logger.warning(f"로그인 상태 확인 요청 처리 실패: {e}")
                    try:
                        os.remove(login_status_file)
                    except:
                        pass
                        
        except Exception as e:
            logger.debug(f"UI 신호 확인 중 오류 (무시됨): {e}")
    
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
                # 먼저 현재 로그인 상태 확인
                current_status = False
                try:
                    if naver_session.page and naver_session.browser:
                        # 현재 로그인 상태 확인에 타임아웃 적용 (12초로 단축)
                        check_task = naver_session.check_login_status()
                        current_status = loop.run_until_complete(asyncio.wait_for(check_task, timeout=12.0))
                    
                    if current_status:
                        logger.info("이미 네이버에 로그인되어 있습니다 - 사용자 요청에 따라 로그인 창을 다시 엽니다")
                        
                        # 이미 로그인되어 있어도 사용자가 명시적으로 재로그인을 요청했으므로 로그인 창을 엽니다
                        try:
                            logger.info("force_visible=True로 네이버 로그인 호출 시작")
                            
                            # 헤드리스 모드 해제하여 로그인 창 표시 (타임아웃 적용)
                            try:
                                login_task = naver_session.login(force_visible=True)
                                result = loop.run_until_complete(asyncio.wait_for(login_task, timeout=30.0))
                                logger.info(f"네이버 로그인 호출 완료, 결과: {result}")
                            except asyncio.TimeoutError:
                                logger.error("네이버 로그인 호출 타임아웃 (30초)")
                                result = False
                            
                            if result:
                                logger.info("네이버 재로그인 성공")
                                request_data['status'] = 'completed'
                                request_data['completed_at'] = datetime.now().isoformat()
                                request_data['message'] = '재로그인 성공'
                            else:
                                logger.warning("네이버 재로그인 실패 또는 취소됨")
                                request_data['status'] = 'failed'
                                request_data['failed_at'] = datetime.now().isoformat()
                                request_data['error'] = '재로그인 실패 또는 사용자 취소'
                            
                            with open(login_request_file, 'w', encoding='utf-8') as f:
                                json.dump(request_data, f, ensure_ascii=False, indent=2)
                                
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
                            
                        except Exception as e:
                            logger.error(f"재로그인 처리 중 오류: {e}")
                            import traceback
                            logger.error(f"재로그인 처리 오류 상세:\n{traceback.format_exc()}")
                            
                            request_data['status'] = 'failed'
                            request_data['failed_at'] = datetime.now().isoformat()
                            request_data['error'] = f'재로그인 처리 오류: {str(e)}'
                            
                            with open(login_request_file, 'w', encoding='utf-8') as f:
                                json.dump(request_data, f, ensure_ascii=False, indent=2)
                        
                        return
                        
                except Exception as e:
                    logger.info(f"로그인 상태 확인 중 오류 (새로 로그인 시도): {e}")
                
                # 로그인이 필요한 경우 브라우저 창 열기
                logger.info("네이버 로그인이 필요합니다. 브라우저 창을 엽니다.")
                try:
                    login_task = naver_session.login()
                    result = loop.run_until_complete(asyncio.wait_for(login_task, timeout=60.0))
                    logger.info(f"네이버 로그인 완료, 결과: {result}")
                except asyncio.TimeoutError:
                    logger.error("네이버 로그인 타임아웃 (60초)")
                    result = False
                
                # 결과에 따른 상태 업데이트
                try:
                    if result:
                        logger.info("네이버 로그인 성공")
                        request_data['status'] = 'completed'
                        request_data['completed_at'] = datetime.now().isoformat()
                        request_data['message'] = '로그인 성공'
                    else:
                        logger.warning("네이버 로그인 실패 또는 취소됨")
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

    def handle_login_status_request(self, status_data):
        """로그인 상태 확인 요청 처리 (별도 스레드)"""
        # status_data는 로깅 용도로만 사용될 수 있음
        _ = status_data
        
        try:
            from src.browser.naver_session import naver_session
            
            # 새 이벤트 루프 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # 로그인 상태 확인 (상세 로깅 추가)
                logger.info("네이버 세션 상태 확인 시작")
                logger.info(f"naver_session.page 존재: {naver_session.page is not None}")
                logger.info(f"naver_session.browser 존재: {naver_session.browser is not None}")
                
                if naver_session.page and naver_session.browser:
                    logger.info("브라우저 세션이 존재함 - 로그인 상태 확인 진행")
                    try:
                        # 로그인 상태 확인에 타임아웃 적용 (15초로 단축)
                        check_task = naver_session.check_login_status()
                        is_logged_in = loop.run_until_complete(asyncio.wait_for(check_task, timeout=15.0))
                        status = "logged_in" if is_logged_in else "logged_out"
                        logger.info(f"로그인 상태 확인 결과: {status} (is_logged_in: {is_logged_in})")
                    except asyncio.TimeoutError:
                        logger.error("로그인 상태 확인 타임아웃 (15초) - unknown 상태로 처리")
                        status = "unknown"
                    except Exception as check_error:
                        logger.error(f"로그인 상태 확인 중 예외: {check_error}")
                        status = "unknown"
                else:
                    logger.warning("브라우저 세션이 없음 - 로그아웃 상태로 처리")
                    status = "logged_out"
                
                # 결과 파일 생성
                login_result_file = os.path.join(config.data_dir, "login_status_result.json")
                result_data = {
                    "action": "login_status_result",
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    "checked_at": datetime.now().isoformat()
                }
                
                logger.info(f"로그인 상태 결과 파일 생성 시작: {login_result_file}")
                
                with open(login_result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"로그인 상태 확인 완료 및 결과 파일 저장: {status}")
                logger.info(f"결과 데이터: {result_data}")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"로그인 상태 확인 처리 중 오류: {e}")
            
            # 오류 발생 시 unknown 상태로 결과 생성
            try:
                login_result_file = os.path.join(config.data_dir, "login_status_result.json")
                result_data = {
                    "action": "login_status_result",
                    "status": "unknown",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                
                with open(login_result_file, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                    
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


def main():
    """메인 함수"""
    try:
        app = StreamerAlarmApp()
        app.run()
    except Exception as e:
        logger.error(f"애플리케이션 실행 중 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()