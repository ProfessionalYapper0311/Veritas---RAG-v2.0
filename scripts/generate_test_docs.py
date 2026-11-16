"""Generate realistic test PDFs for testing Veritas RAG document ingestion and retrieval."""
import os
from pathlib import Path
from fpdf import FPDF
from pypdf import PdfReader

OUT_DIR = Path(__file__).resolve().parent.parent / "test_docs"
OUT_DIR.mkdir(exist_ok=True)


class StyledPDF(FPDF):
    def __init__(self, title_text: str):
        super().__init__()
        self.doc_title = title_text
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 110, 125)
        self.cell(0, 8, self.doc_title.upper(), align="L")
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, "VERITAS ENTERPRISE KNOWLEDGE BASE", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(220, 225, 235)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(220, 225, 235)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 130, 145)
        self.cell(0, 8, f"Page {self.page_no()} of {{nb}} - Internal and Confidential", align="C")

    def add_chapter_title(self, num: int, label: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(26, 35, 50)
        self.cell(0, 8, f"{num}. {label}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def add_section(self, label: str):
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(42, 143, 130)  # Verdigris teal
        self.cell(0, 6, label, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def add_paragraph(self, text: str):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(50, 60, 75)
        self.multi_cell(0, 5, text)
        self.ln(3)


def generate_hr_policy_pdf():
    pdf = StyledPDF("Acme Global - Employee Handbook & Leave Policy 2026")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Cover Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 50)
    pdf.cell(0, 10, "Acme Global Technologies Inc.", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 110, 125)
    pdf.cell(0, 6, "Employee Handbook & Workplace Benefits Policy (Version 4.2 - 2026)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Section 1
    pdf.add_chapter_title(1, "Working Hours and Remote Work Arrangements")
    pdf.add_section("1.1 Standard Core Hours")
    pdf.add_paragraph(
        "Standard full-time working hours for Acme Global employees are 40 hours per calendar week, "
        "typically structured from Monday through Friday. Core operating hours are 10:00 AM to 4:00 PM "
        "local workspace time, during which employees are expected to be available for collaborative meetings, "
        "client check-ins, and scheduled project synchronizations."
    )
    pdf.add_section("1.2 Hybrid and Remote Work Policy")
    pdf.add_paragraph(
        "Acme operates a flexible hybrid workplace framework. Engineering, Product, and Support staff may work "
        "remotely up to three (3) days per week with manager approval. Fully remote arrangements require explicit "
        "written approval from the department VP and People Operations. Remote staff are provided an initial "
        "$800 home-office ergonomic stipend upon hire, followed by a $50 monthly internet allowance."
    )

    # Section 2
    pdf.add_chapter_title(2, "Annual Leave and Paid Time Off (PTO)")
    pdf.add_section("2.1 Annual Paid Vacation Allotment")
    pdf.add_paragraph(
        "All permanent full-time employees receive twenty-four (24) working days of paid annual vacation leave per year, "
        "accruing on the first day of each month at a rate of 2.0 days per calendar month. Up to five (5) unused vacation "
        "days may be carried over into the subsequent fiscal year, but must be taken before March 31st of that year."
    )
    pdf.add_section("2.2 Sick and Wellness Leave")
    pdf.add_paragraph(
        "Employees receive twelve (12) days of dedicated paid sick and mental wellness leave annually. For absences "
        "exceeding three (3) consecutive business days, a certified medical practitioner note must be submitted to "
        "People Operations via the BambooHR portal."
    )
    pdf.add_section("2.3 Parental and Caregiver Leave")
    pdf.add_paragraph(
        "Primary caregivers (birth, adoption, or surrogacy) are eligible for eighteen (18) weeks of fully paid parental leave. "
        "Secondary caregivers receive eight (8) weeks of fully paid leave. Both benefits may be taken consecutively or in two "
        "separate blocks within the first twelve months following birth or placement."
    )

    pdf.add_page()

    # Section 3
    pdf.add_chapter_title(3, "Travel and Business Expense Reimbursements")
    pdf.add_section("3.1 Daily Per Diem Rates")
    pdf.add_paragraph(
        "Domestic business travel per diem is capped at $85 per day ($20 breakfast, $25 lunch, $40 dinner). "
        "For international assignments in Tier-1 metropolitan areas (London, Tokyo, Zurich, Singapore, New York), "
        "the maximum daily per diem allowance is adjusted to $130 per day."
    )
    pdf.add_section("3.2 Flight and Hotel Booking Guidelines")
    pdf.add_paragraph(
        "All corporate travel must be booked via Navan or the company travel desk at least fourteen (14) days in advance "
        "for domestic trips and twenty-one (21) days for international flights. Flights under six (6) hours must be booked in "
        "Economy or Economy Plus. For continuous flight segments exceeding eight (8) hours, Business Class is permitted with "
        "prior Director sign-off."
    )

    # Section 4
    pdf.add_chapter_title(4, "Professional Development and Tuition Sponsorship")
    pdf.add_section("4.1 Annual Learning Stipend")
    pdf.add_paragraph(
        "Every full-time team member is eligible for an annual professional development budget of $1,800 USD. "
        "This budget can be allocated towards industry conference registrations, professional certifications (e.g. AWS, "
        "Google Cloud, PMP, CISSP), accredited online coursework, or relevant technical literature."
    )

    dest = OUT_DIR / "Acme_Employee_Handbook_2026.pdf"
    pdf.output(str(dest))
    print(f"Generated: {dest}")


def generate_security_policy_pdf():
    pdf = StyledPDF("Veritas - Information Security & Data Governance Policy")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Cover Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 35, 50)
    pdf.cell(0, 10, "Veritas AI Technologies", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(100, 110, 125)
    pdf.cell(0, 6, "Information Security Management System (ISMS-SEC-2026-V1)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Section 1
    pdf.add_chapter_title(1, "Access Control and Identity Management")
    pdf.add_section("1.1 Authentication & Password Requirements")
    pdf.add_paragraph(
        "All system access requires mandatory Multi-Factor Authentication (MFA) using hardware security keys (YubiKey) "
        "or time-based one-time password (TOTP) authenticator applications. SMS-based 2FA is strictly prohibited for production "
        "systems. Passwords must be at least sixteen (16) characters in length, containing upper and lowercase letters, numeric "
        "digits, and at least two symbols. Passwords expire every ninety (90) days for privileged accounts."
    )
    pdf.add_section("1.2 Principle of Least Privilege (PoLP)")
    pdf.add_paragraph(
        "User permissions and database roles are provisioned strictly on a need-to-know basis. Production database access "
        "is restricted to automated deployment pipelines; direct engineer shell access requires temporary JIT (Just-In-Time) "
        "break-glass authorization approved by two (2) senior infrastructure leads, logged with maximum 4-hour automatic expiration."
    )

    # Section 2
    pdf.add_chapter_title(2, "Data Classification and Retention Tiers")
    pdf.add_section("2.1 Classification Scheme")
    pdf.add_paragraph(
        "All documents and databases must be categorized into one of four sensitivity classifications:\n"
        "- Tier 1: Public  -  Marketing materials, published documentation, public blog posts.\n"
        "- Tier 2: Internal  -  Architecture diagrams, company wikis, sprint backlogs.\n"
        "- Tier 3: Confidential  -  Customer tenant data, PII, commercial contracts, financial audits.\n"
        "- Tier 4: Restricted  -  Cryptographic keys, API secrets, unreleased patents, personnel disciplinary records."
    )
    pdf.add_section("2.2 Encryption Standards")
    pdf.add_paragraph(
        "Data at rest must be encrypted using AES-256 with AWS KMS customer-managed keys (CMK) with annual automatic rotation. "
        "Data in transit must strictly enforce TLS 1.3 with cipher suites supporting Perfect Forward Secrecy (PFS). Deprecated TLS "
        "1.0, 1.1, and 1.2 are blocked at all ingress load balancers."
    )

    pdf.add_page()

    # Section 3
    pdf.add_chapter_title(3, "Incident Response and Breach Notification Protocol")
    pdf.add_section("3.1 Severity Levels and Response Windows")
    pdf.add_paragraph(
        "Security incidents are classified into three severity levels:\n"
        "- Severity 1 (Critical): Active unauthorized data exfiltration, ransomware, or compromise of root infrastructure. "
        "Mandatory response time: fifteen (15) minutes. 24/7 incident commander paging.\n"
        "- Severity 2 (Major): Unauthorized privilege escalation or misconfigured S3 bucket with potential exposure. "
        "Mandatory response time: one (1) hour.\n"
        "- Severity 3 (Moderate): Phishing attempt, suspicious login from unverified IP, or single endpoint malware isolation. "
        "Response time: four (4) business hours."
    )
    pdf.add_section("3.2 External Customer & Regulatory Notification")
    pdf.add_paragraph(
        "Under Veritas SOC2 and GDPR compliance commitments, any confirmed breach of customer confidential data must be "
        "communicated in writing to affected tenant administrators within seventy-two (72) hours of incident confirmation, "
        "coordinated by General Counsel and the Chief Information Security Officer (CISO)."
    )

    # Section 4
    pdf.add_chapter_title(4, "Device Security and Bring Your Own Device (BYOD)")
    pdf.add_section("4.1 Corporate Laptop Hardening")
    pdf.add_paragraph(
        "All corporate laptops (macOS and Windows) must have full-disk encryption enabled (FileVault 2 / BitLocker with TPM 2.0). "
        "CrowdStrike Falcon EDR and Jamf/Intune MDM profiles must remain installed and active at all times. Employees may not "
        "disable security agents, sideload unapproved kernel extensions, or share devices with family members."
    )

    dest = OUT_DIR / "Veritas_Security_and_Compliance_Policy_2026.pdf"
    pdf.output(str(dest))
    print(f"Generated: {dest}")


def verify_pdfs():
    print("\n--- Verifying Generated PDFs with pypdf ---")
    for pdf_file in OUT_DIR.glob("*.pdf"):
        reader = PdfReader(str(pdf_file))
        total_pages = len(reader.pages)
        total_chars = sum(len(p.extract_text() or "") for p in reader.pages)
        print(f"Verified: {pdf_file.name}")
        print(f"  Pages: {total_pages}, Extracted characters: {total_chars}")
        assert total_pages >= 2, "PDF should have at least 2 pages"
        assert total_chars > 1000, "PDF should have extracted text"
    print("All PDFs verified valid for Veritas ingestion!\n")


if __name__ == "__main__":
    generate_hr_policy_pdf()
    generate_security_policy_pdf()
    verify_pdfs()
