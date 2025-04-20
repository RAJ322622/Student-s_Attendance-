import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import os
import pandas as pd
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit.components.v1 import html
import platform
import subprocess

# Initialize face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Session state setup
if 'attendance' not in st.session_state:
    if os.path.exists('data/attendance.csv'):
        st.session_state.attendance = pd.read_csv('data/attendance.csv')
    else:
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time', 'Method', 'Photo Path', 'FingerprintID'])

if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Password', 'FingerprintRegistered'])

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Create directories
os.makedirs('data/faces', exist_ok=True)
os.makedirs('data/attendance_photos', exist_ok=True)
os.makedirs('data/fingerprints', exist_ok=True)

# Email configuration (replace with your actual credentials)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_password"

# Fingerprint scanner setup
def check_fingerprint_scanner():
    """Check if a fingerprint scanner is connected"""
    try:
        if platform.system() == 'Windows':
            result = subprocess.run(['powershell', 'Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match "USB" }'], 
                                  capture_output=True, text=True)
            return "Fingerprint" in result.stdout
        else:
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            return "Fingerprint" in result.stdout
    except:
        return False

# WebAuthn fingerprint implementation for mobile
fingerprint_js = """
<script>
async function authenticateFingerprint(studentId) {
    try {
        const credential = await navigator.credentials.get({
            publicKey: {
                challenge: new Uint8Array([1,2,3,4,5,6,7,8]),
                rpId: window.location.hostname,
                allowCredentials: [{
                    type: 'public-key',
                    id: new TextEncoder().encode(studentId),
                    transports: ['internal']
                }],
                userVerification: 'required'
            }
        });
        
        return {success: true, studentId: studentId};
    } catch (error) {
        return {success: false, error: error.message};
    }
}

async function registerFingerprint(studentId) {
    try {
        const credential = await navigator.credentials.create({
            publicKey: {
                rp: {
                    name: "Attendance System",
                    id: window.location.hostname
                },
                user: {
                    id: new TextEncoder().encode(studentId),
                    name: studentId,
                    displayName: studentId
                },
                pubKeyCredParams: [
                    {type: "public-key", alg: -7}  // ES256
                ],
                authenticatorSelection: {
                    userVerification: "required",
                    requireResidentKey: true
                },
                attestation: "direct",
                challenge: new Uint8Array([1,2,3,4,5,6,7,8])
            }
        });
        
        return {success: true, studentId: studentId};
    } catch (error) {
        return {success: false, error: error.message};
    }
}
</script>
"""

# Page config
st.set_page_config(page_title="Student Attendance System", layout="wide")
st.title("Student Attendance System")

# Helper functions
def send_email(to_email, student_name, time):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = "Attendance Notification"
        
        body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                <p>Your attendance has been recorded at {time}.</p>
                <p>Thank you!</p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email failed: {str(e)}")
        return False

def detect_faces(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return len(faces) > 0

def record_attendance(student_id, method, photo_path=None, fingerprint_id=None):
    student_info = st.session_state.student_data[
        st.session_state.student_data['Student ID'] == student_id
    ]
    
    if not student_info.empty:
        student_name = student_info['Name'].values[0]
        student_email = student_info['Email'].values[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_entry = pd.DataFrame([[student_id, student_name, student_email, now, method, photo_path, fingerprint_id]], 
                              columns=['Student ID', 'Name', 'Email', 'Time', 'Method', 'Photo Path', 'FingerprintID'])
        st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
        st.session_state.attendance.to_csv('data/attendance.csv', index=False)
        st.success(f"Attendance recorded for {student_name}")
        send_email(student_email, student_name, now)
    else:
        st.warning("Student not found")

# Check for fingerprint scanner
fingerprint_scanner_connected = check_fingerprint_scanner()

# Login/Registration System
if not st.session_state.logged_in:
    with st.form("Login"):
        st.header("Student Login")
        student_id = st.text_input("Student ID")
        password = st.text_input("Password", type="password")
        
        if st.form_submit_button("Login"):
            student_info = st.session_state.student_data[
                (st.session_state.student_data['Student ID'] == student_id) & 
                (st.session_state.student_data['Password'] == password)
            ]
            if not student_info.empty:
                st.session_state.logged_in = True
                st.session_state.current_student = student_info.iloc[0]
                st.rerun()
            else:
                st.error("Invalid credentials")

    with st.expander("New Student Registration"):
        with st.form("Register"):
            st.header("Student Registration")
            new_id = st.text_input("Student ID")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email Address")
            new_password = st.text_input("Create Password", type="password")
            
            if st.form_submit_button("Register"):
                if new_id and new_name and new_email and new_password:
                    if new_id in st.session_state.student_data['Student ID'].values:
                        st.error("Student ID already exists")
                    else:
                        new_student = pd.DataFrame([[new_id, new_name, new_email, new_password, False]], 
                                                 columns=['Student ID', 'Name', 'Email', 'Password', 'FingerprintRegistered'])
                        st.session_state.student_data = pd.concat([st.session_state.student_data, new_student], ignore_index=True)
                        st.session_state.student_data.to_csv('data/students.csv', index=False)
                        st.success("Registration successful! Please login.")
                else:
                    st.error("Please fill all fields")
else:
    # Main App
    st.sidebar.header(f"Welcome, {st.session_state.current_student['Name']}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Mark Attendance", "View Attendance", "Professor Portal"])

    with tab1:
        st.header("Mark Attendance")
        method = st.radio("Authentication Method", ["Face Recognition", "Fingerprint"])
        
        if method == "Face Recognition":
            picture = st.camera_input("Take a picture for attendance")
            
            if picture:
                # Save attendance photo with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                photo_path = f"data/attendance_photos/{st.session_state.current_student['Student ID']}_{timestamp}.jpg"
                with open(photo_path, "wb") as f:
                    f.write(picture.getbuffer())
                
                # Convert image to OpenCV format
                img_bytes = picture.getvalue()
                img_array = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if detect_faces(img):
                    record_attendance(
                        st.session_state.current_student['Student ID'], 
                        "Face Recognition",
                        photo_path
                    )
                else:
                    st.warning("No face detected - please try again")
        
        elif method == "Fingerprint":
            # Mobile fingerprint authentication
            html(f"""
            <script>
            async function handleAuth() {{
                const result = await authenticateFingerprint('{st.session_state.current_student['Student ID']}');
                if (result.success) {{
                    window.parent.postMessage({{
                        type: 'fingerprintAuth',
                        success: true,
                        studentId: result.studentId
                    }}, '*');
                }} else {{
                    alert("Fingerprint authentication failed: " + result.error);
                }}
            }}
            
            async function handleRegister() {{
                const result = await registerFingerprint('{st.session_state.current_student['Student ID']}');
                if (result.success) {{
                    window.parent.postMessage({{
                        type: 'fingerprintRegister',
                        success: true,
                        studentId: result.studentId
                    }}, '*');
                }} else {{
                    alert("Fingerprint registration failed: " + result.error);
                }}
            }}
            </script>
            {fingerprint_js}
            """, height=0)
            
            if not st.session_state.current_student['FingerprintRegistered']:
                st.info("Register your fingerprint for future logins")
                if st.button("Register Fingerprint"):
                    html("<script>handleRegister()</script>")
            else:
                st.info("Authenticate with your fingerprint")
                if st.button("Authenticate with Fingerprint"):
                    html("<script>handleAuth()</script>")
            
            # USB fingerprint scanner fallback
            if fingerprint_scanner_connected:
                st.info("USB fingerprint scanner detected")
                if st.button("Use USB Fingerprint Scanner"):
                    # Simulate USB fingerprint verification
                    record_attendance(
                        st.session_state.current_student['Student ID'], 
                        "Fingerprint (USB)",
                        fingerprint_id=st.session_state.current_student['Student ID']
                    )

    with tab2:
        st.header("Your Attendance Records")
        student_records = st.session_state.attendance[
            st.session_state.attendance['Student ID'] == st.session_state.current_student['Student ID']
        ]
        st.dataframe(student_records)

    with tab3:
        st.header("Professor Portal")
        professor_password = st.text_input("Enter Professor Password", type="password")
        
        if professor_password == "admin123":
            st.success("Professor Access Granted")
            
            st.subheader("All Attendance Records")
            st.dataframe(st.session_state.attendance)
            
            st.subheader("Download Data")
            
            csv = st.session_state.attendance.to_csv(index=False)
            b64_csv = base64.b64encode(csv.encode()).decode()
            href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="attendance_records.csv">Download Attendance CSV</a>'
            st.markdown(href_csv, unsafe_allow_html=True)
            
            if st.button("Prepare Photos for Download"):
                import zipfile
                from io import BytesIO
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for index, row in st.session_state.attendance.iterrows():
                        if pd.notna(row['Photo Path']) and os.path.exists(row['Photo Path']):
                            zip_file.write(
                                row['Photo Path'], 
                                f"{row['Student ID']}_{row['Name']}_{os.path.basename(row['Photo Path'])}"
                            )
                
                zip_buffer.seek(0)
                b64_zip = base64.b64encode(zip_buffer.read()).decode()
                href_zip = f'<a href="data:application/zip;base64,{b64_zip}" download="attendance_photos.zip">Download All Photos</a>'
                st.markdown(href_zip, unsafe_allow_html=True)

# Handle fingerprint authentication results
html("""
<script>
window.addEventListener('message', (event) => {
    if (event.data.type === 'fingerprintAuth' && event.data.success) {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", window.location.href, true);
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.send(`fingerprint_auth=${event.data.studentId}`);
    }
    if (event.data.type === 'fingerprintRegister' && event.data.success) {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", window.location.href, true);
        xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
        xhr.send(`fingerprint_register=${event.data.studentId}`);
    }
});
</script>
""")

# Handle fingerprint authentication from JavaScript
if 'fingerprint_auth' in st.query_params:
    student_id = st.query_params['fingerprint_auth']
    if student_id == st.session_state.current_student['Student ID']:
        record_attendance(student_id, "Fingerprint (Mobile)")

if 'fingerprint_register' in st.query_params:
    student_id = st.query_params['fingerprint_register']
    if student_id == st.session_state.current_student['Student ID']:
        st.session_state.student_data.loc[
            st.session_state.student_data['Student ID'] == student_id,
            'FingerprintRegistered'
        ] = True
        st.session_state.student_data.to_csv('data/students.csv', index=False)
        st.success("Fingerprint registered successfully!")
        st.rerun()
