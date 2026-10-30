import re
from pathlib import Path

class PolicyRetriever:
    """Small keyword retriever: splits policy into named chunks and returns only relevant matches."""
    def __init__(self, path):
        raw=Path(path).read_text(encoding="utf-8")
        self.chunks=[]
        current_id=None; current=[]
        for line in raw.splitlines():
            if line.startswith("## "):
                if current_id: self.chunks.append({"id":current_id,"text":" ".join(current)})
                current_id=line[3:].strip().replace(" ","_").lower(); current=[]
            elif line.strip():
                current.append(line.strip())
        if current_id: self.chunks.append({"id":current_id,"text":" ".join(current)})

    def retrieve(self, query, limit=2):
        stop={"what","is","my","the","a","an","can","i","to","do","for","on","in","of","and","please","how"}
        terms={x for x in re.findall(r"[a-z0-9]+",query.lower()) if len(x)>2 and x not in stop}
        scored=[]
        for c in self.chunks:
            words=set(re.findall(r"[a-z0-9]+",c["text"].lower()))
            score=len(terms & words)
            if score: scored.append((score,c))
        scored.sort(key=lambda x:x[0],reverse=True)
        return [c for _,c in scored[:limit]]
