from file import det_ebook_cls, HTMLtoLines
import sys

file = "../books/LP.epub"
ebook = det_ebook_cls(file)
# try:
#    try:
#        ebook.initialize()
#    except Exception as e:
#        sys.exit("ERRO: Badly-structured ebook.\n" + str(e))
#    for i in ebook.contents:
#        content = ebook.get_raw_text(i)
#        parser = HTMLtoLines()
#        parser.feed(content)
#        parser.close()
#        src_lines = parser.get_lines()
#        # sys.stdout.reconfigure(encoding="utf-8")  # Python>=3.7
#        for j in src_lines:
#            print(j + "\n\n")
# finally:
#    ebook.cleanup()
ebook.initialize()

print(ebook.contents)
