# XMUCourseHelper

参考项目 [XMUCourseEnroller](https://github.com/usamimeri/XMUCourseEnroller)

## 功能特性

- 监控指定课程的选课人数和容量
- 课程有空位时自动弹窗提醒 + 声音提示
- 支持自动选课（抢课）
- 支持验证码自动识别（通过大模型 API）
- 随机查询间隔，降低被检测风险

## 安装

```bash
pip install -r requirements.txt
```

## 配置

可直接修改`config.example`文件夹为`config`

### 1. 用户配置（必需）

创建 `config/user.yaml`：

```yaml
username: "学号"
password: "密码"
campus: "6"          # 校区代码: 1=思明, 6=翔安, 9=漳州
captcha_auto: false  # 是否启用自动验证码识别
```

### 2. 验证码配置（可选）

如需自动识别验证码，创建 `config/captcha.yaml`：

```yaml
# 大模型 API 配置（OpenAI 格式）
base_url: "https://api.openai.com/v1"   # API 地址
api_key: "sk-xxxx"                       # API Key
model: "gpt-4o"                          # 支持视觉的模型
```

验证码为简单的加减乘除计算题，程序会将图片发送给大模型进行识别计算。

---

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--watch` | 进入添加监听模式，交互式选择要监控的课程 |
| `--listen` | 进入持续监听模式，定时查询课程余量 |
| `--type` | 课程类型（添加监听时必需） |
| `--key` | 搜索关键词（可选） |
| `--interval` | 查询间隔秒数，默认 60 秒 |
| `--autoadd` | 启用自动选课，有空位时自动抢课 |
| `--random` | 启用随机间隔（在设定间隔的 ±50% 范围内波动） |

### 课程类型 (`--type`)

| 类型名称 | 说明 |
|----------|------|
| `本专业计划课程` | 本专业培养方案内的课程 |
| `本专业其他年级课程` | 本专业其他年级开设的课程 |
| `方案外课程` | 培养方案外的课程 |
| `体育/大学英语课程` | 体育课和大学英语 |
| `校选课` | 全校性选修课 |

---

## 使用方法

### 第一步：添加监听课程

使用 `--watch` 模式将想要抢的课程加入监听列表：

```bash
# 搜索并添加"数据库"相关的本专业课程
python xmuxk.py --watch --type "本专业计划课程" --key "数据库"

# 搜索并添加体育课
python xmuxk.py --watch --type "体育/大学英语课程" --key "羽毛球"

# 不指定关键词，浏览所有校选课
python xmuxk.py --watch --type "校选课"
```

程序会：
1. 登录选课系统（需输入验证码，或自动识别）
2. 列出搜索结果
3. 使用 **方向键** 选择课程，按 **回车** 确认
4. 确认后添加到监听列表

监听列表保存在 `cache/watch_list.json`，可直接编辑删除不需要的课程。

### 第二步：启动监听

添加完课程后，启动监听模式：

```bash
# 基础监听（仅提醒，不自动选课），默认 60 秒间隔
python xmuxk.py --listen

# 自定义查询间隔（30 秒）
python xmuxk.py --listen --interval 30

# 启用自动选课（推荐）
python xmuxk.py --listen --autoadd

# 自动选课 + 随机间隔（最推荐）
python xmuxk.py --listen --autoadd --random --interval 60
```

### 监听模式行为

程序会持续运行，循环执行以下操作：

1. 查询监听列表中每个课程的 **已选人数** 和 **容量**
2. 当 `已选人数 < 容量` 时：
   - 播放提示音 (`\a`)
   - 弹出 Windows 消息框提醒
   - 如果启用了 `--autoadd`，自动发起选课请求
3. 选课成功后，该课程自动从监听列表中移除
4. 等待指定间隔后，重复查询
5. 登录失效时自动重新登录（连续失败 5 次后弹出错误提示）

---

## 完整示例

```bash
# 1. 添加想抢的课程到监听列表
python xmuxk.py --watch --type "本专业计划课程" --key "机器学习"

# 2. 继续添加其他课程
python xmuxk.py --watch --type "校选课" --key "摄影"

# 3. 开始监听抢课（自动选课 + 随机间隔 45 秒左右）
python xmuxk.py --listen --autoadd --random --interval 45
```

---

## 文件结构

```
XMUCourseHelper/
├── xmuxk.py              # 主程序入口
├── login.py              # 登录模块（验证码获取、密码加密、登录请求）
├── captcha.py            # 验证码识别（调用大模型 API）
├── course_controller.py  # 课程查询 / 选课请求
├── watch.py              # 监听列表管理（添加、保存、加载）
├── config/
│   ├── user.yaml         # 用户配置（学号、密码、校区）
│   └── captcha.yaml      # 验证码 API 配置
├── cache/
│   └── watch_list.json   # 监听课程列表
├── info/
│   ├── clazzType.json    # 课程类型映射
│   ├── KKDW.json         # 开课单位
│   └── FXYX.json         # 分选院系
└── utils/
    ├── aes_util.py       # AES-ECB 密码加密
    └── helpers.py        # 辅助函数（console、style）
```

---

## 注意事项

1. **验证码**：每次登录需要验证码，启用 `captcha_auto: true` 可自动识别
2. **登录有效期**：session 会过期，程序会自动重新登录
3. **查询间隔**：建议 ≥ 30 秒，避免给服务器造成压力
4. **平台限制**：弹窗提醒使用了 Windows API，仅支持 Windows 系统
5. **网络问题**：程序内置重试机制，单次请求最多重试 3 次

---

## 待完成

- [x] 有空缺时自动选课
- [ ] 接入聊天机器人推送通知
- [ ] 跨平台支持（Linux/macOS/Android）
