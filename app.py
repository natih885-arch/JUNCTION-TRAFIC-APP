import io
import os
import urllib.request
import streamlit as st
import streamlit.components.v1 as components
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

# --- מחולל סקיצת צומת ורכבת קלה (SVG דינמי) ---
def generate_junction_svg(junction_type, has_overhead_cable, arm_settings):
    """
    מייצרת תרשים SVG דינמי של צומת עם מסילת רכבת קלה, פנסי תנועה, פנסי הולכי רגל משני הצדדים, פנסי רק"ל ועמודים.
    """
    svg = """<svg width="500" height="500" viewBox="0 0 500 500" xmlns="http://www.w3.org/2000/svg" style="background-color: #1e293b; border-radius: 8px;">
    <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8"/>
        </marker>
    </defs>
    """
    
    # כבישים
    if junction_type == "צומת X (4 זרועות)":
        svg += '<rect x="0" y="200" width="500" height="100" fill="#334155" />'
        svg += '<rect x="200" y="0" width="100" height="500" fill="#334155" />'
    elif junction_type == "צומת T (3 זרועות - ללא צפון)":
        svg += '<rect x="0" y="200" width="500" height="100" fill="#334155" />'
        svg += '<rect x="200" y="200" width="100" height="300" fill="#334155" />'
    else: # קטע ישר
        svg += '<rect x="0" y="200" width="500" height="100" fill="#334155" />'

    # קווי נתיבים
    svg += '<line x1="0" y1="250" x2="500" y2="250" stroke="#94a3b8" stroke-dasharray="8,8" stroke-width="2"/>'
    if junction_type == "צומת X (4 זרועות)":
        svg += '<line x1="250" y1="0" x2="250" y2="500" stroke="#94a3b8" stroke-dasharray="8,8" stroke-width="2"/>'

    # מסילת רק"ל
    svg += '<rect x="0" y="240" width="500" height="20" fill="#475569" />'
    svg += '<line x1="0" y1="243" x2="500" y2="243" stroke="#cbd5e1" stroke-width="3"/>'
    svg += '<line x1="0" y1="257" x2="500" y2="257" stroke="#cbd5e1" stroke-width="3"/>'
    svg += '<text x="15" y="235" fill="#f59e0b" font-size="11" font-weight="bold">תוואי מסילת רק"ל</text>'

    # כבילה עילית
    if has_overhead_cable:
        svg += '<line x1="20" y1="50" x2="480" y2="450" stroke="#f97316" stroke-dasharray="6,4" stroke-width="2.5"/>'
        svg += '<text x="25" y="45" fill="#f97316" font-size="11" font-weight="bold">תוואי כבילה עילית זמנית</text>'

    anchors = {
        "צפון": {"x": 250, "y": 120, "dx": 0, "dy": -40},
        "דרום": {"x": 250, "y": 380, "dx": 0, "dy": 40},
        "מזרח": {"x": 380, "y": 250, "dx": 40, "dy": 0},
        "מערב": {"x": 120, "y": 250, "dx": -40, "dy": 0}
    }

    for arm_name, config in arm_settings.items():
        if arm_name not in anchors:
            continue
        
        ax = anchors[arm_name]["x"]
        ay = anchors[arm_name]["y"]
        dx = anchors[arm_name]["dx"]
        dy = anchors[arm_name]["dy"]

        # מעבר חצייה
        if config.get("crosswalk"):
            if arm_name in ["צפון", "דרום"]:
                svg += f'<rect x="{ax-45}" y="{ay}" width="90" height="15" fill="none" stroke="#ffffff" stroke-width="2"/>'
                for offset in range(-40, 50, 15):
                    svg += f'<rect x="{ax+offset}" y="{ay+2}" width="8" height="11" fill="#ffffff"/>'
                
                # פנסי הולכי רגל משני צידי המעבר
                ped_color = "#a855f7" if config.get("ped_light") != "מבוטל" else "#94a3b8"
                svg += f'<circle cx="{ax-52}" cy="{ay+7}" r="5" fill="{ped_color}" stroke="#ffffff" stroke-width="1"/>'
                svg += f'<circle cx="{ax+52}" cy="{ay+7}" r="5" fill="{ped_color}" stroke="#ffffff" stroke-width="1"/>'
            else:
                svg += f'<rect x="{ax}" y="{ay-45}" width="15" height="90" fill="none" stroke="#ffffff" stroke-width="2"/>'
                for offset in range(-40, 50, 15):
                    svg += f'<rect x="{ax+2}" y="{ay+offset}" width="11" height="8" fill="#ffffff"/>'
                
                ped_color = "#a855f7" if config.get("ped_light") != "מבוטל" else "#94a3b8"
                svg += f'<circle cx="{ax+7}" cy="{ay-52}" r="5" fill="{ped_color}" stroke="#ffffff" stroke-width="1"/>'
                svg += f'<circle cx="{ax+7}" cy="{ay+52}" r="5" fill="{ped_color}" stroke="#ffffff" stroke-width="1"/>'

        # עמוד ופנס תנועה לרכב
        pole_type = config.get("pole_type", "עמוד מתכת")
        pole_color = "#94a3b8" if pole_type == "עמוד מתכת" else "#b45309" # חום לעץ
        side_offset = -25 if config.get("pole_side") == "צד שמאל" else (25 if config.get("pole_side") == "צד ימין" else 0)
        
        px, py = ax + side_offset, ay
        
        status_car = config.get("car_light")
        if status_car != "ללא":
            # ציור עמוד
            svg += f'<circle cx="{px}" cy="{py}" r="6" fill="{pole_color}" stroke="#ffffff" stroke-width="1"/>'
            
            if status_car == "חדש / הוזז":
                svg += f'<circle cx="{px+dx}" cy="{py+dy}" r="8" fill="#22c55e" stroke="#ffffff" stroke-width="1.5"/>'
                svg += f'<line x1="{px}" y1="{py}" x2="{px+dx}" y2="{py+dy}" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)"/>'
                svg += f'<text x="{px+dx+10}" y="{py+dy+4}" fill="#22c55e" font-size="10">פנס תנועה הוזז ({pole_type})</text>'
            elif status_car == "מבוטל":
                svg += f'<line x1="{px-8}" y1="{py-8}" x2="{px+8}" y2="{py+8}" stroke="#ef4444" stroke-width="2.5"/>'
                svg += f'<line x1="{px-8}" y1="{py+8}" x2="{px+8}" y2="{py-8}" stroke="#ef4444" stroke-width="2.5"/>'
            else:
                svg += f'<circle cx="{px}" cy="{py}" r="7" fill="#22c55e" stroke="#ffffff" stroke-width="1"/>'

        # פנס רכבת קלה (רק"ל)
        status_lrt = config.get("lrt_light")
        if status_lrt != "ללא":
            lx, ly = px + 15, py + 15
            if status_lrt == "חדש / הוזז":
                svg += f'<rect x="{lx-6}" y="{ly-6}" width="12" height="12" fill="#ef4444" opacity="0.6"/>'
                svg += f'<rect x="{lx+dx-6}" y="{ly+dy-6}" width="12" height="12" fill="#3b82f6" stroke="#ffffff" stroke-width="1.5"/>'
                svg += f'<line x1="{lx}" y1="{ly}" x2="{lx+dx}" y2="{ly+dy}" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)"/>'
                svg += f'<text x="{lx+dx+12}" y="{ly+dy+4}" fill="#3b82f6" font-size="10">פנס רק"ל חדש</text>'
            elif status_lrt == "מבוטל":
                svg += f'<rect x="{lx-6}" y="{ly-6}" width="12" height="12" fill="#94a3b8"/>'
                svg += f'<line x1="{lx-8}" y1="{ly-8}" x2="{lx+8}" y2="{ly+8}" stroke="#ef4444" stroke-width="2.5"/>'
            else:
                svg += f'<rect x="{lx-6}" y="{ly-6}" width="12" height="12" fill="#3b82f6" stroke="#ffffff" stroke-width="1"/>'

    # מקרא
    svg += """
    <rect x="10" y="400" width="190" height="90" fill="#0f172a" rx="5" opacity="0.9"/>
    <circle cx="25" cy="415" r="5" fill="#22c55e"/>
    <text x="38" y="419" fill="#ffffff" font-size="9">פנס תנועה לרכב (ירוק)</text>
    <rect x="20" y="428" width="10" height="10" fill="#3b82f6"/>
    <text x="38" y="437" fill="#ffffff" font-size="9">פנס רק"ל (כחול)</text>
    <circle cx="25" cy="448" r="4" fill="#a855f7"/>
    <text x="38" y="451" fill="#ffffff" font-size="9">פנס הולכי רגל (סגול)</text>
    <line x1="20" y1="465" x2="32" y2="465" stroke="#38bdf8" stroke-width="2" marker-end="url(#arrow)"/>
    <text x="38" y="468" fill="#38bdf8" font-size="9">תוואי העתקת פנס / עמוד</text>
    <circle cx="25" cy="480" r="4" fill="#b45309"/>
    <text x="38" y="483" fill="#ffffff" font-size="9">עמוד עץ / זמני</text>
    """

    svg += "</svg>"
    return svg

def generate_pdf(report_num, site_title, junction_name, inspector, license_no, permit_no, date_str, work_type, notes, photo_sections, svg_code=None):
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

    story = []

    title_line1 = heb("ד.ד מהנדסים בע''מ") + " - D.D. ENGINEERS LTD"
    title_line2 = heb(f"דו\"ח פיקוח ואכיפת הסדרי תנועה מס' {report_num}")
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

    # שילוב סקיצת SVG במידה וקיימת
    if svg_code:
        try:
            svg_io = io.BytesIO(svg_code.encode('utf-8'))
            drawing = svg2rlg(svg_io)
            if drawing:
                drawing.width = 14 * cm
                drawing.height = 14 * cm
                drawing.scale(14 * cm / drawing.width, 14 * cm / drawing.height)
                
                sketch_title = Table([[Paragraph(heb("סקיצת צומת והעתקת פנסים/תשתיות:"), style_sec_header)]], colWidths=[18 * cm])
                sketch_title.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#cbd5e1")),
                    ('LINELEFT', (0,0), (0,-1), 3, colors.HexColor("#182b49")),
                    ('TOPPADDING', (0,0), (-1,-1), 5),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ]))
                story.append(KeepTogether([sketch_title, Spacer(1, 0.2 * cm), drawing]))
                story.append(Spacer(1, 0.5 * cm))
        except Exception:
            pass

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
        "רכבת קלה / העתקת פנסים ורמזורים",
        "הקמת צומת", 
        "הקמת צומת חדשה", 
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

# --- מחולל סקיצת צומת (אופציונלי / מופעל אוטומטית ברכבת קלה) ---
st.markdown('<div class="section-title">📐 מחולל סקיצת צומת והעתקת תשתיות</div>', unsafe_allow_html=True)

show_sketch = st.checkbox("פתח מחולל סקיצה דינמי לצומת", value=(selected_work_type == "רכבת קלה / העתקת פנסים ורמזורים"))

generated_svg_code = None

if show_sketch:
    st.caption("הגדר את פרטי הצומת והעתקת הפנסים. הסקיצה תיווצר בלייב ותצורף לדו\"ח ה-PDF ולענן.")
    
    sk_col1, sk_col2 = st.columns([1, 1])
    
    with sk_col1:
        j_type = st.selectbox("סוג מבנה הצומת", ["צומת X (4 זרועות)", "צומת T (3 זרועות - ללא צפון)", "קטע כביש ישר / חציית מסילה"])
        has_overhead = st.checkbox("קיימת כבילה עילית זמנית (הזנה עילית)", value=True)
        
        status_opts = ["ללא", "קיים / ללא שינוי", "חדש / הוזז", "מבוטל"]
        pole_types = ["עמוד מתכת", "עמוד עץ / זמני"]
        pole_sides = ["צד ימין", "צד שמאל", "מרכז"]
        
        arm_settings = {}
        arms = ["דרום", "צפון", "מזרח", "מערב"] if j_type == "צומת X (4 זרועות)" else ["דרום", "מזרח", "מערב"]
        
        for arm in arms:
            with st.expander(f"🚦 הגדרות זרוע {arm}", expanded=(arm == "דרום")):
                car_l = st.selectbox(f"פנס תנועה לרכב ({arm})", status_opts, index=2 if arm == "דרום" else 1, key=f"car_{arm}")
                pole_t = st.selectbox(f"סוג עמוד ({arm})", pole_types, index=1 if arm == "דרום" else 0, key=f"ptype_{arm}")
                pole_s = st.selectbox(f"מיקום עמוד ({arm})", pole_sides, index=0, key=f"pside_{arm}")
                lrt_l = st.selectbox(f"פנס רכבת קלה ({arm})", status_opts, index=2 if arm == "דרום" else 0, key=f"lrt_{arm}")
                ped_l = st.selectbox(f"פנס הולכי רגל ({arm})", status_opts, index=1, key=f"ped_{arm}")
                cross = st.checkbox(f"מעבר חצייה ({arm})", value=True, key=f"cross_{arm}")
                
                arm_settings[arm] = {
                    "car_light": car_l,
                    "pole_type": pole_t,
                    "pole_side": pole_s,
                    "lrt_light": lrt_l,
                    "ped_light": ped_l,
                    "crosswalk": cross
                }

    with sk_col2:
        st.markdown("##### 🎨 תצוגה מקדימה של הסקיצה (SVG)")
        generated_svg_code = generate_junction_svg(j_type, has_overhead, arm_settings)
        components.html(generated_svg_code, height=510)
        
        st.download_button(
            label="⬇️ הורד קובץ סקיצה (SVG) בלבד לענן",
            data=generated_svg_code,
            file_name=f"Sketch_{site_name}_{date_val}.svg",
            mime="image/svg+xml",
            use_container_width=True
        )

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
            st.success(f"הנתונים נשמרו בהצלחה ב-Google Sheets (דו\"ח מס' {report_num})!")   
            
            photo_sections = [
                {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files, "captions": before_caps},
                {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files, "captions": after_caps},
                {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files, "captions": mechanism_caps},
                {"title_he": "החלפת מעבד (CPU) / רכיב עיבוד", "files": cpu_files, "captions": cpu_caps},
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
                        photo_sections=photo_sections,
                        svg_code=generated_svg_code if show_sketch else None
                    )
                    
                    st.session_state['pdf_bytes'] = pdf_bytes
                    st.session_state['pdf_filename'] = f"DD_Engineers_Report_{report_num}_{date_val}.pdf"
                    st.success(f"✅ דו\"ח מס' {report_num} הופק בהצלחה!")
                except Exception as e:
                    st.error(f"שגיאה בהפקת ה-PDF: {e}")
        else:
            st.error("לא ניתן להפיק PDF משום שהשמירה ב-Google Sheets נכשלה.")

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
