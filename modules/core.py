import re
import html
import zipfile
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

# XML 네임스페이스 정의
XML_NAMESPACES = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "epub": "http://www.idpf.org/2007/ops",
}

for prefix, uri in XML_NAMESPACES.items():
    ET.register_namespace(prefix if prefix != "opf" else "", uri)

def read_text_lossy(path: Path):
    """여러 인코딩을 시도하여 텍스트를 읽음"""
    for enc in ["utf-8", "cp949", "euc-kr", "utf-16"]:
        try:
            return path.read_text(encoding=enc)
        except:
            continue
    return path.read_bytes().decode("utf-8", errors="replace")

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

def try_parse_xml_string(text: str):
    try:
        return ET.fromstring(text.encode("utf-8"))
    except:
        return None

def sanitize_invalid_tags_in_markup(text: str):
    """HTML 표준에 맞지 않는 태그나 속성을 정리 (오픈/클로즈 태그 모두 대응)"""
    valid_tags = {
        "html", "head", "body", "title", "link", "meta", "style",
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "br", "hr",
        "ol", "ul", "li", "a", "img", "blockquote", "pre", "code", "em", "strong", "b", "i",
        "table", "tr", "td", "th", "thead", "tbody", "caption",
        "section", "article", "nav", "aside", "header", "footer"
    }
    
    # 1. 태그명 추출 (오픈 및 클로즈 모두 처리)
    def repl(m):
        prefix = m.group(1) or "" # "/" if closing
        tag = m.group(2).lower()
        suffix = m.group(3) or "" # attributes
        
        if tag in valid_tags:
            return m.group(0)
        
        # 비표준 태그는 <fixed_tag> 형태로 중립화
        return f"<{prefix}{tag}_fixed{suffix}>"
    
    # <(/)?(tagname)( attributes)?> 형태 매칭
    return re.sub(r"<(/)?([a-zA-Z0-9]+)([^>]*)>", repl, text)

def strip_event_handlers_and_risky_tags(text: str):
    """onmouseover, onclick 등 이벤트 핸들러 및 script 태그 제거"""
    text = re.sub(r' (on[a-z]+)="[^"]*"', '', text, flags=re.I)
    text = re.sub(r' (on[a-z]+)=\'[^\']*\'', '', text, flags=re.I)
    text = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.S | re.I)
    return text

def find_opf_path(root: Path):
    container = root / "META-INF" / "container.xml"
    if container.exists():
        try:
            tree = ET.parse(container)
            root_node = tree.getroot()
            for item in root_node.findall(".//{http://www.idpf.org/2007/opf}rootfile"):
                return item.get("full-path")
        except:
            pass
    # 폴더를 직접 뒤짐
    for p in root.rglob("*.opf"):
        return p.relative_to(root).as_posix()
    return None

def ensure_container_xml(root: Path, opf_rel_path: str):
    container_dir = root / "META-INF"
    container_dir.mkdir(parents=True, exist_ok=True)
    content = f'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="{opf_rel_path}" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
    (container_dir / "container.xml").write_text(content, encoding="utf-8")

def ensure_mimetype(root: Path):
    (root / "mimetype").write_text("application/epub+zip", encoding="utf-8")

def extract_epub(epub_path: Path, extract_to: Path):
    with zipfile.ZipFile(epub_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

def create_epub(folder: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as epub:
        mimetype_path = folder / "mimetype"
        if mimetype_path.exists():
            epub.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        all_files = []
        for p in folder.rglob("*"):
            if p.is_file() and p != mimetype_path and p.resolve() != output_path.resolve():
                all_files.append(p)

        for p in sorted(all_files):
            rel = p.relative_to(folder).as_posix()
            epub.write(p, rel, compress_type=zipfile.ZIP_DEFLATED)
