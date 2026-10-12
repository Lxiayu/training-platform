"""统一响应壳：成功 {"code": 0, "message": "ok", "data": ...}。

失败响应由 main.py 的 BizException 处理器生成：
{"code": <HTTP 状态码>, "message": "<中文提示>"}。
"""


def ok(data=None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}
