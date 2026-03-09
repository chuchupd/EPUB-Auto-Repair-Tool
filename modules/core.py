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
    "dcterms": "http://purl.org/dc/terms/",
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
    """BOM 제거 및 Unix 스타일(LF) 줄바꿈으로 통일하여 저장"""
    path.parent.mkdir(parents=True, exist_ok=True)
    if text.startswith('\ufeff'):
        text = text[1:]
    # CRLF를 LF로 통일
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    with path.open("w", encoding="utf-8", newline='\n') as f:
        f.write(text)

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

def upgrade_to_html5(text: str, target_version: str = "3.0"):
    """XHTML 1.1 등을 EPUB 규격(2.0 또는 3.0)에 맞춰 정밀 변환"""
    # 0. BOM(Byte Order Mark) 제거
    if text.startswith('\ufeff'):
        text = text[1:]

    # 1. XML 선언 및 DOCTYPE 처리
    if target_version == "2.0":
        # EPUB 2.0/구형 리더기는 XML 선언부를 명시적으로 요구하는 경우가 많음
        if not re.search(r'<\?xml[^>]*\?>', text):
            text = '<?xml version="1.0" encoding="utf-8"?>\n' + text
        # DOCTYPE을 XHTML 1.1로 유지 또는 교체
        if not re.search(r'<!DOCTYPE [^>]+>', text, flags=re.I):
            text = text.replace('?>', '?>\n<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">', 1)
    else:
        # EPUB 3.0 (HTML5) - XML 선언 제거 (권장) 및 DOCTYPE 단순화
        text = re.sub(r'<\?xml[^>]*\?>', '', text)
        text = re.sub(r'<!DOCTYPE [^>]+>', '<!DOCTYPE html>', text, flags=re.I)
    
    # 3. html 태그 특성 정규화
    if '<html' in text:
        # epub 네임스페이스 추가 (EPUB 3 필수, 2에서도 무해)
        if 'xmlns:epub' not in text:
            text = text.replace('<html', '<html xmlns:epub="http://www.idpf.org/2007/ops"', 1)
        # 기본 네임스페이스 확인
        if 'xmlns="http://www.w3.org/1999/xhtml"' not in text:
            text = text.replace('<html', '<html xmlns="http://www.w3.org/1999/xhtml"', 1)
        # 언어 설정 동기화
        if ' lang="ko"' not in text:
            text = text.replace('<html', '<html lang="ko"', 1)
        if ' xml:lang="ko"' not in text:
            text = text.replace('<html', '<html xml:lang="ko"', 1)

    # 4. Meta Charset 현대화 (Content-Type 대신 <meta charset="utf-8"/> 권장)
    text = re.sub(r'<meta[^>]*http-equiv=["\']Content-Type["\'][^>]*>', '', text, flags=re.I)
    if '<head>' in text and 'charset="utf-8"' not in text:
        text = text.replace('<head>', '<head>\n<meta charset="utf-8"/>', 1)

    # 4-1. Title 보강 (빈 제목 방지)
    title_match = re.search(r'<title>([^<]*)</title>', text, flags=re.I)
    if title_match:
        if not title_match.group(1).strip():
            # h1이 있으면 추출
            h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', text, flags=re.I)
            new_title = h1_match.group(1).strip() if h1_match else "Chapter"
            text = text.replace(title_match.group(0), f'<title>{new_title}</title>')
    elif '<head>' in text:
        text = text.replace('<head>', '<head>\n<title>Chapter</title>', 1)

    # 5. 레거시 속성 정밀 교정 (Google Books 호환성 핵심)
    # img 태그의 width, height % 단위를 style로 이동 (HTML5 규격 위반 해결)
    def img_attr_repl(m):
        tag_content = m.group(0)
        # width="80%" -> style="width: 80%"
        w_match = re.search(r'width=["\'](\d+%)["\']', tag_content)
        h_match = re.search(r'height=["\'](\d+%)["\']', tag_content)
        if w_match or h_match:
            styles = []
            if w_match: 
                styles.append(f"width: {w_match.group(1)}")
                tag_content = re.sub(r'width=["\']\d+%["\']', '', tag_content)
            if h_match: 
                styles.append(f"height: {h_match.group(1)}")
                tag_content = re.sub(r'height=["\']\d+%["\']', '', tag_content)
            
            new_style = "; ".join(styles)
            if 'style="' in tag_content:
                tag_content = tag_content.replace('style="', f'style="{new_style}; ', 1)
            else:
                tag_content = tag_content.replace('<img', f'<img style="{new_style}"', 1)
        return tag_content

    text = re.sub(r'<img[^>]+>', img_attr_repl, text, flags=re.I)
    
    # 6. 정렬 속성(align) 교정
    text = re.sub(r' align=["\'](left|right|center|justify)["\']', r' style="text-align: \1"', text, flags=re.I)
    
    # 7. XHTML 엔티티 교정 (Google Books/XHTML 엄격 모드 대응)
    # &nbsp; 등은 XML에서 미정의 엔티티일 확률이 높음 -> 수치형으로 변환
    text = text.replace("&nbsp;", "&#160;")
    text = text.replace("&hellip;", "&#8230;")
    text = text.replace("&middot;", "&#183;")
    
    return text.strip()

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

def create_nav_xhtml(root: Path, nav_items: list, title: str = "Navigation"):
    """EPUB 3 필수 요소인 nav.xhtml 생성 (Pure HTML5 호환용)"""
    nav_dir = root / "OEBPS"
    nav_dir.mkdir(parents=True, exist_ok=True)
    
    ol_items = ""
    for item in nav_items:
        ol_items += f'<li><a href="{item["href"]}">{html.escape(item["label"])}</a></li>\n'
        
    first_href = nav_items[0]["href"] if nav_items else "text/cover.xhtml"
    
    # XML 선언 제거 (XHTML 5 규격 호환성 극대화)
    content = f'''<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="ko" xml:lang="ko">
<head>
    <title>{html.escape(title)}</title>
    <meta charset="utf-8" />
    <style>
        nav ol {{ list-style-type: none; }}
    </style>
</head>
<body>
    <nav epub:type="toc" id="toc">
        <h1>{html.escape(title)}</h1>
        <ol>
            {ol_items}
        </ol>
    </nav>
    <nav epub:type="landmarks" id="guide" hidden="hidden">
        <h2>Guide</h2>
        <ol>
            <li><a epub:type="toc" href="nav.xhtml">Table of Contents</a></li>
            <li><a epub:type="bodymatter" href="{first_href}">Begin Reading</a></li>
        </ol>
    </nav>
</body>
</html>'''
    (nav_dir / "nav.xhtml").write_text(content, encoding="utf-8")

def extract_epub(epub_path: Path, extract_to: Path):
    with zipfile.ZipFile(epub_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

def create_epub(folder: Path, output_path: Path):
    """EPUB 규격에 맞게 ZIP 압축 (mimetype 선두 배치 및 정규화)"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 제외 대상 (시스템 가비지 파일)
    junk_patterns = [".ds_store", "__macosx", ".git", ".ipynb_checkpoints", "thumbs.db"]
    
    with zipfile.ZipFile(output_path, "w") as epub:
        # 1. mimetype 파일은 반드시 첫 번째여야 함 (압축 없이 STORED, Extra field 없음, 38바이트 정밀 준수)
        mimetype_info = zipfile.ZipInfo("mimetype")
        mimetype_info.compress_type = zipfile.ZIP_STORED
        mimetype_info.external_attr = 0o644 << 16
        mimetype_info.create_system = 0  # 시스템 의존 정보 제거
        mimetype_info.extra = b""        # extra 필드 강제 제거
        epub.writestr(mimetype_info, b"application/epub+zip")

        # 2. 나머지 파일들 추가
        all_files = []
        for p in folder.rglob("*"):
            if not p.is_file(): continue
            if p.name.lower() in junk_patterns: continue
            if any(part.lower() in junk_patterns for part in p.parts): continue
            
            # mimetype은 위에서 처리함
            if p.name == "mimetype" and p.parent == folder: continue
            # 자기 자신(출력 파일) 제외
            if p.resolve() == output_path.resolve(): continue
            
            all_files.append(p)

        for p in sorted(all_files):
            rel = p.relative_to(folder).as_posix()
            epub.write(p, rel, compress_type=zipfile.ZIP_DEFLATED)
