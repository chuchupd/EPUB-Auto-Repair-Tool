# EPUB-Auto-Repair-Tool

# EPUB Auto Repair Tool

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python script that automatically repairs common structural and XHTML problems in EPUB files so they can pass strict publishing platform validation.

This tool is designed for EPUB files generated from:

- PDF → EPUB conversion
- OCR pipelines
- legacy ebook generators
- broken publishing exports

These sources often produce malformed XHTML, invalid metadata, or unsupported resources that cause EPUB uploads to fail.

This script attempts to automatically repair those issues.

---

# Features

## 1. Broken XHTML Tag Repair

Some EPUB generators accidentally insert text that looks like XML tags, breaking the document.

Example:

```html
<IRA___ ...>
<Beati pauperes="" ...>
<MI5 ...>
<per ardua="" ...>
```

These are automatically escaped so they become plain text instead of invalid tags.

---

## 2. NULL Byte Removal

Removes `0x00` NULL bytes that often appear in EPUB files generated from OCR or PDF conversion.

These bytes commonly break XML parsers used by publishing platforms.

---

## 3. HTML Entity Fix

Converts:

```
&nbsp;
```

into the XHTML-safe equivalent:

```
&#160;
```

---

## 4. Metadata Repair

Automatically repairs or creates the required metadata fields in `content.opf`:

- `dc:identifier`
- `unique-identifier`

---

## 5. Dangerous Tag Cleanup

Removes unsupported tags that may break ebook readers or upload validators:

- `<script>`
- `<form>`
- `<button>`
- inline JavaScript event attributes

---

## 6. TIFF Image Conversion (Optional)

If `Pillow` is installed, the script converts:

```
.tif
.tiff
```

images into:

```
.jpg
```

and updates references in the EPUB.

---

## 7. EPUB Repackaging

Rebuilds the EPUB archive with correct EPUB specification structure:

- `mimetype` must be the **first file**
- `mimetype` must be stored **without compression**
- correct ZIP archive ordering

---

# Folder Structure

```
project/
│
├─ fix_epub_aggressive_tag_escape_batch_fixed.py
│
├─ inputs/
│   ├─ book1.epub
│   ├─ book2.epub
│
└─ outputs/
```

---

# Usage

Run the script:

```bash
python3 fix_epub_aggressive_tag_escape_batch_fixed.py
```

All EPUB files placed in the `inputs/` directory will be processed and repaired versions will be written to the `outputs/` directory.

Example output:

```
[OK] book.epub -> book.epub | changed_files=5
```

---

# Optional Dependency

To enable TIFF image conversion:

```bash
pip install pillow
```

If Pillow is not installed, TIFF conversion will be skipped.

---

# Requirements

Python 3.8+

Standard libraries used:

- zipfile
- xml.etree
- pathlib
- regex
- uuid

---

# Typical Problems This Tool Fixes

Publishing platform upload failures such as:

- malformed XHTML
- invalid XML token errors
- missing identifier metadata
- unsupported image formats
- broken EPUB ZIP structure

---

# Recommended Validation

For strict EPUB validation you may still want to run:

```
epubcheck
```

after processing.

---

# License

MIT License
