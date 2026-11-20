# -*- coding: utf-8 -*-
"""修正文档中的 Chroma 集合名（knowledge_chunks → enterprise_knowledge）。"""
import glob
import os

from docx import Document

OLD = "knowledge_chunks"
NEW = "enterprise_knowledge"

for f in glob.glob(r"D:\课设\智维台\*.docx"):
    if os.path.basename(f).startswith("_srs_backup"):
        continue
    doc = Document(f)
    n = 0
    for p in doc.paragraphs:
        for r in p.runs:
            if OLD in r.text:
                r.text = r.text.replace(OLD, NEW)
                n += 1
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    for r in p.runs:
                        if OLD in r.text:
                            r.text = r.text.replace(OLD, NEW)
                            n += 1
    if n:
        doc.save(f)
        print("%-34s 修正 %d 处" % (os.path.basename(f), n))
    else:
        print("%-34s 无需修改" % os.path.basename(f))
