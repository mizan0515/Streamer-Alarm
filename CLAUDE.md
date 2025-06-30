# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python-based Windows desktop application that monitors Korean VTuber streamers (아리사, 카린, 엘리, 에리스, 소풍왔니, 아라하시 타비) across multiple platforms and sends real-time notifications for:
- CHZZK live stream alerts
- Naver Cafe new posts
- X(Twitter) new tweets

## Environment Setup

- Python 3.12.10 virtual environment in `venv/`
- Activate: `venv\Scripts\activate` (Windows)
- Install dependencies: `pip install -r requirements.txt`
- Install browsers: `playwright install`

## Development Commands

- **Run application**: `python main.py` or `run.bat`
- **Install packages**: `pip install -r requirements.txt && playwright install`
- **View logs**: Check `logs/` directory for daily log files with automatic rotation (10MB limit)
- **Clean browser cache**: `python cleanup_cache.py` (removes cache files while preserving session data)
- **Clean browser data**: Delete `data/browser_data/` folder (full reset, requires re-login)
- **Reset settings**: Delete files in `data/` folder

## Project Architecture

### Core Components

- **`main.py`**: Application entry point and orchestrator with integrated system tray functionality
- **`streamlit_run.py`**: Streamlit app launcher and UI entry point
- **`src/config.py`**: Configuration management with JSON file storage
- **`src/ui/main_window.py`**: Streamlit-based main UI with tabs for streamer management, notifications, and settings
- **`cleanup_cache.py`**: Browser cache and temporary file cleanup utility

### Monitoring System

- **`src/monitors/chzzk_monitor.py`**: CHZZK API polling for live status
- **`src/monitors/cafe_monitor.py`**: Naver Cafe post monitoring via Playwright
- **`src/monitors/twitter_monitor.py`**: X(Twitter) RSS monitoring via Nitter instances

### Browser Automation

- **`src/browser/naver_session.py`**: Playwright-based Naver login and session management
- **Dual Browser Architecture**: Separate headless monitoring browser and visible user interaction browser
- **Login Completion Detection**: Automatic monitoring and cleanup of visible browsers after successful login
- **Multi-fallback Re-login**: 3-tier strategy (Playwright → System Browser → Manual Guidance)
- Persistent browser context with cookie/localStorage preservation
- Automatic headless mode switching after login

### Utilities

- **`src/utils/notification.py`**: Windows toast notifications with profile images and optimized HTTP client
- **`src/utils/logger.py`**: RotatingFileHandler with 10MB limit, automatic cleanup of logs older than 7 days
- **`src/utils/autostart.py`**: Windows registry-based autostart management

### IPC Communication

- **File-based IPC**: UI and monitoring processes communicate via JSON files in `data/` directory
- **Request/Response Pattern**: Login requests, status checks, and results use temporary JSON files
- **Signal Processing**: Main monitoring loop processes UI signals every 2 seconds

### Data Storage

All data stored as JSON files in `data/` directory:
- `streamers.json`: Streamer configurations and IDs
- `notifications.json`: Notification history
- `settings.json`: Application settings
- `browser_session.json`: Naver login session data

## Key Technical Details

### API Endpoints
- **CHZZK**: `https://api.chzzk.naver.com/polling/v2/channels/{id}/live-status`
- **Naver Cafe**: `https://cafe.naver.com/ca-fe/cafes/{CLUB_ID}/members/{userId}`
- **Nitter RSS**: `https://nitter.instance/{username}/rss`

### Browser Session Management
- **Dual Browser System**: Headless monitoring browser + separate visible browser for user interaction
- **Session Persistence**: Uses Playwright persistent context with `data/browser_data/` storage
- **Login Detection**: DOM elements (`MyView-module__my_info___GNmHz`) and cookie-based validation
- **Auto-cleanup**: Visible browsers automatically close after login completion or 5-minute timeout
- **Browser Separation Architecture**: Prevents conflicts between monitoring and user interaction

### Monitoring Logic
- All monitors run in async loops with configurable intervals
- First check establishes baseline (no notifications)
- Subsequent checks compare against previous state
- Profile images fetched from CHZZK channel API for notifications

### Error Handling
- Multiple Nitter instances as fallbacks for RSS feeds
- Graceful degradation when services are unavailable
- Comprehensive logging for debugging

## Development Patterns

- **Async/await**: All I/O operations use asyncio
- **JSON storage**: Lightweight data persistence without database
- **Modular design**: Separate monitors for each platform
- **Event-driven**: Notifications only on state changes
- **Resource management**: Proper cleanup of browser/HTTP clients with connection pooling
- **HTTP Optimization**: Connection limits (max_keepalive_connections=5, max_connections=10)
- **Memory Efficiency**: Rotating logs, automatic cache cleanup, optimized browser contexts

## Common Tasks

- **Add new streamer**: Modify default_streamers in config.py or use UI
- **Add monitoring platform**: Create new monitor in `src/monitors/`
- **Modify notification format**: Edit NotificationManager methods
- **Change UI**: Update `src/ui/main_window.py` Streamlit components
- **Debug monitoring**: Check logs and enable debug logging level
- **Performance troubleshooting**: Run `python cleanup_cache.py` for memory issues
- **Browser issues**: Delete `data/browser_data/` to reset Naver session
- **Force re-login**: Use UI "네이버 다시 로그인" button to trigger multi-fallback strategy

## Configuration Notes

- **Multiple Cafe IDs**: Supports different cafe communities per streamer (30919539, 30288368, 29424353)
- **Check interval**: Default 30 seconds, configurable in settings
- **Profile images**: Cached in temp directory, auto-resized to 80x80
- **Autostart**: Uses Windows registry HKCU\Run key
- **UI Caching**: Login status cached for 30 seconds to prevent UI flickering
- **HTTP Timeouts**: 10s for CHZZK, 15s for Twitter RSS, connection pooling for efficiency
- **Log Management**: 10MB rotating files, auto-cleanup after 7 days

## Recent Optimizations (2025-06-30)

### Code Cleanup
- Removed unused `src/tray.py` (functionality integrated into main.py)
- Eliminated backup/flet_ui directory (old UI framework files)
- Consolidated imports and removed duplications
- Updated default_streamers to include all 6 monitored streamers

### Performance Improvements
- **HTTP Connection Pooling**: All monitors use optimized connection limits
- **Memory Management**: Browser cache cleanup utility (`cleanup_cache.py`)
- **Log Optimization**: RotatingFileHandler prevents excessive disk usage
- **Browser Efficiency**: Dual browser architecture reduces resource conflicts

### Maintenance Utilities
- **`cleanup_cache.py`**: Safely removes browser cache while preserving session data
- **Automatic Log Cleanup**: Removes logs older than 7 days
- **Cache Size Monitoring**: Browser data can grow to 326MB+ without cleanup

## Security Considerations

- Browser session data stored locally (encrypted by Playwright)
- No sensitive data hardcoded in source
- Uses standard Windows notification system
- Network requests use proper User-Agent headers
- Session isolation between monitoring and user interaction browsers