# 💎 EPUB Master

**수리부터 변환까지, 당신의 완벽한 EPUB 솔루션**

`EPUB Master`는 손상된 EPUB 파일을 복구하고, 일반 텍스트(TXT) 파일을 고품질 정체 EPUB으로 변환하는 올인원 도구입니다. 전문가 수준의 아키텍처와 세련된 블랙 & 그린 UI를 통해 최상의 사용자 경험을 제공합니다.

---

## ✨ 핵심 기능

### 🛠 EPUB Repair (자동 수리 엔진)
- **표준 규격 준수**: `epubcheck` 기준에 맞춰 파일 구조, 메타데이터, XHTML 문법을 자동 교정합니다.
- **보안 세정**: 불필요한 스크립트(JS) 및 위험한 HTML 이벤트를 제거하여 뷰어의 안정성을 확보합니다.
- **이미지 최적화**: 비표준 TIFF 이미지를 호환성이 높은 JPEG로 자동 변환합니다.
- **식별자 복구**: 누락된 도서 ID(UUID)를 생성하고 OPF 구조를 보정합니다.

### ✍️ TXT to EPUB (변환 생성 엔진)
- **스마트 분석**: 텍스트를 분석하여 제목, 저자, 챕터를 자동으로 추출합니다.
- **표지 자동 검색**: Google Books 및 Open Library API를 연동하여 도서 정보를 찾고 표지를 매칭합니다.
- **하이브리드 호환성**: 구글 북스 및 다양한 이북 리더기를 위해 최적화된 JPEG 표지와 가이드 태그를 생성합니다.
- **고음질 생성**: 5,000라인 단위 분할 및 전문적인 CSS 스타일링을 적용합니다.

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

## 🍱 아키텍처 (v2.1 Modular)
- `modules/core.py`: XML 처리 및 공통 유틸리티
- `modules/repairer.py`: EPUB 수리 전문 클래스
- `modules/converter.py`: TXT 변환 전문 클래스
- `app.py`: Streamlit 기반 마스터 버전 UI

상세한 버전별 변경 사항은 [history.md](history.md)에서 확인하실 수 있습니다.

---

## 🛡️ 라이선스
MIT License

---
**Made with ❤️ for Readers & Publishers** | Enhanced by Lindor Persona
