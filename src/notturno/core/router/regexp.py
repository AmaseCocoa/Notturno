try:
    import re2 as re
except ModuleNotFoundError:
    import re


class RegExpRouter:
    def __init__(self, root_path: str = ""):
        self.routes = {}
        self.root_path = root_path
        self.compiled_regex = {}

    def add_route(self, method, pattern, handler):
        pattern = self.root_path + pattern
        if pattern == "/" or pattern == "":
            regex_pattern = r"^/$"
        else:
            regex_pattern = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", pattern)
            regex_pattern = re.sub(r"\*", r"(.+)", regex_pattern)

        if method not in self.routes:
            self.routes[method] = []

        self.routes[method].append((regex_pattern, handler))
        self.compile_routes(method)

    def compile_routes(self, method):
        combined_pattern = "|".join(
            f"(?P<route_{index}_{method}>{pattern})"
            for index, (pattern, _) in enumerate(self.routes[method])
        )
        self.compiled_regex[method] = re.compile(combined_pattern)

    def match(self, path):
        result = {
            method: (
                {
                    "func": handler,
                    "params": {
                        key: match.group(key)
                        for key in match.groupdict()
                        if key
                        and key
                        not in [f"route_{i}_{method}" for i in range(len(patterns))]
                    },
                }
            )
            if (match := self.compiled_regex[method].match(path))
            and any(
                (match.group(f"route_{index}_{method}") and (handler := handler_value))
                for index, (pattern, handler_value) in enumerate(patterns)
            )
            else None
            for method, patterns in self.routes.items()
            if method in self.compiled_regex
        } or None
        return result if result else None

    def combine(self, other_router):
        for method, routes in other_router.routes.items():
            for pattern, handler in routes:
                self.add_route(method, pattern, handler)
