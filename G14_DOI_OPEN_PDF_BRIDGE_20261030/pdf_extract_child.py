#!/usr/bin/env python3
"""Isolated bounded text extraction; no network, journal, or scientific claims."""
import io, json, sys
from pypdf import PdfReader


def main():
    page = int(sys.argv[1])
    raw = sys.stdin.buffer.read(8_000_001)
    if len(raw) > 8_000_000 or not raw.startswith(b'%PDF-'):
        raise ValueError('NOT_A_BOUNDED_PDF')
    pdf = PdfReader(io.BytesIO(raw), strict=False)
    if pdf.is_encrypted:
        raise ValueError('ENCRYPTED_PDF')
    count = len(pdf.pages)
    if not 1 <= count <= 250 or not 1 <= page <= count:
        raise ValueError('PAGE_RANGE_OR_DOCUMENT_TOO_LARGE')
    first = '\n'.join((pdf.pages[i].extract_text() or '')[:12000]
                      for i in range(min(2, count)))
    selected = pdf.pages[page - 1].extract_text() or ''
    print(json.dumps({'page_count':count, 'first_text':first[:16000],
                      'page_text':selected[:22000]}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(json.dumps({'error':type(e).__name__+':'+str(e)[:150]}))
        sys.exit(3)
