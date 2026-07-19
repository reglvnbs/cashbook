"""可安全返回给客户端的业务错误。"""

from __future__ import annotations


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        fields: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.fields = fields


class ValidationError(AppError):
    def __init__(self, fields: dict[str, str], message: str = "请检查填写内容") -> None:
        super().__init__("VALIDATION_ERROR", message, 400, fields)

