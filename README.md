# 💎 EPUB Master

**수리부터 변환까지, 당신의 완벽한 EPUB 솔루션**

`EPUB Master`는 손상된 EPUB 파일을 복구하고, 일반 텍스트(TXT) 파일을 고품질 정체 EPUB으로 변환하는 올인원 도구입니다. 

---

## ✨ 핵심 기능

- **EPUB 3.0 Modernization**: 구형 EPUB 2.0 파일을 최신 3.0 규격으로 자동 업그레이드 (Google Books 완벽 호환)
- **Hybrid Navigation**: EPUB 3 `nav.xhtml`과 EPUB 2 `toc.ncx`를 동시 생성하여 모든 리더기 대응
- **Nuclear Conversion**: 구글 북스 업로드 실패의 핵심인 비표준 속성(img width%), 커스텀 폰트 의존성, XML 선언부 전면 소거
- **High-Fidelity Navigation**: NCX 및 XHTML 타이틀 분석을 통한  목차 라벨링 (`id0` 등 무의미한 라벨 자동 교정)
- **Standard Compliance**: 전 파일 Unix LF 및 BOM-free 강제로 최신 이북 파서와의 무결성 확보
- **Pure ZIP Optimization**: `mimetype` 전면 배치 및 가비지 필터링으로 업로드 무결성 확보
- **Rich AI Interface**: Streamlit 기반의  직관적인 UI/UX

### ✍️ TXT to EPUB (변환 생성 엔진)
- **스마트 분석**: 텍스트를 분석하여 제목, 저자, 챕터를 자동으로 추출합니다.
- **표지 자동 검색**: Google Books 및 Open Library API를 연동하여 도서 정보를 찾고 표지를 매칭합니다.
- **하이브리드 호환성**: 구글 북스 및 다양한 이북 리더기를 위해 최적화된 JPEG 표지와 가이드 태그를 생성합니다.
- **고음질 생성**: 5,000라인 단위 분할 및  CSS 스타일링을 적용합니다.

---

## 🚀 시작하기

### 1단계: 설치
```bash
git clone https://github.com/chuchupd/EPUB-Auto-Repair-Tool.git
cd EPUB-Auto-Repair-Tool
pip install -r requirements.txt
```

### 2단계: 실행
**웹 UI 모드 (추천)**
```bash
python3 -m streamlit run app.py
```

**터미널 모드 (대량 처리)**
```bash
python3 fix_epub.py [대상파일/폴더]
```

---

## 🍱 아키텍처 (v2.3 Master)
- **[2026-03-09] v2.3 (Forensic)**: 구글 북스 최종 승인을 위한 세부적인 기능 체크
- **[2026-03-08] v2.2 (Standard Upgrade)**: Google Books 호환성을 위한 EPUB 3.0 내부 정밀 체크 (폰트 MIME, Spine 구조 개선)
- **[2026-03-08] v2.1 (Master Repair)**: 진단 리포트 기능 추가
- `app.py`: Streamlit 기반 환경 UI

상세한 버전별 변경 사항은 [history.md](history.md)에서 확인하실 수 있습니다.

---

## 🛡️ 라이선스
MIT License

---
**Made with ❤️ for Readers & Publishers** | Enhanced by Lindor Persona
