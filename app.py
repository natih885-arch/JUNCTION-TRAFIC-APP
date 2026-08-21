import streamlit as st
import os
import io
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from svglib.svglib import svg2rlg

# הגדרות עמוד Streamlit
st.set_page_config(page_title="מערכת פיקוח דוחות צומת", layout="wide")

st.title("🚦 מערכת פיקוח וניהול דוחות צומת")

# --- טופס הגדרות הצומת ---
st.subheader("🛠️ הגדרות סקיצת הצומת")

toggle_sketch = st.checkbox("פתח מחולל סקיצה דינמי לצומת", value=True)

if toggle_sketch:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        junction_type = st.selectbox("סוג מבנה הצומת", ["(זרועות 4) X צומת", "(זרועות 3) T צומת"])
        has_temp_cable = st.checkbox("קיימת כבילה עילית זמנית (הזנה עילית)", value=True)

        arm_settings = {}
        directions = ["צפון", "דרום", "מזרח", "מערב"] if "4" in junction_type else ["צפון", "דרום", "מזרח"]

        for d in directions:
            with st.expander(f"🚦 הגדרות זרוע {d}"):
                traffic_light = st.selectbox(f"פנס תנועה לרכב ({d})", ["קיים / ללא שינוי", "מבוטל", "חדש", "ללא"], key=f"tl_{d}")
                traffic_dir = st.selectbox(f"כיוון פנס תנועה ({d})", ["נכנס לצומת", "יוצא מהצומת", "דו-כיווני (לשני הצדדים)"], key=f"tdir_{d}")
                
                pole_type = st.selectbox(f"סוג עמוד ({d})", ["עמוד מתכת", "עמוד עץ", "ללא עמוד"], key=f"pole_{d}")
                pole_pos = st.selectbox(f"מיקום עמוד ({d})", ["צד ימין", "צד שמאל", "אי תנועה מרכזי"], key=f"pos_{d}")
                
                pedestrian = st.selectbox(f"פנס הולכי רגל ({d})", ["קיים / ללא שינוי", "מבוטל", "חדש", "ללא"], key=f"ped_{d}")
                crosswalk = st.checkbox(f"מעבר חצייה ({d})", value=True, key=f"cw_{d}")

                arm_settings[d] = {
                    "traffic_light": traffic_light,
                    "traffic_dir": traffic_dir,
                    "pole_type": pole_type,
                    "pole_pos": pole_pos,
                    "pedestrian": pedestrian,
                    "crosswalk": crosswalk
                }

    # --- יצירת קוד SVG של הסקיצה ---
    svg_elements = []
    # רקע כביש כהה וחד
    svg_elements.append('<rect width="500" height="500" fill="#1e1e24" />')
    
    # משטחי כביש (אפור כהה)
    svg_elements.append('<rect x="180" y="0" width="140" height="500" fill="#2c2c34" />')
    svg_elements.append('<rect x="0" y="180" width="500" height="140" fill="#2c2c34" />')
    
    # קווי הפרדה מקווקווים בצהוב
    svg_elements.append('<line x1="250" y1="0" x2="250" y2="180" stroke="#f1c40f" stroke-width="3" stroke-dasharray="10,10" />')
    svg_elements.append('<line x1="250" y1="320" x2="250" y2="500" stroke="#f1c40f" stroke-width="3" stroke-dasharray="10,10" />')
    svg_elements.append('<line x1="0" y1="250" x2="180" y2="250" stroke="#ffffff" stroke-width="3" stroke-dasharray="10,10" />')
    svg_elements.append('<line x1="320" y1="250" x2="500" y2="250" stroke="#ffffff" stroke-width="3" stroke-dasharray="10,10" />')

    # כבילה עילית
    if has_temp_cable:
        svg_elements.append('<line x1="40" y1="40" x2="460" y2="460" stroke="#e67e22" stroke-width="3" stroke-dasharray="6,6" />')
        svg_elements.append('<text x="50" y="35" fill="#e67e22" font-size="12" font-weight="bold">תוואי כבילה עילית זמנית</text>')

    # קואורדינטות בסיס לכל זרוע
    arm_coords = {
        "צפון": {"cw_x": 180, "cw_y": 150, "cw_w": 140, "cw_h": 25, "right_x": 300, "left_x": 200, "y": 140},
        "דרום": {"cw_x": 180, "cw_y": 325, "cw_w": 140, "cw_h": 25, "right_x": 200, "left_x": 300, "y": 360},
        "מזרח": {"cw_x": 325, "cw_y": 180, "cw_w": 25, "cw_h": 140, "right_x": 360, "left_x": 360, "y_right": 190, "y_left": 310},
        "מערב": {"cw_x": 150, "cw_y": 180, "cw_w": 25, "cw_h": 140, "right_x": 140, "left_x": 140, "y_right": 310, "y_left": 190}
    }

    for d, data in arm_settings.items():
        ac = arm_coords[d]

        # --- מעבר חצייה (פסים לבנים ושחורים כמו בכביש) ---
        if data["crosswalk"]:
            if d in ["צפון", "דרום"]:
                svg_elements.append(f'<rect x="{ac["cw_x"]}" y="{ac["cw_y"]}" width="{ac["cw_w"]}" height="{ac["cw_h"]}" fill="#1e1e24" />')
                for i in range(0, ac["cw_w"], 16):
                    svg_elements.append(f'<rect x="{ac["cw_x"] + i}" y="{ac["cw_y"]}" width="10" height="{ac["cw_h"]}" fill="#ffffff" />')
            else:
                svg_elements.append(f'<rect x="{ac["cw_x"]}" y="{ac["cw_y"]}" width="{ac["cw_w"]}" height="{ac["cw_h"]}" fill="#1e1e24" />')
                for i in range(0, ac["cw_h"], 16):
                    svg_elements.append(f'<rect x="{ac["cw_x"]}" y="{ac["cw_y"] + i}" width="{ac["cw_w"]}" height="10" fill="#ffffff" />')

        # --- מיקום עמוד ופנסים בצד ימין / שמאל ---
        if d in ["צפון", "דרום"]:
            pos_x = ac["right_x"] if data["pole_pos"] == "צד ימין" else (ac["left_x"] if data["pole_pos"] == "צד שמאל" else 250)
            pos_y = ac["y"]
        else:
            pos_x = ac["right_x"]
            pos_y = ac["y_right"] if data["pole_pos"] == "צד ימין" else (ac["y_left"] if data["pole_pos"] == "צד שמאל" else 250)

        # ציור עמוד (אם קיים)
        if data["pole_type"] == "עמוד מתכת":
            svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y}" r="7" fill="#7f8c8d" stroke="#ffffff" stroke-width="2" />')
        elif data["pole_type"] == "עמוד עץ":
            svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y}" r="7" fill="#8d6e63" stroke="#5d4037" stroke-width="2" />')

        # --- פנס תנועה (רכב) - ירוק / איקס אדום אם מבוטל ---
        if data["traffic_light"] != "ללא":
            tl_color = "#2ecc71" if data["traffic_light"] in ["קיים / ללא שינוי", "חדש"] else "#2ecc71"
            
            if data["traffic_dir"] == "דו-כיווני (לשני הצדדים)":
                svg_elements.append(f'<circle cx="{pos_x-6}" cy="{pos_y-10}" r="6" fill="{tl_color}" />')
                svg_elements.append(f'<circle cx="{pos_x+6}" cy="{pos_y-10}" r="6" fill="{tl_color}" />')
            else:
                svg_elements.append(f'<circle cx="{pos_x}" cy="{pos_y-12}" r="7" fill="{tl_color}" />')

            # סימון מבוטל (איקס אדום בולט)
            if data["traffic_light"] == "מבוטל":
                svg_elements.append(f'<line x1="{pos_x-10}" y1="{pos_y-22}" x2="{pos_x+10}" y2="{pos_y-2}" stroke="#e74c3c" stroke-width="3" />')
                svg_elements.append(f'<line x1="{pos_x+10}" y1="{pos_y-22}" x2="{pos_x-10}" y2="{pos_y-2}" stroke="#e74c3c" stroke-width="3" />')

        # --- פנס הולכי רגל - סגול / אפור אם מבוטל ---
        if data["pedestrian"] != "ללא":
            ped_color = "#9b59b6" if data["pedestrian"] in ["קיים / ללא שינוי", "חדש"] else "#95a5a6"
            svg_elements.append(f'<rect x="{pos_x-5}" y="{pos_y+8}" width="10" height="10" fill="{ped_color}" stroke="#ffffff" stroke-width="1" />')

    # --- מקרא מפורט ומורחב בסקיצה ---
    svg_elements.append('<rect x="10" y="340" width="200" height="150" fill="#111116" rx="6" stroke="#444" stroke-width="1" opacity="0.95"/>')
    svg_elements.append('<text x="20" y="358" fill="#f1c40f" font-size="12" font-weight="bold">מקרא סמלים:</text>')
    
    # פנס רכב
    svg_elements.append('<circle cx="25" cy="375" r="5" fill="#2ecc71" />')
    svg_elements.append('<text x="40" y="379" fill="#ffffff" font-size="10">פנס תנועה לרכב (ירוק)</text>')
    
    # פנס מבוטל
    svg_elements.append('<circle cx="25" cy="393" r="5" fill="#2ecc71" />')
    svg_elements.append('<line x1="20" y1="388" x2="30" y2="398" stroke="#e74c3c" stroke-width="2" />')
    svg_elements.append('<line x1="30" y1="388" x2="20" y2="398" stroke="#e74c3c" stroke-width="2" />')
    svg_elements.append('<text x="40" y="397" fill="#ffffff" font-size="10">פנס מבוטל (איקס אדום)</text>')

    # פנס הולכי רגל
    svg_elements.append('<rect x="21" y="407" width="8" height="8" fill="#9b59b6" />')
    svg_elements.append('<text x="40" y="415" fill="#ffffff" font-size="10">פנס הולכי רגל (סגול/אפור)</text>')

    # סוגי עמודים
    svg_elements.append('<circle cx="25" cy="432" r="5" fill="#7f8c8d" stroke="#fff" stroke-width="1" />')
    svg_elements.append('<text x="40" y="435" fill="#ffffff" font-size="10">עמוד מתכת</text>')

    svg_elements.append('<circle cx="25" cy="450" r="5" fill="#8d6e63" stroke="#5d4037" stroke-width="1" />')
    svg_elements.append('<text x="40" y="453" fill="#ffffff" font-size="10">עמוד עץ</text>')

    # כבילה
    svg_elements.append('<line x1="18" y1="468" x2="32" y2="468" stroke="#e67e22" stroke-width="2" stroke-dasharray="2,2" />')
    svg_elements.append('<text x="40" y="471" fill="#ffffff" font-size="10">תוואי כבילה עילית</text>')

    full_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">{"".join(svg_elements)}</svg>'

    with col_right:
        st.markdown("### 🎨 תצוגה מקדימה של הסקיצה")
        st.components.v1.html(full_svg, height=520)

# --- הפקת דוח PDF עם הסקיצה בתוכו ---
st.markdown("---")
st.subheader("📄 הפקת דוח מסכם")

if st.button("🚀 הפק דוח PDF מלא (כולל סקיצה)"):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, fontSize=20, leading=24)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], alignment=2, fontSize=12, leading=16)

    story.append(Paragraph("דוח פיקוח ותקנון צומת", title_style))
    story.append(Spacer(1, 15))

    # המרת ה-SVG של הסקיצה לגרפיקה עבור ה-PDF
    svg_bytes = io.BytesIO(full_svg.encode('utf-8'))
    drawing = svg2rlg(svg_bytes)
    
    # התאמת גודל הסקיצה ב-PDF
    drawing.width = 350
    drawing.height = 350
    drawing.scale(350/500, 350/500)

    story.append(Paragraph("<b>סקיצת מצב הצומת:</b>", body_style))
    story.append(Spacer(1, 10))
    story.append(drawing)
    story.append(Spacer(1, 20))

    # טבלת נתונים מסכמת
    table_data = [["זרוע", "פנס תנועה", "כיווניות", "סוג עמוד", "מיקום", "מעבר חצייה", "הולכי רגל"]]
    for d, data in arm_settings.items():
        table_data.append([
            d, 
            data["traffic_light"], 
            data["traffic_dir"], 
            data["pole_type"],
            data["pole_pos"],
            "כן" if data["crosswalk"] else "לא", 
            data["pedestrian"]
        ])

    t = Table(table_data, colWidths=[50, 85, 85, 75, 75, 60, 70])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(t)

    doc.build(story)
    pdf_out = buffer.getvalue()
    buffer.close()

    st.download_button(
        label="📥 הורד דוח PDF מלא",
        data=pdf_out,
        file_name="junction_report.pdf",
        mime="application/pdf"
    )
