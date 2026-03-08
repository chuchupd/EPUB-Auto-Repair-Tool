import io
import re
import uuid
import html
import datetime
import tempfile
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .core import (
    create_epub, XML_NAMESPACES, create_nav_xhtml, upgrade_to_html5
)

class TXTToEPUBConverter:
    def __init__(self):
        pass

    def extract_metadata(self, text):
        """TXT 상단에서 제목, 저자 등 메타데이터 추출"""
        lines = text.split('\n')[:50]
        metadata = {"title": "Untitled", "author": "Unknown Author"}
        
        # 1. 태그 기반 추출 ([제목], <제목>, 제목:)
        for line in lines:
            line = line.strip()
            # 제목 추출
            if not metadata.get("title") or metadata["title"] == "Untitled":
                m = re.search(r'[\[<](?:제목|Title)[\]>]\s*(.+)', line, re.I)
                if m: metadata["title"] = m.group(1).strip()
                elif line.startswith("제목:"): metadata["title"] = line[3:].strip()
            
            # 저자 추출
            if not metadata.get("author") or metadata["author"] == "Unknown Author":
                m = re.search(r'[\[<](?:저자|글|Author)[\]>]\s*(.+)', line, re.I)
                if m: metadata["author"] = m.group(1).strip()
                elif line.startswith("저자:"): metadata["author"] = line[3:].strip()

        # 2. 휴리스틱 (첫 몇 줄 중 가장 짧고 강조된 줄을 제목으로 간주)
        if metadata["title"] == "Untitled":
            for line in lines[:5]:
                clean = line.strip()
                if 2 < len(clean) < 40 and not clean.startswith(("http", "www")):
                    metadata["title"] = clean
                    break
        
        return metadata

    def search_cover(self, title, author=None):
        """Open Library 및 Google Books API를 이용한 자동 표지 및 메타데이터 검색"""
        try:
            query = f"intitle:{title}"
            if author and author != "Unknown Author":
                query += f"+inauthor:{author}"
            
            # Google Books API
            api_url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
            resp = requests.get(api_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data:
                    item = data["items"][0]["volumeInfo"]
                    info = {
                        "title": item.get("title", title),
                        "author": ", ".join(item.get("authors", [author or "Unknown"])),
                        "description": item.get("description", ""),
                        "publishedDate": item.get("publishedDate", ""),
                        "cover_url": item.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
                    }
                    return info
        except Exception as e:
            print(f"  - 표지 검색 중 오류: {e}")
        return None

    def to_epub(self, text, metadata, cover_url=None, cover_bytes=None, log_fn=None):
        """TXT를 EPUB으로 변환 (메모리 버퍼 반환)"""
        def log(msg):
            if log_fn: log_fn(msg)
            print(msg, flush=True)

        log(f"\n[Convert] EPUB 변환 시작 (Ver 1.7 - Hybrid Compatibility) | 크기: {len(text)}자")
        output_buffer = io.BytesIO()
        book_id = f"urn:uuid:{uuid.uuid4()}"
        iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # 임시 폴더 생성
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "OEBPS" / "images").mkdir(parents=True, exist_ok=True)
            
            # 1. (생략) mimetype은 create_epub에서 자동 생성 및 관리함

            # 2. 스타일시트
            log("  - 스타일시트 (style.css) 생성 중...")
            css = '''body { font-family: sans-serif; line-height: 1.6; margin: 5%; text-align: justify; }
h1, h2 { text-align: center; margin-top: 10%; }
.chapter { page-break-before: always; }
img { max-width: 100%; height: auto; }'''
            (root / "OEBPS" / "style.css").write_text(css, encoding="utf-8")

            # 3. 본문 처리 및 XHTML 분할
            lines = text.splitlines()
            log(f"  - 총 {len(lines)}개 라인 처리 및 5000라인 단위 분할 시작...")
            
            chapter_files = []
            chunk_size = 5000
            for i in range(0, len(lines), chunk_size):
                chunk = lines[i:i + chunk_size]
                ch_idx = len(chapter_files) + 1
                fname = f"content{ch_idx}.xhtml"
                
                content = [
                    '<?xml version="1.0" encoding="utf-8"?>',
                    '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko" lang="ko">',
                    f'<head><meta charset="utf-8" /><title>Chapter {ch_idx}</title><link rel="stylesheet" href="style.css" type="text/css" /></head>',
                    '<body>'
                ]
                
                for line in chunk:
                    line = line.strip()
                    if not line:
                        content.append('<p>&#160;</p>')
                    elif len(line) < 30 and (line.startswith("제") or "장" in line or "CHAPTER" in line.upper()):
                        content.append(f'<h2>{html.escape(line)}</h2>')
                    else:
                        content.append(f'<p>{html.escape(line)}</p>')
                
                content.append('</body></html>')
                content_str = '\n'.join(content)
                content_str = upgrade_to_html5(content_str)
                (root / "OEBPS" / fname).write_text(content_str, encoding="utf-8")
                chapter_files.append({"label": f"Chapter {ch_idx}", "href": fname})
                log(f"    ... {min(i+chunk_size, len(lines))}/{len(lines)} 라인 처리 중 ({fname})")

            log(f"  - 총 {len(chapter_files)}개 XHTML 파일 생성 완료")

            # 4. 표지 처리
            has_real_cover = False
            cover_ext = ""
            if cover_bytes:
                log("  - 직접 업로드된 표지 적용 중...")
                try:
                    img = Image.open(io.BytesIO(cover_bytes))
                    cover_ext = "jpg"
                    img.convert("RGB").save(root / "OEBPS" / "images" / "cover.jpg", "JPEG", quality=90)
                    has_real_cover = True
                except Exception as e:
                    log(f"    => 업로드 표지 처리 오류: {e}")

            if not has_real_cover and cover_url:
                log(f"  - 외부 표지 다운로드 중: {cover_url}")
                try:
                    c_resp = requests.get(cover_url, timeout=10)
                    if c_resp.status_code == 200:
                        (root / "OEBPS" / "images" / "cover.jpg").write_bytes(c_resp.content)
                        has_real_cover = True
                        cover_ext = "jpg"
                        log("    => 표지 다운로드 성공")
                except Exception as e:
                    log(f"    => 표지 다운로드 중 오류: {e}")

            if not has_real_cover:
                log("  - 기본 표지 이미지 (cover.jpg) 생성 중...")
                cover_ext = "jpg"
                try:
                    img = Image.new('RGB', (600, 800), color=(238, 238, 238))
                    draw = ImageDraw.Draw(img)
                    font_path = "/System/Library/Fonts/Supplemental/AppleGothic.ttf"
                    try:
                        title_font = ImageFont.truetype(font_path, 40)
                        author_font = ImageFont.truetype(font_path, 25)
                    except:
                        title_font = ImageFont.load_default()
                        author_font = ImageFont.load_default()

                    t_text = metadata["title"]
                    if len(t_text) > 12: t_text = t_text[:12] + ".."
                    draw.text((300, 350), t_text, fill=(51, 51, 51), font=title_font, anchor="mm")
                    draw.text((300, 450), metadata["author"], fill=(102, 102, 102), font=author_font, anchor="mm")
                    img.save(root / "OEBPS" / "images" / "cover.jpg", "JPEG", quality=90)
                except Exception as e:
                    log(f"    => JPEG 생성 중 오류 (SVG 대체): {e}")
                    cover_ext = "svg"
                    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800">
<rect width="100%" height="100%" fill="#eeeeee"/>
<text x="50%" y="40%" font-size="30" text-anchor="middle" fill="#333">{html.escape(metadata["title"])}</text>
<text x="50%" y="50%" font-size="20" text-anchor="middle" fill="#666">{html.escape(metadata["author"])}</text>
</svg>'''
                    (root / "OEBPS" / "images" / "cover.svg").write_text(svg, encoding="utf-8")

            # cover.xhtml (Show image)
            log("  - 표지 페이지 (cover.xhtml) 생성 중...")
            cover_xhtml = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ko" lang="ko">
<head><meta charset="utf-8" /><title>Cover</title><style>body {{ margin:0; padding:0; text-align:center; background-color:#eeeeee; }} img {{ max-width:100%; height:auto; display:block; margin:0 auto; }}</style></head>
<body><div style="height:100vh; display:flex; align-items:center; justify-content:center;"><img src="images/cover.{cover_ext}" alt="Cover Image" /></div></body></html>'''
            (root / "OEBPS" / "cover.xhtml").write_text(cover_xhtml, encoding="utf-8")

            # nav.xhtml (EPUB 3)
            log("  - EPUB 3 Navigation Document (nav.xhtml) 생성 중...")
            create_nav_xhtml(root, chapter_files, title=metadata["title"])

            # toc.ncx (EPUB 2 backward compatibility)
            log("  - TOC (toc.ncx) 생성 중...")
            ncx = [
                '<?xml version="1.0" encoding="utf-8"?>',
                '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">',
                f'<head><meta name="dtb:uid" content="{book_id}"/><meta name="dtb:depth" content="1"/><meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>',
                f'<docTitle><text>{html.escape(metadata["title"])}</text></docTitle>',
                '<navMap>'
            ]
            for i, item in enumerate(chapter_files):
                ncx.append(f'<navPoint id="navPoint-{i+1}" playOrder="{i+1}"><navLabel><text>{html.escape(item["label"])}</text></navLabel><content src="{item["href"]}"/></navPoint>')
            ncx.append('</navMap></ncx>')
            (root / "OEBPS" / "toc.ncx").write_text('\n'.join(ncx), encoding="utf-8")

            # content.opf
            log("  - 마스터 설정 (content.opf) 생성 중...")
            opf = [
                '<?xml version="1.0" encoding="utf-8"?>',
                '<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid" version="3.0">',
                '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">',
                f'    <dc:identifier id="bookid">{book_id}</dc:identifier>',
                f'    <dc:title>{html.escape(metadata["title"])}</dc:title>',
                f'    <dc:creator>{html.escape(metadata["author"])}</dc:creator>',
                '    <dc:language>ko</dc:language>',
                f'    <dc:date>{metadata.get("publishedDate") or iso_now[:10]}</dc:date>',
                f'    <meta property="dcterms:modified">{iso_now}</meta>',
                '    <meta name="cover" content="cover-image"/>',
                '  </metadata>',
                '  <manifest>',
                '    <item id="style" href="style.css" media-type="text/css"/>',
                '    <item id="cover-page" href="cover.xhtml" media-type="application/xhtml+xml"/>',
                '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
            ]
            for i, item in enumerate(chapter_files):
                opf.append(f'    <item id="ch{i+1}" href="{item["href"]}" media-type="application/xhtml+xml"/>')
            
            m_type = "image/jpeg" if cover_ext == "jpg" else ("image/png" if cover_ext == "png" else "image/svg+xml")
            opf.append(f'    <item id="cover-image" href="images/cover.{cover_ext}" media-type="{m_type}" properties="cover-image"/>')
            opf.append('  </manifest>')
            opf.append('  <spine toc="ncx">')
            opf.append('    <itemref idref="cover-page"/>')
            for i in range(len(chapter_files)):
                opf.append(f'    <itemref idref="ch{i+1}"/>')
            # EPUB 3 nav는 읽기 순서(linear)에서 제외하는 것이 독서 흐름에 좋음
            opf.append('    <itemref idref="nav" linear="no"/>')
            opf.append('  </spine>')
            opf.append('  <guide><reference type="cover" title="Cover" href="cover.xhtml"/></guide>')
            opf.append('</package>')
            (root / "OEBPS" / "content.opf").write_text('\n'.join(opf), encoding="utf-8")

            # 5. EPUB 압축
            log("  - EPUB 압축 및 최종 버퍼 생성 중...")
            create_epub(root, root / "temp.epub")
            output_buffer.write((root / "temp.epub").read_bytes())
            output_buffer.seek(0)
            log("[Success] EPUB 변환 작업이 완료되었습니다.")

        return output_buffer
