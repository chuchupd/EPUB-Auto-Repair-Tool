
# EPUB Auto Repair Tool

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A Python script that automatically repairs common structural and XHTML problems in EPUB files so they can pass strict publishing platform validation.

출판 플랫폼 업로드 시 발생하는 **EPUB 구조 오류와 XHTML 오류를 자동으로 수정하는 Python 스크립트**입니다.

이 도구는 다음과 같은 환경에서 생성된 EPUB 파일을 복구하기 위해 만들어졌습니다.

- PDF → EPUB 변환
- OCR 파이프라인
- 오래된 ebook 제작 도구
- 깨진 EPUB export

이러한 과정에서 종종 **잘못된 XHTML 태그, 깨진 메타데이터, 지원되지 않는 리소스**가 발생하며 업로드가 실패합니다.  
이 스크립트는 이러한 문제를 자동으로 수정합니다.

---

# Features / 주요 기능

## 1. Broken XHTML Tag Repair  
## 깨진 XHTML 태그 자동 복구

Some EPUB generators accidentally insert text that looks like XML tags, breaking the document.

일부 EPUB 생성기는 **본문 텍스트를 XML 태그처럼 잘못 삽입**하여 문서를 깨뜨립니다.

Example:

```
<IRA___ ...>
<Beati pauperes="" ...>
<MI5 ...>
<per ardua="" ...>
```

The script automatically escapes these so they become plain text instead of invalid tags.

스크립트는 이러한 가짜 태그를 자동으로 **텍스트로 escape 처리**하여 XML 구조 오류를 방지합니다.

---

## 2. NULL Byte Removal  
## NULL 바이트 제거

Removes `0x00` NULL bytes often introduced during OCR or PDF conversions.

OCR이나 PDF 변환 과정에서 종종 삽입되는 `0x00` NULL 바이트를 제거합니다.

These bytes frequently break XML parsers used by publishing platforms.

이 바이트는 많은 출판 플랫폼의 XML 파서를 깨뜨립니다.

---

## 3. HTML Entity Fix  
## HTML 엔티티 수정

Converts

```
&nbsp;
```

into XHTML-safe

```
&#160;
```

XHTML 표준과 호환되도록 HTML 엔티티를 수정합니다.

---

## 4. Metadata Repair  
## 메타데이터 자동 복구

Automatically repairs or creates required metadata inside `content.opf`.

`content.opf` 내부의 필수 메타데이터를 자동으로 수정합니다.

- `dc:identifier`
- `unique-identifier`

---

## 5. Dangerous Tag Cleanup  
## 위험 태그 제거

Removes unsupported tags that may break readers or upload validators.

전자책 리더나 업로드 검증을 깨뜨릴 수 있는 태그를 제거합니다.

Removed tags:

- `<script>`
- `<form>`
- `<button>`
- inline JavaScript events

---

## 6. TIFF Image Conversion (Optional)  
## TIFF 이미지 자동 변환 (선택)

If `Pillow` is installed the script converts:

Pillow 라이브러리가 설치된 경우

```
.tif
.tiff
```

images into

```
.jpg
```

TIFF 이미지를 JPG로 변환하고 EPUB 내부 참조를 업데이트합니다.

---

## 7. EPUB Repackaging  
## EPUB 재패키징

Rebuilds the EPUB archive to follow the EPUB specification.

EPUB 규격에 맞게 ZIP 구조를 다시 생성합니다.

- `mimetype` must be the **first file**
- `mimetype` must be **uncompressed**
- correct ZIP structure

---

# Folder Structure / 폴더 구조

```
project/
│
├─ fix_epub.py
│
├─ inputs/
│   ├─ book1.epub
│   ├─ book2.epub
│
└─ outputs/
```

---

# Usage / 사용 방법

Run the script:

스크립트를 실행합니다.

```
python3 fix_epub.py
```

All EPUB files inside `inputs/` will be processed.

`inputs/` 폴더 안의 모든 EPUB 파일이 자동으로 처리됩니다.

Repaired EPUB files will appear in:

수정된 EPUB 파일은 다음 위치에 생성됩니다.

```
outputs/
```

Example output:

```
[OK] book.epub -> book.epub | changed_files=5
```

---

# Optional Dependency / 선택 의존성

To enable TIFF conversion:

TIFF 변환 기능을 사용하려면:

```
pip install pillow
```

If Pillow is not installed, TIFF conversion will be skipped.

설치되지 않은 경우 TIFF 변환 기능은 자동으로 건너뜁니다.

---

# Requirements / 요구 사항

Python 3.8+

Standard libraries:

- zipfile
- xml.etree
- pathlib
- re
- uuid

---

# Typical Problems This Tool Fixes  
# 해결 가능한 대표 문제

Publishing platform upload failures such as:

다음과 같은 EPUB 업로드 실패 문제를 해결합니다.

- malformed XHTML
- invalid XML token errors
- missing identifier metadata
- unsupported image formats
- broken EPUB ZIP structure

---

# License

MIT License
