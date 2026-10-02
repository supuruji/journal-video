# -*- coding: utf-8 -*-
"""
extract_docx.py — pull the editor's preface and every Abstract/Keywords block
out of a journal-issue .docx, to help fill content.json. Standard library only.

Usage:
  python extract_docx.py "JDTREA Vol 5.2_최종.docx"
Writes <name>.fulltext.txt next to the script and prints the useful sections.
"""
import io, os, re, sys, zipfile

def paragraphs(docx_path):
    with zipfile.ZipFile(docx_path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.split(r"</w:p>", xml):
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)
        line = "".join(texts)
        for a, b in (("&amp;","&"),("&lt;","<"),("&gt;",">"),("&quot;",'"'),("&apos;","'")):
            line = line.replace(a, b)
        if line.strip():
            out.append(line.strip())
    return out

def main():
    if len(sys.argv) < 2:
        print("usage: python extract_docx.py <file.docx>"); return
    path = sys.argv[1]
    paras = paragraphs(path)
    base = os.path.splitext(os.path.basename(path))[0]
    txt = base + ".fulltext.txt"
    io.open(txt, "w", encoding="utf-8").write("\n".join(paras))
    print("Saved %s (%d paragraphs)\n" % (txt, len(paras)))

    # editor's / translator's preface
    print("="*70, "\nPREFACE (lines containing 'preface' + following text)\n", "="*70, sep="")
    for i, ln in enumerate(paras):
        if re.search(r"preface|서문|편역자|머리말", ln, re.I) and len(ln) < 80:
            for j in range(i, min(i+40, len(paras))):
                print(paras[j])
                if j > i and re.search(r"Editor of|Editor-in-Chief|편집장", paras[j]): break
            print("-"*40); break

    # abstracts + keywords
    print("\n" + "="*70, "\nABSTRACTS & KEYWORDS\n", "="*70, sep="")
    for i, ln in enumerate(paras):
        if ln.strip().lower() == "abstract" and i+1 < len(paras):
            print("\n[Abstract]\n" + paras[i+1])
        if ln.strip().lower().startswith("keywords"):
            print("[" + ln + "]")

if __name__ == "__main__":
    main()
