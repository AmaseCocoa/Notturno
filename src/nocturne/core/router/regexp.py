import re2

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
            regex_pattern = re2.sub(
                r":(\w+)", r"(?P<\1>[^/]+)", pattern
            )
            regex_pattern = re2.sub(r"\*", r"(.+)", regex_pattern)

        if method not in self.routes:
            self.routes[method] = []

        self.routes[method].append((regex_pattern, handler))
        self.compile_routes(method)

    def compile_routes(self, method):
        combined_pattern = "|".join(
            f"(?P<route_{index}_{method}>{pattern})"
            for index, (pattern, _) in enumerate(self.routes[method])
        )
        self.compiled_regex[method] = re2.compile(combined_pattern)

    def match(self, path):
        result = {}
        for method, patterns in self.routes.items():
            if method not in self.compiled_regex:
                continue

            match = self.compiled_regex[method].match(path)
            if match:
                for index, (pattern, handler) in enumerate(patterns):
                    if match.group(f"route_{index}_{method}"):
                        params = {
                            key: match.group(key)
                            for key in match.groupdict()
                            if key
                            not in [f"route_{i}_{method}" for i in range(len(patterns))]
                        }
                        if not params:
                            params = {}
                        result[method] = {
                            "func": handler,
                            "params": params,
                        }
            else:
                result[method] = None
        return result if result else None

    def combine(self, other_router):
        for method, routes in other_router.routes.items():
            for pattern, handler in routes:
                self.add_route(method, pattern, handler)
