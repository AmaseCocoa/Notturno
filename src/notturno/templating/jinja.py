from jinja2 import Environment, FileSystemLoader

from . import BaseTemplating
from ..models.response import Response


class JinjaTemplating(BaseTemplating):
    def __init__(self, directory):
        self.env = Environment(loader=FileSystemLoader(directory))

    def render(self, file: str, context: dict, headers: dict = {}, content_type: str | None = "text/html"):
        template = self.env.get_template(file)
        rendered = template.render(context)
        return Response(body=rendered, headers=headers, content_type=content_type)