#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import argparse
from pathlib import Path
from modules.core import read_text_lossy, write_text, create_epub
from modules.repairer import EPUBRepairer

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

def process_one(epub_path: Path):
    """단일 EPUB 파일 수리 프로세스 (CLI용)"""
    repairer = EPUBRepairer(output_dir=OUTPUT_DIR)
    
    print(f"\n[*] 처리 중: {epub_path.name}")
    try:
        with open(epub_path, "rb") as f:
            out_buffer, changed_files, notes = repairer.process_buffer(f, epub_path.name)
            
        if changed_files > 0:
            out_path = OUTPUT_DIR / epub_path.name
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(out_buffer.getvalue())
            print(f"  [+] 수리 완료: {out_path}")
            for note in notes:
                print(f"      - {note}")
        else:
            print("  [-] 변경 사항이 없습니다.")
            
    except Exception as e:
        print(f"  [!] 오류 발생: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="EPUB Auto-Repair Tool (v2.0 Modular)")
    parser.add_argument("path", nargs="?", help="수리할 EPUB 파일 또는 폴더 경로")
    args = parser.parse_args()

    if args.path:
        target = Path(args.path)
        if target.is_file():
            process_one(target)
        elif target.is_dir():
            for f in target.glob("*.epub"):
                process_one(f)
    else:
        # 기본 입력 폴더 처리
        if not INPUT_DIR.exists():
            INPUT_DIR.mkdir()
            print(f"[*] '{INPUT_DIR.name}' 폴더가 생성되었습니다. EPUB 파일을 넣고 다시 실행하세요.")
            return 0
        
        epubs = list(INPUT_DIR.glob("*.epub"))
        if not epubs:
            print(f"[*] '{INPUT_DIR.name}' 폴더에 EPUB 파일이 없습니다.")
            return 0
            
        print(f"[*] 총 {len(epubs)}개의 파일을 찾았습니다.")
        for epub in epubs:
            process_one(epub)

    print("\n[*] 모든 작업이 완료되었습니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
