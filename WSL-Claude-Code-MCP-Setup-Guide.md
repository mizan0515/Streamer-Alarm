# WSL에서 Claude Code MCP 서버 자동 설정 가이드

## 개요
WSL 환경에서 Claude Code가 MCP(Model Context Protocol) 서버를 자동으로 설정하고 사용할 수 있도록 하는 완전 자동화 가이드입니다.

## 🤖 Claude Code 자동 실행 명령어들

Claude Code가 이 문서를 보고 자동으로 실행할 수 있는 명령어들입니다.

### 1. 사전 요구사항 확인
```bash
# Node.js 및 npm 버전 확인
node --version && npm --version
```

### 2. MCP 서버 설치 (Claude Code가 실행할 명령어)
```bash
# Desktop Commander MCP 설치
npx -y @smithery/cli@latest install @wonderwhy-er/desktop-commander --client claude --key 760acb5b-9004-430e-a88d-e9e3742cbff8

# Playwright MCP 설치  
npx -y @smithery/cli@latest install @microsoft/playwright-mcp --client claude --key 760acb5b-9004-430e-a88d-e9e3742cbff8
```

### 3. 설정 파일 백업 및 수정 (Claude Code가 실행할 스크립트)
```bash
# 설정 파일 백업
cp ~/.claude.json ~/.claude.json.backup

# Python 스크립트로 설정 자동 추가
python3 -c "
import json
import os

# 현재 작업 디렉토리 가져오기
project_path = os.getcwd()

# 설정 파일 읽기
with open(os.path.expanduser('~/.claude.json'), 'r') as f:
    config = json.load(f)

# 프로젝트가 설정에 없으면 기본 구조 생성
if project_path not in config.get('projects', {}):
    if 'projects' not in config:
        config['projects'] = {}
    config['projects'][project_path] = {
        'allowedTools': [],
        'history': [],
        'mcpContextUris': [],
        'mcpServers': {},
        'enabledMcpjsonServers': [],
        'disabledMcpjsonServers': [],
        'hasTrustDialogAccepted': False
    }

# MCP 서버 설정 추가
config['projects'][project_path]['mcpServers'] = {
    'desktop-commander': {
        'command': 'npx',
        'args': [
            '-y',
            '@smithery/cli@latest',
            'run',
            '@wonderwhy-er/desktop-commander',
            '--key',
            '760acb5b-9004-430e-a88d-e9e3742cbff8'
        ]
    },
    'playwright-automation': {
        'command': 'npx',
        'args': [
            '-y',
            '@smithery/cli@latest',
            'run',
            '@microsoft/playwright-mcp',
            '--key',
            '760acb5b-9004-430e-a88d-e9e3742cbff8'
        ]
    }
}

# 파일 저장
with open(os.path.expanduser('~/.claude.json'), 'w') as f:
    json.dump(config, f, indent=2)

print(f'✅ MCP 서버 설정이 {project_path}에 성공적으로 추가되었습니다.')
"
```

### 4. 설정 확인 (Claude Code가 실행할 명령어)
```bash
# 설정이 올바르게 추가되었는지 확인
grep -A 20 "mcpServers" ~/.claude.json | head -25
```

### 5. MCP 서버 테스트 (Claude Code가 실행할 명령어)
```bash
# Desktop Commander 테스트
npx -y @smithery/cli@latest run @wonderwhy-er/desktop-commander --key 760acb5b-9004-430e-a88d-e9e3742cbff8 --help

# Playwright MCP 테스트
npx -y @smithery/cli@latest run @microsoft/playwright-mcp --key 760acb5b-9004-430e-a88d-e9e3742cbff8 --help
```

## 🔧 Claude Code 실행 순서

Claude Code가 이 가이드를 보고 실행해야 할 순서:

1. **사전 확인**: Node.js/npm 버전 체크
2. **MCP 설치**: 두 개의 install 명령어 실행
3. **설정 백업**: claude.json 백업
4. **설정 추가**: Python 스크립트로 자동 설정
5. **설정 확인**: grep으로 설정 검증
6. **서버 테스트**: 두 MCP 서버 동작 확인
7. **완료 알림**: `/mcp` 명령어로 최종 확인 안내

## 🚨 중요: 자동 실행 방식

**Claude Code는 MCP 서버를 자동으로 실행합니다!**

- ❌ **불필요**: 별도 MCP 서버 프로세스 실행
- ✅ **자동**: Claude Code가 필요할 때 자동으로 MCP 서버 실행
- ✅ **관리**: 프로세스 생명주기를 Claude Code가 자동 관리

### 동작 방식
1. Claude Code 시작
2. `mcp__` 도구 사용 시 MCP 서버 자동 실행  
3. 세션 종료 시 자동 정리

## 📁 설정 파일 구조 예시

완료 후 `~/.claude.json`의 구조:

```json
{
  "projects": {
    "/현재/프로젝트/경로": {
      "mcpServers": {
        "desktop-commander": {
          "command": "npx",
          "args": [
            "-y",
            "@smithery/cli@latest",
            "run",
            "@wonderwhy-er/desktop-commander",
            "--key",
            "760acb5b-9004-430e-a88d-e9e3742cbff8"
          ]
        },
        "playwright-automation": {
          "command": "npx",
          "args": [
            "-y",
            "@smithery/cli@latest",
            "run",
            "@microsoft/playwright-mcp",
            "--key",
            "760acb5b-9004-430e-a88d-e9e3742cbff8"
          ]
        }
      }
    }
  }
}
```

## 🔍 문제 해결

### 일반적인 오류와 해결책

**오류**: `The "file" argument must be of type string. Received undefined`
- **원인**: URL 기반 설정으로 잘못 설정됨
- **해결**: 위의 Python 스크립트 재실행

**오류**: MCP 서버 연결 실패  
- **확인**: Node.js 버전, npm 설치, API 키 정확성
- **해결**: 개별 MCP 서버 테스트 명령어 실행

### 디버그 명령어 (Claude Code가 실행할 수 있음)
```bash
# 디버그 모드로 Claude Code 실행
claude --debug

# 로그 파일 확인
ls -la ~/.cache/claude-cli-nodejs/*/mcp-logs-*

# 캐시 정리 (필요시)
rm -rf ~/.cache/claude-cli-nodejs/*/mcp-logs-*
```

## ✅ 최종 확인

설정 완료 후 확인사항:

1. **Claude Code 재시작**
2. **`/mcp` 명령어 실행**
3. **`mcp__` 접두사 도구들 사용 가능 확인**

## 🛠️ 사용 가능한 MCP 도구들

설정 완료 후 사용 가능한 도구들:

- `mcp__desktop_commander_*`: Windows 데스크톱 자동화 도구
- `mcp__playwright_*`: 웹 브라우저 자동화 도구

## 📋 핵심 정보 요약

- **API 키**: `760acb5b-9004-430e-a88d-e9e3742cbff8`
- **설정 파일**: `~/.claude.json`
- **연결 방식**: `stdio` (command + args)
- **MCP 서버**: Desktop Commander, Playwright Automation
- **필수 도구**: Node.js, npm, npx

---

## 💡 Claude Code에게

이 문서의 명령어들을 순서대로 실행하면 WSL 환경에서 MCP 서버가 자동으로 설정됩니다. 모든 명령어는 Claude Code가 직접 실행할 수 있도록 구성되어 있습니다.