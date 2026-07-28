import io
import os
import smtplib
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import arabic_reshaper
import streamlit as st
from bidi.algorithm import get_display
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# הגדרת תצורת עמוד ב-Streamlit
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

# הורדת פונט עברי אמין (Rubik) מ-Google Fonts
FONT_PATH = "Rubik-Regular.ttf"
FONT_NAME = 'Helvetica'

if not os.path.exists(FONT_PATH):
    font_url = "https://github.com/google/fonts/raw/main/ofl/rubik/Rubik%5Bwght%5D.ttf"
    try:
        urllib.request.urlretrieve(font_url, FONT_PATH)
    except Exception:
        pass

if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont('HebrewFont', FONT_PATH))
        FONT_NAME = 'HebrewFont'
    except Exception:
        FONT_NAME = 'Helvetica'

# פונקציה לעיבוד טקסט בעברית (הפיכת כיוון וחיבור אותיות)
def heb(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    bidi_text = get_display(reshaped_text)
    return bidi_text

# מחלקה למספור עמודים וכותרת תחתית
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont(FONT_NAME, 8)
        self.setFillColor(colors.HexColor("#666666"))
        # 1. הוספת מספר הטלפון בכותרת התחתית ב-PDF
        footer_text = heb(f"כל הזכויות שמורות לנתנאל עוז הררי © | נייד: 054-5520445 | ד.ד מהנדסים בע''מ | עמוד {self._pageNumber} מתוך {page_count}")
        self.drawCentredString(A4[0] / 2.0, 1 * cm, footer_text)
        self.restoreState()

def generate_pdf(site_title, junction_name, inspector, license_no, date_str, work_type, notes, photo_sections):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2.0 * cm
    )

    styles = getSampleStyleSheet()
    
    # סגנונות מעוצבים
    style_header_title = ParagraphStyle('HeaderTitle', fontName=FONT_NAME, fontSize=15, leading=19, textColor=colors.white, alignment=1)
    style_header_sub = ParagraphStyle('HeaderSub', fontName=FONT_NAME, fontSize=12, leading=16, textColor=colors.white, alignment=1)
    style_header_small = ParagraphStyle('HeaderSmall', fontName=FONT_NAME, fontSize=8, leading=10, textColor=colors.HexColor("#e2e8f0"), alignment=1)

    style_proj_title = ParagraphStyle('ProjTitle', fontName=FONT_NAME, fontSize=13, leading=16, textColor=colors.HexColor("#182b49"), alignment=2)
    style_cell_label = ParagraphStyle('CellLabel', fontName=FONT_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_notes_title = ParagraphStyle('NotesTitle', fontName=FONT_NAME, fontSize=11, leading=14, textColor=colors.HexColor("#182b49"), alignment=2)
    style_notes_content = ParagraphStyle('NotesContent', fontName=FONT_NAME, fontSize=9.5, leading=13, textColor=colors.HexColor("#1e293b"), alignment=2)
    style_sec_header = ParagraphStyle('SecHeader', fontName=FONT_NAME, fontSize=10, leading=13, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_caption = ParagraphStyle('Caption', fontName=FONT_NAME, fontSize=8, leading=10, textColor=colors.HexColor("#475569"), alignment=1)

    story = []

    # 1. באנר כותרת ראשית
    header_data = [
        [Paragraph(heb("ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD"), style_header_title)],
        [Paragraph(heb("דו\"ח פיקוח ואכיפת הסדרי תנועה"), style_header_sub)],
        [Paragraph(heb("מסמך פיקוח שטח רשמי"), style_header_small)]
    ]
    header_table = Table(header_data, colWidths=[18 * cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#182b49")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))

    # 2. שם פרויקט
    story.append(Paragraph(heb(f"שם האתר / פרויקט: {site_title}"), style_proj_title))
    story.append(Spacer(1, 0.2 * cm))

    # 3. טבלת פרטים
    insp_str = f"מפקח: {inspector}"
    if license_no.strip():
        insp_str += f" (רישיון: {license_no})"

    info_data = [
        [Paragraph(heb(insp_str), style_cell_label), Paragraph(heb(f"צומת / מיקום: {junction_name}"), style_cell_label)],
        [Paragraph(heb(f"סוג עבודה: {work_type}"), style_cell_label), Paragraph(heb(f"תאריך: {date_str}"), style_cell_label)]
    ]
    info_table = Table(info_data, colWidths=[9 * cm, 9 * cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    # 4. הערות מפקח
    story.append(Paragraph(heb("הערות, ממצאים והנחיות מפקח:"), style_notes_title))
    story.append(Spacer(1, 0.1 * cm))
    
    notes_text = notes.strip() if notes.strip() else "לא נרשמו הערות נוספות."
    notes_data = [[Paragraph(heb(notes_text), style_notes_content)]]
    notes_table = Table(notes_data, colWidths=[18 * cm])
    notes_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(notes_table)
    story.append(Spacer(1, 0.5 * cm))

    # 5. תמונות עם תיאורים דינמיים
    for section in photo_sections:
        files = section.get("files")
        captions = section.get("captions", [])
        if not files:
            continue

        sec_title_data = [[Paragraph(heb(section['title_he']), style_sec_header)]]
        sec_title_table = Table(sec_title_data, colWidths=[18 * cm])
        sec_title_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e2e8f0")),
            ('LINELEFT', (0,0), (0,-1), 3, colors.HexColor("#182b49")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))

        photo_cells = []
        for i, f in enumerate(files):
            try:
                img = Image.open(f)
                img = img.convert("RGB")
                img_temp = io.BytesIO()
                img.save(img_temp, format="JPEG", quality=80)
                img_temp.seek(0)

                rl_img = RLImage(img_temp, width=8.2 * cm, height=5.5 * cm)
                
                # 2. בדיקה אם הוזן תיאור אישי לתמונה
                custom_cap = captions[i].strip() if i < len(captions) and captions[i].strip() else f"תמונה #{i+1}"
                cap = Paragraph(heb(custom_cap), style_caption)
                
                cell_content = [rl_img, Spacer(1, 2), cap]
                photo_cells.append(cell_content)
            except Exception:
                continue

        # סידור תמונות בזוגות
        grid_rows = []
        for i in range(0, len(photo_cells), 2):
            if i + 1 < len(photo_cells):
                grid_rows.append([photo_cells[i+1], photo_cells[i]])
            else:
                grid_rows.append(["", photo_cells[i]])

        if grid_rows:
            grid_table = Table(grid_rows, colWidths=[9 * cm, 9 * cm])
            grid_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(KeepTogether([sec_title_table, Spacer(1, 0.2 * cm), grid_table]))
            story.append(Spacer(1, 0.3 * cm))

    # 6. חתימה
    sig_text = f"שם המפקח: {inspector}"
    if license_no.strip():
        sig_text += f" | מס' רישיון: {license_no}"

    sig_data = [
        [Paragraph(heb(f"תאריך: {date_str}"), style_cell_label), Paragraph(heb(sig_text), style_cell_label)],
        ["", Paragraph(heb("חתימה: _______________________"), style_cell_label)]
    ]
    sig_table = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(KeepTogether([Spacer(1, 0.5 * cm), sig_table]))

    # בניית ה-PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# 3. פונקציה לשליחת המייל עם ה-PDF המצורף
def send_email(sender_email, sender_password, recipient_email, subject, body_text, pdf_data, filename):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    # קובץ ה-PDF המצורף
    part = MIMEApplication(pdf_data, Name=filename)
    part['Content-Disposition'] = f'attachment; filename="{filename}"'
    msg.attach(part)

    # התחברות לשרת SMTP של Gmail
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()


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

st.subheader("📸 העלאת תמונות ותיאורים")

def render_upload_section(label, key_prefix):
    files = st.file_uploader(label, type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=key_prefix)
    captions = []
    if files:
        with st.expander(f"✏️ תיאורים לתמונות: {label}", expanded=False):
            for i, f in enumerate(files):
                cap = st.text_input(f"תיאור לתמונה #{i+1} ({f.name})", key=f"{key_prefix}_cap_{i}")
                captions.append(cap)
    return files, captions

col_a, col_b = st.columns(2)

with col_a:
    before_files, before_caps = render_upload_section("תמונות - לפני הסדר", "before")
    mechanism_files, mechanism_caps = render_upload_section("תמונות - החלפת מנגנון", "mechanism")
    cameras_files, cameras_caps = render_upload_section("תמונות - התקנת מצלמות", "cameras")

with col_b:
    after_files, after_caps = render_upload_section("תמונות - אחרי הסדר", "after")
    detectors_files, detectors_caps = render_upload_section("תמונות - חריצת גלאים", "detectors")
    plan_files, plan_caps = render_upload_section("צילום תוכנית / שרטוט", "plan")

misc_files, misc_caps = render_upload_section("תמונות - שונות / נספחים", "misc")

st.divider()

# יצירת ה-PDF ושמירתו ב-Session State כדי שיהיה זמין גם להורדה וגם לשליחה
if st.button("🚀 הפק דו\"ח מפקח PDF", type="primary", use_container_width=True):
    if not site_name or not junction_name or not inspector_name:
        st.error("⚠️ אנא מלא את שם האתר, שם הצומת ושם המפקח.")
    else:
        photo_sections = [
            {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files, "captions": before_caps},
            {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files, "captions": after_caps},
            {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files, "captions": mechanism_caps},
            {"title_he": "חריצת גלאים", "files": detectors_files, "captions": detectors_caps},
            {"title_he": "התקנת מצלמות תנועה", "files": cameras_files, "captions": cameras_caps},
            {"title_he": "תוכנית הסדר תנועה מאושרת", "files": plan_files, "captions": plan_caps},
            {"title_he": "נספחים / תמונות שונות", "files": misc_files, "captions": misc_caps}
        ]
        
        with st.spinner("מפיק דו\"ח מפקח מקצועי..."):
            try:
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
                
                st.session_state['pdf_bytes'] = pdf_bytes
                st.session_state['pdf_filename'] = f"DD_Engineers_Report_{date_val}.pdf"
                st.success("✅ הדו\"ח הופק בהצלחה!")
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

# אפשרויות הורדה ושליחה במייל מופיעות לאחר שהדו"ח נוצר
if 'pdf_bytes' in st.session_state:
    st.download_button(
        label="⬇️ הורד דו\"ח PDF למכשיר",
        data=st.session_state['pdf_bytes'],
        file_name=st.session_state['pdf_filename'],
        mime="application/pdf",
        use_container_width=True
    )
    
    st.divider()
    
    # 3. ממשק שליחת מייל
    st.subheader("📧 שליחת הדו\"ח במייל")
    
    recipient_email = st.text_input("הכנס כתובת מייל למשלוח הדו\"ח", placeholder="example@domain.com")
    
    with st.expander("⚙️ הגדרות שרת מייל (Gmail)", expanded=False):
        sender_email = st.text_input("כתובת Gmail השולחת", placeholder="your_email@gmail.com")
        sender_password = st.text_input("סיסמת אפליקציה (App Password)", type="password")
        st.caption("מילוי חד-פעמי או דרך Streamlit Secrets. מומלץ להפיק App Password מתוך חשבון ה-Google.")

    if st.button("✉️ שלח דו\"ח למייל", use_container_width=True):
        if not recipient_email or not sender_email or not sender_password:
            st.warning("⚠️ אנא מלא את כתובת המייל של המקבל ואת פרטי התחברות ה-Gmail.")
        else:
            with st.spinner("שולח את המייל..."):
                try:
                    send_email(
                        sender_email=sender_email,
                        sender_password=sender_password,
                        recipient_email=recipient_email,
                        subject=f"דו\"ח פיקוח - {site_name} - {date_val}",
                        body_text=f"שלום,\n\ מצורף דו\"ח פיקוח הסדר תנועה עבור {site_name}.\n\nבברכה,\n{inspector_name}\nד.ד מהנדסים בע''מ",
                        pdf_data=st.session_state['pdf_bytes'],
                        filename=st.session_state['pdf_filename']
                    )
                    st.success(f"📬 הדו\"ח נשלח בהצלחה ל- {recipient_email}")
                except Exception as e:
                    st.error(f"שגיאה בשליחת המייל: {e}")

st.caption("© כל הזכויות שמורות לנתנאל עוז הררי (Netanel Oz Harary) | נייד: 054-5520445. אין לעשות שימוש או להפיץ ללא אישור בכתב.")
