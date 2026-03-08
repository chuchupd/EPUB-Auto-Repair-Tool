import io
import os
import zipfile
from pathlib import Path
from modules.repairer import EPUBRepairer

def forensic_check():
    repairer = EPUBRepairer()
    input_path = Path("/Users/chuyouuwoo/Documents/GitHub/EPUB-Auto-Repair-Tool/private/output.epub")
    if not input_path.exists():
        print("Input file not found")
        return

    print(f"--- Original File: {input_path.name} ---")
    with zipfile.ZipFile(input_path, "r") as z:
        orig_info = z.infolist()
        orig_total_uncomp = sum(f.file_size for f in orig_info)
        orig_total_comp = sum(f.compress_size for f in orig_info)
        print(f"Files: {len(orig_info)}")
        print(f"Uncompressed: {orig_total_uncomp} bytes")
        print(f"Compressed: {orig_total_comp} bytes")

    with open(input_path, "rb") as f:
        buffer = io.BytesIO(f.read())
    
    out_buffer, changed, notes = repairer.process_buffer(buffer, "repair_test.epub")
    
    output_path = Path("/Users/chuyouuwoo/Documents/GitHub/EPUB-Auto-Repair-Tool/private/forensic_repaired.epub")
    output_path.write_bytes(out_buffer.getvalue())

    print(f"\n--- Repaired File: {output_path.name} ---")
    with zipfile.ZipFile(output_path, "r") as z:
        new_info = z.infolist()
        new_total_uncomp = sum(f.file_size for f in new_info)
        new_total_comp = sum(f.compress_size for f in new_info)
        print(f"Files: {len(new_info)}")
        print(f"Uncompressed: {new_total_uncomp} bytes")
        print(f"Compressed: {new_total_comp} bytes")
        
        # Compare file lists
        orig_names = {f.filename for f in orig_info}
        new_names = {f.filename for f in new_info}
        
        missing = orig_names - new_names
        added = new_names - orig_names
        
        if missing:
            print(f"\nMissing files in repaired version ({len(missing)}):")
            for m in sorted(list(missing))[:10]: print(f" - {m}")
        if added:
            print(f"\nAdded files in repaired version ({len(added)}):")
            for a in sorted(list(added))[:10]: print(f" - a")

if __name__ == "__main__":
    forensic_check()
