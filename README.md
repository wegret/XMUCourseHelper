优化后的XMU选课助手（2026.1.4，已经将史山重构）

```
XMUCourseHelper
├─ .gitignore
├─ requirements.txt
├─ cache                    # （运行后会自动生成的缓存文件）
├─ config
│  └─ user.yaml             # 配置文件（需要预先配置！）
├─ utils
│  ├─ aes_util.py
│  └─ __init__.py
├─ captcha.py               # 验证码处理模块
├─ client.py                # 主要的客户端逻辑
├─ info
│  ├─ clazzType.json
│  ├─ FXYX.json
│  └─ KKDW.json
└─ README.md

```

参考项目 [XMUCourseEnroller](https://github.com/usamimeri/XMUCourseEnroller)

xmu选课助手。目前支持添加监听课程列表，间隔一定时间检查课容量空位，非已满时自动发出提醒。

## 配置过程

在项目下新建`config/user.yaml`文件，加入下列内容：

```yaml
username: "<学号>"
password: "<密码>"
campus: "<校区id>"      # 不填这个默认翔安校区，翔安校区填入6，漳州校区填入9，思明校区填入1
auto_add_enable: True   # 是否自动选课，如果作为脚本开启，就填入True
check_interval: 120     # 监听间隔时间，单位秒

captcha:
  type: "llm"
  base_url: "<base_url>"
  api_key: "<你的API Key>"
  model: "<模型名称>"

```

现在的验证码使用多模态LLM自动识别，我测试推荐使用豆包`doubao-seed-1-6-thinking-250615`模型，成功率比较高。

一个示例的`captcha`配置：

```yaml
captcha:
  type: "llm"
  base_url: "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
  api_key: "<你的API Key>"
  model: "doubao-seed-1-6-thinking-250615"
```

## 使用方法

控制台测试，直接使用`python client.py`即可。然后根据提示添加课程监控、开始循环。

```bash
python -m venv venv
source venv/bin/activate  # Linux or macOS
.\venv\Scripts\activate     # Windows

python -m pip install -r requirements.txt

python client.py

```


## 等待完成

- [ ] 测试更多模型

- [ ] 增加github actions部署支持