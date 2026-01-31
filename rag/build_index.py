from pathlib import Path
import json, re

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIRS = [ROOT/'docs', ROOT/'research']
INDEX_PATH = ROOT/'rag'/'index.jsonl'

def chunk(text, size=900, overlap=150):
    out, i = [], 0
    while i < len(text):
        out.append(text[i:i+size])
        i += size - overlap
    return out

def clean(s): return re.sub(r'\s+', ' ', s).strip()

def main():
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with INDEX_PATH.open('w', encoding='utf-8') as w:
        for d in CORPUS_DIRS:
            if not d.exists(): continue
            for p in d.rglob('*'):
                if p.suffix.lower() not in ('.txt', '.md'): continue
                txt = p.read_text('utf-8', errors='ignore')
                for i, piece in enumerate(chunk(txt)):
                    rec = {"path": str(p), "chunk_id": i, "text": clean(piece)}
                    w.write(json.dumps(rec) + '\n')
                    n += 1
    print(f'Indexed {n} chunks -> {INDEX_PATH}')

if __name__ == '__main__':
    main()
