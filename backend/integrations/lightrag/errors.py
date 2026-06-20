class LightRAGError(Exception):
    def __init__(
        self,
        message: str,
        operation: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.status_code = status_code
        self.response_text = response_text

    def __str__(self) -> str:
        parts = [f"LightRAG {self.operation} failed", self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.response_text:
            parts.append(f"response={self.response_text[:500]}")
        return ": ".join(parts)


class LightRAGTimeoutError(LightRAGError):
    pass


class LightRAGNotFoundError(LightRAGError):
    pass
