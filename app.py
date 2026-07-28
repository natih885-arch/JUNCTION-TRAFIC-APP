import os
import streamlit as st
from fpdf import FPDF
from PIL import Image

# הגדרת תצורת עמוד ב-Streamlit
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

# ==============================================================================
# מתג אבטחה ואישור הפעלה (Kill-Switch)
APP_ACTIVE = True
# ==============================================================================

if not APP_ACTIVE:
    st.error("⛔ המערכת אינה פעילה כעת. אנא פנה למפתח המערכת לקבלת גישה.")
    st.stop()

# פונקציה לניקוי תווים שאינם ב-latin-1 כדי למנוע קריסת קידוד ב-FPDF
def clean_text(text):
    if not text:
        return ""
    # המרה בטוחה לפורמט שנתמך ע"י פונטים סטנדרטיים ב-PDF
    return str(text).encode('latin-1', 'replace').decode('latin-1')

# --- מחלקת יצירת PDF הנדסי ומעוצב ---
class TrafficInspectionPDF(FPDF):
    def header(self):
        # פס כותרת כחול כהה
        self.set_fill_color(24, 43, 73)
        self.rect(0, 0, 210, 28, 'F')
        
        # שם החברה בראש הדו"ח
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, "D.D. ENGINEERS LTD", ln=True, align="C")
        
        # כותרת הדו"ח
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 6, "TRAFFIC CONTROL INSPECTION REPORT", ln=True, align="C")
        
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 5, "Official Field Traffic Management Record", ln=True, align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(128, 128, 128)
        copyright_text = "Page %d | (c) All Rights Reserved to Netanel Oz Harary. Unauthorized use or distribution is strictly prohibited." % self.page_no()
        self.cell(0, 10, copyright_text, align="C")

def generate_pdf(site_title, junction_name, inspector, license_no, date_str, work_type, notes, photo_sections):
    pdf = TrafficInspectionPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    pdf.set_text_color(40, 40, 40)
    
    # 1. כותרת הפרויקט
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Project Site: {clean_text(site_title)}", ln=True)
    pdf.set_draw_color(24, 43, 73)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # 2. טבלת נתונים מרכזית
    pdf.set_fill_color(240, 244, 248)
    pdf.set_font("Helvetica", "B", 10)
    
    col_w = 95
    pdf.cell(col_w, 7, f" Junction / Location: {clean_text(junction_name)}", border=1, fill=True)
    
    inspector_info = f" Inspector: {clean_text(inspector)}"
    if license_no.strip():
        inspector_info += f" (Lic. #{clean_text(license_no)})"
    pdf.cell(col_w, 7, inspector_info, border=1, fill=True, ln=True)
    
    pdf.cell(col_w, 7, f" Date: {clean_text(date_str)}", border=1, fill=True)
    pdf.cell(col_w, 7, f" Activity Type: {clean_text(work_type)}", border=1, fill=True, ln=True)
    
    pdf.ln(4)
    
    # 3. הערות מפקח
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "Traffic Field Observations & Directives:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    
    notes_text = clean_text(notes) if notes.strip() else "No additional engineering notes recorded."
    pdf.multi_cell(190, 6, notes_text, border=1)
    pdf.ln(8)
    
    # 4. גלריית תמונות
    def add_photos(title_en, files, prefix):
        if not files:
            return
            
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(220, 228, 238)
        pdf.cell(0, 7, f" {title_en}", ln=True, fill=True)
        pdf.ln(4)
        
        col = 0
        y_start = pdf.get_y()
        
        for i, f in enumerate(files):
            if pdf.get_y() > 230:
                pdf.add_page()
                y_start = pdf.get_y()
                col = 0
                
            img = Image.open(f)
            temp = f"temp_{prefix}_{i}.jpg"
            img.convert("RGB").save(temp)
            
            x_pos = 10 if col == 0 else 105
            curr_y = pdf.get_y() if col == 0 else y_start
            
            pdf.image(temp, x=x_pos, y=curr_y, w=85, h=60)
            pdf.rect(x_pos, curr_y, 85, 60)
            
            pdf.set_xy(x_pos, curr_y + 61)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(85, 4, f"Photo #{i+1} - {prefix.upper()}", align="C")
            
            if col == 1:
                pdf.set_y(curr_y + 68)
                col = 0
            else:
                y_start = curr_y
                col = 1
                
            if os.path.exists(temp):
                os.remove(temp)
                
        if col == 1:
            pdf.set_y(y_start + 68)
        pdf.ln(4)

    for section in photo_sections:
        add_photos(section["title_en"], section["files"], section["prefix"])
    
    # 5. חתימת מפקח
    if pdf.get_y() > 230:
        pdf.add_page()
        
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    
    sign_text = f"Inspector: {clean_text(inspector)}"
    if license_no.strip():
        sign_text += f" | License No: {clean_text(license_no)}"
        
    pdf.cell(0, 6, sign_text, ln=True)
    pdf.cell(120, 6, "Signature: _______________________", ln=False)
    pdf.cell(70, 6, f"Date: {clean_text(date_str)}", ln=True)
    
    return bytes(pdf.output())


# --- ממשק המשתמש (Streamlit UI) ---
st.title("🚦 ד.ד מהנדסים בע''מ")
st.subheader("מערכת הפקת דו\"ח מפקח הסדר תנועה")
st.write("מלא את הפרטים והעלה תמונות להפקת דו\"ח PDF מקצועי מהשטח.")

st.divider()

st.subheader("📋 פרטי האתר והמפקח")

col1, col2 = st.columns(2)
with col1:
    site_name = st.text_input("שם האתר / פרויקט (אנגלית/מספרים לדו\"ח)", "Project Center 1")
    junction_name = st.text_input("שם הצומת / מיקום (אנגלית/מספרים לדו\"ח)", "Junction Herzl-Jabotinsky")
    inspector_name = st.text_input("שם המפקח", "Netanel Oz")
    license_no = st.text_input("מספר רישיון / מ.פ (אופציונלי)", "")

with col2:
    date_val = st.date_input("תאריך הבדיקה")
    work_type = st.selectbox("סוג הפעילות / העבודה", [
        "Temporary Traffic Arrangement",
        "Controller Replacement",
        "Detector Loop Slitting",
        "Camera Installation",
        "Lane Shift Approval",
        "Signage Inspection",
        "Traffic Light Maintenance",
        "Periodic Inspection",
        "Other"
    ])

notes = st.text_area("הערות מפקח, מפגעים ודגשים (באנגלית/מספרים)", placeholder="Enter engineering notes here...")

st.divider()

st.subheader("📸 העלאת תמונות (העלה רק לקטגוריות הרלוונטיות)")

col_a, col_b = st.columns(2)

with col_a:
    before_files = st.file_uploader("תמונות - לפני הסדר", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="before")
    mechanism_files = st.file_uploader("תמונות - החלפת מנגנון", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="mechanism")
    cameras_files = st.file_uploader("תמונות - התקנת מצלמות", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="cameras")

with col_b:
    after_files = st.file_uploader("תמונות - אחרי הסדר", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="after")
    detectors_files = st.file_uploader("תמונות - חריצת גלאים", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="detectors")
    plan_files = st.file_uploader("צילום תוכנית / שרטוט", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="plan")

misc_files = st.file_uploader("תמונות - שונות / נספחים", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="misc")

st.divider()

if st.button("🚀 הפק דו\"ח מפקח PDF", type="primary", use_container_width=True):
    if not site_name or not junction_name or not inspector_name:
        st.error("⚠️ אנא מלא את שם האתר, שם הצומת ושם המפקח.")
    else:
        photo_sections = [
            {"title_en": "BEFORE WORKS (Initial Field Condition)", "files": before_files, "prefix": "before"},
            {"title_en": "AFTER WORKS (Final Traffic Arrangement)", "files": after_files, "prefix": "after"},
            {"title_en": "CONTROLLER REPLACEMENT (Mechanism)", "files": mechanism_files, "prefix": "mechanism"},
            {"title_en": "DETECTOR LOOP SLITTING", "files": detectors_files, "prefix": "detectors"},
            {"title_en": "TRAFFIC CAMERA INSTALLATION", "files": cameras_files, "prefix": "cameras"},
            {"title_en": "APPROVED TRAFFIC PLAN / DRAWING", "files": plan_files, "prefix": "plan"},
            {"title_en": "MISCELLANEOUS / ATTACHMENTS", "files": misc_files, "prefix": "misc"}
        ]
        
        with st.spinner("מפיק דו\"ח מפקח מעוצב..."):
            pdf_bytes = generate_pdf(
                site_title=site_name,
                junction_name=junction_name,
                inspector=inspector_name,
                license_no=license_no,
                date_str=str(date_val),
                work_type=work_type,
                notes=notes,
                photo_sections=photo_sections
            )
        
        st.success("✅ הדו\"ח הופק בהצלחה!")
        
        st.download_button(
            label="⬇️ הורד דו\"ח PDF למכשיר",
            data=pdf_bytes,
            file_name=f"DD_Engineers_Report_{date_val}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

st.caption("© כל הזכויות שמורות לנתנאל עוז הררי (Netanel Oz Harary). אין לעשות שימוש או להפיץ ללא אישור בכתב.")
