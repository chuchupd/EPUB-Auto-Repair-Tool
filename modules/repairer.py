import io
import re
import os
import tempfile
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET
from .core import (
    read_text_lossy, write_text, try_parse_xml_string,
    sanitize_invalid_tags_in_markup, strip_event_handlers_and_risky_tags,
    find_opf_path, ensure_container_xml, ensure_mimetype,
    extract_epub, create_epub, XML_NAMESPACES, create_nav_xhtml, upgrade_to_html5
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

    def upgrade_opf_to_v3(self, opf_path: Path):
        """OPF 파일을 EPUB 3.0 규격으로 업그레이드"""
        text = read_text_lossy(opf_path)
        # 1. 버전 업데이트 (따옴표 및 공백 유연하게 대응)
        text = re.sub(r'version\s*=\s*["\']2\.0["\']', 'version="3.0"', text)
        
        # 2. 폰트 MIME 타입 현대화 (EPUB 3 규격: application/x-font-otf/ttf -> font/otf/ttf)
        text = text.replace('application/x-font-ttf', 'font/ttf')
        text = text.replace('application/x-font-otf', 'font/otf')
        text = text.replace('application/vnd.ms-opentype', 'font/otf')
        
        # 3. dcterms:modified 메타데이터 추가
        import datetime
        iso_now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        if 'dcterms:modified' not in text:
            meta_tag = f'<meta property="dcterms:modified">{iso_now}</meta>'
            text = re.sub(r'(<metadata[^>]*>)', r'\1\n    ' + meta_tag, text)
            
        # 4. Google Books 호환성: 표지 이미지 속성(properties="cover-image") 추가
        # <meta name="cover" content="ID"/> 에서 ID를 찾아 해당 item에 속성 추가
        cover_match = re.search(r'<meta[^>]*name="cover"[^>]*content="([^"]+)"', text)
        if cover_match:
            cover_id = cover_match.group(1)
            # 해당 ID를 가진 item 찾아서 properties="cover-image" 추가 (이미 있으면 무시)
            item_pattern = f'(<item[^>]*id="{cover_id}"[^>]*href="[^"]+"[^>]*media-type="[^"]+")'
            if f'id="{cover_id}"' in text and 'properties="cover-image"' not in text:
                text = re.sub(item_pattern, r'\1 properties="cover-image"', text)
        
        # 5. 빈 메타데이터 태그 및 레거시 항목 제거 (Google Books 검증 오류 방지)
        empty_tags = ["dc:subject", "dc:description", "dc:rights", "dc:source", "dc:publisher", "dc:type"]
        for tag in empty_tags:
            text = re.sub(f'<{tag}[^>]*>\s*</{tag}>', '', text)
            text = re.sub(f'<{tag}[^>]*/>', '', text)
            
        # 6. opf:scheme 등 레거시 속성 제거 (EPUB 3.0에서는 meta property 권장)
        text = re.sub(r'\s+opf:scheme=["\'][^"\']+["\']', '', text)
        
        # 7. spine toc="ncx" 속성 제거 (EPUB 3 전용 모드 시도)
        text = re.sub(r'<spine toc=["\']ncx["\']', '<spine', text)
        
        # 8. 불필요한 메타데이터 제거 (PDFePub3 등)
        text = re.sub(r'<meta[^>]*name="PDFePub3 version"[^>]*/>', '', text)
        
        write_text(opf_path, text)
        return True

    def diagnose_epub(self, extract_root: Path):
        """EPUB 폴더를 스캔하여 잠재적 문제점 진단"""
        issues = []
        
        # 1. Mimetype 확인
        mimetype_path = extract_root / "mimetype"
        if not mimetype_path.exists():
            issues.append("Mimetype 파일 누락 (EPUB 규격 위반)")
        elif mimetype_path.read_text().strip() != "application/epub+zip":
            issues.append("비표준 Mimetype 데이터")

        # 1-1. EPUB 버전 확인
        opf_rel = find_opf_path(extract_root)
        if opf_rel:
            opf_path = extract_root / opf_rel
            opf_text = read_text_lossy(opf_path)
            if 'version="2.0"' in opf_text:
                issues.append("구형 EPUB 2.0 규격 발견 (Google Books에서 렌더링 오류 가능성)")
            
            nav_exists = any(p.name == "nav.xhtml" for p in extract_root.rglob("*.xhtml"))
            if not nav_exists:
                 issues.append("EPUB 3 필수 내비게이션(nav.xhtml) 누락")

        # 2. 이미지 호환성 확인
        for p in extract_root.rglob("*"):
            if p.suffix.lower() in [".tif", ".tiff"]:
                issues.append(f"호환되지 않는 이미지 형식 발견: {p.name} (TIFF)")

        # 3. XHTML 비표준 요소 스캐닝 (샘플링)
        xhtml_issues: int = 0
        all_files: list[Path] = list(extract_root.rglob("*"))
        sample_files = all_files[:50]
        for p in sample_files:
            if p.suffix.lower() in [".xhtml", ".html", ".htm"]:
                text = read_text_lossy(p)
                if "onclick" in text or "onload" in text or "<script" in text:
                    xhtml_issues = xhtml_issues + 1
        
        if xhtml_issues > 0:
            issues.append(f"잠재적 보안 위험 요소(스크립트 등) 발견: {xhtml_issues}개 이상의 파일")

        return issues

    def process_buffer(self, input_buffer, filename, log_fn=None):
        """EPUB 바이너리 버퍼를 받아 복구된 버퍼 반환"""
        def log(msg):
            if log_fn: log_fn(msg)
            print(msg, flush=True)

        log(f"\n[Repair] EPUB 수리 시작: {filename}")
        with tempfile.TemporaryDirectory(prefix="repair_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            in_epub = tmp_path / "input.epub"
            in_epub.write_bytes(input_buffer.read())
            
            extract_to = tmp_path / "extracted"
            extract_to.mkdir()
            
            notes = []
            changed_files = 0
            
            try:
                log("  - EPUB 압축 해제 중...")
                extract_epub(in_epub, extract_to)
                
                # 0. 사전 진단 (신뢰도 향상을 위한 로그 출력)
                log("\n[Diagnosis] EPUB 상태 정밀 진단 중...")
                diagnostics = self.diagnose_epub(extract_to)
                if diagnostics:
                    log(f"  ! 총 {len(diagnostics)}개의 잠재적 문제점이 발견되었습니다:")
                    for issue in diagnostics:
                        log(f"    • {issue}")
                else:
                    log("  ✓ 구조적인 큰 결함은 발견되지 않았으나, 최적화 세정을 진행합니다.")
                log("")

                # 1. Mimetype 및 기초 구조 확인
                log("  - 기본 구조 및 Mimetype 확인 중...")
                ensure_mimetype(extract_to)
                opf_rel = find_opf_path(extract_to)
                if not opf_rel:
                    log("  ! OPF 파일을 찾을 수 없어 기본 구조를 생성합니다.")
                    notes.append("OPF 파일을 찾을 수 없어 기본 구조를 생성합니다.")
                    ensure_container_xml(extract_to, "OEBPS/content.opf")
                    opf_path = extract_to / "OEBPS" / "content.opf"
                else:
                    opf_path = extract_to / opf_rel
                
                # 2. OPF 식별자 확인
                log("  - 메타데이터 식별자(dc:identifier) 검사 중...")
                ensure_identifier_in_opf(opf_path)
                
                # 3. 이미지 호환성 (TIFF -> JPG)
                log("  - 이미지 호환성 검사 중 (TIFF 변환)...")
                conv_imgs = try_convert_tiffs(extract_to)
                if conv_imgs:
                    msg = f"{len(conv_imgs)}개의 TIFF 이미지를 JPG로 변환했습니다."
                    log(f"    => {msg}")
                    notes.append(msg)
                    changed_files += len(conv_imgs)
                
                # 3-1. 폰트 스트리핑 (Nuclear Option: Google Books 호환성 최우선)
                log("  - 폰트 최적화 및 CSS 세정 중 (Google Books Safe Mode)...")
                font_ids = []
                for p in extract_to.rglob("*"):
                    if p.suffix.lower() in [".ttf", ".otf", ".woff", ".woff2"]:
                        font_ids.append(p.stem) # 아이디 추적을 위해 저장 (실제로는 OPF에서 찾음)
                        p.unlink() # 물리 파일 제거
                
                for p in extract_to.rglob("*.css"):
                    css_text = read_text_lossy(p)
                    # @font-face 블록 전체 제거
                    css_text = re.sub(r'@font-face\s*\{[^}]*\}', '', css_text, flags=re.S)
                    # font-family에서 커스텀 명칭 정밀 제거 (따옴표 유무 상관없이 제거하여 시스템 폰트 유도)
                    # 예: font-family: "고딕", sans-serif; -> font-family: sans-serif;
                    # 예: font-family: 명조; -> font-family:;
                    css_text = re.sub(r'font-family\s*:\s*([^;,\}]+)', r'font-family:', css_text)
                    write_text(p, css_text)

                # 4. XHTML 세정 및 확장자 현대화 (.html -> .xhtml)
                log("  - XHTML 본문 세정 및 확장자 현대화 (.html -> .xhtml) 중...")
                xhtml_items = []
                processed_count: int = 0
                for p in extract_to.rglob("*"):
                    if p.suffix.lower() in [".xhtml", ".html", ".htm"]:
                        # 4-1. 내용 세정 (XHTML 5 표준화 및 레거시 속성 제거)
                        text = read_text_lossy(p)
                        cleaned = upgrade_to_html5(text)
                        
                        # 4-2. 확장자 변경 및 파일 이동
                        new_path = p.with_suffix(".xhtml")
                        if p != new_path:
                            if new_path.exists(): new_path.unlink()
                            p.rename(new_path)
                            p = new_path
                            changed_files += 1
                        
                        write_text(p, cleaned)
                        processed_count += 1
                        
                        # OPF 상대 경로 저장
                        rel_href = os.path.relpath(p, opf_path.parent)
                        xhtml_items.append(rel_href)

                        if processed_count % 5 == 0:
                            log(f"    ... {processed_count}개 파일 처리 및 현대화 완료")

                # 4-1. OPF 파일 내의 확장자 동기화 및 폰트 항목 제거
                opf_text = read_text_lossy(opf_path)
                opf_text = re.sub(r'href="([^"]+)\.html"', r'href="\1.xhtml"', opf_text)
                opf_text = re.sub(r'href="([^"]+)\.htm"', r'href="\1.xhtml"', opf_text)
                
                # 매니페스트에서 폰트 아이템 제거
                opf_text = re.sub(r'<item[^>]+media-type="font/[^"]+"[^>]*/>', '', opf_text)
                opf_text = re.sub(r'<item[^>]+media-type="application/(vnd\.ms-opentype|x-font-ttf)"[^>]*/>', '', opf_text)
                
                # 4-2. EPUB 3.0 규격 업그레이드 (Google Books 대응)
                log("  - EPUB 3.0 현대 표준으로 업그레이드 중...")
                write_text(opf_path, opf_text) # 우선 확장자 저장
                self.upgrade_opf_to_v3(opf_path)
                
                # 4-3. nav.xhtml 생성 및 OPF 등록 (v2.2 Fix: 무조건 재생성하여 깨진 링크 수정)
                for p in extract_to.rglob("nav.xhtml"): p.unlink()
                
                log("  - EPUB 3 내비게이션(nav.xhtml) 고정밀 복구 중...")
                
                # 1. NCX에서 라벨 맵 추출 (순차적/강력 스캔)
                ncx_labels: dict[str, str] = {}
                for f_p in extract_to.rglob("*"):
                    if f_p.suffix.lower() == ".ncx":
                        txt = read_text_lossy(f_p)
                        # navPoint 단위로 분할하여 매칭
                        for entry in re.split(r'<navPoint', txt, flags=re.I):
                             t_m = re.search(r'<text[^>]*>([^<]+)</text>', entry, flags=re.I)
                             s_m = re.search(r'src=["\']([^"#\s\?]+)', entry, flags=re.I)
                             if t_m and s_m:
                                 lab, hr = t_m.group(1).strip(), s_m.group(1).strip()
                                 hr = re.sub(r'\.html?$', '.xhtml', hr, flags=re.I)
                                 if hr not in ncx_labels: ncx_labels[hr] = lab

                # 2. OPF에서 본문 항목 추출 및 라벨 부여
                nav_items = []
                opf_text = read_text_lossy(opf_path)
                # Manifest에서 XHTML 항목을 모두 찾아 라벨 매칭
                item_tags = re.findall(r'<item\s+[^>]+>', opf_text, flags=re.I)
                for itag in item_tags:
                    if 'application/xhtml+xml' not in itag.lower(): continue
                    id_m = re.search(r'id=["\']([^"\']+)["\']', itag, flags=re.I)
                    href_m = re.search(r'href=["\']([^"\']+)["\']', itag, flags=re.I)
                    if id_m and href_m:
                        i_id, i_href = id_m.group(1), href_m.group(1)
                        if "nav.xhtml" in i_href: continue
                        
                        # 라벨 결정: NCX -> Title -> id_id
                        label = ncx_labels.get(i_href)
                        if not label:
                            full_p = opf_path.parent / i_href
                            if full_p.exists():
                                c = read_text_lossy(full_p)
                                title_m = re.search(r'<title>([^<]+)</title>', c, flags=re.I)
                                if title_m and title_m.group(1).strip() and title_m.group(1).strip().lower() not in ["chapter", "title"]:
                                    label = title_m.group(1).strip()
                        
                        if not label: label = i_id
                        nav_items.append({"label": label, "href": i_href})
                
                create_nav_xhtml(extract_to, nav_items[:100])
                
                # 3. OPF 메타데이터 "수술적" 세정 (Surgical Purge)
                opf_text = read_text_lossy(opf_path)
                m_start = opf_text.find('<metadata')
                m_end = opf_text.find('</metadata>') + 11
                if m_start >= 0 and m_end > m_start:
                    meta_block = opf_text[m_start:m_end]
                    # 식별자(identifier) 내용만 추출
                    id_vals = re.findall(r'<dc:identifier[^>]*>(.*?)</dc:identifier>', meta_block, flags=re.S | re.I)
                    if id_vals:
                        val = id_vals[0].strip()
                        clean_id_tag = f'\n    <dc:identifier id="udocid">{val}</dc:identifier>'
                        # 기존 식별자들 완전 제거
                        meta_block = re.sub(r'<dc:identifier[^>]*>.*?</dc:identifier>', '', meta_block, flags=re.S | re.I)
                        # 정제된 식별자 삽입
                        meta_block = meta_block.replace('</metadata>', clean_id_tag + '\n</metadata>')
                    
                    # opf:scheme 및 dc:type 속성/태그 완전 제거
                    meta_block = re.sub(r'\s+opf:scheme=["\'][^"\']+["\']', '', meta_block)
                    meta_block = re.sub(r'<dc:type[^>]*>.*?</dc:type>', '', meta_block, flags=re.S | re.I)
                    opf_text = opf_text[:m_start] + meta_block + opf_text[m_end:]

                if 'id="nav"' not in opf_text:
                    # manifest에 nav 추가
                    nav_entry = '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                    opf_text = re.sub(r'(<manifest[^>]*>)', r'\1\n' + nav_entry, opf_text)
                    # spine에 nav 추가
                    opf_text = re.sub(r'(</spine>)', r'    <itemref idref="nav" linear="no"/>\n\1', opf_text)
                
                # 중복 및 잔여 opf:scheme 최종 제거 (전역)
                opf_text = re.sub(r'\s+opf:scheme=["\'][^"\']+["\']', '', opf_text)
                write_text(opf_path, opf_text)

                # 4. nav.xhtml 내의 "id0" 등 무의미한 라벨 최종 교정 (Brute Force)
                for p_nav in extract_to.rglob("nav.xhtml"):
                    nav_c = read_text_lossy(p_nav)
                    # id0, id1... 패턴을 찾아 파일명으로라도 대체 시도 (id0 -> 0.xhtml)
                    def nav_label_repl(m):
                        hr, lab = m.group(1), m.group(2)
                        if lab.startswith("id") and lab[2:].isdigit():
                            new_lab = hr.replace(".xhtml", "")
                            return f'href="{hr}">{new_lab}</a>'
                        return m.group(0)
                    nav_c = re.sub(r'href=["\']([^"\']+)["\']>([^<]+)</a>', nav_label_repl, nav_c)
                    write_text(p_nav, nav_c)

                # 4-4. toc.ncx 동기화 (v2.2 Fix: 하위 호환성 파일도 확장자 최신화, 앵커 대응)
                for ncx_p in extract_to.rglob("*.ncx"):
                    ncx_text = read_text_lossy(ncx_p)
                    # 앵커(#)가 있는 경우와 없는 경우 모두 대응하는 정교한 치환
                    ncx_text = re.sub(r'src="([^"]+)\.html(#|")', r'src="\1.xhtml\2', ncx_text)
                    ncx_text = re.sub(r'src="([^"]+)\.htm(#|")', r'src="\1.xhtml\2', ncx_text)
                    write_text(ncx_p, ncx_text)
                
                # 5. 결과 압축 (mimetype 선두 배치 등의 고도화된 ZIP 로직 사용)
                log("  - 수리된 EPUB 재압축 및 최종 버퍼 생성 중...")
                out_epub = tmp_path / "output.epub"
                create_epub(extract_to, out_epub)
                
                log("[Success] EPUB 수리 작업이 완료되었습니다.")
                return io.BytesIO(out_epub.read_bytes()), changed_files, notes
                
            except Exception as e:
                log(f"[Error] 수리 중 오류 발생: {str(e)}")
                return input_buffer, 0, [f"오류 발생: {str(e)}"]
