#!/usr/bin/env python3
"""화면 데이터 JS 에서 사용자에게 보이는 '실행 상태·대화 문구' 값 앞에 /*[script]*/ 표시를 붙인다(멱등).
나중에 문구를 직접 고칠 때 [script] 로 검색하면 고칠 자리가 모두 나온다. 화면에는 보이지 않는다(JS 주석)."""
import re, sys
KEYS = ("researchSub", "wsSub", "conceptSub", "designNote", "lead", "label", "headline", "body", "effect", "limits")
PAT = re.compile(r'("(?:%s)": )(?!/\*\[script\]\*/)' % "|".join(KEYS))
HUMAN = re.compile(r'("human": )(?!/\*\[script\]\*/)')


def mark(text: str) -> str:
    return HUMAN.sub(r"\1/*[script]*/ ", PAT.sub(r"\1/*[script]*/ ", text))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = open(p, encoding="utf-8").read()
        open(p, "w", encoding="utf-8").write(mark(s))
        print("marked", p, s.count("/*[script]*/"), "→", mark(s).count("/*[script]*/"))
