from urllib.parse import parse_qsl

try:
    from fast_query_parsers import parse_query_string
except ModuleNotFoundError:
    parse_query_string = None

def parse_qs(qs: str) -> dict[str, str]:
    if parse_query_string:
        return dict(parse_query_string(qs, "&"))
    return dict(parse_qsl(qs))