from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union

class Response(BaseModel):
    body: Optional[Union[Dict[str, Any], Any, str, bytes]] = Field(default="", description="Response Body")
    headers: Optional[Dict[str, str]] = Field(default_factory=dict, description="Response Header")
    status_code: Optional[int] = Field(default=200, description="HTTP Status Code")
    content_type: Optional[Union[str, None]] = Field(default=None)
