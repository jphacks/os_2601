from typing import NoReturn

from fastapi import HTTPException


def fail(status: int, message: str) -> NoReturn:
    raise HTTPException(status_code=status, detail=message)
