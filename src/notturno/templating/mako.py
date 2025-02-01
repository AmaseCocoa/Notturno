from mako.lookup import TemplateLookup

from . import BaseTemplating
from ..models.response import Response


class MakoTemplating(BaseTemplating):
    def __init__(
        self,
        directory: list | str,
        module_directory: str | None = None,
        collection_size: int = 500,
    ):
        if isinstance(directory, str):
            directory = [directory]
        self.lookup = TemplateLookup(
            directories=directory,
            module_directory=module_directory,
            collection_size=collection_size,
        )

    def render(
        self,
        file: str,
        context: dict,
        headers: dict = {},
        content_type: str | None = "text/html",
    ):
        template = self.lookup.get_template(file)
        rendered = template.render(**context)
        return Response(body=rendered, headers=headers, content_type=content_type)
