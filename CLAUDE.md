# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소의 코드를 작업할 때 참고할 가이드라인을 제공합니다.

## 프로젝트 개요

한국 VTuber 스트리머들(아리사, 카린, 엘리, 에리스, 소풍왔니, 아라하시 타비)을 여러 플랫폼에서 모니터링하고 실시간 알림을 보내는 Python 기반 Windows 데스크톱 애플리케이션입니다.

**알림 기능:**
- CHZZK 라이브 스트림 알림
- 네이버 카페 새 게시물 알림  
- X(Twitter) 새 트윗 알림

## 환경 설정

- Python 3.12.10 가상환경 (`venv/` 디렉토리)
- 활성화: `venv\Scripts\activate` (Windows)
- 의존성 설치: `pip install -r requirements.txt`
- 브라우저 설치: `playwright install`

## 개발 명령어

- **애플리케이션 실행**: `python main.py` 또는 `run.bat`
- **패키지 설치**: `pip install -r requirements.txt && playwright install`
- **로그 확인**: `logs/` 디렉토리의 일별 로그 파일 확인 (자동 로테이션, 10MB 제한)
- **브라우저 데이터 정리**: `data/browser_data/` 폴더 삭제 (완전 초기화, 재로그인 필요)
- **설정 초기화**: `data/` 폴더의 파일들 삭제

## 프로젝트 아키텍처

### 핵심 컴포넌트

- **`main.py`**: 애플리케이션 진입점 및 오케스트레이터, 시스템 트레이 기능 통합, 주기적 캐시 정리
- **`streamlit_run.py`**: Streamlit 앱 런처 및 UI 진입점
- **`src/config.py`**: JSON 파일 저장을 통한 설정 관리
- **`src/ui/main_window.py`**: 스트리머 관리, 알림, 설정 탭이 있는 Streamlit 기반 메인 UI
- **`src/utils/cache_cleaner.py`**: 브라우저 캐시 및 임시 파일 정리 유틸리티 (자동 주기적 실행)

### 모니터링 시스템

- **`src/monitors/chzzk_monitor.py`**: CHZZK API 폴링을 통한 라이브 상태 확인
- **`src/monitors/cafe_monitor.py`**: Playwright를 통한 네이버 카페 게시물 모니터링
- **`src/monitors/twitter_monitor.py`**: Nitter 인스턴스를 통한 X(Twitter) RSS 모니터링

### 브라우저 자동화

- **`src/browser/naver_session.py`**: Playwright 기반 네이버 로그인 및 세션 관리
- **듀얼 브라우저 아키텍처**: 별도의 헤드리스 모니터링 브라우저와 사용자 상호작용 브라우저
- **로그인 완료 감지**: 성공적인 로그인 후 보이는 브라우저의 자동 모니터링 및 정리
- **다단계 재로그인**: 3단계 전략 (Playwright → 시스템 브라우저 → 수동 가이드)
- 쿠키/localStorage 보존을 통한 영구 브라우저 컨텍스트
- 로그인 후 자동 헤드리스 모드 전환

### 유틸리티

- **`src/utils/notification.py`**: 프로필 이미지와 최적화된 HTTP 클라이언트를 사용한 Windows 토스트 알림
- **`src/utils/logger.py`**: 10MB 제한 RotatingFileHandler, 7일 이상 된 로그 자동 정리
- **`src/utils/autostart.py`**: Windows 레지스트리 기반 자동 시작 관리
- **`src/utils/cache_cleaner.py`**: 비동기 브라우저 캐시 및 임시 파일 정리 (1시간마다 자동 실행)

### IPC 통신

- **파일 기반 IPC**: UI와 모니터링 프로세스가 `data/` 디렉토리의 JSON 파일을 통해 통신
- **요청/응답 패턴**: 로그인 요청, 상태 확인, 결과가 임시 JSON 파일 사용
- **신호 처리**: 메인 모니터링 루프가 2초마다 UI 신호 처리

### 데이터 저장

`data/` 디렉토리에 JSON 파일로 모든 데이터 저장:
- `streamers.json`: 스트리머 설정 및 ID
- `notifications.json`: 알림 기록
- `settings.json`: 애플리케이션 설정
- `browser_session.json`: 네이버 로그인 세션 데이터

## 주요 기술 세부사항

### API 엔드포인트
- **CHZZK**: `https://api.chzzk.naver.com/polling/v2/channels/{id}/live-status`
- **네이버 카페**: `https://cafe.naver.com/ca-fe/cafes/{CLUB_ID}/members/{userId}`
- **Nitter RSS**: `https://nitter.instance/{username}/rss`

### 브라우저 세션 관리
- **듀얼 브라우저 시스템**: 헤드리스 모니터링 브라우저 + 사용자 상호작용용 별도 브라우저
- **세션 지속성**: `data/browser_data/` 저장소를 사용한 Playwright 영구 컨텍스트
- **로그인 감지**: DOM 요소 (`MyView-module__my_info___GNmHz`)와 쿠키 기반 검증
- **자동 정리**: 로그인 완료 또는 5분 타임아웃 후 보이는 브라우저 자동 종료
- **브라우저 분리 아키텍처**: 모니터링과 사용자 상호작용 간 충돌 방지

### 모니터링 로직
- 모든 모니터가 설정 가능한 간격으로 비동기 루프에서 실행
- 첫 번째 확인은 기준선 설정 (알림 없음)
- 후속 확인은 이전 상태와 비교
- 알림용 프로필 이미지를 CHZZK 채널 API에서 가져옴

### 오류 처리
- RSS 피드용 여러 Nitter 인스턴스를 백업으로 사용
- 서비스 사용 불가 시 우아한 성능 저하
- 디버깅을 위한 포괄적인 로깅

## 개발 패턴

- **Async/await**: 모든 I/O 작업에 asyncio 사용
- **JSON 저장**: 데이터베이스 없는 경량 데이터 지속성
- **모듈러 설계**: 각 플랫폼별 별도 모니터
- **이벤트 기반**: 상태 변경 시에만 알림
- **리소스 관리**: 연결 풀링을 통한 브라우저/HTTP 클라이언트의 적절한 정리
- **HTTP 최적화**: 연결 제한 (max_keepalive_connections=5, max_connections=10)
- **메모리 효율성**: 로그 로테이션, 자동 캐시 정리, 최적화된 브라우저 컨텍스트

## 일반적인 작업

- **새 스트리머 추가**: config.py의 default_streamers 수정 또는 UI 사용
- **모니터링 플랫폼 추가**: `src/monitors/`에 새 모니터 생성
- **알림 형식 수정**: NotificationManager 메서드 편집
- **UI 변경**: `src/ui/main_window.py` Streamlit 컴포넌트 업데이트
- **모니터링 디버깅**: 로그 확인 및 디버그 로깅 레벨 활성화
- **성능 문제 해결**: 메모리 문제 시 자동 캐시 정리 시스템 활용
- **브라우저 문제**: `data/browser_data/` 삭제하여 네이버 세션 재설정
- **강제 재로그인**: UI "네이버 다시 로그인" 버튼 사용하여 다단계 백업 전략 트리거

## 설정 참고사항

- **여러 카페 ID**: 스트리머별 다른 카페 커뮤니티 지원 (30919539, 30288368, 29424353)
- **체크 간격**: 기본 30초, 설정에서 변경 가능
- **캐시 정리 간격**: 기본 3600초(1시간), cache_cleanup_interval 설정으로 변경 가능
- **프로필 이미지**: 임시 디렉토리에 캐시, 80x80으로 자동 리사이즈
- **자동 시작**: Windows 레지스트리 HKCU\Run 키 사용
- **UI 캐싱**: UI 깜빡임 방지를 위해 30초간 로그인 상태 캐시
- **HTTP 타임아웃**: CHZZK 10초, Twitter RSS 15초, 효율성을 위한 연결 풀링
- **로그 관리**: 10MB 로테이션 파일, 7일 후 자동 정리

## 최근 최적화 (2025-07-01)

### 코드 정리
- 미사용 파일 제거: `cleanup_cache.py`, `src/ui/components.py`, `src/ui/main_window_backup.py`
- 미사용 유틸리티 제거: `src/utils/memory.py`, `src/utils/performance.py`
- 중복 임포트 제거 및 통합
- 모든 6명의 모니터링 대상 스트리머를 포함하도록 default_streamers 업데이트

### 성능 개선
- **HTTP 연결 풀링**: 모든 모니터가 최적화된 연결 제한 사용
- **자동 캐시 관리**: 새로운 `src/utils/cache_cleaner.py`를 통한 주기적 정리 (1시간마다)
- **로그 최적화**: RotatingFileHandler로 과도한 디스크 사용 방지
- **브라우저 효율성**: 듀얼 브라우저 아키텍처로 리소스 충돌 감소

### 자동 캐시 정리 시스템
- **`src/utils/cache_cleaner.py`**: 세션 데이터 보존하면서 브라우저 캐시 안전 제거
- **주기적 실행**: main.py에 통합되어 1시간마다 자동 실행
- **설정 가능**: cache_cleanup_interval 설정으로 간격 조정 가능
- **비동기 처리**: 메인 모니터링과 독립적으로 실행
- **자동 로그 정리**: 7일 이상 된 로그 제거
- **캐시 크기 모니터링**: 정리 없이 브라우저 데이터가 326MB+ 증가 가능

### 유지보수 유틸리티
- **자동 캐시 정리**: 세션 데이터 보존하면서 브라우저 캐시 안전 제거
- **자동 로그 정리**: 7일 이상 된 로그 제거
- **실시간 모니터링**: 캐시 정리 결과 로깅 및 통계

## 보안 고려사항

- 브라우저 세션 데이터는 로컬에 저장 (Playwright에 의해 암호화)
- 소스에 민감한 데이터 하드코딩 없음
- 표준 Windows 알림 시스템 사용
- 네트워크 요청에 적절한 User-Agent 헤더 사용
- 모니터링과 사용자 상호작용 브라우저 간 세션 격리