from pathlib import Path
import base64

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"

env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def _data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def generate_intel_pdf(data: dict, output_path: str) -> str:
    template = env.get_template("intel_report.html")
    logo_header = BASE_DIR / "assets" / "logo_tvfiscal_header.png"
    logo_default = BASE_DIR / "assets" / "logo_tvfiscal.png"
    data = dict(data or {})
    data.setdefault("logo_header_data_uri", _data_uri(logo_header) or _data_uri(logo_default))
    html_content = template.render(**data)
    HTML(string=html_content).write_pdf(output_path)
    return output_path