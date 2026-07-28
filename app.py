import os
import urllib.request
import streamlit as st
from fpdf import FPDF
from PIL import Image

# הגדרת תצורת עמוד ב-Streamlit
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

# הורדת פונקציה לפונט Arial שתומך בעברית
FONT_PATH = "arial.ttf"
if not os.path.exists(FONT_PATH):
    try:
        urllib.request.urlretrieve("https://github.com/matomo-org/matomo/raw/master/plugins/ImageGraph/fonts/arial.ttf", FONT_PATH)
    except Exception:
        pass

# פונקציה להיפוך טקסט בעברית (RTL) עבור FPDF
def fix_hebrew(text):
    if not text:
        return ""
    words = str(text).split(' ')
    fixed_words = []
    for word in words:
        if any("\u0590" <= c <= "\u05fe" for c in word):
            fixed_words.append(word[::-1])
        else:
            fixed_words.append(word)
    return " ".join(reversed(fixed_words))

# --- מחלקת יצירת PDF ---
class TrafficInspectionPDF(FPDF):
    def header(self):
        self.set_fill_color(24, 43, 73)
        self.rect(0, 0, 210, 28, 'F')
        
        if os.path.exists(FONT_PATH):
            self.add_font("FreeArial", "", FONT_PATH)
            self.add_font("FreeArial", "B", FONT_PATH)
            self.set_font("FreeArial", "B", 14)
        else:
            self.set_font("Helvetica", "B", 14)
            
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, fix_hebrew("ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD"), ln=True, align="C")
        
        self.set_font("FreeArial" if os.path.exists(FONT_PATH) else "Helvetica", "B", 12)
        self.cell(0, 6, fix_hebrew("דו\"ח פיקוח ואכיפת הסדרי תנועה"), ln=True, align="C")
        
        self.set_font("FreeArial" if os.path.exists(FONT_PATH) else "Helvetica", "", 8)
        self.cell(0, 5, fix_hebrew("מסמך פיקוח שטח רשמי"), ln=True, align="C")
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        font_name = "FreeArial" if os.path.exists(FONT_PATH) else "Helvetica"
        self.set_font(font_name, "", 7)
        self.set_text_color(128, 128, 128)
        copyright_text = fix_hebrew("כל הזכויות שמורות לנתנאל עוז הררי © | עמוד %d" % self.page_no())
        self.cell(0, 10, copyright_text, align="C")

def generate_pdf(site_title, junction_name, inspector, license_no, date_str, work_type, notes, photo_sections):
    pdf = TrafficInspectionPDF()
    
    font_name = "Helvetica"
    if os.path.exists(FONT_PATH):
        pdf.add_font("FreeArial", "", FONT_PATH)
        pdf.add_font("FreeArial", "B", FONT_PATH)
        font_name = "FreeArial"

    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_text_color(40, 40, 40)
    
    # 1. כותרת הפרויקט
    pdf.set_font(font_name, "B", 13)
    pdf.cell(0, 8, fix_hebrew(f"שם האתר / פרויקט: {site_title}"), ln=True, align="R")
    pdf.set_draw_color(24, 43, 73)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # 2. טבלת נתונים מרכזית
    pdf.set_fill_color(240, 244, 248)
    pdf.set_font(font_name, "B", 10)
    
    col_w = 95
    pdf.cell(col_w, 8, fix_hebrew(f"צומת / מיקום: {junction_name}"), border=1, fill=True, align="R")
    
    inspector_info = f"מפקח: {inspector}"
    if license_no.strip():
        inspector_info += f" (רישיון: {license_no})"
    pdf.cell(col_w, 8, fix_hebrew(inspector_info), border=1, fill=True, ln=True, align="R")
    
    pdf.cell(col_w, 8, fix_hebrew(f"תאריך: {date_str}"), border=1, fill=True, align="R")
    pdf.cell(col_w, 8, fix_hebrew(f"סוג עבודה: {work_type}"), border=1, fill=True, ln=True, align="R")
    
    pdf.ln(5)
    
    # 3. הערות מפקח
    pdf.set_font(font_name, "B", 11)
    pdf.cell(0, 6, fix_hebrew("הערות, ממצאים והנחיות מפקח:"), ln=True, align="R")
    pdf.set_font(font_name, "", 10)
    
    notes_text = fix_hebrew(notes) if notes.strip() else fix_hebrew("לא נרשמו הערות נוספות.")
    pdf.multi_cell(190, 6, notes_text, border=1, align="R")
    pdf.ln(8)
    
    # 4. גלריית תמונות מתוקנת
    def add_photos(title_he, files, prefix):
        if not files:
            return
            
        pdf.set_font(font_name, "B", 11)
        pdf.set_fill_color(220, 228, 238)
        pdf.cell(0, 7, fix_hebrew(f" {title_he}"), ln=True, fill=True, align="R")
        pdf.ln(4)
        
        col = 0
        y_start = pdf.get_y()
        
        for i, f in enumerate(files):
            # אם אין מספיק מקום לתמונה על העמוד הנוכחי - פתח עמוד חדש
            if y_start + 70 > 270:
                pdf.add_page()
                y_start = pdf.get_y()
                col = 0

            # שמירת התמונה זמנית בפורמט JPEG
            img = Image.open(f)
            temp_filename = f"temp_{prefix}_{i}.jpg"
            img.convert("RGB").save(temp_filename, "JPEG")
            
            # חישוב מיקום X לפי עמודה (0 = ימין, 1 = שמאל)
            x_pos = 110 if col == 0 else 15
            curr_y = y_start
            
            # הטמעת התמונה
            pdf.image(temp_filename, x=x_pos, y=curr_y, w=85, h=55)
            pdf.rect(x_pos, curr_y, 85, 55)
            
            # כיתוב מתחת לתמונה
            pdf.set_xy(x_pos, curr_y + 56)
            pdf.set_font(font_name, "", 8)
            pdf.cell(85, 4, fix_hebrew(f"תמונה #{i+1}"), align="C")
            
            if col == 0:
                col = 1
            else:
                col = 0
                y_start += 65  # מעבר לשורה הבאה
                
            # מחיקת קובץ הזבל הזמני
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                
        if col == 1:
            pdf.set_y(y_start + 65)
        else:
            pdf.set_y(y_start)
            
        pdf.ln(4)

    for section in photo_sections:
        add_photos(section["title_he"], section["files"], section["prefix"])
    
    # 5. חתימה
    if pdf.get_y() > 230:
        pdf.add_page()
        
    pdf.ln(10)
    pdf.set_font(font_name, "B", 10)
    
    sign_text = f"שם המפקח: {inspector}"
    if license_no.strip():
        sign_text += f" | מס' רישיון: {license_no}"
        
    pdf.cell(0, 6, fix_hebrew(sign_text), ln=True, align="R")
    pdf.cell(120, 6, fix_hebrew("חתימה: _______________________"), ln=False, align="R")
    pdf.cell(70, 6, fix_hebrew(f"תאריך: {date_str}"), ln=True, align="R")
    
    return bytes(pdf.output())


# --- ממשק המשתמש (Streamlit UI) ---
st.title("🚦 ד.ד מהנדסים בע''מ")
st.subheader("מערכת הפקת דו\"ח מפקח הסדר תנועה")

st.divider()

st.subheader("📋 פרטי האתר והמפקח")

col1, col2 = st.columns(2)
with col1:
    site_name = st.text_input("שם האתר / פרויקט", "פרויקט מרכז 1")
    junction_name = st.text_input("שם הצומת / מיקום", "צומת הרצל - ז'בוטינסקי")
    inspector_name = st.text_input("שם המפקח", "נתנאל עוז")
    license_no = st.text_input("מספר רישיון / מ.פ", "1015546")

with col2:
    date_val = st.date_input("תאריך הבדיקה")
    work_type = st.selectbox("סוג הפעילות / העבודה", [
        "הסדר תנועה זמני",
        "החלפת מנגנון",
        "חריצת גלאים",
        "התקנת מצלמות",
        "אישור הסטת נתיבים",
        "בדיקת שילוט",
        "תחזוקת רמזורים",
        "ביקורת תקופתית",
        "אחר"
    ])

notes = st.text_area("הערות מפקח, מפגעים ודגשים", placeholder="רשום הערות הנדסיות כאן...")

st.divider()

st.subheader("📸 העלאת תמונות")

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
            {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files, "prefix": "before"},
            {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files, "prefix": "after"},
            {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files, "prefix": "mechanism"},
            {"title_he": "חריצת גלאים", "files": detectors_files, "prefix": "detectors"},
            {"title_he": "התקנת מצלמות תנועה", "files": cameras_files, "prefix": "cameras"},
            {"title_he": "תוכנית הסדר תנועה מאושרת", "files": plan_files, "prefix": "plan"},
            {"title_he": "נספחים / תמונות שונות", "files": misc_files, "prefix": "misc"}
        ]
        
        with st.spinner("מפיק דו\"ח מפקח בעברית..."):
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
