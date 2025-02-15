from urllib.parse import parse_qsl

try:
    from fast_query_parsers import parse_query_string
except ModuleNotFoundError:
    parse_query_string = None

def parse_qs(qs: str) -> dict[str, str]:
    if parse_query_string:
        query = dict(parse_query_string(qs, "&"))
    else:
        query = dict(parse_qsl(qs))
    return query