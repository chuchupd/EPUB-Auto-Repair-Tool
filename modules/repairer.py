import io
import re
import tempfile
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
from .core import (
    read_text_lossy, write_text, try_parse_xml_string,
    sanitize_invalid_tags_in_markup, strip_event_handlers_and_risky_tags,
    find_opf_path, ensure_container_xml, ensure_mimetype,
    extract_epub, create_epub, XML_NAMESPACES
)

try:
    from PIL import Image
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

def clean_text_file(path: Path):
    """XHTML/HTML 파일의 불필요한 스크립트 및 비표준 태그 정리"""
    text = read_text_lossy(path)
    
    # 1. 스크립트 및 이벤트 핸들러 제거
    text = strip_event_handlers_and_risky_tags(text)
    
    # 2. 비표준 태그 완화
    text = sanitize_invalid_tags_in_markup(text)
    
    # 3. &nbsp; 관련 XML 오류 방지
    text = text.replace("&nbsp;", "&#160;")
    
    path.write_text(text, encoding="utf-8")

def ensure_identifier_in_opf(opf_path: Path):
    """OPF 파일에 dc:identifier가 없는 경우 추가"""
    text = read_text_lossy(opf_path)
    root = try_parse_xml_string(text)
    if root is None:
        return
    
    metadata = root.find("opf:metadata", XML_NAMESPACES)
    if metadata is None:
        metadata = ET.SubElement(root, "{http://www.idpf.org/2007/opf}metadata")
        
    dc_id = metadata.find("dc:identifier", XML_NAMESPACES)
    if dc_id is None:
        new_id = f"urn:uuid:{uuid.uuid4()}"
        dc_id = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}identifier")
        dc_id.text = new_id
        dc_id.set("id", "bookid")
        
        # package 태그의 unique-identifier 속성 확인
        if root.get("unique-identifier") is None:
            root.set("unique-identifier", "bookid")
        
        # XML 저장
        write_text(opf_path, ET.tostring(root, encoding="unicode"))

def try_convert_tiffs(root: Path):
    """TIFF 파일을 JPG로 변환 (EPUB 표준 호환)"""
    if not HAS_PILLOW:
        return []
    
    converted = []
    for p in root.rglob("*"):
        if p.suffix.lower() in [".tif", ".tiff"]:
            try:
                with Image.open(p) as img:
                    target = p.with_suffix(".jpg")
                    img.convert("RGB").save(target, "JPEG", quality=85)
                    p.unlink()
                    converted.append((p.name, target.name))
            except:
                continue
    return converted

class EPUBRepairer:
    def __init__(self, output_dir=None):
        self.output_dir = Path(output_dir) if output_dir else None

    def fix_text_content(self, text, suffix):
        """본문 텍스트의 구조적 결함 복구"""
        text = strip_event_handlers_and_risky_tags(text)
        text = sanitize_invalid_tags_in_markup(text)
        text = text.replace("&nbsp;", "&#160;")
        return text

    def repair_opf(self, opf_path_or_tree):
        """OPF 파일의 메타데이터 및 매니페스트 복구"""
        if isinstance(opf_path_or_tree, Path):
            text = read_text_lossy(opf_path_or_tree)
            root = try_parse_xml_string(text)
            if root is None: return
        else:
            root = opf_path_or_tree

        # 1. unique-identifier 처리
        uid_attr = root.get("unique-identifier")
        metadata = root.find("opf:metadata", XML_NAMESPACES)
        if metadata is not None:
            dc_id = metadata.find("dc:identifier", XML_NAMESPACES)
            if dc_id is not None:
                if not uid_attr:
                    root.set("unique-identifier", dc_id.get("id") or "bookid")
                    if not dc_id.get("id"): dc_id.set("id", "bookid")

        # 2. Spine/Manifest 일치 확인 (간단 예시)
        # 실제 구현에서는 더 복잡한 검증이 가능함
        return root

    def process_buffer(self, input_buffer, filename):
        """EPUB 바이너리 버퍼를 받아 복구된 버퍼 반환"""
        with tempfile.TemporaryDirectory(prefix="repair_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            in_epub = tmp_path / "input.epub"
            in_epub.write_bytes(input_buffer.read())
            
            extract_to = tmp_path / "extracted"
            extract_to.mkdir()
            
            notes = []
            changed_files = 0
            
            try:
                extract_epub(in_epub, extract_to)
                
                # 1. Mimetype 및 기초 구조 확인
                ensure_mimetype(extract_to)
                opf_rel = find_opf_path(extract_to)
                if not opf_rel:
                    notes.append("OPF 파일을 찾을 수 없어 기본 구조를 생성합니다.")
                    ensure_container_xml(extract_to, "OEBPS/content.opf")
                    opf_path = extract_to / "OEBPS" / "content.opf"
                else:
                    opf_path = extract_to / opf_rel
                
                # 2. OPF 식별자 확인
                ensure_identifier_in_opf(opf_path)
                
                # 3. 이미지 호환성 (TIFF -> JPG)
                conv_imgs = try_convert_tiffs(extract_to)
                if conv_imgs:
                    notes.append(f"{len(conv_imgs)}개의 TIFF 이미지를 JPG로 변환했습니다.")
                    changed_files += len(conv_imgs)
                
                # 4. XHTML 세정
                for p in extract_to.rglob("*"):
                    if p.suffix.lower() in [".xhtml", ".html", ".htm"]:
                        clean_text_file(p)
                        changed_files += 1
                
                # 5. 결과 압축
                out_epub = tmp_path / "output.epub"
                create_epub(extract_to, out_epub)
                
                return io.BytesIO(out_epub.read_bytes()), changed_files, notes
                
            except Exception as e:
                return input_buffer, 0, [f"오류 발생: {str(e)}"]
