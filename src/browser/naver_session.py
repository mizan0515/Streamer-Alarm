import asyncio
import json
import os
import webbrowser
import subprocess
import platform
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from ..config import config
from ..utils.logger import logger

class NaverSession:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.session_data = None
        self.playwright = None
        self.login_in_progress = False
        self.headless_mode = True  # 현재 헤드리스 모드 상태 추적
        
        # 별도 visible 브라우저 관리
        self.visible_browser = None
        self.visible_page = None
        self.visible_playwright = None
        
    async def start_browser(self, headless: bool = True):
        """브라우저 시작 (강화된 예외 처리)"""
        try:
            logger.info(f"브라우저 시작 시도 - 헤드리스 모드: {headless}")
            
            # 기존 브라우저가 있다면 정리
            if self.browser:
                logger.info("기존 브라우저 정리 중...")
                await self.close_browser()
            
            logger.info("Playwright 시작...")
            self.playwright = await async_playwright().start()
            
            # 사용자 데이터 디렉토리 설정
            user_data_dir = os.path.join(config.data_dir, "browser_data")
            os.makedirs(user_data_dir, exist_ok=True)
            logger.info(f"사용자 데이터 디렉토리: {user_data_dir}")
            
            logger.info("Chromium 브라우저 컨텍스트 생성 중...")
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                viewport={"width": 1280, "height": 720},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security", 
                    "--disable-features=VizDisplayCompositor",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
            )
            logger.info("브라우저 컨텍스트 생성 완료")
            
            # 기존 페이지 사용 (새 페이지 생성하지 않음)
            logger.info("페이지 설정 중...")
            pages = self.browser.pages
            if pages:
                self.page = pages[0]
                logger.info(f"기존 페이지 사용: {len(pages)}개 페이지 중 첫 번째")
            else:
                self.page = await self.browser.new_page()
                logger.info("새 페이지 생성 완료")
            
            # User-Agent 설정
            logger.info("User-Agent 설정 중...")
            await self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            # 헤드리스 모드 상태 추적
            self.headless_mode = headless
            
            logger.info(f"브라우저 시작 완료 (헤드리스: {headless})")
            return True
            
        except Exception as e:
            logger.error(f"브라우저 시작 실패: {e}")
            import traceback
            logger.error(f"브라우저 시작 실패 상세:\n{traceback.format_exc()}")
            
            # 정리 작업
            try:
                if self.browser:
                    await self.browser.close()
                    self.browser = None
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None
                self.page = None
            except:
                pass
            
            return False
    
    async def create_visible_browser(self) -> bool:
        """별도의 visible 브라우저 창 생성 (기존 헤드리스 브라우저와 독립적)"""
        try:
            logger.info("별도 visible 브라우저 창 생성 시작")
            
            # 기존 visible 브라우저가 있다면 정리
            if self.visible_browser:
                logger.info("기존 visible 브라우저 정리 중...")
                await self.close_visible_browser()
            
            # 새로운 Playwright 인스턴스 생성
            logger.info("새 Playwright 인스턴스 시작...")
            self.visible_playwright = await async_playwright().start()
            
            # 별도 데이터 디렉토리 사용 (기존과 구분)
            visible_data_dir = os.path.join(config.data_dir, "visible_browser_data")
            os.makedirs(visible_data_dir, exist_ok=True)
            
            # 기존 세션 데이터를 visible 브라우저로 복사
            main_data_dir = os.path.join(config.data_dir, "browser_data")
            if os.path.exists(main_data_dir):
                logger.info("기존 세션 데이터를 visible 브라우저로 복사 중...")
                import shutil
                try:
                    # 기존 visible 데이터 삭제 후 복사
                    if os.path.exists(visible_data_dir):
                        shutil.rmtree(visible_data_dir)
                    shutil.copytree(main_data_dir, visible_data_dir)
                    logger.info("세션 데이터 복사 완료")
                except Exception as copy_error:
                    logger.warning(f"세션 데이터 복사 실패: {copy_error} - 새 세션으로 진행")
            
            logger.info("Visible Chromium 브라우저 컨텍스트 생성 중...")
            self.visible_browser = await self.visible_playwright.chromium.launch_persistent_context(
                user_data_dir=visible_data_dir,
                headless=False,  # 반드시 visible 모드
                viewport={"width": 1280, "height": 720},
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
            )
            logger.info("Visible 브라우저 컨텍스트 생성 완료")
            
            # 새 페이지 생성
            self.visible_page = await self.visible_browser.new_page()
            
            # User-Agent 설정
            await self.visible_page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            logger.info("별도 visible 브라우저 창 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"별도 visible 브라우저 생성 실패: {e}")
            import traceback
            logger.error(f"별도 visible 브라우저 생성 실패 상세:\n{traceback.format_exc()}")
            
            # 정리 작업
            await self.close_visible_browser()
            return False
    
    async def sync_session_to_main_browser(self):
        """visible 브라우저의 세션 데이터를 메인 헤드리스 브라우저로 동기화"""
        try:
            logger.info("🔄 세션 데이터 동기화 시작 (visible → 헤드리스)")
            
            if not self.visible_browser:
                logger.warning("visible 브라우저가 없어 세션 동기화 불가")
                return False
            
            # visible 브라우저의 쿠키 가져오기
            visible_cookies = await self.visible_browser.cookies()
            naver_cookies = [c for c in visible_cookies if 'naver.com' in c.get('domain', '')]
            
            if not naver_cookies:
                logger.warning("visible 브라우저에 네이버 쿠키가 없음")
                return False
            
            logger.info(f"visible 브라우저에서 {len(naver_cookies)}개 네이버 쿠키 발견")
            
            # 메인 헤드리스 브라우저가 없으면 생성
            if not self.browser or not self.page:
                logger.info("메인 브라우저가 없어 헤드리스 모드로 새로 생성")
                if not await self.start_browser(headless=True):
                    logger.error("메인 헤드리스 브라우저 생성 실패")
                    return False
            
            # 메인 브라우저에 쿠키 설정
            try:
                await self.browser.add_cookies(naver_cookies)
                logger.info("✅ 메인 브라우저에 네이버 쿠키 동기화 완료")
                
                # 추가 검증: 메인 브라우저에서 로그인 상태 확인
                await asyncio.sleep(2)  # 쿠키 적용 대기
                if self.page:
                    try:
                        await self.page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=10000)
                        await asyncio.sleep(1)
                        
                        # 메인 브라우저에서 로그인 상태 재확인
                        login_status = await self._check_login_status_internal()
                        if login_status:
                            logger.info("✅ 메인 브라우저 로그인 상태 확인됨 - 세션 동기화 성공")
                            self.is_logged_in = True
                            return True
                        else:
                            logger.warning("❌ 메인 브라우저 로그인 상태 확인 실패")
                    except Exception as verify_error:
                        logger.warning(f"메인 브라우저 로그인 상태 검증 실패: {verify_error}")
                
                return True
                
            except Exception as cookie_error:
                logger.error(f"메인 브라우저 쿠키 설정 실패: {cookie_error}")
                return False
            
        except Exception as e:
            logger.error(f"세션 동기화 중 오류: {e}")
            import traceback
            logger.error(f"세션 동기화 오류 상세:\n{traceback.format_exc()}")
            return False
    
    async def close_visible_browser(self):
        """별도 visible 브라우저 정리"""
        try:
            if self.visible_page:
                await self.visible_page.close()
                self.visible_page = None
                
            if self.visible_browser:
                await self.visible_browser.close()
                self.visible_browser = None
                
            if self.visible_playwright:
                await self.visible_playwright.stop()
                self.visible_playwright = None
                
            logger.info("별도 visible 브라우저 정리 완료")
            
        except Exception as e:
            logger.warning(f"visible 브라우저 정리 중 오류: {e}")
    
    async def show_login_window(self) -> bool:
        """로그인 창 표시 (기존 헤드리스 브라우저 유지하면서 새 창 열기)"""
        try:
            logger.info("로그인 창 표시 시작 - 기존 브라우저는 유지")
            
            # 별도 visible 브라우저 생성
            if not await self.create_visible_browser():
                logger.error("visible 브라우저 생성 실패")
                return False
            
            # 네이버 메인 페이지로 이동
            try:
                logger.info("visible 브라우저에서 네이버 메인 페이지로 이동")
                await self.visible_page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                
                # 브라우저 창을 최상위로 표시
                try:
                    await self.visible_page.bring_to_front()
                    logger.info("visible 브라우저 창을 최상위로 표시했습니다")
                except Exception as bring_error:
                    logger.warning(f"브라우저 창 최상위 표시 실패: {bring_error}")
                
                logger.info("로그인 창 표시 완료 - 사용자가 브라우저 창에서 네이버를 확인할 수 있습니다")
                
                # 5초 후 자동으로 visible 브라우저 정리 (선택사항)
                async def auto_cleanup():
                    await asyncio.sleep(30)  # 30초 후 자동 정리
                    await self.close_visible_browser()
                    logger.info("visible 브라우저 자동 정리 완료")
                
                # 백그라운드에서 자동 정리 실행
                asyncio.create_task(auto_cleanup())
                
                return True
                
            except Exception as e:
                logger.error(f"네이버 페이지 이동 실패: {e}")
                await self.close_visible_browser()
                return False
                
        except Exception as e:
            logger.error(f"로그인 창 표시 실패: {e}")
            import traceback
            logger.error(f"로그인 창 표시 실패 상세:\n{traceback.format_exc()}")
            return False
    
    async def _handle_request(self, route):
        """요청 가로채기 - 선별적 리다이렉트 차단"""
        try:
            # 페이지나 브라우저가 유효하지 않은 경우 조기 반환
            if not self.page or not self.browser:
                try:
                    await route.continue_()
                except:
                    pass
                return
            
            request = route.request
            url = request.url
            
            # 로그인 진행 중일 때만 선별적으로 차단
            if self.login_in_progress:
                # 명확한 자동 리다이렉트만 차단 (광고, 추적 등)
                blocked_patterns = [
                    "ncpt.naver.com",  # 캡차
                    "siape.veta.naver.com",  # 광고
                    "wcs.naver.net",  # 추적
                    "ssl.pstatic.net",  # 정적 리소스 (일부)
                ]
                
                should_block = False
                for pattern in blocked_patterns:
                    if pattern in url:
                        should_block = True
                        break
                
                # 메인 페이지로의 직접적인 리다이렉트만 차단 (사용자 액션 없이)
                if (url == "https://www.naver.com/" and 
                    request.method == "GET" and
                    not hasattr(self, '_user_action_detected')):
                    should_block = True
                    logger.warning(f"사용자 액션 없는 메인 페이지 리다이렉트 차단: {url}")
                
                if should_block:
                    logger.debug(f"자동 요청 차단: {url}")
                    try:
                        await route.abort()
                    except Exception as abort_error:
                        logger.debug(f"요청 차단 실패: {abort_error}")
                    return
            
            # 정상 요청은 통과
            try:
                await route.continue_()
            except Exception as continue_error:
                logger.debug(f"요청 계속 처리 실패: {continue_error}")
            
        except Exception as e:
            logger.debug(f"요청 처리 중 오류: {e}")
            try:
                await route.continue_()
            except Exception as fallback_error:
                logger.debug(f"요청 처리 폴백 실패: {fallback_error}")
    
    async def check_login_status(self) -> bool:
        """로그인 상태 확인 (타임아웃 추가된 개선된 버전)"""
        try:
            # 전체 메서드에 타임아웃 적용 (10초로 단축)
            return await asyncio.wait_for(self._check_login_status_internal(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("로그인 상태 확인 전체 타임아웃 (10초)")
            self.is_logged_in = False
            return False
        except Exception as e:
            logger.warning(f"로그인 상태 확인 실패: {e}")
            self.is_logged_in = False
            return False
    
    async def _check_login_status_internal(self) -> bool:
        """내부 로그인 상태 확인 로직 (쿠키 우선, DOM 보조)"""
        try:
            if not self.page:
                return False
            
            current_url = self.page.url
            
            # 현재 페이지가 로그인 페이지인 경우, 페이지에서 직접 상태 확인
            if "nidlogin" in current_url:
                # 로그인 페이지에서는 폼 요소 존재 여부로 판단
                form_element = await self.page.query_selector('#frmNIDLogin')
                if form_element:
                    self.is_logged_in = False
                    logger.debug("로그인 페이지에서 확인 - 로그아웃 상태")
                    return False
            
            # 네이버 사이트가 아닌 경우에만 메인 페이지로 이동
            if not current_url or "naver.com" not in current_url:
                logger.info("네이버 메인 페이지로 이동하여 로그인 상태 확인")
                try:
                    # domcontentloaded로 변경하여 빠른 응답성 확보
                    await self.page.goto("https://www.naver.com", wait_until="domcontentloaded", timeout=10000)
                    await asyncio.sleep(1)  # 페이지 로딩 완료 대기 (단축)
                    logger.info("네이버 메인 페이지 이동 완료")
                except Exception as e:
                    logger.warning(f"네이버 메인 페이지 이동 실패: {e}")
                    return False
            else:
                logger.debug(f"현재 페이지에서 로그인 상태 확인: {current_url}")
            
            # 1단계: 쿠키 기반 로그인 상태 확인 (우선 방법)
            cookie_login_status = False
            logger.info("쿠키 기반 로그인 상태 확인 시작")
            try:
                # 빠른 쿠키 확인
                cookies = await asyncio.wait_for(self.page.context.cookies(), timeout=3.0)
                naver_login_cookies = [c for c in cookies if c.get('name') in ['NID_AUT', 'NID_SES'] and 'naver.com' in c.get('domain', '')]
                if naver_login_cookies:
                    logger.info(f"쿠키 기반 로그인 상태 확인됨 - {len(naver_login_cookies)}개 쿠키")
                    cookie_login_status = True
                else:
                    logger.info("네이버 로그인 쿠키 없음")
            except asyncio.TimeoutError:
                logger.warning("쿠키 확인 타임아웃")
            except Exception as e:
                logger.warning(f"쿠키 확인 실패: {e}")
            
            # 2단계: DOM 요소 기반 확인 (보조 방법, 타임아웃 증가)
            dom_login_status = False
            if cookie_login_status:
                # 쿠키가 있는 경우, DOM 확인도 시도하되 실패해도 쿠키 결과 우선
                logger.debug("쿠키 확인됨 - DOM 요소로 추가 검증 시도")
            else:
                # 쿠키가 없는 경우, DOM으로 확실히 확인
                logger.debug("쿠키 없음 - DOM 요소로 로그인 상태 확인")
            
            login_check_selectors = [
                '.MyView-module__my_info___GNmHz',  # 기존 셀렉터
                '.MyView-module__nickname___fcxwI',  # 닉네임 요소
                '.gnb_my',  # GNB MY 영역
                '[data-clk="gnb.my"]',  # GNB MY 링크
                '.gnb_item.gnb_my',  # GNB 마이 아이템
                '#gnb_my_m',  # 모바일 GNB
            ]
            
            for selector in login_check_selectors:
                try:
                    # 타임아웃을 3초로 단축하고 예외 처리 개선
                    element = await asyncio.wait_for(
                        self.page.wait_for_selector(selector, timeout=3000, state="attached"),
                        timeout=3.0
                    )
                    if element:
                        dom_login_status = True
                        logger.debug(f"DOM 로그인 상태 확인 성공: {selector}")
                        break
                except (asyncio.TimeoutError, Exception) as e:
                    logger.debug(f"셀렉터 {selector} 확인 실패: {e}")
                    continue
            
            # 3단계: 최종 로그인 상태 결정 (쿠키 우선)
            if cookie_login_status:
                # 쿠키가 있으면 로그인으로 간주 (DOM 실패해도 OK)
                if not dom_login_status:
                    logger.info("쿠키는 유효하나 DOM 요소 확인 실패 - 쿠키 기반으로 로그인 상태 판단")
                logged_in_element = True
            else:
                # 쿠키가 없으면 DOM 결과에 의존
                logged_in_element = dom_login_status
            
            if logged_in_element:
                self.is_logged_in = True
                logger.info("네이버 로그인 상태 확인됨")
                
                # 사용자 정보 추출 (첫 로그인 시에만)
                if not hasattr(self, '_user_logged') or not self._user_logged:
                    try:
                        nickname_selectors = ['.MyView-module__nickname___fcxwI', '.gnb_my .btn_my']
                        for selector in nickname_selectors:
                            try:
                                nickname_element = await self.page.query_selector(selector)
                                if nickname_element:
                                    nickname = await nickname_element.inner_text()
                                    if nickname.strip():
                                        logger.info(f"로그인된 사용자: {nickname.strip()}")
                                        self._user_logged = True
                                        break
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"사용자 정보 추출 실패: {e}")
                
                return True
            else:
                self.is_logged_in = False
                logger.info("네이버 로그아웃 상태")
                return False
                
        except Exception as e:
            logger.warning(f"내부 로그인 상태 확인 실패: {e}")
            self.is_logged_in = False
            return False
    
    async def login(self, force_visible: bool = False) -> bool:
        """네이버 로그인"""
        try:
            # ⚡ CRITICAL FIX: force_visible=True인 경우 즉시 브라우저 창 표시
            if force_visible:
                logger.info("🚀 force_visible=True - 즉시 브라우저 창 표시 모드")
                
                # 다중 폴백 전략: 여러 방법을 순차적으로 시도
                logger.info("다중 폴백 전략 시작 - 로그인 상태 확인 건너뜀")
                
                # 1차 시도: 별도 Playwright 브라우저 생성
                logger.info("1차 시도: 별도 Playwright 브라우저 창 생성")
                try:
                    if await asyncio.wait_for(self.show_login_window(), timeout=10.0):
                        logger.info("✅ 1차 성공: 별도 Playwright 브라우저 창 생성 완료")
                        return True
                    else:
                        logger.warning("❌ 1차 실패: Playwright 브라우저 창 생성 실패 - 2차 시도")
                except asyncio.TimeoutError:
                    logger.warning("⏰ 1차 실패: Playwright 브라우저 창 생성 타임아웃 - 2차 시도")
                except Exception as e:
                    logger.warning(f"💥 1차 실패: Playwright 브라우저 오류 ({e}) - 2차 시도")
                
                # 2차 시도: 시스템 기본 브라우저로 네이버 열기
                logger.info("2차 시도: 시스템 기본 브라우저로 네이버 열기")
                try:
                    if await asyncio.wait_for(self.open_naver_with_system_browser(), timeout=3.0):
                        logger.info("✅ 2차 성공: 시스템 브라우저로 네이버 열기 완료")
                        return True
                    else:
                        logger.warning("❌ 2차 실패: 시스템 브라우저 열기 실패 - 3차 시도")
                except Exception as e:
                    logger.warning(f"💥 2차 실패: 시스템 브라우저 오류 ({e}) - 3차 시도")
                
                # 3차 시도: 간단한 알림 메시지로 수동 안내
                logger.info("3차 시도: 사용자 수동 안내")
                try:
                    await self.show_manual_guidance()
                    logger.info("✅ 3차 완료: 사용자 수동 안내 표시 완료")
                    return True
                except Exception as e:
                    logger.error(f"💥 3차 실패: 수동 안내 표시 오류: {e}")
                    return False
            
            # 일반 로그인 프로세스 (force_visible=False)
            logger.info("일반 로그인 프로세스 시작")
            
            # 브라우저 상태 확인 및 초기화
            if not self.page or not self.browser:
                logger.info("브라우저 시작 (로그인용)")
                await self.start_browser(headless=False)  # 로그인 시에는 헤드리스 모드 해제
            else:
                # 기존 브라우저가 유효한지 확인
                try:
                    await asyncio.wait_for(self.page.title(), timeout=5.0)  # 페이지가 유효한지 테스트
                except Exception:
                    logger.info("기존 브라우저가 유효하지 않음 - 새로 시작")
                    await self.close_browser()
                    await self.start_browser(headless=False)
            
            # 이미 로그인된 상태인지 확인 (타임아웃 추가)
            try:
                logger.info("로그인 상태 확인 시작 (10초 타임아웃)")
                login_status_check = await asyncio.wait_for(self.check_login_status(), timeout=10.0)
                
                if login_status_check:
                    logger.info("이미 로그인되어 있음 - 헤드리스 모드로 전환")
                    # 이미 로그인되어 있고 브라우저가 헤드리스가 아닌 경우 헤드리스로 전환
                    if not self.headless_mode:
                        logger.info("헤드리스 모드로 전환 중...")
                        # 세션 데이터 백업
                        await self.save_session()
                        await self.close_browser()
                        await self.start_browser(headless=True)
                        # 세션 복원 후 로그인 상태 재확인
                        if await self.restore_session_and_check_login():
                            logger.info("헤드리스 모드 전환 및 로그인 상태 확인 완료")
                        else:
                            logger.warning("헤드리스 모드에서 로그인 상태 확인 실패")
                    return True
                    
            except asyncio.TimeoutError:
                logger.warning("로그인 상태 확인 타임아웃 (10초) - 로그인 프로세스 계속 진행")
            except Exception as e:
                logger.warning(f"로그인 상태 확인 중 오류 (계속 진행): {e}")
            
            logger.info("네이버 로그인 페이지로 이동")
            
            # 로그인 진행 플래그 설정
            self.login_in_progress = True
            
            # 기존 페이지들 정리 (빈 탭 방지)
            pages = self.browser.pages
            for page in pages:
                try:
                    url = page.url
                    # about:blank나 빈 페이지는 닫기
                    if url == "about:blank" or url == "" or "chrome-error://" in url:
                        if page != self.page:  # 현재 사용 중인 페이지가 아니면 닫기
                            await page.close()
                except Exception as e:
                    logger.debug(f"페이지 정리 중 오류: {e}")
                    pass
            
            # 로그인 페이지로 이동 전에 요청 가로채기 설정 (페이지가 유효한 경우에만)
            try:
                await self.page.route("**/*", self._handle_request)
            except Exception as e:
                logger.warning(f"요청 가로채기 설정 실패: {e}")
            
            # 로그인 페이지로 이동
            await self.page.goto("https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/", 
                                wait_until="domcontentloaded", timeout=30000)
            
            # 페이지 안정화 대기
            await asyncio.sleep(3)
            
            # 페이지 스크롤 및 자동 리다이렉트 방지
            await self.page.evaluate("""
                () => {
                    try {
                        // 기존 이벤트 리스너 제거 (중복 방지)
                        window.loginPageStabilized = window.loginPageStabilized || false;
                        
                        if (!window.loginPageStabilized) {
                            // 자동 스크롤 및 새로고침 방지
                            window.addEventListener('scroll', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                return false;
                            }, {passive: false, capture: true});
                            
                            window.addEventListener('wheel', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                return false;
                            }, {passive: false, capture: true});
                            
                            window.addEventListener('touchmove', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                return false;
                            }, {passive: false, capture: true});
                            
                            // 자동 새로고침 및 리다이렉트 방지
                            window.addEventListener('beforeunload', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                e.returnValue = '';
                                return '';
                            });
                            
                            // 페이지 떠나기 방지
                            window.addEventListener('pagehide', (e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                return false;
                            });
                            
                            // 페이지 고정 (body만 제한적으로 적용)
                            if (document.body) {
                                document.body.style.overflow = 'auto';  // 로그인 폼 스크롤 허용
                                document.body.style.position = 'relative';
                            }
                            
                            // 모든 타이머 및 인터벌 제거
                            let id = window.setTimeout(function() {}, 0);
                            while (id--) {
                                window.clearTimeout(id);
                            }
                            id = window.setInterval(function() {}, 0);
                            while (id--) {
                                window.clearInterval(id);
                            }
                            
                            // meta refresh 태그 제거 및 감시
                            const removeMetaRefresh = () => {
                                const metaRefresh = document.querySelectorAll('meta[http-equiv*="refresh" i]');
                                metaRefresh.forEach(meta => meta.remove());
                            };
                            removeMetaRefresh();
                            
                            // meta 태그 추가 감시
                            const observer = new MutationObserver((mutations) => {
                                mutations.forEach((mutation) => {
                                    if (mutation.type === 'childList') {
                                        mutation.addedNodes.forEach((node) => {
                                            if (node.tagName === 'META' && 
                                                node.getAttribute('http-equiv') && 
                                                node.getAttribute('http-equiv').toLowerCase().includes('refresh')) {
                                                node.remove();
                                                console.log('Meta refresh tag blocked');
                                            }
                                        });
                                    }
                                });
                            });
                            observer.observe(document.head, { childList: true, subtree: true });
                            
                            // history API 완전 차단
                            const originalPushState = history.pushState;
                            const originalReplaceState = history.replaceState;
                            const originalGo = history.go;
                            const originalBack = history.back;
                            const originalForward = history.forward;
                            
                            history.pushState = function(...args) {
                                console.log('pushState prevented during login');
                                return;
                            };
                            
                            history.replaceState = function(...args) {
                                console.log('replaceState prevented during login');
                                return;
                            };
                            
                            history.go = function(...args) {
                                console.log('history.go prevented during login');
                                return;
                            };
                            
                            history.back = function(...args) {
                                console.log('history.back prevented during login');
                                return;
                            };
                            
                            history.forward = function(...args) {
                                console.log('history.forward prevented during login');
                                return;
                            };
                            
                            // location 변경 방지
                            const originalLocation = window.location;
                            Object.defineProperty(window, 'location', {
                                get: () => originalLocation,
                                set: (value) => {
                                    console.log('Location change prevented during login:', value);
                                    return false;
                                }
                            });
                            
                            // 자동 로그인 감지 및 차단
                            const blockAutoLogin = () => {
                                // 자동 로그인 관련 쿠키 및 스토리지 항목 임시 제거
                                const autoLoginCookies = document.cookie.split(';').filter(cookie => 
                                    cookie.includes('auto') || cookie.includes('remember') || cookie.includes('keep')
                                );
                                
                                // 폼 자동 제출 방지
                                const forms = document.querySelectorAll('form');
                                forms.forEach(form => {
                                    form.addEventListener('submit', (e) => {
                                        // 사용자가 직접 클릭한 경우만 허용
                                        if (!e.isTrusted) {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            console.log('Auto form submission prevented');
                                            return false;
                                        }
                                    });
                                });
                            };
                            
                            // DOM 로드 후 실행
                            if (document.readyState === 'loading') {
                                document.addEventListener('DOMContentLoaded', blockAutoLogin);
                            } else {
                                blockAutoLogin();
                            }
                            
                            window.loginPageStabilized = true;
                            console.log('Login page stabilization complete with redirect prevention');
                        }
                    } catch (error) {
                        console.error('Login page stabilization error:', error);
                    }
                }
            """)
            
            # 로그인 상태 유지 체크박스 자동 활성화 및 사용자 액션 감지
            try:
                await self.page.wait_for_selector('#keep', timeout=5000)
                
                # JavaScript로 체크박스 상태 확인 및 활성화, 그리고 사용자 액션 감지 설정
                checkbox_result = await self.page.evaluate("""
                    () => {
                        // 로그인 상태 유지 체크박스 자동 활성화
                        const keepCheckbox = document.querySelector('#keep');
                        if (keepCheckbox) {
                            keepCheckbox.checked = true;
                            keepCheckbox.value = 'on';
                            keepCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('로그인 상태 유지 체크박스 활성화됨');
                        }
                        
                        // IP보안도 자동으로 OFF로 설정 (로그인 편의성)
                        const ipSecurityCheckbox = document.querySelector('#switch');
                        if (ipSecurityCheckbox && ipSecurityCheckbox.checked) {
                            ipSecurityCheckbox.checked = false;
                            ipSecurityCheckbox.value = 'off';
                            ipSecurityCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('IP보안 OFF로 설정됨');
                        }
                        
                        // 로그인 버튼 클릭 감지
                        const loginBtn = document.querySelector('#log\\.login');
                        if (loginBtn) {
                            loginBtn.addEventListener('click', () => {
                                window.userLoginAction = true;
                                console.log('User login button clicked detected');
                            });
                        }
                        
                        // 엔터키 감지
                        const passwordInput = document.querySelector('#pw');
                        if (passwordInput) {
                            passwordInput.addEventListener('keydown', (e) => {
                                if (e.key === 'Enter') {
                                    window.userLoginAction = true;
                                    console.log('User login enter key detected');
                                }
                            });
                        }
                        
                        return keepCheckbox ? (keepCheckbox.checked ? '로그인 상태 유지 활성화됨' : '로그인 상태 유지 비활성화') : '체크박스 없음';
                    }
                """)
                logger.info(f"로그인 설정 자동 구성 완료: {checkbox_result}")
                
            except Exception as e:
                logger.warning(f"로그인 설정 구성 실패: {e}")
            
            # 사용자가 수동으로 로그인할 때까지 대기
            logger.info("사용자의 로그인 입력을 대기 중...")
            
            # 로그인 완료까지 대기 (최대 5분)
            max_wait_time = 300  # 5분
            wait_interval = 2  # 2초마다 체크
            
            last_url = ""
            url_stable_count = 0
            
            for _ in range(max_wait_time // wait_interval):
                try:
                    current_url = self.page.url
                    
                    # 로그인 페이지에서 강제로 벗어나려는 시도 감지 및 차단 (deviceConfirm 제외)
                    if (current_url and "nidlogin" not in current_url and "naver.com" in current_url and 
                        "deviceConfirm" not in current_url):
                        # 실제 로그인 상태 확인 (로그인된 사용자 요소가 있는지 체크)
                        login_status_check = await self.page.evaluate("""
                            () => {
                                // 로그인된 사용자 정보 요소가 있는지 확인
                                const loggedInElement = document.querySelector('.MyView-module__my_info___GNmHz');
                                const userNickname = document.querySelector('.MyView-module__nickname___fcxwI');
                                const gnbMy = document.querySelector('.gnb_my');
                                
                                if (loggedInElement || userNickname || gnbMy) {
                                    console.log('Real login detected - user elements found');
                                    return true;  // 실제 로그인 완료
                                }
                                
                                // 로그인되지 않은 상태에서 메인 페이지로 왔다면 자동 리다이렉트
                                console.log('Auto redirect detected - no login elements found');
                                return false;  // 자동 리다이렉트로 판단
                            }
                        """)
                        
                        if not login_status_check:
                            # 자동 리다이렉트로 판단되면 로그인 페이지로 다시 이동
                            logger.warning(f"자동 리다이렉트 감지, 로그인 페이지로 돌아감 (현재 URL: {current_url})")
                            self._user_action_detected = True  # 의도적인 페이지 이동
                            try:
                                await self.page.goto("https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/", 
                                                    wait_until="domcontentloaded", timeout=30000)
                                await asyncio.sleep(2)
                            finally:
                                if hasattr(self, '_user_action_detected'):
                                    delattr(self, '_user_action_detected')
                            
                            # 다시 안정화 스크립트 실행 (초기화 후)
                            await self.page.evaluate("""
                                () => {
                                    // 이전 안정화 설정 완전 제거
                                    if (window.loginPageStabilized) {
                                        delete window.loginPageStabilized;
                                    }
                                }
                            """)
                            
                            # 페이지 안정화 스크립트를 다시 실행
                            logger.info("로그인 페이지 안정화 재적용")
                            await self.page.evaluate("""
                                () => {
                                    try {
                                        // 기존 이벤트 리스너 제거 (중복 방지)
                                        window.loginPageStabilized = false;
                                        
                                        // 자동 스크롤 및 새로고침 방지
                                        window.addEventListener('scroll', (e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            return false;
                                        }, {passive: false, capture: true});
                                        
                                        // 자동 새로고침 및 리다이렉트 방지
                                        window.addEventListener('beforeunload', (e) => {
                                            e.preventDefault();
                                            e.stopPropagation();
                                            e.returnValue = '';
                                            return '';
                                        });
                                        
                                        // 모든 타이머 및 인터벌 제거
                                        let id = window.setTimeout(function() {}, 0);
                                        while (id--) {
                                            window.clearTimeout(id);
                                        }
                                        id = window.setInterval(function() {}, 0);
                                        while (id--) {
                                            window.clearInterval(id);
                                        }
                                        
                                        // meta refresh 태그 제거
                                        const metaRefresh = document.querySelectorAll('meta[http-equiv*="refresh" i]');
                                        metaRefresh.forEach(meta => meta.remove());
                                        
                                        // history API 차단
                                        history.pushState = function(...args) {
                                            console.log('pushState prevented during login');
                                            return;
                                        };
                                        
                                        history.replaceState = function(...args) {
                                            console.log('replaceState prevented during login');
                                            return;
                                        };
                                        
                                        window.loginPageStabilized = true;
                                        console.log('Login page re-stabilization complete');
                                    } catch (error) {
                                        console.error('Login page re-stabilization error:', error);
                                    }
                                }
                            """)
                            
                            url_stable_count = 0
                            last_url = ""
                            continue
                    
                    # URL이 변경되지 않고 안정적인지 확인
                    if current_url == last_url:
                        url_stable_count += 1
                    else:
                        url_stable_count = 0
                        last_url = current_url
                    
                    # 디바이스 확인 페이지 처리
                    if "deviceConfirm" in current_url:
                        logger.info("네이버 디바이스 확인 페이지 감지 - 자동 처리")
                        try:
                            # "다음" 또는 "확인" 버튼 클릭
                            confirm_selectors = [
                                'button:has-text("다음")',
                                'button:has-text("확인")',
                                'input[value="다음"]',
                                'input[value="확인"]',
                                '.btn_next',
                                '.btn_confirm',
                                '#confirmBtn'
                            ]
                            
                            for selector in confirm_selectors:
                                try:
                                    button = await self.page.query_selector(selector)
                                    if button:
                                        await button.click()
                                        logger.info(f"디바이스 확인 버튼 클릭: {selector}")
                                        await asyncio.sleep(3)  # 처리 대기
                                        break
                                except:
                                    continue
                        except Exception as e:
                            logger.warning(f"디바이스 확인 처리 실패: {e}")
                        
                        # 디바이스 확인 후 반복 계속
                        url_stable_count = 0
                        last_url = ""
                        continue
                    
                    # 사용자 액션 감지
                    user_action = await self.page.evaluate("() => window.userLoginAction || false")
                    if user_action:
                        self._user_action_detected = True
                        logger.info("사용자 로그인 액션 감지됨")
                    
                    # 실제 로그인 완료 감지 (사용자 액션이 있었거나 더 엄격한 조건)
                    if ("naver.com" in current_url and "nidlogin" not in current_url and "deviceConfirm" not in current_url and
                        (user_action or url_stable_count >= 3)):  # 사용자 액션이 있거나 3번 연속 같은 URL
                        
                        logger.info(f"로그인 완룈 감지, URL: {current_url} (안정 카운트: {url_stable_count}, 사용자 액션: {user_action})")
                        
                        # 자동로그인 등록 팝업 처리 (새 창에서 나타날 수 있음)
                        await self.handle_autologin_popup()
                        
                        # 실제 로그인 상태 확인
                        if await self.check_login_status():
                            logger.info("네이버 로그인 성공!")
                            
                            # 로그인 완료 후 페이지 안정화 해제
                            try:
                                await self.page.evaluate("""
                                    () => {
                                        // 로그인 완료 후 페이지 안정화 해제
                                        if (window.loginPageStabilized) {
                                            delete window.loginPageStabilized;
                                            console.log('Login page stabilization released');
                                        }
                                        // 사용자 액션 플래그도 초기화
                                        window.userLoginAction = false;
                                    }
                                """)
                            except:
                                pass
                            
                            # 세션 데이터 저장
                            await self.save_session()
                            
                            # 세션 데이터 저장 후 약간의 지연
                            await asyncio.sleep(2)
                            
                            # 브라우저 완전히 닫기 (빈 탭 방지)
                            await self.close_browser()
                            
                            # 약간의 지연 후 헤드리스 모드로 새 브라우저 시작
                            await asyncio.sleep(1)
                            await self.start_browser(headless=True)
                            
                            # 세션 복원 및 로그인 상태 재확인
                            if await self.restore_session_and_check_login():
                                logger.info("헤드리스 모드에서 로그인 상태 재확인 완료")
                                self.login_in_progress = False  # 로그인 완료
                                return True
                            else:
                                logger.warning("헤드리스 모드에서 로그인 상태 재확인 실패")
                        else:
                            logger.warning(f"URL 변경 감지되었으나 로그인 상태 아님: {current_url}")
                            # 사용자 액션이 없었다면 로그인 페이지로 다시 이동
                            if not user_action:
                                self._user_action_detected = True  # 의도적인 페이지 이동
                                try:
                                    await self.page.goto("https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/", 
                                                        wait_until="domcontentloaded", timeout=30000)
                                    await asyncio.sleep(2)
                                finally:
                                    if hasattr(self, '_user_action_detected'):
                                        delattr(self, '_user_action_detected')
                    
                    # 로그인 페이지에서 계속 대기 중인 경우
                    elif "nidlogin" in current_url:
                        logger.debug("로그인 페이지에서 사용자 입력 대기 중...")
                            
                    await asyncio.sleep(wait_interval)
                    
                except Exception as e:
                    logger.error(f"로그인 확인 중 오류: {e}")
                    await asyncio.sleep(wait_interval)
            
            logger.warning("로그인 타임아웃")
            self.login_in_progress = False  # 타임아웃 시 플래그 해제
            return False
            
        except Exception as e:
            logger.error(f"네이버 로그인 실패: {e}")
            self.login_in_progress = False  # 실패 시 플래그 해제
            return False
    
    async def handle_autologin_popup(self):
        """자동로그인 등록 팝업 처리"""
        try:
            # 현재 브라우저의 모든 페이지 확인
            pages = self.browser.pages
            logger.info(f"현재 열린 페이지 수: {len(pages)}")
            
            for i, page in enumerate(pages):
                try:
                    page_url = page.url
                    logger.debug(f"페이지 {i+1}: {page_url}")
                    
                    # 자동로그인 등록 관련 페이지 감지
                    if ("autologin" in page_url or 
                        "자동로그인" in await page.title() or
                        "auto" in page_url.lower()):
                        
                        logger.info(f"자동로그인 팝업 페이지 발견: {page_url}")
                        
                        # 팝업에서 "아니오" 또는 "취소" 버튼 클릭
                        try:
                            # 다양한 버튼 선택자 시도
                            button_selectors = [
                                'button:has-text("아니오")',
                                'button:has-text("취소")',
                                'button:has-text("나중에")',
                                'input[value="아니오"]',
                                'input[value="취소"]',
                                'input[value="나중에"]',
                                '.btn_cancel',
                                '.btn_no',
                                '#btnCancel',
                                '#btnNo'
                            ]
                            
                            button_clicked = False
                            for selector in button_selectors:
                                try:
                                    await page.wait_for_selector(selector, timeout=2000)
                                    await page.click(selector)
                                    logger.info(f"자동로그인 팝업에서 '{selector}' 버튼 클릭됨")
                                    button_clicked = True
                                    break
                                except:
                                    continue
                            
                            if not button_clicked:
                                # 버튼을 찾지 못한 경우 JavaScript로 닫기 시도
                                await page.evaluate("""
                                    () => {
                                        // 일반적인 팝업 닫기 방법들
                                        if (window.close) {
                                            window.close();
                                        }
                                        
                                        // 부모 창으로 포커스 이동
                                        if (window.opener) {
                                            window.opener.focus();
                                        }
                                        
                                        // ESC 키 시뮬레이션
                                        document.dispatchEvent(new KeyboardEvent('keydown', {
                                            key: 'Escape',
                                            code: 'Escape',
                                            keyCode: 27
                                        }));
                                    }
                                """)
                                logger.info("JavaScript로 자동로그인 팝업 닫기 시도")
                            
                            # 잠시 대기 후 페이지 닫기
                            await asyncio.sleep(1)
                            if page != self.page:  # 메인 페이지가 아닌 경우에만 닫기
                                await page.close()
                                logger.info("자동로그인 팝업 페이지 닫기 완료")
                            
                        except Exception as e:
                            logger.warning(f"자동로그인 팝업 처리 중 오류: {e}")
                            # 강제로 페이지 닫기
                            try:
                                if page != self.page:
                                    await page.close()
                            except:
                                pass
                
                except Exception as e:
                    logger.debug(f"페이지 {i+1} 확인 중 오류: {e}")
                    continue
            
            # 메인 페이지에서도 팝업 요소 확인
            try:
                popup_closed = await self.page.evaluate("""
                    () => {
                        // 팝업, 모달, 다이얼로그 요소들 찾기
                        const popupSelectors = [
                            '[class*="popup"]',
                            '[class*="modal"]',
                            '[class*="dialog"]',
                            '[id*="popup"]',
                            '[id*="modal"]',
                            '[id*="dialog"]'
                        ];
                        
                        let closed = false;
                        popupSelectors.forEach(selector => {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(element => {
                                if (element.style.display !== 'none') {
                                    // 팝업 내에서 취소/아니오 버튼 찾기
                                    const buttons = element.querySelectorAll('button, input[type="button"]');
                                    buttons.forEach(btn => {
                                        const text = btn.textContent || btn.value || '';
                                        if (text.includes('아니오') || text.includes('취소') || text.includes('나중에')) {
                                            btn.click();
                                            closed = true;
                                            console.log('팝업 버튼 클릭:', text);
                                        }
                                    });
                                    
                                    // 버튼을 못 찾은 경우 팝업 숨기기
                                    if (!closed) {
                                        element.style.display = 'none';
                                        closed = true;
                                        console.log('팝업 강제 숨기기');
                                    }
                                }
                            });
                        });
                        
                        return closed;
                    }
                """)
                
                if popup_closed:
                    logger.info("메인 페이지에서 팝업 처리 완료")
            
            except Exception as e:
                logger.debug(f"메인 페이지 팝업 확인 중 오류: {e}")
        
        except Exception as e:
            logger.warning(f"자동로그인 팝업 처리 실패: {e}")
    
    async def save_session(self):
        """세션 데이터 저장"""
        try:
            if not self.page:
                return
            
            # 쿠키와 로컬 스토리지 데이터 저장
            cookies = await self.page.context.cookies()
            local_storage = await self.page.evaluate("() => JSON.stringify(localStorage)")
            
            session_data = {
                "cookies": cookies,
                "local_storage": local_storage,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            config.save_browser_session(session_data)
            logger.info("세션 데이터 저장 완료")
            
        except Exception as e:
            logger.error(f"세션 데이터 저장 실패: {e}")
    
    async def restore_session_and_check_login(self) -> bool:
        """세션 복원 및 로그인 상태 확인 (개선된 버전)"""
        try:
            session_data = config.get_browser_session()
            if not session_data:
                logger.debug("저장된 세션 데이터 없음")
                return False
            
            logger.info("헤드리스 모드에서 세션 복원 시작")
            
            # 쿠키 복원
            if "cookies" in session_data:
                try:
                    await self.page.context.add_cookies(session_data["cookies"])
                    logger.debug(f"쿠키 {len(session_data['cookies'])}개 복원 완료")
                except Exception as e:
                    logger.warning(f"쿠키 복원 실패: {e}")
            
            # 네이버 메인 페이지로 이동 (여러 번 시도)
            for attempt in range(3):
                try:
                    logger.debug(f"네이버 메인 페이지 이동 시도 {attempt + 1}/3")
                    await self.page.goto("https://www.naver.com", wait_until="networkidle", timeout=20000)
                    await asyncio.sleep(3)  # 페이지 완전히 로드될 때까지 대기
                    break
                except Exception as e:
                    logger.warning(f"페이지 이동 시도 {attempt + 1} 실패: {e}")
                    if attempt == 2:
                        return False
                    await asyncio.sleep(2)
            
            # 로컬 스토리지 복원
            if "local_storage" in session_data:
                try:
                    await self.page.evaluate(f"""
                        () => {{
                            try {{
                                localStorage.clear();
                                const data = {session_data['local_storage']};
                                Object.keys(data).forEach(key => {{
                                    try {{
                                        localStorage.setItem(key, data[key]);
                                    }} catch(e) {{
                                        console.warn('Failed to set localStorage item:', key, e);
                                    }}
                                }});
                                console.log('LocalStorage restored successfully');
                            }} catch(e) {{
                                console.error('LocalStorage restore failed:', e);
                            }}
                        }}
                    """)
                    logger.debug("로컬 스토리지 복원 완료")
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"로컬 스토리지 복원 실패: {e}")
            
            # 페이지 새로고침 후 로그인 상태 확인
            try:
                await self.page.reload(wait_until="networkidle", timeout=15000)
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"페이지 새로고침 실패: {e}")
            
            # 로그인 상태 확인 (여러 번 시도)
            for attempt in range(3):
                try:
                    logger.debug(f"로그인 상태 확인 시도 {attempt + 1}/3")
                    if await self.check_login_status():
                        logger.info("헤드리스 모드에서 세션 복원 및 로그인 상태 확인 성공")
                        return True
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"로그인 상태 확인 시도 {attempt + 1} 실패: {e}")
                    await asyncio.sleep(2)
            
            logger.warning("헤드리스 모드에서 로그인 상태 확인 실패")
            return False
            
        except Exception as e:
            logger.error(f"세션 복원 실패: {e}")
            return False

    async def load_session(self) -> bool:
        """저장된 세션 데이터 로드"""
        try:
            session_data = config.get_browser_session()
            if not session_data:
                logger.debug("저장된 세션 데이터 없음")
                return False
            
            # 항상 헤드리스 모드로 시작 (세션 로드 시)
            if not self.page or not self.browser:
                logger.info("헤드리스 모드로 브라우저 시작 (세션 로드용)")
                await self.start_browser(headless=True)
            
            # 세션 복원 및 로그인 상태 확인
            if await self.restore_session_and_check_login():
                logger.info("저장된 세션 로드 및 로그인 상태 확인 성공")
                return True
            else:
                logger.debug("세션 데이터는 있지만 로그인 상태가 아님")
                return False
                
        except Exception as e:
            logger.debug(f"세션 데이터 로드 실패: {e}")
            return False
    
    async def get_cafe_posts(self, club_id: str, user_id: str) -> Optional[list]:
        """카페 사용자의 게시물 목록 가져오기 (세션 추적 로깅 포함)"""
        try:
            # 세션 추적 로깅 시작
            logger.debug(f"🔍 카페 게시물 수집 시작 - club_id: {club_id}, user_id: {user_id}")
            
            # 브라우저와 페이지 유효성 확인
            if not self.page or not self.browser:
                logger.warning("❌ 네이버 브라우저 세션이 없음 - 카페 모니터링 불가")
                return None
            
            # 현재 브라우저 쿠키 상태 로깅
            try:
                cookies = await self.page.context.cookies()
                naver_cookies = [c for c in cookies if 'naver.com' in c.get('domain', '')]
                logger.debug(f"🍪 현재 네이버 쿠키 개수: {len(naver_cookies)}")
                
                # 중요한 로그인 쿠키 확인
                login_cookies = [c['name'] for c in naver_cookies if c.get('name') in ['NID_AUT', 'NID_SES']]
                if login_cookies:
                    logger.debug(f"🔑 로그인 관련 쿠키: {login_cookies}")
                else:
                    logger.warning("⚠️ 로그인 관련 쿠키가 없음")
            except Exception as cookie_error:
                logger.debug(f"쿠키 확인 실패: {cookie_error}")
            
            # 캐시된 로그인 상태만 확인 (실시간 확인 제거로 성능 개선)
            if not self.is_logged_in:
                logger.debug("❌ 캐시된 로그인 상태가 False - 카페 접근 건너뜀")
                return None
            else:
                logger.debug("✅ 캐시된 로그인 상태 유효")
            
            url = f"https://cafe.naver.com/ca-fe/cafes/{club_id}/members/{user_id}"
            logger.debug(f"🌐 카페 페이지 접근: {url}")
            
            try:
                # 페이지 로드 타임아웃을 5초로 단축
                await asyncio.wait_for(
                    self.page.goto(url, wait_until="domcontentloaded"),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"❌ 카페 페이지 로드 타임아웃 (5초) - {url}")
                return None
            
            # 현재 페이지 URL 확인 (리다이렉트 등 확인용)
            current_url = self.page.url
            if "nidlogin" in current_url:
                logger.error("❌ 로그인 페이지로 리다이렉트됨 - 세션이 유효하지 않음")
                self.is_logged_in = False  # 캐시 업데이트
                return None
            
            logger.debug(f"✅ 카페 페이지 접근 성공: {current_url}")
            
            # 게시물 목록 요소 대기 (타임아웃 단축)
            try:
                await asyncio.wait_for(
                    self.page.wait_for_selector('tbody tr', timeout=3000),
                    timeout=3.0
                )
                logger.debug("📋 게시물 목록 요소 로드 완료")
            except asyncio.TimeoutError:
                logger.warning("❌ 게시물 목록 요소 로드 타임아웃 (3초)")
                return None
            except Exception as selector_error:
                logger.error(f"❌ 게시물 목록 요소 로드 실패: {selector_error}")
                return None
            
            # 게시물 정보 추출 (새로운 HTML 구조에 맞게 수정)
            posts = await self.page.evaluate("""
                () => {
                    const posts = [];
                    const postElements = document.querySelectorAll('tbody tr');
                    
                    postElements.forEach(post => {
                        const titleElement = post.querySelector('.article');
                        const dateElement = post.querySelector('.td_date');
                        
                        if (titleElement && dateElement) {
                            // URL에서 articleid 추출
                            const href = titleElement.getAttribute('href');
                            let articleId = '';
                            if (href) {
                                const match = href.match(/articleid=([0-9]+)/);
                                if (match) {
                                    articleId = match[1];
                                }
                            }
                            
                            // 제목에서 태그 제거 후 텍스트만 추출
                            const titleText = titleElement.textContent.trim();
                            
                            if (articleId && titleText) {
                                posts.push({
                                    title: titleText,
                                    url: `https://cafe.naver.com${href}`,
                                    date: dateElement.textContent.trim(),
                                    id: articleId
                                });
                            }
                        }
                    });
                    
                    return posts;
                }
            """)
            
            # 세션 추적 로깅 - 결과 요약
            if posts:
                logger.info(f"✅ 카페 게시물 {len(posts)}개 조회 완료")
                logger.debug(f"📝 최신 게시물: {posts[0]['title'][:30]}... ({posts[0]['date']})")
                
                # 세션 유효성 재확인 (성공적으로 데이터를 가져왔으므로 로그인 상태 갱신)
                self.is_logged_in = True
            else:
                logger.warning("⚠️ 게시물 목록이 비어있음 - 세션 문제일 가능성")
            
            return posts
            
        except Exception as e:
            logger.error(f"카페 게시물 조회 실패: {e}")
            return None
    
    async def close_browser(self):
        """브라우저 종료 (모든 브라우저 인스턴스 정리)"""
        try:
            # 로그인 진행 플래그 해제
            self.login_in_progress = False
            
            # 별도 visible 브라우저도 정리
            await self.close_visible_browser()
            
            if self.page:
                try:
                    # 요청 핸들러 제거 (오류 방지)
                    await self.page.unroute("**/*")
                except Exception as e:
                    logger.debug(f"요청 핸들러 제거 실패 (무시): {e}")
                
                try:
                    await self.page.close()
                except Exception as e:
                    logger.debug(f"페이지 닫기 실패 (무시): {e}")
                finally:
                    self.page = None
            
            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.debug(f"브라우저 닫기 실패 (무시): {e}")
                finally:
                    self.browser = None
            
            if self.playwright:
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.debug(f"Playwright 종료 실패 (무시): {e}")
                finally:
                    self.playwright = None
            
            logger.info("브라우저 종료 완료")
            
        except Exception as e:
            logger.error(f"브라우저 종료 실패: {e}")
            # 강제로 모든 참조 제거
            self.page = None
            self.browser = None
            self.playwright = None
    
    async def show_login_window(self) -> bool:
        """별도 visible 브라우저 창 생성 및 네이버 로그인 페이지 표시"""
        try:
            logger.info("🌟 별도 브라우저 창 생성 시작")
            
            # 기존 visible 브라우저가 있다면 정리
            await self.close_visible_browser()
            
            logger.info("🚀 새로운 Playwright 인스턴스 생성 중...")
            # 새로운 Playwright 인스턴스 생성
            self.visible_playwright = await async_playwright().start()
            
            logger.info("🔧 visible 브라우저 설정 중...")
            # visible 브라우저 생성 (강화된 설정)
            self.visible_browser = await self.visible_playwright.chromium.launch(
                headless=False,  # 명시적으로 False 설정
                slow_mo=50,     # 50ms 딜레이로 브라우저 동작 시각화
                devtools=False,  # 개발자 도구 비활성화
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-background-timer-throttling",
                    "--force-device-scale-factor=1",
                    "--start-maximized",  # 최대화된 창으로 시작
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            
            logger.info("📄 새 페이지 생성 중...")
            # 새 페이지 생성
            self.visible_page = await self.visible_browser.new_page()
            
            # 뷰포트 설정 (더 큰 창 크기)
            await self.visible_page.set_viewport_size({"width": 1200, "height": 800})
            
            logger.info("🔧 User-Agent 및 헤더 설정 중...")
            # User-Agent 설정
            await self.visible_page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br"
            })
            
            logger.info("🌐 네이버 로그인 페이지로 이동 중...")
            # 네이버 로그인 페이지로 이동 (더 긴 타임아웃)
            await self.visible_page.goto(
                "https://nid.naver.com/nidlogin.login", 
                wait_until="domcontentloaded",
                timeout=15000  # 15초 타임아웃
            )
            
            # 페이지 제목 확인으로 로드 성공 검증
            page_title = await self.visible_page.title()
            logger.info(f"📋 로드된 페이지 제목: {page_title}")
            
            # 추가 검증: 로그인 폼이 존재하는지 확인
            try:
                await self.visible_page.wait_for_selector("#id", timeout=5000)
                logger.info("✅ 로그인 폼 확인됨")
            except:
                logger.warning("⚠️ 로그인 폼 확인 실패 (하지만 계속 진행)")
            
            # 브라우저 창을 앞으로 가져오기
            try:
                await self.visible_page.bring_to_front()
                logger.info("🔝 브라우저 창을 앞으로 가져옴")
            except:
                logger.debug("브라우저 창 앞으로 가져오기 실패 (무시)")
            
            logger.info("✅ 별도 브라우저 창에 네이버 로그인 페이지 표시 완료")
            
            # 로그인 완료 감지를 위한 백그라운드 모니터링 시작
            asyncio.create_task(self._monitor_login_completion())
            
            return True
            
        except Exception as e:
            logger.error(f"💥 별도 브라우저 창 생성 실패: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")
            await self.close_visible_browser()
            return False
    
    async def close_visible_browser(self):
        """별도 visible 브라우저 정리 (강화된 버전)"""
        try:
            logger.info("🧹 별도 브라우저 정리 시작")
            
            cleanup_tasks = []
            
            if self.visible_page:
                logger.debug("📄 visible_page 정리 중...")
                cleanup_tasks.append(self._safe_close_page(self.visible_page))
                self.visible_page = None
            
            if self.visible_browser:
                logger.debug("🌐 visible_browser 정리 중...")
                cleanup_tasks.append(self._safe_close_browser(self.visible_browser))
                self.visible_browser = None
            
            if self.visible_playwright:
                logger.debug("🎭 visible_playwright 정리 중...")
                cleanup_tasks.append(self._safe_stop_playwright(self.visible_playwright))
                self.visible_playwright = None
            
            # 모든 정리 작업을 병렬로 실행 (타임아웃 5초)
            if cleanup_tasks:
                try:
                    await asyncio.wait_for(
                        asyncio.gather(*cleanup_tasks, return_exceptions=True),
                        timeout=5.0
                    )
                except asyncio.TimeoutError:
                    logger.warning("⏰ 브라우저 정리 타임아웃 (5초)")
                except Exception as e:
                    logger.warning(f"⚠️ 브라우저 정리 중 일부 오류: {e}")
            
            logger.info("✅ 별도 브라우저 정리 완료")
            
        except Exception as e:
            logger.warning(f"💥 별도 브라우저 정리 중 오류: {e}")
    
    async def _safe_close_page(self, page):
        """안전한 페이지 닫기"""
        try:
            await page.close()
            logger.debug("📄 페이지 정리 완료")
        except Exception as e:
            logger.debug(f"페이지 정리 오류 (무시): {e}")
    
    async def _safe_close_browser(self, browser):
        """안전한 브라우저 닫기"""
        try:
            await browser.close()
            logger.debug("🌐 브라우저 정리 완료")
        except Exception as e:
            logger.debug(f"브라우저 정리 오류 (무시): {e}")
    
    async def _safe_stop_playwright(self, playwright):
        """안전한 Playwright 중지"""
        try:
            await playwright.stop()
            logger.debug("🎭 Playwright 정리 완료")
        except Exception as e:
            logger.debug(f"Playwright 정리 오류 (무시): {e}")
    
    async def open_naver_with_system_browser(self) -> bool:
        """시스템 기본 브라우저로 네이버 로그인 페이지 열기"""
        try:
            logger.info("🌐 시스템 기본 브라우저로 네이버 열기 시도")
            
            url = "https://nid.naver.com/nidlogin.login"
            
            # 운영체제별 최적화된 브라우저 열기
            system = platform.system().lower()
            
            if system == "windows":
                logger.info("💻 Windows 환경에서 브라우저 열기")
                try:
                    # 방법 1: start 명령 사용 (Windows)
                    subprocess.run(["start", url], shell=True, check=True)
                    logger.info("✅ start 명령으로 브라우저 열기 성공")
                    return True
                except:
                    logger.warning("⚠️ start 명령 실패, webbrowser 모듈 사용")
            
            # 방법 2: webbrowser 모듈 사용 (크로스 플랫폼)
            logger.info("🔧 webbrowser 모듈로 브라우저 열기 시도")
            success = webbrowser.open(url)
            
            if success:
                logger.info("✅ 시스템 브라우저로 네이버 로그인 페이지 열기 성공")
                return True
            else:
                logger.warning("❌ webbrowser.open() 반환값 False")
                
                # 방법 3: 강제로 기본 브라우저 실행 (Windows)
                if system == "windows":
                    try:
                        logger.info("🔧 Windows 기본 브라우저 강제 실행 시도")
                        subprocess.run(["rundll32", "url.dll,FileProtocolHandler", url], check=True)
                        logger.info("✅ rundll32로 브라우저 열기 성공")
                        return True
                    except Exception as e:
                        logger.warning(f"⚠️ rundll32 실행 실패: {e}")
                
                return False
                
        except Exception as e:
            logger.error(f"💥 시스템 브라우저로 네이버 열기 실패: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")
            return False
    
    async def show_manual_guidance(self) -> bool:
        """사용자 수동 안내 메시지 표시"""
        try:
            # NotificationManager를 사용하여 안내 메시지 표시
            from ..utils.notification import NotificationManager
            
            logger.info("📢 사용자 수동 안내 메시지 표시")
            
            title = "🔐 네이버 로그인 안내"
            message = "자동 브라우저 창 열기에 실패했습니다.\n\n수동으로 브라우저를 열어 naver.com에 로그인해주세요.\n\n로그인 후 앱이 자동으로 감지합니다."
            url = "https://nid.naver.com/nidlogin.login"
            
            # 동기 메서드 호출
            NotificationManager.show_notification(title, message, url)
            
            logger.info("✅ 사용자 안내 메시지 표시 완료")
            
            # 추가적으로 클립보드에 URL 복사 시도
            try:
                subprocess.run(['clip'], input=url.encode('utf-8'), check=True, 
                             creationflags=subprocess.CREATE_NO_WINDOW)
                logger.info("📋 네이버 로그인 URL이 클립보드에 복사됨")
            except:
                logger.debug("클립보드 복사 실패 (무시)")
            
            return True
            
        except Exception as e:
            logger.error(f"💥 사용자 안내 메시지 표시 실패: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")
            return False

    async def _monitor_login_completion(self):
        """별도 브라우저에서 로그인 완료 감지 및 자동 정리"""
        try:
            if not self.visible_page:
                logger.warning("로그인 모니터링: visible_page가 없음")
                return
            
            logger.info("🔍 로그인 완료 감지 모니터링 시작 (최대 5분)")
            
            # 최대 5분 동안 30초 간격으로 확인
            max_monitoring_time = 300  # 5분
            check_interval = 30       # 30초
            checks_done = 0
            max_checks = max_monitoring_time // check_interval
            
            for check_num in range(max_checks):
                try:
                    await asyncio.sleep(check_interval)
                    checks_done += 1
                    
                    logger.debug(f"로그인 완료 확인 중... ({checks_done}/{max_checks})")
                    
                    # 브라우저가 여전히 유효한지 확인
                    if not self.visible_page or not self.visible_browser:
                        logger.info("로그인 모니터링: 브라우저가 이미 닫힘")
                        return
                    
                    # 현재 URL 확인
                    current_url = await self.visible_page.url
                    logger.debug(f"현재 URL: {current_url}")
                    
                    # 네이버 메인 페이지나 로그인 성공 페이지인지 확인
                    success_indicators = [
                        "naver.com" in current_url and "/nidlogin.login" not in current_url,
                        "nid.naver.com/user2/help/myInfo" in current_url,
                        "nid.naver.com/nidregister.form" in current_url
                    ]
                    
                    if any(success_indicators):
                        logger.info("✅ 네이버 메인 페이지 감지 - 로그인 완료 가능성 높음")
                        
                        # 로그인 상태 확인 (DOM 요소 확인)
                        try:
                            # 네이버 로그인 버튼이 없으면 로그인된 상태
                            login_btn_exists = await self.visible_page.query_selector("a[href*='nidlogin.login']")
                            
                            # 내 정보 관련 요소가 있으면 로그인된 상태
                            my_info_selectors = [
                                ".MyView-module__my_info___GNmHz",
                                ".gnb_my",
                                "[data-clk='gnb.myinfo']",
                                ".btn_my"
                            ]
                            
                            my_info_found = False
                            for selector in my_info_selectors:
                                try:
                                    element = await self.visible_page.wait_for_selector(selector, timeout=2000)
                                    if element:
                                        my_info_found = True
                                        logger.info(f"✅ 로그인 상태 확인됨 (요소: {selector})")
                                        break
                                except:
                                    continue
                            
                            if my_info_found and not login_btn_exists:
                                logger.info("🎉 네이버 로그인 완료 감지!")
                                
                                # 세션 데이터를 메인 헤드리스 브라우저로 동기화
                                await self.sync_session_to_main_browser()
                                
                                # 3초 대기 후 브라우저 정리
                                await asyncio.sleep(3)
                                await self.close_visible_browser()
                                logger.info("🗂️ 로그인 완료 후 별도 브라우저 정리 완료")
                                return
                                
                        except Exception as e:
                            logger.debug(f"로그인 상태 확인 중 오류: {e}")
                            
                    # 로그인 페이지에서 벗어났는지만 확인 (간단한 방법)
                    elif "naver.com" in current_url and "/nidlogin.login" not in current_url:
                        logger.info("📱 로그인 페이지에서 벗어남 - 5초 후 브라우저 정리")
                        await asyncio.sleep(5)
                        await self.close_visible_browser()
                        logger.info("🗂️ 페이지 이동 감지 후 별도 브라우저 정리 완료")
                        return
                    
                except Exception as e:
                    logger.warning(f"로그인 완료 확인 중 오류: {e}")
                    continue
            
            # 최대 시간 초과 시 자동 정리
            logger.info("⏰ 로그인 모니터링 시간 초과 (5분) - 브라우저 자동 정리")
            await self.close_visible_browser()
            
        except Exception as e:
            logger.error(f"💥 로그인 완료 모니터링 오류: {e}")
            import traceback
            logger.error(f"상세 오류:\n{traceback.format_exc()}")
            
            # 오류 발생 시에도 브라우저 정리
            try:
                await self.close_visible_browser()
            except:
                pass

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        await self.start_browser()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.close_browser()

# 전역 세션 인스턴스
naver_session = NaverSession()