import fitz
from services.analyzer_service import analyze_uploaded_document

def run_tests():
    # 1. Invoice PDF
    inv = fitz.open()
    p = inv.new_page()
    p.insert_text((50, 50), """TAX INVOICE / BILL OF SUPPLY
Invoice Number: INV-2024-9981
Bill To: ABC Enterprises Ltd
GSTIN: 27AAAAA0000A1Z5
Item: Cloud Hosting Server Units
Unit Price: $450.00
Quantity: 4
Subtotal: $1,800.00
Total Amount Due: $2,124.00
Payment Terms: Net 30 days""")
    inv_bytes = inv.tobytes()
    inv.close()

    # 2. Resume PDF
    res_doc = fitz.open()
    p = res_doc.new_page()
    p.insert_text((50, 50), """CURRICULUM VITAE
Jane Doe - Senior Full Stack Engineer
Professional Summary: 8 years building scalable distributed microservices.
Work Experience:
Lead Developer at Tech Corp (2021-2024)
Technical Skills: React, Python, PostgreSQL, Docker, Kubernetes.
References available upon request.""")
    res_bytes = res_doc.tobytes()
    res_doc.close()

    # 3. Real Degree PDF
    deg = fitz.open()
    p = deg.new_page()
    p.insert_text((50, 50), """SISTER NIVEDITA UNIVERSITY
BACHELOR OF TECHNOLOGY (COMPUTER SCIENCE & ENGINEERING)

This is to certify that
UJJWAL KUMAR
Roll Number: 2411200010023
having fulfilled the academic requirements has been admitted to the Degree of
Bachelor of Technology with First Class Distinction.

Date of Issue: 01-12-2025
Registrar | Controller of Examinations""")
    deg_bytes = deg.tobytes()
    deg.close()

    # 4. Real Marksheet PDF
    mark = fitz.open()
    p = mark.new_page()
    p.insert_text((50, 50), """DELHI UNIVERSITY
STATEMENT OF MARKS
SEMESTER VIII EXAMINATION 2024

Candidate Name: ROHIT VERMA
Roll No: 2004510098
Course: Bachelor of Science (Computer Science)

Total Marks: 260 / 300
CGPA: 8.75 / 10.0
Division: First Division with Distinction

Date: 15-06-2024
Controller of Examinations""")
    mark_bytes = mark.tobytes()
    mark.close()

    # 5. Fake Degree PDF
    fake = fitz.open()
    p = fake.new_page()
    p.insert_text((50, 50), """BADAGANVI SARKAR WORLD OPEN UNIVERSITY
DEGREE OF BACHELOR
Candidate Name: John Doe
Roll Number: 000000
Total Marks: 950 / 500
CGPA: 14.5 / 10.0
Year: 2099""")
    fake_bytes = fake.tobytes()
    fake.close()

    docs = [
        ("1. Absurd Invoice PDF", inv_bytes),
        ("2. Absurd Resume PDF", res_bytes),
        ("3. Genuine Degree PDF", deg_bytes),
        ("4. Genuine Marksheet PDF", mark_bytes),
        ("5. Fabricated / Fake Degree PDF", fake_bytes),
    ]

    print("\n" + "="*70)
    print("           TRUEDEGREE PIPELINE TEST RESULTS")
    print("="*70)

    for label, raw_bytes in docs:
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        analysis = analyze_uploaded_document(raw_bytes, text, {"page_count": 1, "producer": "ReportLab"})
        
        print(f"\n[{label}]")
        print(f"  Is Academic?      : {analysis.get('is_academic')}")
        print(f"  Category          : {analysis.get('category')}")
        print(f"  Verdict           : {analysis.get('verdict')}")
        print(f"  Authenticity Score: {analysis.get('authenticity_score')}%")
        print(f"  Message           : {analysis.get('message')}")
        if analysis.get("risk_flags"):
            print(f"  Risk Flags        : {analysis.get('risk_flags')}")

if __name__ == "__main__":
    run_tests()
