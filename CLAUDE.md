# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XMUCourseHelper is a Python-based automated course enrollment assistant for Xiamen University (XMU). It monitors course availability in real-time and can automatically enroll students when seats become available.

## Commands

```bash
# Setup
python -m venv venv
.\venv\Scripts\activate          # Windows
source venv/bin/activate         # Linux/macOS
python -m pip install -r requirements.txt

# Run
python client.py
```

No formal test suite or linting is configured.

## Architecture

```
XMUCourseHelper/
├── client.py          # Main XMUClient class & interactive CLI entry point
├── captcha.py         # CAPTCHA recognition (LLM, API, manual methods)
├── utils/
│   └── aes_util.py    # AES encryption for password (ECB mode, key: "MWMqg2tPcDkxcm11")
├── config/
│   └── user.yaml      # User credentials & settings (required, gitignored)
├── info/              # Static reference data (course types, faculties, locations)
└── cache/             # Runtime session cache (auto-generated, gitignored)
```

## Core Flow

1. **Authentication**: Load config → Fetch CAPTCHA → Solve (LLM-based) → Encrypt password → Login → Get JWT token & batch ID
2. **Course Selection**: Interactive CLI menu to search and add courses to watch list
3. **Monitoring Loop**: Poll API every N seconds → Detect enrollment changes → Trigger callbacks on vacancy → Optional auto-enroll

## Key Classes

**XMUClient** (`client.py`):
- `login()` - Authenticate with XMU system
- `search_courses(teaching_class_type, keyword, **extra_params)` - Query available courses
- `add_watch(KCH, JXBID, subscriber)` - Add course to monitoring list
- `add_course(KCH, clazzId, clazzType)` - Attempt enrollment
- `start_monitoring(on_change, on_vacancy)` - Begin continuous monitoring
- `save(filepath)` / `load(filepath)` - Session persistence
- `_request(method, endpoint, max_retries, retry_forever, **kwargs)` - HTTP wrapper with retry logic

**Teaching Class Types** (in `info/clazzType.json`):
- TJKC (major), FANKC (other grade), FAWKC (non-plan), TYKC (PE/English), XGKC (electives), ALLKC (search all)

## Important Implementation Details

- **Rate Limiting**: Minimum 1.1s between requests to avoid IP blocking
- **Retry Logic**: Exponential backoff with `retry_forever` option for critical operations; session auto-reset after max retries
- **Session Persistence**: Token, batch_id, cookies, watch_list serialized to `cache/XMUClient.json` for 24/7 operation across restarts
- **SSL**: Verification disabled (`verify=False`)
- **Campus Codes**: 1=Siming, 6=Xiangan (default), 9=Zhangzhou

## API Base URL

`https://xk.xmu.edu.cn/xsxkxmu`

Key endpoints: `/auth/captcha`, `/auth/login`, `/elective/user`, `/elective/xmu/clazz/list`, `/elective/clazz/add`

## Configuration

`config/user.yaml` structure:
```yaml
username: "<student_id>"
password: "<password>"
campus: "<campus_id>"           # 1, 6, or 9
auto_add_enable: True/False
check_interval: 120             # seconds

captcha:
  type: "llm"
  base_url: "<api_url>"
  api_key: "<api_key>"
  model: "doubao-seed-1-6-thinking-250615"
```

## Dependencies

requests, pycryptodomex (AES encryption), pillow (image processing), PyYAML
