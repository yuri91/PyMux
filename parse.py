import re
from enum import Enum

layout = "136x29,0,0{68x29,0,0,18,67x29,69,0[67x14,69,0,23,67x14,69,15{33x14,69,15,24,33x14,103,15[33x7,103,15,25,33x6,103,23,26]}]}"

class LAYOUT_TYPE(Enum):
    NONE = 0
    TOP_BOTTOM = 1
    LEFT_RIGHT = 2

class Layout:
    def __init__(self, parent, sx, sy, xoff, yoff):
        self.parent = parent

        self.sx=sx
        self.sy=sy
        self.xoff=xoff
        self.yoff=yoff

        self.type = LAYOUT_TYPE.NONE
        self.id = ""
        self.children = []

    def __repr__(self):
        if self.type == LAYOUT_TYPE.NONE:
            last = ","+self.id
        else:
            brackets = "[]" if self.type == LAYOUT_TYPE.TOP_BOTTOM else "{}"
            last = brackets[0]
            first = True
            for c in self.children:
                if not first:
                    last += ","
                first = False
                last += repr(c)
            last += brackets[1]
        return "{}x{},{},{}{}".format(self.sx,self.sy,self.xoff,self.yoff, last)

def parse_layout(parent, layout, cur):
    r = re.search("^(\d+)x(\d+),(\d+),(\d+)", layout[cur:])
    if not r:
        return None, cur
    cur += len(r.group(0))
    l = Layout(parent, *r.groups())
    if layout[cur] == ",":
        r = re.search("^,(\d+)",layout[cur:])
        if r == None:
            return None, cur
        cur += len(r.group(0))
        l.id = r.group(1)
    if cur == len(layout) or layout[cur] in ',}]': return (l,cur)
    if layout[cur] == "{":
        l.type = LAYOUT_TYPE.LEFT_RIGHT
    elif layout[cur] == "[":
        l.type = LAYOUT_TYPE.TOP_BOTTOM
    else:
        return None, cur
    while True:
        cur += 1
        child,cur = parse_layout(l, layout, cur)
        if child == None:
            return None, cur
        l.children.append(child)
        if layout[cur] != ",": break

    if l.type == LAYOUT_TYPE.LEFT_RIGHT:
        if layout[cur] != "}": return None, cur
    elif l.type == LAYOUT_TYPE.TOP_BOTTOM:
        if layout[cur] != "]": return None, cur

    cur +=1

    return (l,cur)

if __name__ == "__main__":
    l,cur = parse_layout(None, layout, 0)
    print(l)
    print(layout)
