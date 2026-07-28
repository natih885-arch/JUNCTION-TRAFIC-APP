import base64
import io
import streamlit as st
from PIL import Image
from weasyprint import HTML

# הגדרת תצורת עמוד ב-Streamlit
st.set_page_config(page_title="דו\"ח מפקח הסדר תנועה - ד.ד מהנדסים בע''מ", page_icon="🚦", layout="centered")

def image_to_base64(uploaded_file):
    """ממיר תמונה שהועלתה למחרוזת Base64 כדי להטמיע ב-HTML"""
    try:
        img = Image.open(uploaded_file)
        img = img.convert("RGB")
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        return None

def generate_pdf_html(site_title, junction_name, inspector, license_no, date_str, work_type, notes, photo_sections):
    
    # בניית גלריית התמונות ב-HTML
    photos_html = ""
    for section in photo_sections:
        files = section.get("files")
        if files:
            photos_html += f"""
            <div class="section-title">{section['title_he']}</div>
            <div class="photo-grid">
            """
            for i, f in enumerate(files):
                b64_img = image_to_base64(f)
                if b64_img:
                    photos_html += f"""
                    <div class="photo-card">
                        <img src="{b64_img}" alt="תמונה">
                        <div class="photo-caption">תמונה #{i+1}</div>
                    </div>
                    """
            photos_html += "</div>"

    if not photos_html:
        photos_html = "<p style='color: #666;'>לא צורפו תמונות לדו\"ח זה.</p>"

    # תבנית ה-HTML המלאה לעיצוב ה-PDF
    html_content = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="he">
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 12mm 15mm 15mm 15mm;
                @bottom-center {{
                    content: "כל הזכויות שמורות לנתנאל עוז הררי © | ד.ד מהנדסים בע''מ";
                    font-family: 'Arial', 'Segoe UI', sans-serif;
                    font-size: 8pt;
                    color: #777777;
                }}
            }}
            
            body {{
                font-family: 'Arial', 'Segoe UI', sans-serif;
                margin: 0;
                padding: 0;
                color: #222222;
                direction: rtl;
            }}

            /* כותרת מודרנית */
            .header-banner {{
                background-color: #182b49;
                color: #ffffff;
                text-align: center;
                padding: 15px 10px;
                margin-bottom: 20px;
                border-radius: 4px;
            }}

            .header-banner h1 {{
                margin: 0;
                font-size: 18pt;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}

            .header-banner h2 {{
                margin: 4px 0 0 0;
                font-size: 13pt;
                font-weight: normal;
                color: #e2e8f0;
            }}

            .header-banner p {{
                margin: 3px 0 0 0;
                font-size: 8pt;
                color: #cbd5e1;
            }}

            /* כותרת פרויקט */
            .project-title {{
                font-size: 14pt;
                font-weight: bold;
                color: #182b49;
                border-bottom: 2px solid #182b49;
                padding-bottom: 4px;
                margin-bottom: 12px;
            }}

            /* טבלת פרטים */
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
            }}

            .info-table td {{
                width: 50%;
                padding: 8px 12px;
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                font-size: 10pt;
            }}

            .info-table td span.label {{
                font-weight: bold;
                color: #0f172a;
            }}

            /* תיבת הערות */
            .notes-box {{
                border: 1px solid #cbd5e1;
                background-color: #ffffff;
                padding: 10px 12px;
                border-radius: 4px;
                margin-bottom: 20px;
                min-height: 50px;
                font-size: 10pt;
                line-height: 1.4;
            }}

            .notes-title {{
                font-weight: bold;
                color: #182b49;
                font-size: 11pt;
                margin-bottom: 6px;
            }}

            /* גלריית תמונות ב-Grid */
            .section-title {{
                background-color: #e2e8f0;
                color: #0f172a;
                font-weight: bold;
                padding: 6px 10px;
                font-size: 11pt;
                margin-top: 15px;
                margin-bottom: 10px;
                border-right: 4px solid #182b49;
                page-break-after: avoid;
            }}

            .photo-grid {{
                display: table;
                width: 100%;
                margin-bottom: 10px;
                page-break-inside: avoid;
            }}

            .photo-card {{
                display: table-cell;
                width: 48%;
                padding: 1%;
                vertical-align: top;
                box-sizing: border-box;
                text-align: center;
            }}

            .photo-card img {{
                width: 100%;
                max-height: 200px;
                object-fit: cover;
                border: 1px solid #cbd5e1;
                border-radius: 4px;
            }}

            .photo-caption {{
                font-size: 8.5pt;
                color: #475569;
                margin-top: 4px;
            }}

            /* חתימה */
            .signature-container {{
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #cbd5e1;
                page-break-inside: avoid;
            }}

            .signature-table {{
                width: 100%;
                font-size: 10pt;
            }}

            .signature-table td {{
                padding: 4px 0;
            }}
        </style>
    </head>
    <body>

        <!-- כותרת ראשית -->
        <div class="header-banner">
            <h1>ד.ד מהנדסים בע''מ - D.D. ENGINEERS LTD</h1>
            <h2>דו"ח פיקוח ואכיפת הסדרי תנועה</h2>
            <p>מסמך פיקוח שטח רשמי</p>
        </div>

        <!-- שם הפרויקט -->
        <div class="project-title">
            שם האתר / פרויקט: {site_title}
        </div>

        <!-- טבלת פרטי בדיקה -->
        <table class="info-table">
            <tr>
                <td><span class="label">צומת / מיקום:</span> {junction_name}</td>
                <td><span class="label">מפקח:</span> {inspector} {f'(רישיון: {license_no})' if license_no else ''}</td>
            </tr>
            <tr>
                <td><span class="label">תאריך:</span> {date_str}</td>
                <td><span class="label">סוג עבודה:</span> {work_type}</td>
            </tr>
        </table>

        <!-- הערות מפקח -->
        <div class="notes-title">הערות, ממצאים והנחיות מפקח:</div>
        <div class="notes-box">
            {notes.replace('\n', '<br>') if notes.strip() else 'לא נרשמו הערות נוספות.'}
        </div>

        <!-- גלריית תמונות -->
        {photos_html}

        <!-- חתימה -->
        <div class="signature-container">
            <table class="signature-table">
                <tr>
                    <td style="width: 50%;"><strong>שם המפקח:</strong> {inspector} {f'| מס\' רישיון: {license_no}' if license_no else ''}</td>
                    <td style="width: 50%; text-align: left;"><strong>תאריך:</strong> {date_str}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding-top: 15px;"><strong>חתימה:</strong> _______________________</td>
                </tr>
            </table>
        </div>

    </body>
    </html>
    """
    
    # המרת HTML ל-PDF באמצעות WeasyPrint
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


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
            {"title_he": "מצב קיים בשטח (לפני העבודות)", "files": before_files},
            {"title_he": "הסדר תנועה סופי (אחרי העבודות)", "files": after_files},
            {"title_he": "החלפת מנגנון / בקר תנועה", "files": mechanism_files},
            {"title_he": "חריצת גלאים", "files": detectors_files},
            {"title_he": "התקנת מצלמות תנועה", "files": cameras_files},
            {"title_he": "תוכנית הסדר תנועה מאושרת", "files": plan_files},
            {"title_he": "נספחים / תמונות שונות", "files": misc_files}
        ]
        
        with st.spinner("מפיק דו\"ח מפקח בעברית מושלמת..."):
            try:
                pdf_bytes = generate_pdf_html(
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
            except Exception as e:
                st.error(f"שגיאה בהפקת ה-PDF: {e}")

st.caption("© כל הזכויות שמורות לנתנאל עוז הררי (Netanel Oz Harary). אין לעשות שימוש או להפיץ ללא אישור בכתב.")
