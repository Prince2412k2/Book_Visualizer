import file
import time
import zipfile
import xml.etree.ElementTree as ET


book1= file.Epub("../books/LP.epub")
book2= file.Epub("../books/HP.epub")
book1.initialize()
book2.initialize()
content2=book2.contents
content1=book1.contents
toc=book1.toc_entries

print(content1)
# text_html = book1.get_raw_text(content1[0])

# start_time = time.time()

# content_parser = file.HTMLtoLines()
# content_parser.feed(text_html)
# lines = content_parser.get_lines()
# print(text_html)

# toc_parser = file.HTMLtoLines()
# toc_list = [toc_parser.feed(i) for i in toc[1]]
# toc_lines = toc_parser.get_lines()

# end_time = time.time()
# print(len(lines))
#print(toc[1])

# print(f"Time taken: {end_time - start_time:.6f} seconds")

#

