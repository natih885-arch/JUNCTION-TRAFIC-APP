import io
import os
import urllib.request

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

# --- הגדרת תצורת עמוד ב-Streamlit ---
st.set_page_config(
    page_title="ד.ד מהנדסים בע''מ - מערכת פיקוח הנדסית",
    page_icon="📐",
    layout="centered"
)

# --- עיצוב CSS הנדסי ומקצועי לממשק המשתמש ---
st.markdown("""
    <style>
    /* רקע כללי נקי וטכני */
    .stApp {
        background-color: #f1f5f9;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* באנר עליון הנדסי */
    .engineering-header {
        background: #0f172a;
        border-right: 6px solid #2563eb;
        border-left: 1px solid #334155;
        border-top: 1px solid #334155;
        border-bottom: 1px solid #334155;
        padding: 22px 20px;
        border-radius: 4px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .engineering-header .sys-tag {
        font-family: monospace;
        color: #38bdf8;
        font-size: 11px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .engineering-header h1 {
        color: #ffffff !important;
        font-size: 24px !important;
        font-weight: 800 !important;
        margin: 0 0 4px 0 !important;
        letter-spacing: -0.5px;
    }
    .engineering-header p {
        color: #94a3b8 !important;
        font-size: 14px !important;
        margin: 0 !important;
    }

    /* כותרות סעיף הנדסיות */
    .sec-badge {
        display: flex;
        align-items: center;
        background: #e2e8f0;
        border-right: 4px solid #0f172a;
        padding: 8px 12px;
        font-weight: 700;
        color: #0f172a;
        font-size: 15px;
        margin-top: 20px;
        margin-bottom: 15px;
        border-radius: 2px;
    }

    /* כפתור הפקה טכני */
    .stButton>button {
        background-color: #0f172a !important;
        color: #ffffff !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        padding: 14px 28px !important;
        border-radius: 4px !important;
        border: 1px solid #1e293b !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
        width: 100%;
        transition: all 0.15s ease-in-out !important;
    }
    .stButton>button:hover {
        background-color: #1e3a8a !important;
        border-color: #2563eb !important;
        color: #ffffff !important;
    }

    /* תיבות קלט נקיות */
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        border-radius: 3px !important;
        border: 1px solid #cbd5e1 !important;
        background-color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- הורדה ורישום פונטים סטטיים (פותר לחלוטין את בעיית המלבנים השחורים) ---
FONT_REGULAR_PATH = "Rubik-Regular.ttf"
FONT_BOLD_PATH = "Rubik-Bold.ttf"

FONT_NAME = 'Helvetica'
FONT_BOLD_NAME = 'Helvetica-Bold'

# הורדת פונטים סטטיים נקיים ממאגר Google Fonts
if not os.path.exists(FONT_REGULAR_PATH):
    try:
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/static/Rubik-Regular.ttf", 
            FONT_REGULAR_PATH
        )
    except Exception:
        pass

if not os.path.exists(FONT_BOLD_PATH):
    try:
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/static/Rubik-Bold.ttf", 
            FONT_BOLD_PATH
        )
    except Exception:
        pass

# רישום הגופנים ב-ReportLab
if os.path.exists(FONT_REGULAR_PATH):
    try:
        pdfmetrics.registerFont(TTFont('Rubik-Regular', FONT_REGULAR_PATH))
        FONT_NAME = 'Rubik-Regular'
    except Exception:
        FONT_NAME = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH):
    try:
        pdfmetrics.registerFont(TTFont('Rubik-Bold', FONT_BOLD_PATH))
        FONT_BOLD_NAME = 'Rubik-Bold'
    except Exception:
        FONT_BOLD_NAME = FONT_NAME


def heb(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    bidi_text = get_display(reshaped_text)
    return bidi_text


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
        self.setFillColor(colors.HexColor("#475569"))
        footer_text = heb(f"ד.ד מהנדסים בע''מ | דו\"ח מפקח שטח הנדסי | נייד: 054-5520445 | עמוד {self._pageNumber} מתוך {page_count}")
        self.drawCentredString(A4[0] / 2.0, 1 * cm, footer_text)
        self.restoreState()


def generate_pdf(site_title, junction_name, inspector, license_no, date_str, work_type, notes, photo_sections):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=2.0 * cm
    )

    styles = getSampleStyleSheet()
    
    # --- סגנונות הנדסיים מודגשים עבור ה-PDF ---
    style_header_title = ParagraphStyle('HeaderTitle', fontName=FONT_BOLD_NAME, fontSize=19, leading=23, textColor=colors.white, alignment=1)
    style_header_sub = ParagraphStyle('HeaderSub', fontName=FONT_BOLD_NAME, fontSize=13, leading=17, textColor=colors.HexColor("#93c5fd"), alignment=1)
    style_header_small = ParagraphStyle('HeaderSmall', fontName=FONT_NAME, fontSize=8.5, leading=11, textColor=colors.HexColor("#cbd5e1"), alignment=1)

    style_proj_title = ParagraphStyle('ProjTitle', fontName=FONT_BOLD_NAME, fontSize=15, leading=19, textColor=colors.HexColor("#0f172a"), alignment=2)
    
    # טקסט בולט ומודגש בטבלאות
    style_cell_label = ParagraphStyle('CellLabel', fontName=FONT_BOLD_NAME, fontSize=10.5, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_notes_title = ParagraphStyle('NotesTitle', fontName=FONT_BOLD_NAME, fontSize=12, leading=16, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_notes_content = ParagraphStyle('NotesContent', fontName=FONT_BOLD_NAME, fontSize=10, leading=15, textColor=colors.HexColor("#1e293b"), alignment=2)
    
    style_sec_header = ParagraphStyle('SecHeader', fontName=FONT_BOLD_NAME, fontSize=11, leading=15, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_caption = ParagraphStyle('Caption', fontName=FONT_BOLD_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#334155"), alignment=1)

    story = []

    # 1. באנר כותרת הנדסי בולט
    header_data = [
        [Paragraph(heb("ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD"), style_header_title)],
        [Paragraph(heb("דו\"ח פיקוח ואכיפת הסדרי תנועה"), style_header_sub)],
        [Paragraph(heb("מסמך פיקוח שטח רשמי - מנהל תנועה ותחבורה"), style_header_small)]
    ]
    header_table = Table(header_data, colWidths=[18.6 * cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#0f172a")),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,-1), (-1,-1), 3, colors.HexColor("#2563eb")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))

    # 2. שם פרויקט
    story.append(Paragraph(heb(f"שם האתר / פרויקט: {site_title}"), style_proj_title))
    story.append(Spacer(1, 0.25 * cm))

    # 3. טבלת פרטים מובנית ומודגשת
    insp_str = f"מפקח: {inspector}"
    if license_no.strip():
        insp_str += f" (מס' רישיון: {license_no})"

    info_data = [
        [Paragraph(heb(insp_str), style_cell_label), Paragraph(heb(f"צומת / מיקום: {junction_name}"), style_cell_label)],
        [Paragraph(heb(f"סוג עבודה: {work_type}"), style_cell_label), Paragraph(heb(f"תאריך בדיקה: {date_str}"), style_cell_label)]
    ]
    info_table = Table(info_data, colWidths=[9.3 * cm, 9.3 * cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    # 4. הערות מפקח
    story.append(Paragraph(heb("1.0 הערות, ממצאים והנחיות מפקח:"), style_notes_title))
    story.append(Spacer(1, 0.15 * cm))
    
    notes_text = notes.strip() if notes.strip() else "לא נרשמו הערות נוספות."
    notes_data = [[Paragraph(heb(notes_text), style_notes_content)]]
    notes_table = Table(notes_data, colWidths=[18.6 * cm])
    notes_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#94a3b8")),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(notes_table)
    story.append(Spacer(1, 0.5 * cm))

    # 5. תמונות עם תיאורים
    sec_idx = 2
    for section in photo_sections:
        files = section.get("files")
        captions = section.get("captions", [])
        if not files:
            continue

        sec_title_data = [[Paragraph(heb(f"{sec_idx}.0 {section['title_he']}"), style_sec_header)]]
        sec_title_table = Table(sec_title_data, colWidths=[18.6 * cm])
        sec_title_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e2e8f0")),
            ('LINELEFT', (0,0), (0,-1), 4, colors.HexColor("#0f172a")),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))

        photo_cells = []
        for i, f in enumerate(files):
            try:
                img = Image.open(f)
                img = img.convert("RGB")
                img_temp = io.BytesIO()
                img.save(img_temp, format="JPEG", quality=85)
                img_temp.seek(0)

                rl_img = RLImage(img_temp, width=8.5 * cm, height=5.7 * cm)
                
                custom_cap = captions[i].strip() if i < len(captions) and captions[i].strip() else f"תמונה #{i+1}"
                cap = Paragraph(heb(custom_cap), style_caption)
                
                cell_content = [rl_img, Spacer(1, 4), cap]
                photo_cells.append(cell_content)
            except Exception:
                continue

        grid_rows = []
        for i in range(0, len(photo_cells), 2):
            if i + 1 < len(photo_cells):
                grid_rows.append([photo_cells[i+1], photo_cells[i]])
            else:
                grid_rows.append(["", photo_cells[i]])

        if grid_rows:
            grid_table = Table(grid_rows, colWidths=[9.3 * cm, 9.3 * cm])
            grid_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(KeepTogether([sec_title_table, Spacer(1, 0.2 * cm), grid_table]))
            story.append(Spacer(1, 0.3 * cm))
            sec_idx += 1

    # 6. חתימת מפקח
    sig_text = f"שם המפקח: {inspector}"
    if license_no.strip():
        sig_text += f" | רישיון: {license_no}"

    sig_data = [
        [Paragraph(heb(f"תאריך: {date_str}"), style_cell_label), Paragraph(heb(sig_text), style_cell_label)],
        ["", Paragraph(heb("חתימה וחותמת: _______________________"), style_cell_label)]
    ]
    sig_table = Table(sig_data, colWidths=[9.3 * cm, 9.3 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(KeepTogether([Spacer(1, 0.5 * cm), sig_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# --- ממשק המשתמש ההנדסי ב-Streamlit ---

st.markdown("""
    <div class="engineering-header">
        <div class="sys-tag">System Version 3.0 // Inspection Portal</div>
        <h1>📐 ד.ד מהנדסים בע''מ</h1>
        <p>מערכת הנדסית להפקת דו"חות פיקוח הסדרי תנועה בשטח</p>
    </div>
""", unsafe_allow_html=True)

# 1. פרטי אתר ומפקח
with st.container():
    st.markdown('<div class="sec-badge">📋 1.0 פרטי פרויקט ומפקח שטח</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        site_name = st.text_input("שם האתר / פרויקט", "פרויקט מרכז 1")
        junction_name = st.text_input("שם הצומת / מיקום מדויק", "צומת הרצל - ז'בוטינסקי")
        inspector_name = st.text_input("שם המפקח", "נתנאל עוז")
        license_no = st.text_input("מספר רישיון / מ.פ", "1015546")

    with col2:
        date_val = st.date_input("תאריך הבדיקה")
        work_type = st.selectbox("סוג העבודה / הפעילות", [
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

    notes = st.text_area("הערות מפקח, מפגעים ותנאים בשטח", placeholder="הזן הערות הנדסיות וממצאים...", height=110)

# 2. העלאת תמונות לפי קטגוריות
with st.container():
    st.markdown('<div class="sec-badge">📸 2.0 תיעוד מצולם לפי סעיפים</div>', unsafe_allow_html=True)

    def render_upload_section(label, key_prefix):
        files = st.file_uploader(label, type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=key_prefix)
        captions = []
        if files:
            with st.expander(f"✏️ תיאורים לתמונות: {label}", expanded=False):
                for i, f in enumerate(files):
                    cap = st.text_input(f"תיאור תמונה #{i+1} ({f.name})", key=f"{key_prefix}_cap_{i}")
                    captions.append(cap)
        return files, captions

    col_a, col_b = st.columns(2)

    with col_a:
        before_files, before_caps = render_upload_section("מצב קיים (לפני)", "before")
        mechanism_files, mechanism_caps = render_upload_section("החלפת מנגנון", "mechanism")
        cameras_files, cameras_caps = render_upload_section("התקנת מצלמות", "cameras")

    with col_b:
        after_files, after_caps = render_upload_section("הסדר תנועה (אחרי)", "after")
        detectors_files, detectors_caps = render_upload_section("חריצת גלאים", "detectors")
        plan_files, plan_caps = render_upload_section("תוכנית / שרטוט", "plan")

    misc_files, misc_caps = render_upload_section("נספחים / תמונות שונות", "misc")

st.markdown("<br>", unsafe_allow_html=True)

# 3. כפתור הפקה
if st.button("⚙️ הפק דו\"ח מפקח הנדסי (PDF)", use_container_width=True):
    if not site_name or not junction_name or not inspector_name:
        st.error("⚠️ אנא מלא את הפרטים הנדרשים: שם האתר, שם הצומת ושם המפקח.")
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
        
        with st.spinner("מפיק דו\"ח הנדסי מותאם..."):
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
                st.session_state['pdf_filename'] = f"DD_Engineering_Report_{date_val}.pdf"
                st.success("✅ הדו\"ח הופק בהצלחה!")
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

if 'pdf_bytes' in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇️ הורד קובץ PDF הנדסי",
        data=st.session_state['pdf_bytes'],
        file_name=st.session_state['pdf_filename'],
        mime="application/pdf",
        use_container_width=True
    )

st.markdown("<hr style='border: 0.5px solid #cbd5e1;'>", unsafe_allow_html=True)
st.caption("© כל הזכויות שמורות לנתנאל עוז הררי | נייד: 054-5520445 | ד.ד מהנדסים בע''מ")
