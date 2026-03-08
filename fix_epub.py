#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import uuid
import html
import zipfile
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "inputs"
OUTPUT_DIR = BASE_DIR / "outputs"

TEXT_EXTS = {".xhtml", ".html", ".htm", ".xml", ".css", ".ncx", ".opf", ".txt"}
XHTML_EXTS = {".xhtml", ".html", ".htm"}

VALID_HTML_TAGS = {
    "html", "head", "title", "meta", "link", "style", "body",
    "div", "span", "p", "br", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "td", "th", "colgroup", "col", "caption",
    "img", "a", "strong", "em", "b", "i", "u", "s", "sub", "sup", "small", "big",
    "blockquote", "pre", "code", "kbd", "samp", "var",
    "ruby", "rb", "rt", "rp",
    "figure", "figcaption",
    "section", "article", "aside", "nav",
    "center",
    "svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text",
    "image",
}

XML_NAMESPACES = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "ncx": "http://www.daisy.org/z3986/2005/ncx/",
    "xhtml": "http://www.w3.org/1999/xhtml",
}

for prefix, uri in XML_NAMESPACES.items():
    ET.register_namespace(prefix if prefix != "opf" else "", uri)


def read_text_lossy(path: Path):
    raw = path.read_bytes()
    changed = False

    if b"\x00" in raw:
        raw = raw.replace(b"\x00", b"")
        changed = True

    text = None
    for enc in ("utf-8", "utf-8-sig", "cp949", "euc-kr", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except Exception:
            pass
    if text is None:
        text = raw.decode("utf-8", errors="replace")

    if path.suffix.lower() in {".xml", ".opf", ".ncx", ".xhtml", ".html", ".htm"}:
        for end_tag in ("</html>", "</ncx>", "</package>", "</container>"):
            idx = text.lower().rfind(end_tag)
            if idx != -1:
                end_pos = idx + len(end_tag)
                tail = text[end_pos:]
                if tail and any(ch not in " \t\r\n" for ch in tail):
                    text = text[:end_pos] + "\n"
                    changed = True
                break

    if "&nbsp;" in text:
        text = text.replace("&nbsp;", "&#160;")
        changed = True

    return text, changed


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def try_parse_xml_string(text: str):
    try:
        ET.fromstring(text.encode("utf-8"))
        return True
    except Exception:
        return False


def sanitize_invalid_tags_in_markup(text: str):
    changed = False
    tag_like_re = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<!DOCTYPE.*?>|<\?.*?\?>|</?[^<>]+?>", re.I | re.S)

    def repl(m):
        nonlocal changed
        tok = m.group(0)

        if tok.startswith("<!--") or tok.startswith("<![CDATA[") or tok.startswith("<?") or tok.upper().startswith("<!DOCTYPE"):
            return tok

        inner = tok[1:-1].strip()
        if not inner:
            changed = True
            return html.escape(tok)

        closing = inner.startswith("/")
        inner2 = inner[1:].strip() if closing else inner

        if inner2.endswith("/"):
            inner2 = inner2[:-1].rstrip()

        if not inner2:
            changed = True
            return html.escape(tok)

        name = inner2.split(None, 1)[0]
        base = name.split(":", 1)[-1].lower()

        valid_name = re.fullmatch(r"[A-Za-z_][A-Za-z0-9._:-]*", name) is not None
        known_tag = base in VALID_HTML_TAGS

        if not valid_name or not known_tag:
            changed = True
            return html.escape(tok)

        return tok

    new_text = tag_like_re.sub(repl, text)
    return new_text, changed


def strip_event_handlers_and_risky_tags(text: str):
    changed = False

    risky_blocks = [
        re.compile(r"<script\b.*?</script\s*>", re.I | re.S),
        re.compile(r"<form\b.*?</form\s*>", re.I | re.S),
        re.compile(r"<button\b.*?</button\s*>", re.I | re.S),
    ]
    for pat in risky_blocks:
        new_text, n = pat.subn("", text)
        if n:
            text = new_text
            changed = True

    new_text, n = re.subn(r'\s+on[a-zA-Z]+\s*=\s*"[^"]*"', "", text)
    if n:
        text = new_text
        changed = True
    new_text, n = re.subn(r"\s+on[a-zA-Z]+\s*=\s*'[^']*'", "", text)
    if n:
        text = new_text
        changed = True

    return text, changed


def clean_text_file(path: Path):
    text, changed = read_text_lossy(path)
    notes = []

    if path.suffix.lower() in XHTML_EXTS:
        text2, c1 = strip_event_handlers_and_risky_tags(text)
        if c1:
            text = text2
            changed = True
            notes.append("risky-tag-clean")

        # Aggressively escape suspicious pseudo-tags even before parse check
        text2, c2 = sanitize_invalid_tags_in_markup(text)
        if c2:
            text = text2
            changed = True
            notes.append("pseudo-tag-escaped")

    if changed:
        write_text(path, text)

    return changed, notes


def find_opf_path(root: Path):
    container = root / "META-INF" / "container.xml"
    if container.exists():
        try:
            tree = ET.parse(container)
            r = tree.getroot()
            elem = r.find(".//{*}rootfile")
            if elem is not None:
                full_path = elem.attrib.get("full-path")
                if full_path:
                    p = root / full_path
                    if p.exists():
                        return p
        except Exception:
            pass

    cands = list(root.rglob("*.opf"))
    return cands[0] if cands else None


def ensure_container_xml(root: Path, opf_rel_path: str):
    meta_inf = root / "META-INF"
    meta_inf.mkdir(parents=True, exist_ok=True)
    container_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
        '  <rootfiles>\n'
        f'    <rootfile full-path="{opf_rel_path}" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n'
        '</container>\n'
    )
    (meta_inf / "container.xml").write_text(container_xml, encoding="utf-8")


def ensure_identifier_in_opf(opf_path: Path):
    notes = []
    changed = False

    try:
        tree = ET.parse(opf_path)
        root = tree.getroot()

        metadata = root.find("{*}metadata")
        if metadata is None:
            metadata = ET.SubElement(root, "{http://www.idpf.org/2007/opf}metadata")
            changed = True
            notes.append("metadata-created")

        pkg_uid = root.attrib.get("unique-identifier", "").strip()
        identifiers = metadata.findall("{http://purl.org/dc/elements/1.1/}identifier")
        target = None

        if pkg_uid:
            for ident in identifiers:
                if ident.attrib.get("id") == pkg_uid:
                    target = ident
                    break

        if target is None and identifiers:
            target = identifiers[0]
            if not target.attrib.get("id"):
                target.attrib["id"] = pkg_uid or "bookid"
                changed = True
                notes.append("identifier-id-added")

        if target is None:
            target = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}identifier")
            target.text = f"urn:uuid:{uuid.uuid4()}"
            target.attrib["id"] = pkg_uid or "bookid"
            changed = True
            notes.append("identifier-created")

        if not pkg_uid or target.attrib.get("id") != pkg_uid:
            root.attrib["unique-identifier"] = target.attrib.get("id", "bookid")
            changed = True
            notes.append("unique-identifier-fixed")

        if not (target.text or "").strip():
            target.text = f"urn:uuid:{uuid.uuid4()}"
            changed = True
            notes.append("identifier-value-filled")

        if changed:
            tree.write(opf_path, encoding="utf-8", xml_declaration=True)

    except Exception as e:
        notes.append(f"opf-identifier-error:{e}")

    return changed, notes


def try_convert_tiffs(root: Path):
    notes = []
    changed = False
    try:
        from PIL import Image
    except Exception:
        return changed, notes

    tif_files = list(root.rglob("*.tif")) + list(root.rglob("*.tiff"))
    if not tif_files:
        return changed, notes

    opf = find_opf_path(root)
    opf_text = opf.read_text(encoding="utf-8", errors="ignore") if opf and opf.exists() else None

    for tif in tif_files:
        try:
            jpg = tif.with_suffix(".jpg")
            with Image.open(tif) as im:
                if im.mode not in ("RGB", "L"):
                    im = im.convert("RGB")
                im.save(jpg, format="JPEG", quality=90)
            tif.unlink()
            changed = True
            notes.append(f"tiff->jpg:{tif.name}")

            old_name = tif.name
            new_name = jpg.name

            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in TEXT_EXTS.union(XHTML_EXTS):
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                    new_txt = txt.replace(old_name, new_name)
                    if new_txt != txt:
                        p.write_text(new_txt, encoding="utf-8")

            if opf_text:
                opf_text = opf_text.replace(f'href="{old_name}"', f'href="{new_name}"')
                opf_text = opf_text.replace('media-type="image/tiff"', 'media-type="image/jpeg"')
        except Exception as e:
            notes.append(f"tiff-convert-fail:{tif.name}:{e}")

    if changed and opf and opf_text is not None:
        opf.write_text(opf_text, encoding="utf-8")

    return changed, notes


def ensure_mimetype(root: Path):
    mt = root / "mimetype"
    content = "application/epub+zip"
    if not mt.exists() or mt.read_text(encoding="utf-8", errors="ignore").strip() != content:
        mt.write_text(content, encoding="utf-8")
        return True
    return False


def extract_epub(epub_path: Path, extract_to: Path):
    with zipfile.ZipFile(epub_path, "r") as zf:
        zf.extractall(extract_to)


def create_epub(folder: Path, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as epub:
        mimetype_path = folder / "mimetype"
        epub.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)

        all_files = []
        for p in folder.rglob("*"):
            if p.is_file() and p != mimetype_path:
                all_files.append(p)

        for p in sorted(all_files):
            rel = p.relative_to(folder).as_posix()
            epub.write(p, rel, compress_type=zipfile.ZIP_DEFLATED)


def process_one(epub_path: Path):
    notes = []
    changed_files = 0

    with tempfile.TemporaryDirectory(prefix="epubfix_") as td:
        root = Path(td)
        extract_epub(epub_path, root)

        if ensure_mimetype(root):
            notes.append("mimetype-fixed")

        opf_path = find_opf_path(root)
        if opf_path is None:
            raise RuntimeError("content.opf not found")

        opf_rel = opf_path.relative_to(root).as_posix()
        ensure_container_xml(root, opf_rel)
        notes.append("container-fixed")

        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS.union(XHTML_EXTS):
                changed, extra = clean_text_file(p)
                if changed:
                    changed_files += 1
                    notes.extend(f"{p.name}:{x}" for x in extra)

        opf_changed, opf_notes = ensure_identifier_in_opf(opf_path)
        if opf_changed:
            changed_files += 1
        notes.extend(opf_notes)

        tiff_changed, tiff_notes = try_convert_tiffs(root)
        if tiff_changed:
            changed_files += 1
        notes.extend(tiff_notes)

        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS.union(XHTML_EXTS):
                changed, extra = clean_text_file(p)
                if changed:
                    changed_files += 1
                    notes.extend(f"{p.name}:{x}" for x in extra)

        out_path = OUTPUT_DIR / epub_path.name
        create_epub(root, out_path)

    return out_path, changed_files, notes


def main():
    if not INPUT_DIR.exists():
        print("inputs 폴더가 없습니다.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    epubs = sorted(INPUT_DIR.glob("*.epub"))
    if not epubs:
        print("inputs 폴더에 epub 파일이 없습니다.")
        return 1

    success = 0
    fail = 0

    for epub in epubs:
        try:
            out_path, changed_files, notes = process_one(epub)
            summary = ", ".join(notes[:10])
            if len(notes) > 10:
                summary += f" ... (+{len(notes)-10})"
            print(f"[OK] {epub.name} -> {out_path.name} | changed_files={changed_files}" + (f" | {summary}" if summary else ""))
            success += 1
        except Exception as e:
            print(f"[FAIL] {epub.name} -> {e}")
            fail += 1

    print("")
    print("완료")
    print(f"success: {success}")
    print(f"fail: {fail}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
