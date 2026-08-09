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
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# =========================================================
# הגדרות כלליות
# =========================================================

st.set_page_config(
    page_title='דו"ח מפקח הסדר תנועה - ד.ד מהנדסים בע"מ',
    page_icon="🚦",
    layout="centered"
)

# המספר הראשון של המערכת
START_NUMBER = 100

# שמות עמודות Google Sheets
SHEET_HEADERS = [
    "מספר דו\"ח",
    "תאריך",
    "שם האתר / פרויקט",
    "צומת / מיקום",
    "מפקח",
    "מספר רישיון",
    "מספר היתר",
    "סוג עבודה",
    "הערות",
    "סטטוס",
    "שם קובץ PDF",
    "זמן יצירה"
]


# =========================================================
# GOOGLE SHEETS
# =========================================================

@st.cache_resource
def get_google_sheet():
    """
    חיבור ל-Google Sheets.
    החיבור נשמר בזיכרון של Streamlit כל עוד האפליקציה פעילה.
    """

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = dict(st.secrets["gcp_service_account"])

    credentials = Credentials.from_service_account_info(
        creds_dict,
        scopes=scope
    )

    client = gspread.authorize(credentials)

    sheet_url = st.secrets["sheets"]["spreadsheet_url"]

    spreadsheet = client.open_by_url(sheet_url)
    sheet = spreadsheet.sheet1

    initialize_sheet(sheet)

    return sheet


def initialize_sheet(sheet):
    """
    אם הגיליון ריק לחלוטין - יוצר את שורת הכותרות.
    אם כבר קיימות כותרות - לא משנה אותן.
    """

    try:
        first_row = sheet.row_values(1)

        if not first_row:
            sheet.update(
                "A1:L1",
                [SHEET_HEADERS]
            )

        elif first_row != SHEET_HEADERS:
            # אם יש גיליון ישן/מבנה אחר,
            # אנחנו לא מוחקים מידע אוטומטית.
            pass

    except Exception as e:
        raise Exception(f"שגיאה באתחול Google Sheets: {e}")


def get_next_report_number(sheet):
    """
    מוצא את מספר הדוח הגבוה ביותר בגיליון
    ומחזיר את המספר הבא.

    אם אין דוחות -> מתחיל ב-100.
    """

    try:
        values = sheet.col_values(1)

        numbers = []

        for value in values[1:]:
            try:
                number = int(str(value).strip())

                if number >= START_NUMBER:
                    numbers.append(number)

            except (ValueError, TypeError):
                continue

        if not numbers:
            return START_NUMBER

        return max(numbers) + 1

    except Exception as e:
        raise Exception(f"שגיאה בקריאת מספרי הדוחות: {e}")


def append_report_to_sheet(
    sheet,
    report_num,
    date_str,
    site_title,
    junction_name,
    inspector,
    license_no,
    permit_no,
    work_type,
    notes,
    pdf_filename,
    status="הופק בהצלחה"
):
    """
    שומר דוח חדש ב-Google Sheets.
    """

    from datetime import datetime

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_row = [
        str(report_num),
        str(date_str),
        str(site_title),
        str(junction_name),
        str(inspector),
        str(license_no),
        str(permit_no),
        str(work_type),
        str(notes),
        str(status),
        str(pdf_filename),
        created_at
    ]

    sheet.append_row(
        new_row,
        value_input_option="USER_ENTERED"
    )


# =========================================================
# גופנים עבריים
# =========================================================

FONT_NAME = "HebrewFont"
FONT_BOLD_NAME = "HebrewFont-Bold"


def setup_hebrew_fonts():

    font_reg_path = "Rubik-Regular.ttf"
    font_bold_path = "Rubik-Bold.ttf"

    url_reg = (
        "https://raw.githubusercontent.com/google/fonts/main/"
        "ofl/rubik/Rubik%5Bwght%5D.ttf"
    )

    url_bold = (
        "https://raw.githubusercontent.com/google/fonts/main/"
        "ofl/rubik/Rubik-Bold.ttf"
    )

    # Regular
    if not os.path.exists(font_reg_path):

        try:

            req = urllib.request.Request(
                url_reg,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req) as response:
                with open(font_reg_path, "wb") as out_file:
                    out_file.write(response.read())

        except Exception:
            pass

    # Bold
    if not os.path.exists(font_bold_path):

        try:

            req = urllib.request.Request(
                url_bold,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req) as response:
                with open(font_bold_path, "wb") as out_file:
                    out_file.write(response.read())

        except Exception:
            pass

    try:

        if os.path.exists(font_reg_path):

            pdfmetrics.registerFont(
                TTFont(
                    FONT_NAME,
                    font_reg_path
                )
            )

        if os.path.exists(font_bold_path):

            pdfmetrics.registerFont(
                TTFont(
                    FONT_BOLD_NAME,
                    font_bold_path
                )
            )

        elif os.path.exists(font_reg_path):

            pdfmetrics.registerFont(
                TTFont(
                    FONT_BOLD_NAME,
                    font_reg_path
                )
            )

    except Exception:
        pass


setup_hebrew_fonts()


# =========================================================
# עברית / RTL
# =========================================================

def heb(text):

    if text is None:
        return ""

    text = str(text)

    if not text:
        return ""

    try:

        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)

        return bidi_text

    except Exception:

        return text


# =========================================================
# מספור עמודים ב-PDF
# =========================================================

class NumberedCanvas(canvas.Canvas):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self._saved_page_states = []

    def showPage(self):

        self._saved_page_states.append(
            dict(self.__dict__)
        )

        self._startPage()

    def save(self):

        num_pages = len(
            self._saved_page_states
        )

        for state in self._saved_page_states:

            self.__dict__.update(state)

            self.draw_page_number(
                num_pages
            )

            super().showPage()

        super().save()

    def draw_page_number(self, page_count):

        self.saveState()

        self.setFont(
            FONT_NAME,
            8
        )

        self.setFillColor(
            colors.HexColor("#666666")
        )

        footer_text = heb(
            f"כל הזכויות שמורות לנתנאל עוז הררי © | "
            f"נייד: 054-5520445 | "
            f"ד.ד מהנדסים בע\"מ | "
            f"עמוד {self._pageNumber} מתוך {page_count}"
        )

        self.drawCentredString(
            A4[0] / 2.0,
            1 * cm,
            footer_text
        )

        self.restoreState()


# =========================================================
# יצירת PDF
# =========================================================

def generate_pdf(
    report_num,
    site_title,
    junction_name,
    inspector,
    license_no,
    permit_no,
    date_str,
    work_type,
    notes,
    photo_sections
):

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

    # -----------------------------------------------------
    # סגנונות
    # -----------------------------------------------------

    style_header_title = ParagraphStyle(
        "HeaderTitle",
        fontName=FONT_BOLD_NAME,
        fontSize=16,
        leading=20,
        textColor=colors.white,
        alignment=1
    )

    style_header_sub = ParagraphStyle(
        "HeaderSub",
        fontName=FONT_BOLD_NAME,
        fontSize=13,
        leading=17,
        textColor=colors.white,
        alignment=1
    )

    style_header_small = ParagraphStyle(
        "HeaderSmall",
        fontName=FONT_NAME,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#e2e8f0"),
        alignment=1
    )

    style_proj_title = ParagraphStyle(
        "ProjTitle",
        fontName=FONT_BOLD_NAME,
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#182b49"),
        alignment=2
    )

    style_cell_label = ParagraphStyle(
        "CellLabel",
        fontName=FONT_BOLD_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        alignment=2
    )

    style_notes_title = ParagraphStyle(
        "NotesTitle",
        fontName=FONT_BOLD_NAME,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#182b49"),
        alignment=2
    )

    style_notes_content = ParagraphStyle(
        "NotesContent",
        fontName=FONT_NAME,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        alignment=2
    )

    style_sec_header = ParagraphStyle(
        "SecHeader",
        fontName=FONT_BOLD_NAME,
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
        alignment=2
    )

    style_caption = ParagraphStyle(
        "Caption",
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    story = []

    # -----------------------------------------------------
    # 1. כותרת
    # -----------------------------------------------------

    title_line1 = (
        heb("ד.ד מהנדסים בע\"מ")
        + " - D.D. ENGINEERS LTD"
    )

    title_line2 = heb(
        f'דו"ח פיקוח ואכיפת הסדרי תנועה מס\' {report_num}'
    )

    title_line3 = heb(
        "מסמך פיקוח שטח רשמי"
    )

    header_data = [
        [
            Paragraph(
                title_line1,
                style_header_title
            )
        ],
        [
            Paragraph(
                title_line2,
                style_header_sub
            )
        ],
        [
            Paragraph(
                title_line3,
                style_header_small
            )
        ]
    ]

    header_table = Table(
        header_data,
        colWidths=[18 * cm]
    )

    header_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#182b49")
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )

    story.append(header_table)

    story.append(
        Spacer(1, 0.4 * cm)
    )

    # -----------------------------------------------------
    # 2. שם פרויקט
    # -----------------------------------------------------

    story.append(
        Paragraph(
            heb(
                f"שם האתר / פרויקט: {site_title}"
            ),
            style_proj_title
        )
    )

    story.append(
        Spacer(1, 0.2 * cm)
    )

    # -----------------------------------------------------
    # 3. פרטי הדוח
    # -----------------------------------------------------

    insp_str = f"מפקח: {inspector}"

    if license_no and license_no.strip():

        insp_str += (
            f" (רישיון: {license_no.strip()})"
        )

    work_type_str = (
        f"סוג עבודה: {work_type}"
    )

    if permit_no and permit_no.strip():

        work_type_str += (
            f" | היתר: {permit_no.strip()}"
        )

    info_data = [
        [
            Paragraph(
                heb(insp_str),
                style_cell_label
            ),
            Paragraph(
                heb(
                    f"צומת / מיקום: {junction_name}"
                ),
                style_cell_label
            )
        ],
        [
            Paragraph(
                heb(work_type_str),
                style_cell_label
            ),
            Paragraph(
                heb(f"תאריך: {date_str}"),
                style_cell_label
            )
        ]
    ]

    info_table = Table(
        info_data,
        colWidths=[
            9 * cm,
            9 * cm
        ]
    )

    info_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#f1f5f9")
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#cbd5e1")
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )

    story.append(info_table)

    story.append(
        Spacer(1, 0.4 * cm)
    )

    # -----------------------------------------------------
    # 4. הערות
    # -----------------------------------------------------

    story.append(
        Paragraph(
            heb(
                "הערות, ממצאים והנחיות מפקח:"
            ),
            style_notes_title
        )
    )

    story.append(
        Spacer(1, 0.1 * cm)
    )

    notes_text = (
        notes.strip()
        if notes and notes.strip()
        else "לא נרשמו הערות נוספות."
    )

    notes_data = [
        [
            Paragraph(
                heb(notes_text),
                style_notes_content
            )
        ]
    ]

    notes_table = Table(
        notes_data,
        colWidths=[18 * cm]
    )

    notes_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.white
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#cbd5e1")
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                8
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )

    story.append(notes_table)

    story.append(
        Spacer(1, 0.5 * cm)
    )

    # -----------------------------------------------------
    # 5. תמונות
    # -----------------------------------------------------

    for section in photo_sections:

        files = section.get(
            "files"
        )

        captions = section.get(
            "captions",
            []
        )

        if not files:
            continue

        sec_title_data = [
            [
                Paragraph(
                    heb(section["title_he"]),
                    style_sec_header
                )
            ]
        ]

        sec_title_table = Table(
            sec_title_data,
            colWidths=[18 * cm]
        )

        sec_title_table.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#cbd5e1")
                ),
                (
                    "LINELEFT",
                    (0, 0),
                    (0, -1),
                    3,
                    colors.HexColor("#182b49")
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                )
            ])
        )

        photo_cells = []

        for i, f in enumerate(files):

            try:

                img = Image.open(f)

                img = img.convert("RGB")

                img_temp = io.BytesIO()

                img.save(
                    img_temp,
                    format="JPEG",
                    quality=90
                )

                img_temp.seek(0)

                rl_img = RLImage(
                    img_temp,
                    width=8.2 * cm,
                    height=5.5 * cm
                )

                if (
                    i < len(captions)
                    and captions[i]
                    and captions[i].strip()
                ):

                    custom_cap = captions[i].strip()

                else:

                    custom_cap = (
                        f"תמונה #{i + 1}"
                    )

                cap = Paragraph(
                    heb(custom_cap),
                    style_caption
                )

                cell_content = [
                    rl_img,
                    Spacer(1, 2),
                    cap
                ]

                photo_cells.append(
                    cell_content
                )

            except Exception:
                continue

        grid_rows = []

        for i in range(
            0,
            len(photo_cells),
            2
        ):

            if i + 1 < len(photo_cells):

                # RTL - תמונה ראשונה מימין
                grid_rows.append([
                    photo_cells[i + 1],
                    photo_cells[i]
                ])

            else:

                grid_rows.append([
                    "",
                    photo_cells[i]
                ])

        if grid_rows:

            grid_table = Table(
                grid_rows,
                colWidths=[
                    9 * cm,
                    9 * cm
                ]
            )

            grid_table.setStyle(
                TableStyle([
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
