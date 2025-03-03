import base64
import zipfile
import re
import os
import textwrap
import shutil
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from html.parser import HTMLParser
from html import unescape
import textwrap
import mobi
from icecream import ic
import sys


try:
    import _markupbase
except ImportError:
    import markupbase as _markupbase


class Epub:
    NS = {
        "DAISY": "http://www.daisy.org/z3986/2005/ncx/",
        "OPF": "http://www.idpf.org/2007/opf",
        "CONT": "urn:oasis:names:tc:opendocument:xmlns:container",
        "XHTML": "http://www.w3.org/1999/xhtml",
        "EPUB": "http://www.idpf.org/2007/ops",
    }

    def __init__(self, fileepub):
        self.path = os.path.abspath(fileepub)
        self.file = zipfile.ZipFile(fileepub, "r")

    def get_meta(self):
        meta = []
        # why self.file.read(self.rootfile) problematic
        cont = ET.fromstring(self.file.open(self.rootfile).read())
        for i in cont.findall("OPF:metadata/*", self.NS):
            if i.text is not None:
                meta.append([re.sub("{.*?}", "", i.tag), i.text])
        return meta

    def initialize(self):
        cont = ET.parse(self.file.open("META-INF/container.xml"))
        self.rootfile = cont.find("CONT:rootfiles/CONT:rootfile", self.NS).attrib[
            "full-path"
        ]
        self.rootdir = (
            os.path.dirname(self.rootfile) + "/"
            if os.path.dirname(self.rootfile) != ""
            else ""
        )
        cont = ET.parse(self.file.open(self.rootfile))

        # EPUB3
        self.version = cont.getroot().get("version")

        if self.version == "2.0":
            # Use a fallback if the TOC element is not found
            toc_element = cont.find(
                "OPF:manifest/*[@media-type='application/x-dtbncx+xml']", self.NS
            )

            if toc_element is not None:
                self.toc = self.rootdir + toc_element.get("href")
            else:
                self.toc = "default_toc_path"  # or handle this case appropriately

        elif self.version == "3.0":
            toc_element = cont.find("OPF:manifest/*[@properties='nav']", self.NS)
            if toc_element is not None:
                self.toc = self.rootdir + toc_element.get("href")
            else:
                self.toc = "default_toc_path"  # or handle this case appropriately

        self.contents = []
        self.toc_entries = [[], [], []]

        # cont = ET.parse(self.file.open(self.rootfile)).getroot()
        self.manifest = []
        for i in cont.findall("OPF:manifest/*", self.NS):
            # EPUB3
            # if i.get("id") != "ncx" and i.get("properties") != "nav":
            if (
                i.get("media-type") != "application/x-dtbncx+xml"
                and i.get("properties") != "nav"
                or i.get("media-type") == ("text/css")
            ):
                self.manifest.append([i.get("id"), i.get("href")])

        self.spine, contents = [], []
        for i in cont.findall("OPF:spine/*", self.NS):
            self.spine.append(i.get("idref"))
        for i in self.spine:
            for j in self.manifest:
                if i == j[0]:
                    self.contents.append(self.rootdir + unquote(j[1]))
                    contents.append(unquote(j[1]))
                    self.manifest.remove(j)
                    # TODO: test is break necessary
                    break

        try:
            toc = ET.parse(self.file.open(self.toc)).getroot()
            # EPUB3
            if self.version == "2.0":
                navPoints = toc.findall("DAISY:navMap//DAISY:navPoint", self.NS)
            elif self.version == "3.0":
                navPoints = toc.findall(
                    "XHTML:body//XHTML:nav[@EPUB:type='toc']//XHTML:a", self.NS
                )
            for i in navPoints:
                if self.version == "2.0":
                    src = i.find("DAISY:content", self.NS).get("src")
                    name = i.find("DAISY:navLabel/DAISY:text", self.NS).text
                elif self.version == "3.0":
                    src = i.get("href")
                    name = "".join(list(i.itertext()))
                src = src.split("#")
                try:
                    idx = contents.index(unquote(src[0]))
                except ValueError:
                    continue
                self.toc_entries[0].append(name)
                self.toc_entries[1].append(idx)
                if len(src) == 2:
                    self.toc_entries[2].append(src[1])
                elif len(src) == 1:
                    self.toc_entries[2].append("")
        except AttributeError:
            pass
        return self

    def get_raw_text(self, chpath):
        # using try-except block to catch
        # zlib.error: Error -3 while decompressing data: invalid distance too far back
        # caused by forking PROC_COUNTLETTERS
        while True:
            try:
                content = self.file.open(chpath).read()
                break
            except:
                continue
        return content.decode("utf-8")

    def get_img_bytestr(self, impath):
        return impath, self.file.read(impath)

    def cleanup(self):
        return


class Mobi(Epub):
    def __init__(self, filemobi):
        self.path = os.path.abspath(filemobi)
        self.file, _ = mobi.extract(filemobi)

    def get_meta(self):
        meta = []
        # why self.file.read(self.rootfile) problematic
        with open(os.path.join(self.rootdir, "content.opf")) as f:
            cont = ET.parse(f).getroot()
        for i in cont.findall("OPF:metadata/*", self.NS):
            if i.text is not None:
                meta.append([re.sub("{.*?}", "", i.tag), i.text])
        return meta

    def initialize(self):
        self.rootdir = os.path.join(self.file, "mobi7")
        self.toc = os.path.join(self.rootdir, "toc.ncx")
        self.version = "2.0"

        self.contents = []
        self.toc_entries = [[], [], []]

        with open(os.path.join(self.rootdir, "content.opf")) as f:
            cont = ET.parse(f).getroot()
        self.manifest = []
        for i in cont.findall("OPF:manifest/*", self.NS):
            # EPUB3
            # if i.get("id") != "ncx" and i.get("properties") != "nav":
            if (
                i.get("media-type") != "application/x-dtbncx+xml"
                and i.get("properties") != "nav"
            ):
                self.manifest.append([i.get("id"), i.get("href")])

        self.spine, contents = [], []
        for i in cont.findall("OPF:spine/*", self.NS):
            self.spine.append(i.get("idref"))
        for i in self.spine:
            for j in self.manifest:
                if i == j[0]:
                    self.contents.append(os.path.join(self.rootdir, unquote(j[1])))
                    contents.append(unquote(j[1]))
                    self.manifest.remove(j)
                    # TODO: test is break necessary
                    break

        with open(self.toc) as f:
            toc = ET.parse(f).getroot()
        # EPUB3
        if self.version == "2.0":
            navPoints = toc.findall("DAISY:navMap//DAISY:navPoint", self.NS)
        elif self.version == "3.0":
            navPoints = toc.findall(
                "XHTML:body//XHTML:nav[@EPUB:type='toc']//XHTML:a", self.NS
            )
        for i in navPoints:
            if self.version == "2.0":
                src = i.find("DAISY:content", self.NS).get("src")
                name = i.find("DAISY:navLabel/DAISY:text", self.NS).text
            elif self.version == "3.0":
                src = i.get("href")
                name = "".join(list(i.itertext()))
            src = src.split("#")
            try:
                idx = contents.index(unquote(src[0]))
            except ValueError:
                continue
            self.toc_entries[0].append(name)
            self.toc_entries[1].append(idx)
            if len(src) == 2:
                self.toc_entries[2].append(src[1])
            elif len(src) == 1:
                self.toc_entries[2].append("")
        return self

    def get_raw_text(self, chpath):
        # using try-except block to catch
        # zlib.error: Error -3 while decompressing data: invalid distance too far back
        # caused by forking PROC_COUNTLETTERS
        while True:
            try:
                with open(chpath) as f:
                    content = f.read()
                break
            except:
                continue
        # return content.decode("utf-8")
        return content

    def get_img_bytestr(self, impath):
        # TODO: test on windows
        # if impath "Images/asdf.png" is problematic
        with open(os.path.join(self.rootdir, impath), "rb") as f:
            src = f.read()
        return impath, src

    def cleanup(self):
        shutil.rmtree(self.file)
        return


class Azw3(Epub):
    def __init__(self, fileepub):
        self.path = os.path.abspath(fileepub)
        self.tmpdir, self.tmpepub = mobi.extract(fileepub)
        self.file = zipfile.ZipFile(self.tmpepub, "r")

    def cleanup(self):
        shutil.rmtree(self.tmpdir)
        return


class FictionBook:
    NS = {"FB2": "http://www.gribuser.ru/xml/fictionbook/2.0"}

    def __init__(self, filefb):
        self.path = os.path.abspath(filefb)
        self.file = filefb

    def get_meta(self):
        desc = self.root.find("FB2:description", self.NS)
        alltags = desc.findall("*/*")
        return [[re.sub("{.*?}", "", i.tag), " ".join(i.itertext())] for i in alltags]

    def initialize(self):
        cont = ET.parse(self.file)
        self.root = cont.getroot()

        self.contents = []
        self.toc_entries = [[], [], []]

        self.contents = self.root.findall("FB2:body/*", self.NS)
        # TODO
        for n, i in enumerate(self.contents):
            title = i.find("FB2:title", self.NS)
            if title is not None:
                self.toc_entries[0].append("".join(title.itertext()))
                self.toc_entries[1].append(n)
                self.toc_entries[2].append("")
        return self

    def get_raw_text(self, node):
        ET.register_namespace("", "http://www.gribuser.ru/xml/fictionbook/2.0")
        # the line below was commented
        # sys.exit(ET.tostring(node, encoding="utf8", method="html").decode("utf-8").replace("ns1:",""))
        return (
            ET.tostring(node, encoding="utf8", method="html")
            .decode("utf-8")
            .replace("ns1:", "")
        )

    def get_img_bytestr(self, imgid):
        imgid = imgid.replace("#", "")
        img = self.root.find("*[@id='{}']".format(imgid))
        imgtype = img.get("content-type").split("/")[1]
        return imgid + "." + imgtype, base64.b64decode(img.text)

    def cleanup(self):
        return


#:class Pdf(Epub):


class HTMLtoLines(HTMLParser):
    para = {"p", "div"}
    inde = {"q", "dt", "dd", "blockquote"}
    pref = {"pre"}
    bull = {"li"}
    hide = {"script", "style", "head"}
    ital = {"i", "em"}
    bold = {"b"}
    # hide = {"script", "style", "head", ", "sub}

    def __init__(self, sects={""}):
        HTMLParser.__init__(self)
        self.text = [""]
        self.imgs = []
        self.ishead = False
        self.isinde = False
        self.isbull = False
        self.ispref = False
        self.ishidden = False
        self.idhead = set()
        self.idinde = set()
        self.idbull = set()
        self.idpref = set()
        self.sects = sects
        self.sectsindex = {}
        self.initital = []
        self.initbold = []

    def handle_starttag(self, tag, attrs):
        if re.match("h[1-6]", tag) is not None:
            self.ishead = True
        elif tag in self.inde:
            self.isinde = True
        elif tag in self.pref:
            self.ispref = True
        elif tag in self.bull:
            self.isbull = True
        elif tag in self.hide:
            self.ishidden = True
        elif tag == "sup":
            self.text[-1] += "^{"
        elif tag == "sub":
            self.text[-1] += "_{"
        # NOTE: "img" and "image"
        # In HTML, both are startendtag (no need endtag)
        # but in XHTML both need endtag
        elif tag in {"img", "image"}:
            for i in attrs:
                if (tag == "img" and i[0] == "src") or (
                    tag == "image" and i[0].endswith("href")
                ):
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))
        # formatting
        elif tag in self.ital:
            if len(self.initital) == 0 or len(self.initital[-1]) == 4:
                self.initital.append([len(self.text) - 1, len(self.text[-1])])
        elif tag in self.bold:
            if len(self.initbold) == 0 or len(self.initbold[-1]) == 4:
                self.initbold.append([len(self.text) - 1, len(self.text[-1])])
        if self.sects != {""}:
            for i in attrs:
                if i[0] == "id" and i[1] in self.sects:
                    # self.text[-1] += " (#" + i[1] + ") "
                    # self.sectsindex.append([len(self.text), i[1]])
                    self.sectsindex[len(self.text) - 1] = i[1]

    def handle_startendtag(self, tag, attrs):
        if tag == "br":
            self.text += [""]
        elif tag in {"img", "image"}:
            for i in attrs:
                #  if (tag == "img" and i[0] == "src")\
                #     or (tag == "image" and i[0] == "xlink:href"):
                if (tag == "img" and i[0] == "src") or (
                    tag == "image" and i[0].endswith("href")
                ):
                    self.text.append("[IMG:{}]".format(len(self.imgs)))
                    self.imgs.append(unquote(i[1]))
                    self.text.append("")
        # sometimes attribute "id" is inside "startendtag"
        # especially html from mobi module (kindleunpack fork)
        if self.sects != {""}:
            for i in attrs:
                if i[0] == "id" and i[1] in self.sects:
                    # self.text[-1] += " (#" + i[1] + ") "
                    self.sectsindex[len(self.text) - 1] = i[1]

    def handle_endtag(self, tag):
        if re.match("h[1-6]", tag) is not None:
            self.text.append("")
            self.text.append("")
            self.ishead = False
        elif tag in self.para:
            self.text.append("")
        elif tag in self.hide:
            self.ishidden = False
        elif tag in self.inde:
            if self.text[-1] != "":
                self.text.append("")
            self.isinde = False
        elif tag in self.pref:
            if self.text[-1] != "":
                self.text.append("")
            self.ispref = False
        elif tag in self.bull:
            if self.text[-1] != "":
                self.text.append("")
            self.isbull = False
        elif tag in {"sub", "sup"}:
            self.text[-1] += "}"
        elif tag in {"img", "image"}:
            self.text.append("")
        # formatting
        elif tag in self.ital:
            if len(self.initital[-1]) == 2:
                self.initital[-1] += [len(self.text) - 1, len(self.text[-1])]
            elif len(self.initital[-1]) == 4:
                self.initital[-1][2:4] = [len(self.text) - 1, len(self.text[-1])]
        elif tag in self.bold:
            if len(self.initbold[-1]) == 2:
                self.initbold[-1] += [len(self.text) - 1, len(self.text[-1])]
            elif len(self.initbold[-1]) == 4:
                self.initbold[-1][2:4] = [len(self.text) - 1, len(self.text[-1])]

    def handle_data(self, raw):
        if raw and not self.ishidden:
            if self.text[-1] == "":
                tmp = raw.lstrip()
            else:
                tmp = raw
            if self.ispref:
                line = unescape(tmp)
            else:
                line = unescape(re.sub(r"\s+", " ", tmp))
            self.text[-1] += line
            if self.ishead:
                self.idhead.add(len(self.text) - 1)
            elif self.isbull:
                self.idbull.add(len(self.text) - 1)
            elif self.isinde:
                self.idinde.add(len(self.text) - 1)
            elif self.ispref:
                self.idpref.add(len(self.text) - 1)

    def get_lines(self, width=0):
        text, sect = [], {}
        formatting = {"italic": [], "bold": []}
        tmpital = []
        for i in self.initital:
            # handle uneven markup
            # like <i> but no </i>
            if len(i) == 4:
                if i[0] == i[2]:
                    tmpital.append([i[0], i[1], i[3] - i[1]])
                elif i[0] == i[2] - 1:
                    tmpital.append([i[0], i[1], len(self.text[i[0]]) - i[1]])
                    tmpital.append([i[2], 0, i[3]])
                elif i[2] - i[0] > 1:
                    tmpital.append([i[0], i[1], len(self.text[i[0]]) - i[1]])
                    for j in range(i[0] + 1, i[2]):
                        tmpital.append([j, 0, len(self.text[j])])
                    tmpital.append([i[2], 0, i[3]])
        tmpbold = []
        for i in self.initbold:
            if len(i) == 4:
                if i[0] == i[2]:
                    tmpbold.append([i[0], i[1], i[3] - i[1]])
                elif i[0] == i[2] - 1:
                    tmpbold.append([i[0], i[1], len(self.text[i[0]]) - i[1]])
                    tmpbold.append([i[2], 0, i[3]])
                elif i[2] - i[0] > 1:
                    tmpbold.append([i[0], i[1], len(self.text[i[0]]) - i[1]])
                    for j in range(i[0] + 1, i[2]):
                        tmpbold.append([j, 0, len(self.text[j])])
                    tmpbold.append([i[2], 0, i[3]])

        if width == 0:
            return self.text
        for n, i in enumerate(self.text):
            startline = len(text)
            # findsect = re.search(r"(?<= \(#).*?(?=\) )", i)
            # if findsect is not None and findsect.group() in self.sects:
            # i = i.replace(" (#" + findsect.group() + ") ", "")
            # # i = i.replace(" (#" + findsect.group() + ") ", " "*(5+len(findsect.group())))
            # sect[findsect.group()] = len(text)
            if n in self.sectsindex.keys():
                sect[self.sectsindex[n]] = len(text)
            if n in self.idhead:
                text += [i.rjust(width // 2 + len(i) // 2)] + [""]
                formatting["bold"] += [
                    [j, 0, len(text[j])] for j in range(startline, len(text))
                ]
            elif n in self.idinde:
                text += ["   " + j for j in textwrap.wrap(i, width - 3)] + [""]
            elif n in self.idbull:
                tmp = textwrap.wrap(i, width - 3)
                text += [" - " + j if j == tmp[0] else "   " + j for j in tmp] + [""]
            elif n in self.idpref:
                tmp = i.splitlines()
                wraptmp = []
                for line in tmp:
                    wraptmp += [j for j in textwrap.wrap(line, width - 6)]
                text += ["   " + j for j in wraptmp] + [""]
            else:
                text += textwrap.wrap(i, width) + [""]

            # TODO: inline formats for indents
            endline = len(text)  # -1
            tmp_filtered = [j for j in tmpital if j[0] == n]
            for j in tmp_filtered:
                tmp_count = 0
                # for k in text[startline:endline]:
                for k in range(startline, endline):
                    if n in self.idbull | self.idinde:
                        if tmp_count <= j[1]:
                            tmp_start = [k, j[1] - tmp_count + 3]
                        if tmp_count <= j[1] + j[2]:
                            tmp_end = [k, j[1] + j[2] - tmp_count + 3]
                        tmp_count += len(text[k]) - 2
                    else:
                        if tmp_count <= j[1]:
                            tmp_start = [k, j[1] - tmp_count]
                        if tmp_count <= j[1] + j[2]:
                            tmp_end = [k, j[1] + j[2] - tmp_count]
                        tmp_count += len(text[k]) + 1
                if tmp_start[0] == tmp_end[0]:
                    formatting["italic"].append(tmp_start + [tmp_end[1] - tmp_start[1]])
                elif tmp_start[0] == tmp_end[0] - 1:
                    formatting["italic"].append(
                        tmp_start + [len(text[tmp_start[0]]) - tmp_start[1] + 1]
                    )
                    formatting["italic"].append([tmp_end[0], 0, tmp_end[1]])
                # elif tmp_start[0]-tmp_end[1] > 1:
                else:
                    formatting["italic"].append(
                        tmp_start + [len(text[tmp_start[0]]) - tmp_start[1] + 1]
                    )
                    for l in range(tmp_start[0] + 1, tmp_end[0]):
                        formatting["italic"].append([l, 0, len(text[l])])
                    formatting["italic"].append([tmp_end[0], 0, tmp_end[1]])
            tmp_filtered = [j for j in tmpbold if j[0] == n]
            for j in tmp_filtered:
                tmp_count = 0
                # for k in text[startline:endline]:
                for k in range(startline, endline):
                    if n in self.idbull | self.idinde:
                        if tmp_count <= j[1]:
                            tmp_start = [k, j[1] - tmp_count + 3]
                        if tmp_count <= j[1] + j[2]:
                            tmp_end = [k, j[1] + j[2] - tmp_count + 3]
                        tmp_count += len(text[k]) - 2
                    else:
                        if tmp_count <= j[1]:
                            tmp_start = [k, j[1] - tmp_count]
                        if tmp_count <= j[1] + j[2]:
                            tmp_end = [k, j[1] + j[2] - tmp_count]
                        tmp_count += len(text[k]) + 1
                if tmp_start[0] == tmp_end[0]:
                    formatting["bold"].append(tmp_start + [tmp_end[1] - tmp_start[1]])
                elif tmp_start[0] == tmp_end[0] - 1:
                    formatting["bold"].append(
                        tmp_start + [len(text[tmp_start[0]]) - tmp_start[1] + 1]
                    )
                    formatting["bold"].append([tmp_end[0], 0, tmp_end[1]])
                # elif tmp_start[0]-tmp_end[1] > 1:
                else:
                    formatting["bold"].append(
                        tmp_start + [len(text[tmp_start[0]]) - tmp_start[1] + 1]
                    )
                    for l in range(tmp_start[0] + 1, tmp_end[0]):
                        formatting["bold"].append([l, 0, len(text[l])])
                    formatting["bold"].append([tmp_end[0], 0, tmp_end[1]])

        return text, self.imgs, sect, formatting


def det_ebook_cls(file):
    filext = os.path.splitext(file)[1]
    if filext == ".epub":
        return Epub(file).initialize()
    elif filext == ".fb2":
        return FictionBook(file).initialize()
    elif filext == ".mobi":
        return Mobi(file).initialize()
    elif filext == ".azw3":
        return Azw3(file).initialize()
    else:
        sys.exit("ERROR: Format not supported. (Supported: epub, fb2, mobi, azw3)")
