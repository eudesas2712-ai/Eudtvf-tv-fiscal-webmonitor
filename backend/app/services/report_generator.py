from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def generate_intel_pdf(data: dict, output_path: str) -> str:
    template = env.get_template("intel_report.html")
    html_content = template.render(**data)
    HTML(string=html_content).write_pdf(output_path)
    return output_path