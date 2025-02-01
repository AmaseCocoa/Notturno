from typing import Annotated, Any

from yarl import URL as YarlURL
from pydantic import BaseModel, PlainValidator, ValidationInfo

def validate(v: Any, info: ValidationInfo) -> YarlURL:
    if isinstance(v, YarlURL):
        ans = v
    elif isinstance(v, str):
        ans = YarlURL(v)
    else:
        raise TypeError(
            f"Expected yarl.URL, got {type(v)}"
        )
    return ans

URL = Annotated[
    YarlURL,
    PlainValidator(validate)
]