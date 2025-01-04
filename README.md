```
XMUCourseHelper
├─ .gitignore
├─ alert.mp3
├─ captcha.py
├─ course_controller.py
├─ info
│  ├─ clazzType.json
│  ├─ FXYX.json
│  └─ KKDW.json
├─ login.py
├─ README.md
├─ requirements.txt
├─ selection.py
├─ utils
│  ├─ aes_util.py
│  ├─ config_handler.py
│  ├─ helpers.py
│  └─ __init__.py
├─ watch.py
└─ xmuxk.py

```

参考项目 [XMUCourseEnroller](https://github.com/usamimeri/XMUCourseEnroller)

xmu选课助手。目前支持添加监听课程列表，间隔一定时间检查课容量空位，非已满时自动发出提醒。

## 配置过程

在项目下新建`config/user.yaml`文件，加入下列内容：

```yaml
username: "<学号>"
password: "<密码>"
campus: "<校区id>"      # 不填这个默认翔安校区，翔安校区填入6，漳州校区填入9，思明校区填入1

captcha_auto: False     # 自动开启验证码识别，需要适配验证码API，默认False

```

如果有验证码API，在`config/captcha.yaml`中加入API的配置：

```yaml

captcha_token: "<API token>"

```

## 使用方法

### 添加关注课程列表

```bash
python xmuxk.py --watch --type <课程类型> [--key <关键词>]  # type 必填，决定是从哪个页面获取课程列表 key 可以不填
```

例如，关注本专业计划课程里的数据库

```bash
python xmuxk.py --watch --type "本专业计划课程" --key "数据库"
```

选中课程后加入监听列表。

```
课程类型填入字段

"本专业计划课程",
"本专业其他年级课程",
"方案外课程",
"体育/大学英语课程",
"校选课"

```

### 开始监听

```bash
python xmuxk.py --listen [--interval <间隔时间>]  # interval 选填，单位秒，默认60
```


## 等待完成

- [ ] 有空缺时自动选课

- [ ] 接入聊天机器人

- [ ] kivy打包成安卓应用？这样可以在手机端后台运行