import pdfplumber
import os

docs_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(docs_dir, "extracted")
os.makedirs(output_dir, exist_ok=True)

pdfs = [
    "Ley-21663_08-ABR-2024.pdf",
    "Ley-21719_13-DIC-2024.pdf",
    "PR-TI-001- GESTIÓN DE ACCESOS Y ACTIVOS TIL v.1.pdf",
]

for pdf_name in pdfs:
    pdf_path = os.path.join(docs_dir, pdf_name)
    out_name = pdf_name.replace(".pdf", ".txt")
    out_path = os.path.join(output_dir, out_name)
    
    print(f"Extracting: {pdf_name}")
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"\n--- PAGE {i+1} ---\n{page_text}"
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  -> Saved to {out_path} ({len(text)} chars)")

print("\nDone!")
