# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XMUCourseHelper is a Python CLI tool for Xiamen University (XMU) course enrollment automation. It monitors course availability on xk.xmu.edu.cn and can automatically enroll when spots open.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Add courses to watch list (--type is required)
python xmuxk.py --watch --type "本专业计划课程" --key "数据库"

# Start monitoring loop
python xmuxk.py --listen --interval 60

# Monitor with auto-enrollment
python xmuxk.py --listen --autoadd --interval 60

# With randomized intervals (±50%)
python xmuxk.py --listen --autoadd --random
```

Valid course types: `本专业计划课程`, `本专业其他年级课程`, `方案外课程`, `体育/大学英语课程`, `校选课`

## Architecture

**Entry Point**: `xmuxk.py` - CLI with argparse, main loop with retry logic (max 5 failures)

**Authentication Flow** (`login.py`):
- Loads credentials from `config/user.yaml`
- Fetches captcha, optionally auto-solves via external API (jfbym)
- AES-ECB encrypts password (fixed key: `MWMqg2tPcDkxcm11`)
- Maintains session with auth token and batchId

**Course Operations** (`course_controller.py`):
- `search_courses()` - POST to `/xsxkxmu/elective/xmu/clazz/list`
- `add_course()` - POST to `/xsxkxmu/elective/clazz/add` with secretVal

**Watch System** (`watch.py`):
- Interactive course selection with questionary
- Persists to `cache/watch_list.json`
- Each entry stores: JXBID, courseName_zh, clazzType, secretVal

**Monitoring Loop** (`xmuxk.py:listen_loop`):
1. Load watch list
2. Query each course's current capacity
3. If `numberOfSelected < classCapacity`: alert (sound + messagebox) and optionally auto-enroll
4. Successfully enrolled courses are removed from watch list
5. Sleep for interval (with optional random jitter)

## Configuration

Create `config/user.yaml`:
```yaml
username: "<学号>"
password: "<密码>"
campus: "6"  # 1=思明, 6=翔安, 9=漳州
captcha_auto: False
```

Optional `config/captcha.yaml` for auto captcha:
```yaml
captcha_token: "<API token>"
```

## Key Implementation Notes

- SSL verification is disabled globally
- Windows-specific: uses `windows-curses` and `ctypes.windll` for messageboxes
- Session retries up to 3 times with exponential backoff on network errors
- Type hints added for pylance support - maintain them when editing
