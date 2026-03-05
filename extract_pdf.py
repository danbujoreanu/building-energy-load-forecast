import pdfplumber
import os

pdf_path = "/Users/danalexandrubujoreanu/NCI/0. MSCTOPUP/Thesis WIP 2026/Aditional resources/Activation types for DL models.pdf"

if os.path.exists(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        with open("activation_types_text.txt", "w") as f:
            f.write(text)
    print("PDF extraction complete: activation_types_text.txt")
else:
    print(f"Error: PDF not found at {pdf_path}")
