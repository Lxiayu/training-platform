"""业务异常：service 层抛出，由 main.py 的全局异常处理器统一转 HTTP 响应。"""


class BizException(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(message)
