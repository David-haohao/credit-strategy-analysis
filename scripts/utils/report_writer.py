"""HTML 报告模板渲染接口。"""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_template(template_dir: str | Path, template_name: str, context: dict[str, Any]) -> str:
    environment = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return environment.get_template(template_name).render(**context)
