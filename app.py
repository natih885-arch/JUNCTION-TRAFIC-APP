import io
import os
import urllib.request
import streamlit as st
import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from svglib.svglib import svg2rlg

# --- הגדרת תצורת עמוד ב-Streamlit ---
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

START_NUMBER = 100

def get_gspread_client():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(credentials)
    except Exception:
        return None

def get_next_report_number():
    """שולף את מספר הדו"ח הגבוה ביותר מטור A בלבד"""
    try:
        client = get_gspread_client()
        if not client:
            return START_NUMBER
        sheet_url = st.secrets["sheets"]["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        col_a = sheet.col_values(1)
        
        if len(col_a) <= 1:
            return START_NUMBER
        
        report_numbers = []
        for val in col_a[1:]:
            if val and str(val).strip().isdigit():
                report_numbers.append(int(val.strip()))
        
        if report_numbers:
            return max(report_numbers) + 1
        return START_NUMBER
    except Exception:
        return START_NUMBER

def append_to_google_sheets(report_num, date_str, site_title, junction_name, inspector, license_no, permit_no, work_type, notes):
    try:
        client = get_gspread_client()
        if not client:
            st.error("שגיאה: לא ניתן להתחבר ל-Google Sheets.")
            return False
            
        sheet_url = st.secrets["sheets"]["spreadsheet_url"]
        sheet = client.open_by_url(sheet_url).sheet1
        
        new_row = [
            str(report_num),
            str(date_str),
            str(site_title),
            str(junction_name),
            str(inspector),
            str(license_no),
            str(permit_no),
            str(work_type),
            str(notes)
        ]
        sheet.append_row(new_row, table_range="A1:I1000")
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירה ל-Google Sheets: {str(e)}")
        return False

# --- הגדרת פונטים עבור PDF ---
FONT_NAME = 'HebrewFont'
FONT_BOLD_NAME = 'HebrewFont-Bold'

def setup_hebrew_fonts():
    font_reg_path = "Rubik-Regular.ttf"
    font_bold_path = "Rubik-Bold.ttf"

    url_reg = "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/Rubik%5Bwght%5D.ttf"
    url_bold = "https://raw.githubusercontent.com/google/fonts/main/ofl/rubik/Rubik-Bold.ttf"

    if not os.path.exists(font_reg_path):
        try:
            req = urllib.request.Request(url_reg, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_reg_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception:
            pass

    if not os.path.exists(font_bold_path):
        try:
            req = urllib.request.Request(url_bold, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(font_bold_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception:
            pass

    try:
        if os.path.exists(font_reg_path):
            pdfmetrics.registerFont(TTFont(FONT_NAME, font_reg_path))
        if os.path.exists(font_bold_path):
            pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, font_bold_path))
        else:
            pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, font_reg_path))
    except Exception:
        pass

setup_hebrew_fonts()

def heb(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)

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

def generate_pdf(report_num, site_title, junction_name, inspector, license_no, permit_no, date_str, work_type, notes, photo_sections, lr_svg=None, lr_arm_settings=None):
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
    
    style_header_title = ParagraphStyle('HeaderTitle', fontName=FONT_BOLD_NAME, fontSize=16, leading=20, textColor=colors.white, alignment=1)
    style_header_sub = ParagraphStyle('HeaderSub', fontName=FONT_BOLD_NAME, fontSize=13, leading=17, textColor=colors.white, alignment=1)
    style_header_small = ParagraphStyle('HeaderSmall', fontName=FONT_NAME, fontSize=9, leading=12, textColor=colors.HexColor("#e2e8f0"), alignment=1)
    style_proj_title = ParagraphStyle('ProjTitle', fontName=FONT_BOLD_NAME, fontSize=14, leading=18, textColor=colors.HexColor("#182b49"), alignment=2)
    style_cell_label = ParagraphStyle('CellLabel', fontName=FONT_BOLD_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_notes_title = ParagraphStyle('NotesTitle', fontName=FONT_BOLD_NAME, fontSize=12, leading=16, textColor=colors.HexColor("#182b49"), alignment=2)
    style_notes_content = ParagraphStyle('NotesContent', fontName=FONT_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#1e293b"), alignment=2)
    style_sec_header = ParagraphStyle('SecHeader', fontName=FONT_BOLD_NAME, fontSize=11, leading=14, textColor=colors.HexColor("#0f172a"), alignment=2)
    style_caption = ParagraphStyle('Caption', fontName=FONT_NAME, fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"), alignment=1)
    style_table_header = ParagraphStyle('TableHeader', fontName=FONT_BOLD_NAME, fontSize=9.5, leading=13, textColor=colors.HexColor("#0f172a"), alignment=1)

    story = []

    title_line1 = heb("ד.ד מהנדסים בע''מ") + " - D.D. ENGINEERS LTD"
    title_line2 = heb(f'דו"ח פיקוח ואכיפת הסדרי תנועה מס\' {report_num}')
    title_line3 = heb("מסמך פיקוח שטח רשמי")

    header_data = [
        [Paragraph(title_line1, style_header_title)],
        [Paragraph(title_line2, style_header_sub)],
        [Paragraph(title_line3, style_header_small)]
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

    story.append(Paragraph(heb(f"שם האתר / פרויקט: {site_title}"), style_proj_title))
    story.append(Spacer(1, 0.2 * cm))

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

    # --- הוספת סקיצת רכבת קלה ---
    if lr_svg and lr_arm_settings:
        story.append(Paragraph(heb('סקיצה הנדסית - צומת רכבת קלה (רק"ל):'), style_notes_title))
        story.append(Spacer(1, 0.2 * cm))

        try:
            svg_bytes = io.BytesIO(lr_svg.encode('utf-8'))
            drawing = svg2rlg(svg_bytes)
            drawing.width = 380
            drawing.height = 380
            drawing.scale(380/500, 380/500)
            story.append(drawing)
            story.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass

        table_data = [[
            Paragraph(heb("הולכי רגל"), style_table_header),
            Paragraph(heb("מעבר חצייה"), style_table_header),
            Paragraph(heb("מיקום עמוד"), style_table_header),
            Paragraph(heb("סוג עמוד"), style_table_header),
            Paragraph(heb('פנס רק"ל'), style_table_header),
            Paragraph(heb('פ"ת'), style_table_header),
            Paragraph(heb("זרוע"), style_table_header)
        ]]

        for d, data in lr_arm_settings.items():
            pole_str = data["pole_type"]
            if data["traffic_dir"] == "דו-כיווני (לשני הצדדים)":
                pole_str += f" / {data['pole_type_opp']}"

            table_data.append([
                Paragraph(heb(data["pedestrian"]), style_caption),
                Paragraph(heb("כן" if data["crosswalk"] else "לא"), style_caption),
                Paragraph(heb(data["pole_pos"]), style_caption),
                Paragraph(heb(pole_str), style_caption),
                Paragraph(heb(data["light_rail"]), style_caption),
                Paragraph(heb(data["traffic_light"]), style_caption),
                Paragraph(heb(d), style_caption)
            ])

        lr_table = Table(table_data, colWidths=[2.5 * cm, 2.0 * cm, 2.5 * cm, 3.0 * cm, 2.8 * cm, 2.7 * cm, 2.5 * cm])
        lr_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94a3b8')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(lr_table)
        story.append(Spacer(1, 0.5 * cm))

    # --- הוספת תמונות ---
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
                img.save(img_temp, format="JPEG", quality=90)
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


# --- UI ---

st.markdown("""
    <style>
    .stApp { background-color: #e2e8f0; }
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
    .main-header h1 { color: #ffffff !important; font-size: 26px !important; font-weight: 800 !important; margin-bottom: 6px !important; }
    .main-header p { color: #cbd5e1 !important; font-size: 15px !important; margin: 0 !important; }
    .section-title { color: #0f172a; font-size: 18px; font-weight: 800; border-right: 5px solid #2563eb; padding-right: 12px; margin-top: 25px; margin-bottom: 15px; }
    .stButton>button { background-color: #0f172a !important; color: white !important; font-size: 18px !important; font-weight: bold !important; padding: 14px 28px !important; border-radius: 6px !important; border: none !important; }
    .stButton>button:hover { background-color: #2563eb !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="main-header">
        <h1>🚦 ד.ד מהנדסים בע''מ</h1>
        <p>מערכת מקצועית להפקת דו"חות פיקוח הסדרי תנועה</p>
    </div>
""", unsafe_allow_html=True)

current_num = get_next_report_number()
st.info(f'📌 **מספר הדו"ח המיועד להפקה הבאה:** #{current_num}')

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
        'עבודות רכבת קלה (רק"ל)',
        "החלפת מנגנון",
        "החלפת מעבד (CPU)", 
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

# --- מחולל סקיצת רכבת קלה ---
full_svg = None
arm_settings = {}

if selected_work_type == 'עבודות רכבת קלה (רק"ל)':
    st.markdown('<div class="section-title">🚃 מחולל סקיצה דינמי - רכבת קלה</div>', unsafe_allow_html=True)
    
    toggle_sketch = st.checkbox('הצג מחולל סקיצת צומת רק"ל', value=True)

    if toggle_sketch:
        col_sketch_l, col_sketch_r = st.columns([1, 1])

        with col_sketch_l:
            junction_type = st.selectbox("סוג מבנה הצומת", ["(זרועות 4) X צומת", "(זרועות 3) T צומת"])
            has_temp_cable = st.checkbox("קיימת כבילה עילית זמנית (הזנה עילית)", value=True)

            directions = ["צפון", "דרום", "מזרח", "מערב"] if "4" in junction_type else ["צפון", "דרום", "מזרח"]

            for d in directions:
                with st.expander(f"🚦 הגדרות זרוע {d}"):
                    traffic_light = st.selectbox(f'פ"ת לרכב ({d})', ["קיים / ללא שינוי", "חדש", "מבוטל", "ללא"], key=f"tl_{d}")
                    traffic_dir = st.selectbox(f'כיוון פ"ת ({d})', ["נכנס לצומת", "יוצא מהצומת", "דו-כיווני (לשני הצדדים)"], key=f"tdir_{d}")
                    pole_type = st.selectbox(f"סוג עמוד ראשי ({d})", ["עמוד מתכת", "עמוד עץ", "ללא עמוד"], key=f"pole_{d}")
                    
                    pole_type_opp = "ללא עמוד"
                    if traffic_dir == "דו-כיווני (לשני הצדדים)":
                        pole_type_opp = st.selectbox(f"סוג עמוד נגדי בצומת ({d})", ["עמוד מתכת", "עמוד עץ", "ללא עמוד"], key=f"pole_opp_{d}")

                    pole_pos = st.selectbox(f"מיקום עמוד ({d})", ["צד ימין", "צד שמאל", "אי תנועה מרכזי"], key=f"pos_{d}")
                    light_rail = st.selectbox(f"פנס רכבת קלה ({d})", ["ללא", "קיים / ללא שינוי", "חדש", "מבוטל"], key=f"lr_{d}")
                    pedestrian = st.selectbox(f"פנס הולכי רגל ({d})", ["קיים / ללא שינוי", "חדש", "מבוטל", "ללא"], key=f"ped_{d}")
                    crosswalk = st.checkbox(f"מעבר חצייה ({d})", value=True, key=f"cw_{d}")

                    arm_settings[d] = {
                        "traffic_light": traffic_light,
                        "traffic_dir": traffic_dir,
                        "pole_type": pole_type,
                        "pole_type_opp": pole_type_opp,
                        "pole_pos": pole_pos,
                        "light_rail": light_rail,
                        "pedestrian": pedestrian,
                        "crosswalk": crosswalk
                    }

        # בנאי ה-SVG
        svg_elements = []
        svg_elements.append('<rect width="500" height="500" fill="#1e1e24" />')
        svg_elements.append('<rect x="180" y="0" width="140" height="500" fill="#2c2c34" />')
        svg_elements.append('<rect x="0" y="180" width="500" height="140" fill="#2c2c34" />')
        
        # מסילת רק"ל
        svg_elements.append('<rect x="0" y="240" width="500" height="20" fill="#4a4a5a" />')
        svg_elements.append('<line x1="0" y1="245" x2="500" y2="245" stroke="#a6a6b8" stroke-width="2" />')
        svg_elements.append('<line x1="0" y1="255" x2="500" y2="255" stroke="#a6a6b8" stroke-width="2" />')

        # נתיבים
        svg_elements.append('<line x1="250" y1="0" x2="250" y2="180" stroke="#f1c40f" stroke-width="2" stroke-dasharray="8,8" />')
        svg_elements.append('<line x1="250" y1="320" x2="250" y2="500" stroke="#f1c40f" stroke-width="2" stroke-dasharray="8,8" />')

        if has_temp_cable:
            svg_elements.append('<line x1="30" y1="30" x2="470" y2="470" stroke="#e67e22" stroke-width="3" stroke-dasharray="6,6" />')

        arm_coords = {
            "צפון": {"cw_x": 180, "cw_y": 150, "cw_w": 140, "cw_h": 20, "right_x": 295, "left_x": 205, "y": 135, "ped_left_x": 190, "ped_right_x": 310, "ped_y": 160},
            "דרום": {"cw_x": 180, "cw_y": 330, "cw_w": 140, "cw_h": 20, "right_x": 205, "left_x": 295, "y": 365, "ped_left_x": 190, "ped_right_x": 310, "ped_y": 340},
            "מזרח": {"cw_x": 330, "cw_y": 180, "cw_w": 20, "cw_h": 140, "right_x": 365, "left_x": 365, "y_right": 195, "y_left": 305, "ped_x": 340, "ped_top_y": 190, "ped_bot_y": 310},
            "מערב": {"cw_x": 150, "cw_y": 180, "cw_w": 20, "cw_h": 140, "right_x": 135, "left_x": 135, "y_right": 305, "y_left": 195, "ped_x": 160, "ped_top_y": 190, "ped_bot_y": 310}
        }

        for d, data in arm_settings.items():
            ac = arm_coords[d]

            if data["crosswalk"]:
                svg_elements.append(f'<rect x="{ac["cw_x"]}" y="{ac["cw_y"]}" width="{ac["cw_w"]}" height="{ac["cw_h"]}" fill="#1e1e24" />')
                if d in ["צפון", "דרום"]:
                    for i in range(0, ac["cw_w"], 14):
                        svg_elements.append(f'<rect x="{ac["cw_x"] + i}" y="{ac["cw_y"]}" width="8" height="{ac["cw_h"]}" fill="#ffffff" />')
                else:
                    for i in range(0, ac["cw_h"], 14):
                        svg_elements.append(f'<rect x="{ac["cw_x"]}" y="{ac["cw_y"] + i}" width="{ac["cw_w"]}" height="8" fill="#ffffff" />')

            if d in ["צפון", "דרום"]:
                pos_x = ac["right_x"] if data["pole_pos"] == "צד ימין" else (ac["left_x"] if data["pole_pos"] == "צד שמאל" else 250)
                pos_y = ac["y"]
                opp_x = ac["left_x"] if data["pole_pos"] == "צד ימין" else ac["right_x"]
                opp_y = pos_y
            else:
                pos_x = ac["right_x"]
                pos_y = ac["y_right"] if data["pole_pos"] == "צד ימין" else (ac["y_left"] if data["pole_pos"] == "צד שמאל" else 250)
                opp_x = pos_x
                opp_y = ac["y_left"] if data["pole_pos"] == "צד ימין" else ac["y_right"]

            # עמוד ראשי
            if data["pole_type"] == "עמוד מתכת":
                svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y}" r="6" fill="#7f8c8d" stroke="#ffffff" stroke-width="1.5" />')
            elif data["pole_type"] == "עמוד עץ":
                svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y}" r="6" fill="#8d6e63" stroke="#5d4037" stroke-width="1.5" />')

            # עמוד נגדי במידה ודו-כיווני
            if data["traffic_dir"] == "דו-כיווני (לשני הצדדים)":
                if data["pole_type_opp"] == "עמוד מתכת":
                    svg_elements.append(f'<circle cx="{opp_x}" cy="{opp_y}" r="6" fill="#7f8c8d" stroke="#ffffff" stroke-width="1.5" />')
                elif data["pole_type_opp"] == "עמוד עץ":
                    svg_elements.append(f'<circle cx="{opp_x}" cy="{opp_y}" r="6" fill="#8d6e63" stroke="#5d4037" stroke-width="1.5" />')

            # פ"ת ראשי
            if data["traffic_light"] != "ללא":
                tl_color = "#00ff66" if data["traffic_light"] == "חדש" else "#2ecc71"
                svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y-10}" r="6" fill="{tl_color}" stroke="#ffffff" stroke-width="0.5" />')

                if data["traffic_dir"] == "דו-כיווני (לשני הצדדים)":
                    svg_elements.append(f'<circle cx="{opp_x}" cy="{opp_y-10}" r="6" fill="{tl_color}" stroke="#ffffff" stroke-width="0.5" />')

                if data["traffic_light"] == "מבוטל":
                    svg_elements.append(f'<line x1="{pos_x-8}" y1="{pos_y-18}" x2="{pos_x+8}" y2="{pos_y-2}" stroke="#e74c3c" stroke-width="3" />')
                    svg_elements.append(f'<line x1="{pos_x+8}" y1="{pos_y-18}" x2="{pos_x-8}" y2="{pos_y-2}" stroke="#e74c3c" stroke-width="3" />')

            # פנס רק"ל
            if data["light_rail"] != "ללא":
                lr_color = "#00d2ff" if data["light_rail"] != "מבוטל" else "#7f8c8d"
                svg_elements.append(f'<rect x="{pos_x-6}" y="{pos_y-24}" width="12" height="12" fill="{lr_color}" stroke="#ffffff" stroke-width="1" />')
                if data["light_rail"] == "מבוטל":
                    svg_elements.append(f'<line x1="{pos_x-6}" y1="{pos_y-24}" x2="{pos_x+6}" y2="{pos_y-12}" stroke="#e74c3c" stroke-width="2" />')
                    svg_elements.append(f'<line x1="{pos_x+6}" y1="{pos_y-24}" x2="{pos_x-6}" y2="{pos_y-12}" stroke="#e74c3c" stroke-width="2" />')

            # פנס הולכי רגל
            if data["pedestrian"] != "ללא":
                ped_color = "#9b59b6" if data["pedestrian"] in ["קיים / ללא שינוי", "חדש"] else "#95a5a6"
                if d in ["צפון", "דרום"]:
                    svg_elements.append(f'<rect x="{ac["ped_left_x"]}" y="{ac["ped_y"]}" width="8" height="8" fill="{ped_color}" stroke="#ffffff" stroke-width="1" />')
                    svg_elements.append(f'<rect x="{ac["ped_right_x"]}" y="{ac["ped_y"]}" width="8" height="8" fill="{ped_color}" stroke="#ffffff" stroke-width="1" />')
                else:
                    svg_elements.append(f'<rect x="{ac["ped_x"]}" y="{ac["ped_top_y"]}" width="8" height="8" fill="{ped_color}" stroke="#ffffff" stroke-width="1" />')
                    svg_elements.append(f'<rect x="{ac["ped_x"]}" y="{ac["ped_bot_y"]}" width="8" height="8" fill="{ped_color}" stroke="#ffffff" stroke-width="1" />')

        # מקרא מפורט ומעוצב עם כיוון טקסט ישר בעברית (RTL)
        svg_elements.append('<rect x="10" y="360" width="165" height="130" fill="#111116" rx="6" stroke="#4a5568" stroke-width="1" opacity="0.95"/>')
        
        legend_items = [
            ('<circle cx="22" cy="375" r="4" fill="#2ecc71" />', 'פ"ת קיים', 379),
            ('<circle cx="22" cy="390" r="4" fill="#00ff66" stroke="#fff" stroke-width="0.5" />', 'פ"ת חדש', 394),
            ('<rect x="18" y="401" width="8" height="8" fill="#00d2ff" />', 'פנס רק"ל', 408),
            ('<rect x="18" y="416" width="8" height="8" fill="#9b59b6" />', "הולכי רגל", 423),
            ('<circle cx="22" cy="433" r="4" fill="#7f8c8d" stroke="#fff" stroke-width="1" />', "עמוד מתכת", 437),
            ('<circle cx="22" cy="448" r="4" fill="#8d6e63" stroke="#5d4037" stroke-width="1" />', "עמוד עץ", 452),
            ('<line x1="16" y1="463" x2="28" y2="463" stroke="#e67e22" stroke-width="2" stroke-dasharray="2,2" />', "כבילה עילית", 467)
        ]

        for icon, txt, text_y in legend_items:
            svg_elements.append(icon)
            svg_elements.append(f'<text x="36" y="{text_y}" fill="#ffffff" font-family="Arial, sans-serif" font-size="11" font-weight="bold" direction="rtl" xml:lang="he">{txt}</text>')

        full_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">{"".join(svg_elements)}</svg>'

        with col_sketch_r:
            st.markdown("##### 🎨 תצוגה מקדימה של סקיצת הרק\"ל")
            st.components.v1.html(full_svg, height=520)

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

col_top1, col_top2 = st.columns(2)
with col_top1:
    before_files, before_caps = render_upload_section("1️⃣ תמונות - לפני הסדר (מצב קיים)", "before")
with col_top2:
    after_files, after_caps = render_upload_section("2️⃣ תמונות - אחרי הסדר (מצב סופי)", "after")

st.markdown("<hr style='border: 0.5px dashed #cbd5e1; margin: 15px 0;'>", unsafe_allow_html=True)
st.markdown("##### ➕ תמונות לפי קטגוריות מקצועיות (רשות)")

col_a, col_b = st.columns(2)
with col_a:
    mechanism_files, mechanism_caps = render_upload_section("תמונות - החלפת מנגנון", "mechanism")
    cpu_files, cpu_caps = render_upload_section("תמונות - החלפת מעבד (CPU)", "cpu")
    cameras_files, cameras_caps = render_upload_section("תמונות - התקנת מצלמות", "cameras")
    plan_files, plan_caps = render_upload_section("צילום תוכנית / שרטוט", "plan")

with col_b:
    detectors_files, detectors_caps = render_upload_section("תמונות - חריצת גלאים", "detectors")
    ups_files, ups_caps = render_upload_section("תמונות - התקנת עמדת UPS", "ups")
    misc_files, misc_caps = render_upload_section("תמונות - שונות / נספחים", "misc")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("🚀 הפק דו\"ח מפקח PDF", use_container_width=True):
    if not site_name or not junction_name or not inspector_name:
        st.error("⚠️ אנא מלא את שם האתר, שם הצומת ושם המפקח.")
    else:
        report_num = get_next_report_number()
        
        success = append_to_google_sheets(
            report_num=report_num,
            date_str=str(date_val),
            site_title=site_name,
            junction_name=junction_name,
            inspector=inspector_name,
            license_no=license_no,
            permit_no=permit_no,
            work_type=final_work_type,
            notes=notes
        )
        if success:
            st.success(f'הנתונים נשמרו בהצלחה ב-Google Sheets (דו"ח מס\' {report_num})!')   
            
            photo_sections = [
                {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files, "captions": before_caps},
                {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files, "captions": after_caps},
                {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files, "captions": mechanism_caps},
                {"title_he": "החלפת מעבד (CPU) / רכיב עיבוד", "files": cpu_files, "captions": cpu_caps},
                {"title_he": "חריצת גלאים", "files": detectors_files, "captions": detectors_caps},
                {"title_he": "התקנת מצלמות", "files": cameras_files, "captions": cameras_caps},
                {"title_he": "התקנת עמדת UPS", "files": ups_files, "captions": ups_caps},
                {"title_he": "צילום תוכנית / שרטוט", "files": plan_files, "captions": plan_caps},
                {"title_he": "תמונות נוספות / נספחים", "files": misc_files, "captions": misc_caps}
            ]

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
                photo_sections=photo_sections,
                lr_svg=full_svg,
                lr_arm_settings=arm_settings
            )

            st.download_button(
                label="📥 הורד דו\"ח PDF מושלם",
                data=pdf_bytes,
                file_name=f"DD_Engineers_Report_{report_num}_{date_val}.pdf",
                mime="application/pdf"
            )
