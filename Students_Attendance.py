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
import time
from streamlit.components.v1 import html
import json

if 'fingerprint_auth' not in st.session_state:
    st.session_state.fingerprint_auth = False

# Initialize session state for authentication status
if 'auth_status' not in st.session_state:
    st.session_state.auth_status = None

# Initialize face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Session state setup
if 'attendance' not in st.session_state:
    if os.path.exists('data/attendance.csv'):
        st.session_state.attendance = pd.read_csv('data/attendance.csv')
    else:
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time', 'Method', 'Photo Path'])

if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Password'])

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Create directories
os.makedirs('data/faces', exist_ok=True)
os.makedirs('data/attendance_photos', exist_ok=True)

# Email configuration (replace with your actual email settings)
EMAIL_ADDRESS = "your_email@example.com"
EMAIL_PASSWORD = "your_email_password"
SMTP_SERVER = "smtp.example.com"
SMTP_PORT = 587

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

def record_attendance(student_id, method, photo_path=None):
    student_info = st.session_state.student_data[
        st.session_state.student_data['Student ID'] == student_id
    ]
    
    if not student_info.empty:
        student_name = student_info['Name'].values[0]
        student_email = student_info['Email'].values[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_entry = pd.DataFrame([[student_id, student_name, student_email, now, method, photo_path]], 
                              columns=['Student ID', 'Name', 'Email', 'Time', 'Method', 'Photo Path'])
        st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
        st.session_state.attendance.to_csv('data/attendance.csv', index=False)
        st.success(f"Attendance recorded for {student_name}")
        send_email(student_email, student_name, now)
    else:
        st.warning("Student not found")

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
                st.session_state.current_student = student_info.iloc[0].to_dict()
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
                        new_student = pd.DataFrame([[new_id, new_name, new_email, new_password]], 
                                                 columns=['Student ID', 'Name', 'Email', 'Password'])
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
        st.session_state.auth_status = None
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Mark Attendance", "View Attendance", "Professor Portal"])



# ... (keep your existing imports)

with tab1:
    st.header("Mark Attendance")
    method = st.radio("Authentication Method", ["Face Recognition", "Fingerprint"])
    
    if method == "Face Recognition":
        # ... (keep your existing face recognition code)
    
        elif method == "Fingerprint":
            # Generate a unique key for this component
            fingerprint_key = f"fingerprint_{st.session_state.current_student['Student ID']}"
            
            # Fingerprint sensor HTML/JS
            fingerprint_js = f"""
            <div id="fingerprint-container-{fingerprint_key}" style="text-align: center;">
                <h3>Place and hold your finger on the sensor</h3>
                <div id="sensor-{fingerprint_key}" style="
                    width: 120px;
                    height: 120px;
                    margin: 0 auto;
                    background: #e0e0e0;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 40px;
                    cursor: pointer;
                    user-select: none;
                " onmousedown="startScan{fingerprint_key}()" onmouseup="stopScan{fingerprint_key}()" 
                ontouchstart="startScan{fingerprint_key}()" ontouchend="stopScan{fingerprint_key}()">🖐️</div>
                <p id="status-{fingerprint_key}">Press and hold your finger on the sensor</p>
            </div>
    
            <script>
            let scanTimer{fingerprint_key};
            let isScanning{fingerprint_key} = false;
            
            function startScan{fingerprint_key}() {{
                if (isScanning{fingerprint_key}) return;
                isScanning{fingerprint_key} = true;
                const sensor = document.getElementById('sensor-{fingerprint_key}');
                const status = document.getElementById('status-{fingerprint_key}');
                
                sensor.innerHTML = "👆";
                sensor.style.background = "#FFC107";
                status.textContent = "Scanning fingerprint...";
                
                // Simulate scan time (2-3 seconds)
                scanTimer{fingerprint_key} = setTimeout(() => {{
                    if (isScanning{fingerprint_key}) {{
                        // 80% chance of success for realism
                        if (Math.random() < 0.8) {{
                            sensor.innerHTML = "✅";
                            sensor.style.background = "#4CAF50";
                            status.textContent = "Fingerprint verified!";
                            
                            // Report success to Streamlit
                            window.parent.postMessage({{
                                type: 'fingerprintResult',
                                success: true,
                                studentId: '{st.session_state.current_student['Student ID']}'
                            }}, '*');
                        }} else {{
                            sensor.innerHTML = "❌";
                            sensor.style.background = "#FF5252";
                            status.textContent = "Scan failed. Try again.";
                        }}
                        isScanning{fingerprint_key} = false;
                    }}
                }}, 2000 + Math.random() * 1000);
            }}
            
            function stopScan{fingerprint_key}() {{
                isScanning{fingerprint_key} = false;
                clearTimeout(scanTimer{fingerprint_key});
                const sensor = document.getElementById('sensor-{fingerprint_key}');
                const status = document.getElementById('status-{fingerprint_key}');
                
                sensor.innerHTML = "🖐️";
                sensor.style.background = "#e0e0e0";
                status.textContent = "Press and hold your finger on the sensor";
            }}
            </script>
            """
            
            # Display the fingerprint sensor
            html(fingerprint_js)
            
            # JavaScript to handle communication with Streamlit
            fingerprint_handler = """
            <script>
            window.addEventListener('message', function(event) {
                if (event.data.type === 'fingerprintResult' && event.data.success) {
                    const data = {
                        student_id: event.data.studentId,
                        success: event.data.success
                    };
                    parent.window.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: JSON.stringify(data)
                    }, '*');
                }
            });
            </script>
            """
            html(fingerprint_handler)
            
            # Handle the fingerprint result
            if st.session_state.get('fingerprint_auth'):
                record_attendance(
                    st.session_state.current_student['Student ID'],
                    "Fingerprint"
                )
                del st.session_state['fingerprint_auth']
                st.rerun()
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
