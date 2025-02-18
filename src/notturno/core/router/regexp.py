try:
    import re2 as re
except ModuleNotFoundError:
    import re


class PathRouter:
    def __init__(self, root_path: str = ""):
        self.routes = {}
        self.static_routes = {}
        self.root_path = root_path
        self.compiled_regex = {}
        self.http_root = {}

    def add_route(self, method, pattern, handler):
        pattern = self.root_path + pattern

        if pattern in {"/", ""}:
            self.http_root[method] = {"func": handler, "params": {}}
            return

        if ":" not in pattern and "*" not in pattern:
            self.static_routes.setdefault(method, {})[pattern] = handler
        else:
            regex_pattern = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", pattern)
            regex_pattern = re.sub(r"\*", r"(.+)", regex_pattern)
            self.routes.setdefault(method, []).append((regex_pattern, handler))
            self.compile_routes(method)

    def compile_routes(self, method):
        combined_pattern = "|".join(
            f"(?P<route_{index}_{method}>{pattern})"
            for index, (pattern, _) in enumerate(self.routes.get(method, []))
        )
        self.compiled_regex[method] = re.compile(combined_pattern)

    def match(self, path):
        if path in {"/", ""}:
            return self.http_root

        for method, patterns in self.static_routes.items():
            if path in patterns:
                return {
                    method: {
                        "func": patterns[path],
                        "params": {}
                    }
                }

        for method, patterns in self.routes.items():
            if method in self.compiled_regex:
                match = self.compiled_regex[method].match(path)
                if match:
                    for index, (pattern, handler_value) in enumerate(patterns):
                        if match.group(f"route_{index}_{method}"):
                            return {
                                method: {
                                    "func": handler_value,
                                    "params": {key: match.group(key) for key in match.groupdict() if key}
                                }
                            }
        return None

    def combine(self, other_router):
        for method, routes in other_router.routes.items():
            for pattern, handler in routes:
                self.add_route(method, pattern, handler)

        for method, patterns in other_router.static_routes.items():
            for pattern, handler in patterns.items():
                self.add_route(method, pattern, handler)
