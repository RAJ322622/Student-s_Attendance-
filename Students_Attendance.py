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

# Initialize face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize session state
if 'attendance' not in st.session_state:
    if os.path.exists('data/attendance.csv'):
        st.session_state.attendance = pd.read_csv('data/attendance.csv')
    else:
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method'])
        
if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'FingerprintID'])

if 'fingerprint_registered' not in st.session_state:
    st.session_state.fingerprint_registered = {}

# Create data directory
os.makedirs('data', exist_ok=True)
os.makedirs('data/faces', exist_ok=True)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "rajkumar.k0322@gmail.com"
EMAIL_PASSWORD = "kcxf lzrq xnts xlng"

# Fingerprint authentication JavaScript
fingerprint_js = """
<script>
async function authenticateFingerprint(studentId) {
    try {
        // WebAuthn API for fingerprint authentication
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
        
        window.parent.postMessage({
            type: 'fingerprintAuth',
            success: true,
            studentId: studentId
        }, '*');
    } catch (error) {
        window.parent.postMessage({
            type: 'fingerprintAuth',
            success: false,
            error: error.message
        }, '*');
    }
}

function registerFingerprint(studentId) {
    if (window.confirm(`Register fingerprint for student ${studentId}?`)) {
        window.parent.postMessage({
            type: 'fingerprintRegistration',
            studentId: studentId,
            success: true
        }, '*');
    }
}
</script>
"""

# Page config
st.set_page_config(page_title="Student Attendance System", layout="wide")
st.title("Student Attendance System")

# Helper functions
def send_email(to_email, student_name, time_in=None, time_out=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = "Attendance Notification"
        
        body = f"""
        <html>
            <body>
                <p>Dear {student_name},</p>
                {f"<p>Your attendance has been recorded:</p><ul><li>Time In: {time_in}</li>{f"<li>Time Out: {time_out}</li>" if time_out else ""}</ul>"}
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

def record_attendance(student_id, method):
    student_info = st.session_state.student_data[
        st.session_state.student_data['Student ID'] == student_id
    ]
    
    if not student_info.empty:
        student_name = student_info['Name'].values[0]
        student_email = student_info['Email'].values[0]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if this is time-in or time-out
        existing_entry = st.session_state.attendance[
            (st.session_state.attendance['Student ID'] == student_id) & 
            (st.session_state.attendance['Time Out'].isna())
        ]
        
        if existing_entry.empty:
            # Time In
            new_entry = pd.DataFrame([[student_id, student_name, student_email, now, None, method]], 
                                  columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method'])
            st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
            st.success(f"Time In recorded for {student_name} at {now}")
            send_email(student_email, student_name, time_in=now)
        else:
            # Time Out
            idx = existing_entry.index[0]
            st.session_state.attendance.at[idx, 'Time Out'] = now
            st.success(f"Time Out recorded for {student_name} at {now}")
            send_email(student_email, student_name, 
                     time_in=st.session_state.attendance.at[idx, 'Time In'], 
                     time_out=now)
        
        st.session_state.attendance.to_csv('data/attendance.csv', index=False)
    else:
        st.warning("Student ID not found in database")

# Student Registration
with st.sidebar:
    st.header("Student Registration")
    student_id = st.text_input("Student ID")
    student_name = st.text_input("Full Name")
    student_email = st.text_input("Email Address")
    
    if st.button("Register Student"):
        if student_id and student_name and student_email:
            new_student = pd.DataFrame([[student_id, student_name, student_email, ""]], 
                                     columns=['Student ID', 'Name', 'Email', 'FingerprintID'])
            st.session_state.student_data = pd.concat([st.session_state.student_data, new_student], ignore_index=True)
            st.session_state.student_data.to_csv('data/students.csv', index=False)
            st.success(f"Student {student_name} registered!")
        else:
            st.error("Please fill all fields")

    # Fingerprint registration
    if student_id:
        html(f"""
        <button onclick="registerFingerprint('{student_id}')">Register Fingerprint</button>
        {fingerprint_js}
        """, height=50)
    
    # Face registration
    st.write("Register Face")
    picture = st.camera_input("Take a picture")
    if picture and student_id:
        img_path = f"data/faces/{student_id}.jpg"
        with open(img_path, "wb") as f:
            f.write(picture.getbuffer())
        st.success("Face registered!")

# Main App
tab1, tab2, tab3 = st.tabs(["Mark Attendance", "View Attendance", "Professor Portal"])

with tab1:
    st.header("Mark Attendance")
    method = st.radio("Authentication Method", ["Face Recognition", "Fingerprint"])
    
    if method == "Face Recognition":
        student_id = st.text_input("Enter Student ID", key="face_id")
        picture = st.camera_input("Take a picture for attendance")
        
        if picture and student_id:
            # Convert image to OpenCV format
            img_bytes = picture.getvalue()
            img_array = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            # Check if face is detected
            if detect_faces(img):
                record_attendance(student_id, "Face Recognition")
            else:
                st.warning("No face detected - please try again")
    
    elif method == "Fingerprint":
        student_id = st.text_input("Enter Student ID", key="fingerprint_id")
        html(f"""
        <button onclick="authenticateFingerprint('{student_id}')">Authenticate with Fingerprint</button>
        {fingerprint_js}
        """, height=50)

with tab2:
    st.header("Attendance Records")
    st.dataframe(st.session_state.attendance)
    
    if not st.session_state.attendance.empty:
        csv = st.session_state.attendance.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="attendance.csv">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

with tab3:
    st.header("Professor Portal")
    password = st.text_input("Enter password", type="password")
    
    if password == "admin123":  # Change this in production
        st.success("Logged in")
        st.dataframe(st.session_state.attendance)
        
        # Student lookup
        search_id = st.text_input("Search Student ID")
        if search_id:
            results = st.session_state.attendance[st.session_state.attendance['Student ID'] == search_id]
            st.dataframe(results)

# Handle fingerprint authentication results
html("""
<script>
window.addEventListener('message', (event) => {
    if (event.data.type === 'fingerprintRegistration') {
        alert(`Fingerprint registered for student ${event.data.studentId}`);
    }
    if (event.data.type === 'fingerprintAuth') {
        if (event.data.success) {
            // Record attendance when fingerprint authentication succeeds
            const studentId = event.data.studentId;
            const xhr = new XMLHttpRequest();
            xhr.open("POST", "/", true);
            xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
            xhr.send(`fingerprint_auth=${studentId}`);
        } else {
            alert(`Authentication failed: ${event.data.error}`);
        }
    }
});
</script>
""")

# Handle fingerprint authentication from JavaScript
if st.experimental_get_query_params().get("fingerprint_auth"):
    student_id = st.experimental_get_query_params()["fingerprint_auth"][0]
    record_attendance(student_id, "Fingerprint")
