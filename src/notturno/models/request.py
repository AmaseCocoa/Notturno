from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..utils.url import URL


class Request(BaseModel):
    method: str = Field(description="HTTP Method")
    url: URL = Field(description="Request URL")
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Request Header"
    )
    query: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Query Params"
    )
    body: Optional[Any] = Field(default=None, description="Request Body")
