from typing import Optional, Dict, Any, Union

class Response:
    def __init__(self, body: Optional[Union[Dict[str, Any], Any, str, bytes]]="", headers: Dict[str, str] = {}, status_code: int = 200, content_type: Union[str, None] = None):
        self.body: Optional[Union[Dict[str, Any], Any, str, bytes]]= body
        self.headers: Dict[str, str] = headers
        self.status_code: Optional[int] = status_code
        self.content_type: Union[str, None] = content_type