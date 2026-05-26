"""
Dong goi E/ F/ Y/ BALO/ thanh templates.zip
de upload len GitHub Releases.

Cach dung:
    python pack_templates.py

Ket qua:
    templates.zip (~ 400 KB)

Upload len:
    GitHub repo > Releases > Create release > Tag: templates-v1
    Attach templates.zip
"""
import os
import zipfile


def pack():
    folders = ["E", "F", "Y", "BALO"]
    output = "templates.zip"
    count = 0

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in folders:
            if not os.path.isdir(folder):
                print(f"  [!] {folder}/ khong ton tai — bo qua")
                continue
            for fn in sorted(os.listdir(folder)):
                if fn.endswith(".png"):
                    fp = os.path.join(folder, fn)
                    zf.write(fp)
                    count += 1

    size = os.path.getsize(output)
    print(f"Da tao: {output}")
    print(f"  {count} files, {size // 1024} KB")
    print()
    print("Upload len GitHub Releases:")
    print("  1. Vao repo > Releases > Create new release")
    print("  2. Tag: templates-v1")
    print("  3. Attach file templates.zip")


if __name__ == "__main__":
    pack()
