# 📜 EPUB Master Version History

이 문서는 `EPUB Master` (구 EPUB Auto-Repair Tool)의 개발 여정과 각 버전별 주요 변경 사항을 기록합니다.

---

## 💎 v2.1 (Master Edit) - 2026-03-08
**"브랜드의 완성: EPUB Master 리뉴얼"**

- **브랜드 통합**: 프로젝트 명칭을 `EPUB Master`로 변경 및 로고/아이콘(💎) 적용
- **UI/UX 혁신**:
    - Black & Green (Emerald on Dark) 테마 적용
    - Glassmorphism 효과가 적용된 현대적인 카드형 디자인
    - **Dual-Core Entry**: 'Generate'와 'Repair'를 분리한 직관적인 초기 화면 구현
    - 세션 기반 상태 관리로 매끄러운 화면 전환 지원
- **문서화**: 브랜드 성향에 맞춘 전문적인 `README.md` 및 `history.md` 작성

## 🍱 v2.0 (Modular Expansion) - 2026-03-08
**"아키텍처의 혁신: 모듈화 시스템 도입"**

- **패키지화**: 거대한 단일 파일 구조에서 `modules/` 패키지 구조로 전면 개편
    - `core.py`: XML 처리 및 공통 유틸리티 통합
    - `repairer.py`: EPUB 수리 로직 독립화
    - `converter.py`: TXT 변환 엔진 독립화
- **CLI/GUI 공용 엔진**: `fix_epub.py`와 `app.py`가 동일한 모듈 엔진을 사용하도록 통일하여 유지보수성 향상
- **수리 엔진 고도화**: 비표준 태그 중화(Neutralization) 로직 강화 및 `epubcheck` 연동 검증 프로세스 구축

## 🚀 v1.x (Foundation & Compliance)
**"기능의 완성 및 표준 준수"**

- **v1.6 ~ v1.7**:
    - 이북 리더기 호환성 강화 (Google Books 지원 최적화)
    - TIFF 이미지의 JPEG 자동 변환 지원
    - 한국어 폰트 및 인코딩 처리 안정화
- **v1.4 ~ v1.5 (Modern Standard)**:
    - `cover.xhtml` 자동 생성 기능 도입
    - 전문적인 타이포그래피 CSS 스타일링 적용
    - EPUB 3 Navigation Landmarks 및 가이드 태그 표준화
- **v1.2 ~ v1.3 (Compliance Patch)**:
    - 필수 메타데이터(`dc:identifier`, `dc:date` 등) 자동 보정
    - Binary mimetype 및 Charset 태그 표준 준수 패치
- **v1.0 ~ v1.1 (Core Engine)**:
    - TXT to EPUB 변환 기본 로직 구축
    - 메모리 효율적인 증분 쓰기(Incremental Writing) 구현
    - 자동 장(Chapter) 분할 및 실시간 진행 로그 시스템

---
**Made with ❤️ for Readers & Publishers** | Enhanced by Lindor Persona
