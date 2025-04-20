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
import fpylll  # For fingerprint processing (example library)
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

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "your_password"       # Replace with your password

# Fingerprint scanner setup
def check_fingerprint_scanner():
    """Check if a fingerprint scanner is connected"""
    try:
        if platform.system() == 'Windows':
            # Windows - check for connected USB devices
            result = subprocess.run(['powershell', 'Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match "USB" }'], 
                                  capture_output=True, text=True)
            return "Fingerprint" in result.stdout
        else:
            # Linux/Mac - check for connected USB devices
            result = subprocess.run(['lsusb'], capture_output=True, text=True)
            return "Fingerprint" in result.stdout
    except:
        return False

def enroll_fingerprint(student_id):
    """Simulate fingerprint enrollment"""
    # In a real implementation, this would interface with the fingerprint scanner SDK
    fingerprint_file = f"data/fingerprints/{student_id}.fpr"
    with open(fingerprint_file, 'w') as f:
        f.write(f"Fingerprint data for {student_id}")
    return True

def verify_fingerprint(student_id):
    """Simulate fingerprint verification"""
    # In a real implementation, this would interface with the fingerprint scanner SDK
    fingerprint_file = f"data/fingerprints/{student_id}.fpr"
    return os.path.exists(fingerprint_file)

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
            if not fingerprint_scanner_connected:
                st.warning("No fingerprint scanner detected. Please connect a USB fingerprint scanner.")
            else:
                st.info("Fingerprint scanner detected and ready")
                
                # Check if student has registered fingerprint
                if not st.session_state.current_student['FingerprintRegistered']:
                    if st.button("Register Fingerprint"):
                        if enroll_fingerprint(st.session_state.current_student['Student ID']):
                            st.session_state.student_data.loc[
                                st.session_state.student_data['Student ID'] == st.session_state.current_student['Student ID'],
                                'FingerprintRegistered'
                            ] = True
                            st.session_state.student_data.to_csv('data/students.csv', index=False)
                            st.success("Fingerprint registered successfully!")
                        else:
                            st.error("Fingerprint registration failed")
                else:
                    if st.button("Authenticate with Fingerprint"):
                        if verify_fingerprint(st.session_state.current_student['Student ID']):
                            record_attendance(
                                st.session_state.current_student['Student ID'], 
                                "Fingerprint",
                                fingerprint_id=st.session_state.current_student['Student ID']
                            )
                        else:
                            st.error("Fingerprint verification failed")

    with tab2:
        st.header("Your Attendance Records")
        student_records = st.session_state.attendance[
            st.session_state.attendance['Student ID'] == st.session_state.current_student['Student ID']
        ]
        st.dataframe(student_records)

    with tab3:
        st.header("Professor Portal")
        professor_password = st.text_input("Enter Professor Password", type="password")
        
        if professor_password == "admin123":  # Change this in production
            st.success("Professor Access Granted")
            
            # Full attendance records
            st.subheader("All Attendance Records")
            st.dataframe(st.session_state.attendance)
            
            # Download options
            st.subheader("Download Data")
            
            # Download CSV
            csv = st.session_state.attendance.to_csv(index=False)
            b64_csv = base64.b64encode(csv.encode()).decode()
            href_csv = f'<a href="data:file/csv;base64,{b64_csv}" download="attendance_records.csv">Download Attendance CSV</a>'
            st.markdown(href_csv, unsafe_allow_html=True)
            
            # Download photos zip
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
