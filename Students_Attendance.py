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
import zipfile
from io import BytesIO

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

    with tab1:
    
        st.header("Mark Attendance")
        method = st.radio("Authentication Method", ["Face Recognition", "Fingerprint"])
        
        if method == "Face Recognition":
            picture = st.camera_input("Take a picture for attendance")
            
            if picture:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                photo_path = f"data/attendance_photos/{st.session_state.current_student['Student ID']}_{timestamp}.jpg"
                with open(photo_path, "wb") as f:
                    f.write(picture.getbuffer())
                
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
            st.markdown("""
            <h2>Fingerprint Authentication</h2>
            <p>Place your finger on the scanner when ready</p>
            """, unsafe_allow_html=True)
            
            # Fingerprint scanner integration
            fingerprint_js = """
            <script src="https://webgateway.csccloud.in/assets/js/jquery-3.2.1.min.js"></script>
            
            <button type="button" id="scanFingerprint">Scan Fingerprint</button>
            <div id="fingerprintResult"></div>
            <img id="fingerprintImage" src="" width="200" />
            
            <script>
            var template;
            
            function callFingerprintAPI() {
                var url = "http://localhost:8080/CallMorphoAPI";
                var xmlhttp = new XMLHttpRequest();
                
                xmlhttp.onreadystatechange = function() {
                    if (xmlhttp.readyState == 4 && xmlhttp.status == 200) {
                        var fpobject = JSON.parse(xmlhttp.responseText);
                        
                        if(fpobject.ReturnCode === "0") {
                            // Successful scan
                            document.getElementById("fingerprintImage").src = 
                                "data:image/png;base64," + fpobject.Base64BMPIMage;
                            
                            // Send the result back to Streamlit
                            window.parent.postMessage({
                                type: 'fingerprintResult',
                                success: true,
                                studentId: '%s',
                                image: fpobject.Base64BMPIMage,
                                template: fpobject.Base64ISOTemplate
                            }, '*');
                        } else {
                            document.getElementById("fingerprintResult").innerHTML = 
                                "Scan failed. Please try again.";
                        }
                    }
                };
                
                xmlhttp.open("POST", url, true);
                xmlhttp.send();
            }
            
            // Set up event listener for the scan button
            document.getElementById("scanFingerprint").addEventListener("click", function() {
                document.getElementById("fingerprintResult").innerHTML = "Scanning...";
                callFingerprintAPI();
            });
            
            // For demo purposes - simulate a scanner if the API isn't available
            function simulateFingerprintScan() {
                setTimeout(function() {
                    // 80% chance of success for realism
                    if(Math.random() < 0.8) {
                        window.parent.postMessage({
                            type: 'fingerprintResult',
                            success: true,
                            studentId: '%s',
                            image: '',
                            template: 'simulated_template_xyz123'
                        }, '*');
                        document.getElementById("fingerprintResult").innerHTML = "Verification successful!";
                    } else {
                        document.getElementById("fingerprintResult").innerHTML = "Scan failed. Please try again.";
                    }
                }, 2000);
            }
            
            // Fallback if real scanner not available
            if(typeof XMLHttpRequest === 'undefined') {
                document.getElementById("scanFingerprint").addEventListener("click", simulateFingerprintScan);
            }
            </script>
            """ % (st.session_state.current_student['Student ID'], 
                  st.session_state.current_student['Student ID'])
            
            html(fingerprint_js, height=300)
            
            # Handle the fingerprint result
            if 'fingerprint_success' in st.session_state and st.session_state.fingerprint_success:
                record_attendance(
                    st.session_state.current_student['Student ID'],
                    "Fingerprint"
                )
                del st.session_state.fingerprint_success
                st.rerun()
            
            # JavaScript to handle communication with Streamlit
            fingerprint_handler = """
            <script>
            window.addEventListener('message', function(event) {
                if (event.data.type === 'fingerprintResult' && event.data.success) {
                    // Send data to Streamlit
                    const data = {
                        student_id: event.data.studentId,
                        success: event.data.success,
                        image: event.data.image,
                        template: event.data.template
                    };
                    
                    // Store template in localStorage for comparison later
                    if(event.data.template) {
                        localStorage.setItem('fingerprintTemplate', event.data.template);
                    }
                    
                    parent.window.postMessage({
                        type: 'streamlit:setComponentValue',
                        value: JSON.stringify(data)
                    }, '*');
                }
            });
            </script>
            """
            html(fingerprint_handler)

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
