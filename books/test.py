import fitz

book = fitz.open("./LP.epub")
# print(book.get_toc())
print(book.metadata)
