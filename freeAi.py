import threading
from flask import Flask, request, jsonify
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from plugins import *
import requests
import json

app = Flask(__name__)
flag = 1
qwen_cookie = ""

@plugins.register(
    name="FreeAI",
    desire_priority=1000,
    desc="使用未开放接口的模型",
    version="0.2",
    author="huang0752",
    enabled=True,
)
class FreeAI(Plugin):
    def __init__(self):
        global qwen_cookie
        super().__init__()
        # 加载config.josn
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
            qwen_cookie = config.get("qwen_cookie")
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.app = app

    def start_flask_app(self):
        self.app.run(host='0.0.0.0', port=5000)

    def on_handle_context(self, e_context):
        global flag,qwen_cookie
        # 如果config.json都为空
        if qwen_cookie == "":
            reply = Reply()
            reply.type = ReplyType.TEXT
            reply.content = " FreeAI 插件未配置，请配置"
            e_context['reply'] = reply
            e_context.action = EventAction.BREAK_PASS  # 事件结束，并跳过处理context的默认逻辑
        if e_context['context'].type != ContextType.TEXT:
            logger.error("FreeAI only supports text context")
            return
        if flag == 1:
            # 启动 Flask 服务器
            print("Starting Flask server in a separate thread...")
            flask_thread = threading.Thread(target=self.start_flask_app)
            flask_thread.start()
            print("Flask server started.")
            flag = 0


def to_qwen(content):
    global qwen_cookie
    # 目标URL
    url = 'https://qianwen.biz.aliyun.com/dialog/conversation'

    # 请求头
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0',
        'Content-Type': 'application/json',
        'cookie': qwen_cookie
    }

    # 请求体，这里是JSON格式的数据
    data = {"model": "", "action": "next", "mode": "chat", "userAction": "new_top",
            "requestId": "1f49d2da1e944f0dabee40c44556263d", "sessionId": "", "sessionType": "text_chat",
            "parentMsgId": "", "contents": [{"content": content, "contentType": "text", "role": "user"}],
            "params": {"fileUploadBatchId": "eea08bbda5fd49c797cf2cf2679da881", "agentId": ""}}

    #将字典转换为JSON格式的字符串
    json_data = json.dumps(data, ensure_ascii=False)

    # 发送POST请求
    response = requests.post(url, headers=headers, data=json_data)

    try:
        # 打印响应内容
        parts = response.text.split("data: ")[-2]
        dict_list = json.loads(parts)['contents']
        for dict in dict_list:
            if dict['role'] == "assistant":
                if dict['contentType'] == "text":
                    Reply = dict['content']
                    logger.info(f"Qwen2.5 Reply: {Reply}")
                    return Reply
            continue
    except:
        return "cookie配置错误"

# 接收请求
@app.route('/qwen/chat/completions', methods=['POST'])
def qwen_post():
    # 获取JSON格式的请求数据
    data = request.get_json()
    # 处理数据...
    content = str(data['messages'])
    reply = to_qwen(content)
    # 创建响应JSON
    response_json = {
        "id": "chatcmpl-flILZyNW7EY2ROwizBpiHth4As3Cd",
        "object": "chat.completion",
        "created": 1677633787,
        "model": "gpt-4o",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": reply,
                },
                "logprobs": None,
                "finish_reason": "stop"

            }
        ],
        "system_fingerprint": "fp_9edba07c36",
        "usage": {
            "completion_tokens": 180,
            "prompt_tokens": 20,
            "total_tokens": 200
        }

    }
    # 返回响应
    return jsonify(response_json)
