"""아주 작은 HTML 파서 (외부 라이브러리 없이 표·목록을 읽을 때 사용)"""

from html.parser import HTMLParser

VOID = {"img", "br", "hr", "input", "meta", "link", "source", "col", "area", "base", "wbr"}


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children, self.text = [], []

    def cls(self):
        return (self.attrs.get("class") or "").split()

    def all_text(self):
        out = list(self.text)
        for c in self.children:
            out.append(c.all_text())
        return " ".join(" ".join(out).split())

    def find_all(self, tag=None, cls=None):
        res = []
        for c in self.children:
            if (tag is None or c.tag == tag) and (cls is None or cls in c.cls()):
                res.append(c)
            res.extend(c.find_all(tag, cls))
        return res

    def find(self, tag=None, cls=None):
        r = self.find_all(tag, cls)
        return r[0] if r else None


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root", [])
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if data.strip():
            self.cur.text.append(data)
