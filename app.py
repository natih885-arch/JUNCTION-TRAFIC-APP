import os
import io
import zipfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
import streamlit as st
from geopy.distance import geodesic
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# --- הגדרות עמוד ---
st.set_page_config(
    page_title="מערכת דיווח וסיווג צמתים - ענן ומייל",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    body, div, p, span, h1, h2, h3, h4, h5, h6, label {
        direction: RTL;
        text-align: right;
    }
    .stButton>button {
        width: 100%;
        background-color: #0066cc;
        color: white;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- ניהול משתמשים בדיסק ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""
if 'user_name' not in st.session_state:
    st.session_state['user_name'] = ""
if 'users_db' not in st.session_state:
    st.session_state['users_db'] = {}

# --- רשימת צמתים וקואורדינטות ---
JUNCTIONS = {
    "צומת_402_רעננה": (32.1842, 34.8711),
    "צומת_הרצליה_מרכז": (32.1663, 34.8433),
    "צומת_מחלף_הסירות": (32.1642, 34.8115),
    "צומת_ראשון_לציון_מרכז": (31.9652, 34.8031)
}
MAX_DISTANCE_METERS = 100

# --- פונקציות GPS ---
def convert_to_degrees(value):
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)

def get_gps_coordinates(image):
    try:
        exif_data = image._getexif()
        if not exif_data:
            return None
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for g_tag in value:
                    g_name = GPSTAGS.get(g_tag, g_tag)
                    gps_info[g_name] = value[g_tag]
        if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
            lat = convert_to_degrees(gps_info['GPSLatitude'])
            if gps_info.get('GPSLatitudeRef') != 'N':
                lat = -lat
            lon = convert_to_degrees(gps_info['GPSLongitude'])
            if gps_info.get('GPSLongitudeRef') != 'E':
                lon = -lon
            return lat, lon
    except Exception:
        pass
    return None

def find_matching_junction(coords):
    if not coords:
        return "תמונות_ללא_מיקום_GPS"
    for junction_name, junction_coords in JUNCTIONS.items():
        dist = geodesic(coords, junction_coords).meters
        if dist <= MAX_DISTANCE_METERS:
            return junction_name
    return "צומת_לא_מוכר_לפי_GPS"

# --- פונקציית שליחת מייל מרוכז ---
def send_email_report(sender_email, sender_password, target_email, subject, body_text, files_dict):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = target_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

        for filename, file_bytes in files_dict.items():
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(file_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, target_email, msg.as_string())
        server.quit()
        return True, "הדוח המרוכז נשלח בהצלחה למייל!"
    except Exception as e:
        return False, f"שגיאה בשליחת המייל: {str(e)}"

# ==================== תפריט התחברות / הרשמה (Sidebar) ====================
st.sidebar.title("👤 אזור אישי ואימות")

if not st.session_state['logged_in']:
    auth_mode = st.sidebar.radio("בחר פעולה:", ["התחברות", "הרשמה"])
    
    if auth_mode == "הרשמה":
        st.sidebar.subheader("הרשמת מפקח חדש")
        reg_name = st.sidebar.text_input("שם מלא:")
        reg_email = st.sidebar.text_input("כתובת אימייל:")
        reg_pass = st.sidebar.text_input("סיסמה:", type="password")
        
        if st.sidebar.button("ביצוע הרשמה"):
            if reg_email and reg_pass and reg_name:
                st.session_state['users_db'][reg_email] = {"name": reg_name, "pass": reg_pass}
                st.sidebar.success("ההרשמה בוצעה בהצלחה! כעת תוכל להתחבר.")
            else:
                st.sidebar.error("אנא מלא את כל השדות.")

    elif auth_mode == "התחברות":
        st.sidebar.subheader("התחברות למערכת")
        login_email = st.sidebar.text_input("אימייל:")
        login_pass = st.sidebar.text_input("סיסמה:", type="password")
        
        if st.sidebar.button("התחבר"):
            user = st.session_state['users_db'].get(login_email)
            if user and user['pass'] == login_pass:
                st.session_state['logged_in'] = True
                st.session_state['user_email'] = login_email
                st.session_state['user_name'] = user['name']
                st.rerun()
            else:
                st.sidebar.error("פרטי התחברות שגויים או שאינך רשום.")
else:
    st.sidebar.success(f"מחובר כ: **{st.session_state['user_name']}**")
    st.sidebar.write(f"אימייל: `{st.session_state['user_email']}`")
    if st.sidebar.button("התנתק"):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = ""
        st.session_state['user_name'] = ""
        st.rerun()

# ==================== המסך המרכזי ====================
st.title("🚦 מערכת מרוכזת לדיווח צמתים וסיווג תמונות")

if not st.session_state['logged_in']:
    st.warning("⚠️ יש להתחבר או להירשם בתפריט הצדדי כדי להתחיל לעבוד במערכת.")
else:
    col_right, col_left = st.columns([1, 1])

    with col_right:
        st.subheader("📁 העלאת תמונות מהשטח")
        
        files_before = st.file_uploader(
            "📷 תמונות 'לפני הסדר':", 
            type=['jpg', 'jpeg', 'png'], 
            accept_multiple_files=True,
            key="before_files"
        )
        
        files_after = st.file_uploader(
            "📸 תמונות 'אחרי הסדר':", 
            type=['jpg', 'jpeg', 'png'], 
            accept_multiple_files=True,
            key="after_files"
        )

    with col_left:
        st.subheader("📝 דוח מילולי מרוכז")
        change_report = st.text_area("דוח שינויים שבוצעו:", placeholder="פרט כאן שינויים...", height=80)
        defects_report = st.text_area("דוח ליקויים שנתגלו:", placeholder="פרט כאן ליקויים...", height=80)
        general_notes = st.text_area("הערות כלליות:", placeholder="הערות נוספות...", height=80)

    if files_before or files_after:
        st.divider()
        st.subheader("📸 עיבוד ותצוגה מקדימה")
        
        files_to_email = {}
        summary_lines = [
            f"=== דוח מרכזי מאת המפקח: {st.session_state['user_name']} ({st.session_state['user_email']}) ===",
            "\n--- פירוט דוחות בכתב ---",
            f"דוח שינויים:\n{change_report if change_report else 'אין'}",
            f"\nדוח ליקויים:\n{defects_report if defects_report else 'אין'}",
            f"\nהערות כלליות:\n{general_notes if general_notes else 'אין'}",
            "\n--- פירוט תמונות מועלות ---"
        ]

        # פונקציית עזר לעיבוד רשימת תמונות
        def process_files(file_list, category_label):
            for file in file_list:
                img = Image.open(file)
                coords = get_gps_coordinates(img)
                junction_folder = find_matching_junction(coords)
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.image(img, width=150)
                with c2:
                    st.write(f"**קובץ:** {file.name} | **צומת:** `{junction_folder}` | **סיווג:** {category_label}")
                
                file_bytes = file.getvalue()
                safe_filename = f"{junction_folder}_{category_label}_{file.name}"
                files_to_email[safe_filename] = file_bytes
                
                summary_lines.append(f"קובץ: {file.name} | צומת: {junction_folder} | סיווג: {category_label} | GPS: {coords}")

        if files_before:
            st.markdown("#### 🔹 תמונות לפני הסדר:")
            process_files(files_before, "לפני_הסדר")

        if files_after:
            st.markdown("#### 🔹 תמונות אחרי הסדר:")
            process_files(files_after, "אחרי_הסדר")

        full_report_text = "\n".join(summary_lines)

        st.divider()
        st.subheader("📧 שליחת דוח מרוכז במייל מרכזי")
        
        st.info("הזן פרטי שרת דואר לשליחת הדוח המאוחד (כולל כל התמונות והמלל) למשרד:")
        
        c_mail1, c_mail2 = st.columns(2)
        with c_mail1:
            dest_email = st.text_input("מייל יעד (למי לשלוח במשרד):", value="office@company.com")
            sender_email = st.text_input("מייל שולח (Gmail):", value=st.session_state['user_email'])
        with c_mail2:
            sender_pass = st.text_input("סיסמת אפליקציה לשולח (App Password):", type="password")

        if st.button("🚀 שגר דוח מרוכז אחד למייל"):
            if not sender_email or not sender_pass or not dest_email:
                st.error("אנא מלא את כל פרטי המייל לשליחה.")
            else:
                files_to_email["דוח_ריכוז_מלא.txt"] = full_report_text.encode('utf-8')
                
                with st.spinner("שולח דוח מרוכז ותמונות..."):
                    success, msg = send_email_report(
                        sender_email=sender_email,
                        sender_password=sender_pass,
                        target_email=dest_email,
                        subject=f"דוח צמתים מרוכז - {st.session_state['user_name']}",
                        body_text=full_report_text,
                        files_dict=files_to_email
                    )
                if success:
                    st.success(msg)
                else:
                    st.error(msg)