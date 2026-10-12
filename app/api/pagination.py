"""API 层公共依赖：分页参数。"""
from fastapi import Query


class Pagination:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="页码，从 1 开始"),
        page_size: int = Query(20, ge=1, le=100, alias="pageSize", description="每页条数"),
    ):
        self.page = page
        self.page_size = page_size
