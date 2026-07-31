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
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

# --- ניהול מספר דו"ח רץ (מציאת/עדכון קובץ המנה המקומי) ---
COUNTER_FILE = "report_counter.txt"
START_NUMBER = 100

def get_next_report_number():
    if not os.path.exists(COUNTER_FILE):
        return START_NUMBER
    try:
        with open(COUNTER_FILE, "r") as f:
            val = int(f.read().strip())
            return val
    except Exception:
        return START_NUMBER

def increment_report_number():
    current = get_next_report_number()
    next_num = current + 1
    with open(COUNTER_FILE, "w") as f:
        f.write(str(next_num))
    return current

# --- עיצוב CSS הנדסי עם רקע אפור בטון לממשק ---
st.markdown("""
    <style>
    .stApp {
        background-color: #e2e8f0;
    }
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-right: 6px solid #2563eb;
        padding: 22px;
        border-radius: 8px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
    }
    .main-header h1 {
        color: #ffffff !important;
        font-size: 26px !important;
        font-weight: 800 !important;
        margin-bottom: 6px !important;
    }
    .main-header p {
        color: #cbd5e1 !important;
        font-size: 15px !important;
        margin: 0 !important;
    }
    .section-title {
        color: #0f172a;
        font-size: 18px;
        font-weight: 800;
        border-right: 5px solid #2563eb;
        padding-right: 12px;
        margin-top: 25px;
        margin-bottom: 15px;
    }
    .stButton>button {
        background-color: #0f172a !important;
        color: white !important;
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 14px 28px !important;
        border-radius: 6px !important;
        border: none !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
    }
    .stButton>button:hover {
        background-color: #2563eb !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- פונקציית הורדה מאובטחת של גופנים עבריים ---
FONT_REGULAR_PATH = "Rubik-Regular.ttf"
FONT_BOLD_PATH = "Rubik-Bold.ttf"

def safe_download_font(urls, dest_path):
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
        return True
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for url in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response, open(dest_path, 'wb') as out_file:
                out_file.write(response.read())
            if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10000:
                return True
        except Exception:
            continue
    return False

regular_urls = [
    "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/static/Rubik-Regular.ttf",
    "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/Roboto-Regular.ttf"
]
bold_urls = [
    "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/static/Rubik-Bold.ttf",
    "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/Roboto-Bold.ttf"
]

safe_download_font(regular_urls, FONT_REGULAR_PATH)
safe_download_font(bold_urls, FONT_BOLD_PATH)

FONT_NAME = 'Helvetica'
FONT_BOLD_NAME = 'Helvetica-Bold'

if os.path.exists(FONT_REGULAR_PATH) and os.path.getsize(FONT_REGULAR_PATH) > 10000:
    try:
        pdfmetrics.registerFont(TTFont('HebrewFont', FONT_REGULAR_PATH))
        FONT_NAME = 'HebrewFont'
    except Exception:
        FONT_NAME = 'Helvetica'

if os.path.exists(FONT_BOLD_PATH) and os.path.getsize(FONT_BOLD_PATH) > 10000:
    try:
        pdfmetrics.registerFont(TTFont('HebrewFont-Bold', FONT_BOLD_PATH))
        FONT_BOLD_NAME = 'HebrewFont-Bold'
    except Exception:
        FONT_BOLD_NAME = FONT_NAME
else:
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
        self.setFillColor(colors.HexColor("#666666"))
        footer_text = heb(f"כל הזכויות שמורות לנתנאל עוז הררי © | נייד: 054-5520445 | ד.ד מהנדסים בע''מ | עמוד {self._pageNumber} מתוך {page_count}")
        self.drawCentredString(A4[0] / 2.0, 1 * cm, footer_text)
        self.restoreState()


def generate_pdf(report_num, site_title, junction_name, inspector, license_no, permit_no, date_str, work_type, notes, photo_sections):
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
    
    style_header_title = ParagraphStyle('HeaderTitle', fontName=FONT_BOLD_NAME, fontSize=18, leading=22, textColor=colors.white, alignment=1)
    style_header_sub = ParagraphStyle('HeaderSub', fontName=FONT_BOLD_NAME, fontSize=13, leading=17, textColor=colors.white, alignment=1)
    style_header_small = ParagraphStyle('HeaderSmall', fontName=FONT_NAME, fontSize=9, leading=11, textColor=colors.HexColor("#e2e8f0"), alignment=1)

    style_proj_title = ParagraphStyle('ProjTitle', fontName=FONT_BOLD_NAME, fontSize=14, leading=18, textColor=colors.HexColor("#182b49"), alignment=2)
    style_cell_label = ParagraphStyle('CellLabel', fontName=FONT_BOLD_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_notes_title = ParagraphStyle('NotesTitle', fontName=FONT_BOLD_NAME, fontSize=12, leading=16, textColor=colors.HexColor("#182b49"), alignment=2)
    style_notes_content = ParagraphStyle('NotesContent', fontName=FONT_BOLD_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#1e293b"), alignment=2)
    style_sec_header = ParagraphStyle('SecHeader', fontName=FONT_BOLD_NAME, fontSize=11, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_caption = ParagraphStyle('Caption', fontName=FONT_BOLD_NAME, fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"), alignment=1)

    story = []

    # 1. באנר כותרת ראשית (כולל מספר דו"ח רץ)
    header_data = [
        [Paragraph(heb("ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD"), style_header_title)],
        [Paragraph(heb(f"דו\"ח פיקוח ואכיפת הסדרי תנועה מס' {report_num}"), style_header_sub)],
        [Paragraph(heb("מסמך פיקוח שטח רשמי"), style_header_small)]
    ]
    header_table = Table(header_data, colWidths=[18 * cm])
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
    if license_no and license_no.strip():
        insp_str += f" (רישיון: {license_no.strip()})"

    work_type_str = f"סוג עבודה: {work_type}"
    if permit_no and permit_no.strip():
        work_type_str += f" | היתר: {permit_no.strip()}"

    info_data = [
        [Paragraph(heb(insp_str), style_cell_label), Paragraph(heb(f"צומת / מיקום: {junction_name}"), style_cell_label)],
        [Paragraph(heb(work_type_str), style_cell_label), Paragraph(heb(f"תאריך: {date_str}"), style_cell_label)]
    ]
    info_table = Table(info_data, colWidths=[9 * cm, 9 * cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
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

    # 5. תמונות לפי קטגוריות
    for section in photo_sections:
        files = section.get("files")
        captions = section.get("captions", [])
        if not files:
            continue

        sec_title_data = [[Paragraph(heb(section['title_he']), style_sec_header)]]
        sec_title_table = Table(sec_title_data, colWidths=[18 * cm])
        sec_title_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#cbd5e1")),
            ('LINELEFT', (0,0), (0,-1), 3, colors.HexColor("#182b49")),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
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
                
                custom_cap = captions[i].strip() if i < len(captions) and captions[i].strip() else f"תמונה #{i+1}"
                cap = Paragraph(heb(custom_cap), style_caption)
                
                cell_content = [rl_img, Spacer(1, 2), cap]
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
    if license_no and license_no.strip():
        sig_text += f" | מס' רישיון: {license_no.strip()}"
    if permit_no and permit_no.strip():
        sig_text += f" | היתר עבודה: {permit_no.strip()}"

    sig_data = [
        [Paragraph(heb(f"תאריך: {date_str}"), style_cell_label), Paragraph(heb(sig_text), style_cell_label)],
        ["", Paragraph(heb("חתימת המפקח: _______________________"), style_cell_label)]
    ]
    sig_table = Table(sig_data, colWidths=[9 * cm, 9 * cm])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(KeepTogether([Spacer(1, 0.5 * cm), sig_table]))

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# --- ממשק המשתמש (Streamlit UI) ---

st.markdown("""
    <div class="main-header">
        <h1>🚦 ד.ד מהנדסים בע''מ</h1>
        <p>מערכת מקצועית להפקת דו"חות פיקוח הסדרי תנועה</p>
    </div>
""", unsafe_allow_html=True)

# הצגת מספר הדו"ח הנוכחי בממשק
current_num = get_next_report_number()
st.info(f"📌 **מספר הדו\"ח המיועד להפקה הבאה:** #{current_num}")

st.markdown('<div class="section-title">📋 פרטי האתר והמפקח</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    site_name = st.text_input("שם האתר / פרויקט", "פרויקט מרכז 1")
    junction_name = st.text_input("שם הצומת / מיקום", "צומת הרצל - ז'בוטינסקי")
    inspector_name = st.text_input("שם המפקח", "נתנאל עוז")
    license_no = st.text_input("מספר רישיון / מ.פ (רשות)", "1015546")
    permit_no = st.text_input("מספר היתר עבודה (רשות)", placeholder="לדוגמה: H-2026-99")

with col2:
    date_val = st.date_input("תאריך הבדיקה")
    
    work_type_options = [
        "הסדר תנועה זמני",
        "הקמת צומת",
        "הקמת צומת חדשה",
        "החלפת מנגנון",
        "חריצת גלאים",
        "התקנת מצלמות",
        "התקנת עמדת UPS",
        "אישור הסטת נתיבים",
        "בדיקת שילוט",
        "תחזוקת רמזורים",
        "ביקורת תקופתית",
        "אחר"
    ]
    selected_work_type = st.selectbox("סוג הפעילות / העבודה", work_type_options)
    
    if selected_work_type == "אחר":
        custom_work_type = st.text_input("רשום את סוג העבודה (אחר):", placeholder="לדוגמה: תיקון כבל תקשורת")
        final_work_type = custom_work_type if custom_work_type.strip() else "אחר"
    else:
        final_work_type = selected_work_type

notes = st.text_area("הערות מפקח, מפגעים ודגשים", placeholder="רשום הערות הנדסיות כאן...", height=100)

st.markdown('<div class="section-title">📸 העלאת תמונות ותיאורים</div>', unsafe_allow_html=True)

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
    ups_files, ups_caps = render_upload_section("תמונות - התקנת עמדת UPS", "ups")

plan_files, plan_caps = render_upload_section("צילום תוכנית / שרטוט", "plan")
misc_files, misc_caps = render_upload_section("תמונות - שונות / נספחים", "misc")

st.markdown("<br>", unsafe_allow_html=True)

# יצירת ה-PDF
if st.button("🚀 הפק דו\"ח מפקח PDF", use_container_width=True):
    if not site_name or not junction_name or not inspector_name:
        st.error("⚠️ אנא מלא את שם האתר, שם הצומת ושם המפקח.")
    else:
        # מקבלים ומעלים את מספר הדו"ח הרץ
        report_num = increment_report_number()
        
        photo_sections = [
            {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files, "captions": before_caps},
            {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files, "captions": after_caps},
            {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files, "captions": mechanism_caps},
            {"title_he": "חריצת גלאים", "files": detectors_files, "captions": detectors_caps},
            {"title_he": "התקנת מצלמות תנועה", "files": cameras_files, "captions": cameras_caps},
            {"title_he": "התקנת עמדת UPS", "files": ups_files, "captions": ups_caps},
            {"title_he": "תוכנית הסדר תנועה מאושרת", "files": plan_files, "captions": plan_caps},
            {"title_he": "נספחים / תמונות שונות", "files": misc_files, "captions": misc_caps}
        ]
        
        with st.spinner("מפיק דו\"ח מפקח מקצועי..."):
            try:
                pdf_bytes = generate_pdf(
                    report_num=report_num,
                    site_title=site_name,
                    junction_name=junction_name,
                    inspector=inspector_name,
                    license_no=license_no,
                    permit_no=permit_no,
                    date_str=str(date_val),
                    work_type=final_work_type,
                    notes=notes,
                    photo_sections=photo_sections
                )
                
                st.session_state['pdf_bytes'] = pdf_bytes
                st.session_state['pdf_filename'] = f"DD_Engineers_Report_{report_num}_{date_val}.pdf"
                st.success(f"✅ דו\"ח מס' {report_num} הופק בהצלחה!")
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

if 'pdf_bytes' in st.session_state:
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="⬇️ הורד דו\"ח PDF למכשיר",
        data=st.session_state['pdf_bytes'],
        file_name=st.session_state['pdf_filename'],
        mime="application/pdf",
        use_container_width=True
    )

st.markdown("<hr style='border: 0.5px solid #cbd5e1;'>", unsafe_allow_html=True)
st.caption("© כל הזכויות שמורות לנתנאל עוז הררי | נייד: 054-5520445. אין לעשות שימוש או להפיץ ללא אישור בכתב.")
