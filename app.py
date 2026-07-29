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
    page_title="ד.ד מהנדסים בע''מ - הפקת דו\"ח מפקח",
    page_icon="🚦",
    layout="centered"
)

# --- עיצוב CSS מותאם אישית לממשק המשתמש ---
st.markdown("""
    <style>
    /* עיצוב כללי ורקע לממשק */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* כותרת ראשית של האפליקציה */
    .main-header {
        background: linear-gradient(135deg, #182b49 0%, #0f172a 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #ffffff !important;
        font-size: 26px !important;
        font-weight: 700 !important;
        margin-bottom: 5px !important;
    }
    .main-header p {
        color: #94a3b8 !important;
        font-size: 15px !important;
        margin: 0 !important;
    }

    /* עיצוב מסגרות וכרטיסיות קלט */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {
        border-radius: 10px;
    }

    /* התאמת כפתור ההפקה */
    .stButton>button {
        background-color: #182b49 !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton>button:hover {
        background-color: #2563eb !important;
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.15) !important;
        transform: translateY(-1px);
    }

    /* עיצוב כותרות סקשנים בטופס */
    .section-title {
        color: #182b49;
        font-size: 18px;
        font-weight: 700;
        border-right: 4px solid #2563eb;
        padding-right: 10px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_text_html=True)

# --- הורדת פונט עברי איכותי (Heebo & Heebo-Bold) עבור ה-PDF ---
FONT_REGULAR_PATH = "Heebo-Regular.ttf"
FONT_BOLD_PATH = "Heebo-Bold.ttf"

FONT_NAME = 'Helvetica'
FONT_BOLD_NAME = 'Helvetica-Bold'

# הורדת הפונטים מ-Google Fonts במידת הצורך
if not os.path.exists(FONT_REGULAR_PATH):
    try:
        urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/heebo/Heebo%5Bwght%5D.ttf", FONT_REGULAR_PATH)
    except Exception:
        pass

if not os.path.exists(FONT_BOLD_PATH):
    try:
        urllib.request.urlretrieve("https://github.com/google/fonts/raw/main/ofl/heebo/static/Heebo-Bold.ttf", FONT_BOLD_PATH)
    except Exception:
        pass

# רישום הפונטים ב-ReportLab
if os.path.exists(FONT_REGULAR_PATH):
    try:
        pdfmetrics.registerFont(TTFont('HebrewFont', FONT_REGULAR_PATH))
        FONT_NAME = 'HebrewFont'
    except Exception:
        FONT_NAME = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH):
    try:
        pdfmetrics.registerFont(TTFont('HebrewFont-Bold', FONT_BOLD_PATH))
        FONT_BOLD_NAME = 'HebrewFont-Bold'
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
        self.setFont(FONT_NAME, 8.5)
        self.setFillColor(colors.HexColor("#475569"))
        footer_text = heb(f"כל הזכויות שמורות לנתנאל עוז הררי © | נייד: 054-5520445 | ד.ד מהנדסים בע''מ | עמוד {self._pageNumber} מתוך {page_count}")
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
    
    # --- סגנונות טקסט מעודכנים ומוגדלים ב-PDF ---
    # כותרת ראשית מוגדלת ומודגשת
    style_header_title = ParagraphStyle('HeaderTitle', fontName=FONT_BOLD_NAME, fontSize=18, leading=22, textColor=colors.white, alignment=1)
    style_header_sub = ParagraphStyle('HeaderSub', fontName=FONT_BOLD_NAME, fontSize=13, leading=17, textColor=colors.white, alignment=1)
    style_header_small = ParagraphStyle('HeaderSmall', fontName=FONT_NAME, fontSize=9, leading=11, textColor=colors.HexColor("#cbd5e1"), alignment=1)

    # כותרות פרטים ומלל מודגש
    style_proj_title = ParagraphStyle('ProjTitle', fontName=FONT_BOLD_NAME, fontSize=14, leading=18, textColor=colors.HexColor("#182b49"), alignment=2)
    style_cell_label = ParagraphStyle('CellLabel', fontName=FONT_BOLD_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    
    # מלל והערות מפקח
    style_notes_title = ParagraphStyle('NotesTitle', fontName=FONT_BOLD_NAME, fontSize=12, leading=16, textColor=colors.HexColor("#182b49"), alignment=2)
    style_notes_content = ParagraphStyle('NotesContent', fontName=FONT_NAME, fontSize=10.5, leading=15, textColor=colors.HexColor("#1e293b"), alignment=2)
    
    # כותרות סעיפי תמונות
    style_sec_header = ParagraphStyle('SecHeader', fontName=FONT_BOLD_NAME, fontSize=11, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_caption = ParagraphStyle('Caption', fontName=FONT_BOLD_NAME, fontSize=9, leading=11, textColor=colors.HexColor("#334155"), alignment=1)

    story = []

    # 1. באנר כותרת ראשית בולט
    header_data = [
        [Paragraph(heb("ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD"), style_header_title)],
        [Paragraph(heb("דו\"ח פיקוח ואכיפת הסדרי תנועה"), style_header_sub)],
        [Paragraph(heb("מסמך פיקוח שטח רשמי"), style_header_small)]
    ]
    header_table = Table(header_data, colWidths=[18.6 * cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#182b49")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
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
    info_table = Table(info_data, colWidths=[9.3 * cm, 9.3 * cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.8, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.4 * cm))

    # 4. הערות מפקח
    story.append(Paragraph(heb("הערות, ממצאים והנחיות מפקח:"), style_notes_title))
    story.append(Spacer(1, 0.15 * cm))
    
    notes_text = notes.strip() if notes.strip() else "לא נרשמו הערות נוספות."
    notes_data = [[Paragraph(heb(notes_text), style_notes_content)]]
    notes_table = Table(notes_data, colWidths=[18.6 * cm])
    notes_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(notes_table)
    story.append(Spacer(1, 0.5 * cm))

    # 5. תמונות עם תיאורים
    for section in photo_sections:
        files = section.get("files")
        captions = section.get("captions", [])
        if not files:
            continue

        sec_title_data = [[Paragraph(heb(section['title_he']), style_sec_header)]]
        sec_title_table = Table(sec_title_data, colWidths=[18.6 * cm])
        sec_title_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e2e8f0")),
            ('LINELEFT', (0,0), (0,-1), 4, colors.HexColor("#182b49")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
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
                
                cell_content = [rl_img, Spacer(1, 3), cap]
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

    # 6. חתימה
    sig_text = f"שם המפקח: {inspector}"
    if license_no.strip():
        sig_text += f" | מס' רישיון: {license_no}"

    sig_data = [
        [Paragraph(heb(f"תאריך: {date_str}"), style_cell_label), Paragraph(heb(sig_text), style_cell_label)],
        ["", Paragraph(heb("חתימה: _______________________"), style_cell_label)]
    ]
    sig_table = Table(sig_data, colWidths=[9.3 * cm, 9.3 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(KeepTogether([Spacer(1, 0.5 * cm), sig_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# --- ממשק המשתמש המשודרג ב-Streamlit ---

# באנר עליון מרהיב
st.markdown("""
    <div class="main-header">
        <h1>🚦 ד.ד מהנדסים בע''מ</h1>
        <p>מערכת מקצועית להפקת דו"חות פיקוח הסדרי תנועה</p>
    </div>
""", unsafe_text_html=True)

# 1. כרטיסיית פרטי אתר
with st.container():
    st.markdown('<div class="section-title">📋 פרטי האתר והמפקח</div>', unsafe_text_html=True)
    
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

    notes = st.text_area("הערות מפקח, מפגעים ודגשים", placeholder="רשום הערות הנדסיות כאן...", height=110)

# 2. כרטיסיית תמונות ותיאורים
with st.container():
    st.markdown('<div class="section-title">📸 העלאת תמונות ותיאורים (לפי קטגוריות)</div>', unsafe_text_html=True)

    def render_upload_section(label, key_prefix):
        files = st.file_uploader(label, type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=key_prefix)
        captions = []
        if files:
            with st.expander(f"✏️ תיאורים לתמונות ב- {label}", expanded=False):
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

st.markdown("<br>", unsafe_text_html=True)

# 3. הפקה והורדה
if st.button("🚀 הפק דו\"ח מפקח PDF מעוצב", use_container_width=True):
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
        
        with st.spinner("מפיק דו\"ח מפקח מעוצב באיכות גבוהה..."):
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

if 'pdf_bytes' in st.session_state:
    st.markdown("<br>", unsafe_text_html=True)
    st.download_button(
        label="⬇️ הורד דו\"ח PDF למכשיר",
        data=st.session_state['pdf_bytes'],
        file_name=st.session_state['pdf_filename'],
        mime="application/pdf",
        use_container_width=True
    )

st.markdown("<hr>", unsafe_text_html=True)
st.caption("© כל הזכויות שמורות לנתנאל עוז הררי | נייד: 054-5520445. אין לעשות שימוש או להפיץ ללא אישור בכתב.")
