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

# Initialize face detector
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize session state
if 'attendance' not in st.session_state:
    if os.path.exists('data/attendance.csv'):
        st.session_state.attendance = pd.read_csv('data/attendance.csv')
    else:
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time', 'Method'])
        
if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email'])

# Create data directory
os.makedirs('data', exist_ok=True)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

# Simplified face detection function
def detect_faces(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return len(faces) > 0

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

# Student Registration
with st.sidebar:
    st.header("Student Registration")
    student_id = st.text_input("Student ID")
    student_name = st.text_input("Full Name")
    student_email = st.text_input("Email Address")
    
    if st.button("Register Student"):
        if student_id and student_name and student_email:
            new_student = pd.DataFrame([[student_id, student_name, student_email]], 
                                     columns=['Student ID', 'Name', 'Email'])
            st.session_state.student_data = pd.concat([st.session_state.student_data, new_student], ignore_index=True)
            st.session_state.student_data.to_csv('data/students.csv', index=False)
            st.success(f"Student {student_name} registered!")
        else:
            st.error("Please fill all fields")

    # Face registration
    st.write("Register Face")
    picture = st.camera_input("Take a picture")
    
    if picture and student_id:
        img_path = f"data/faces/{student_id}.jpg"
        with open(img_path, "wb") as f:
            f.write(picture.getbuffer())
        st.success(f"Face registered for ID: {student_id}")

# Main App
tab1, tab2, tab3 = st.tabs(["Mark Attendance", "View Attendance", "Professor Portal"])

with tab1:
    st.header("Mark Attendance")
    student_id = st.text_input("Enter your Student ID")
    picture = st.camera_input("Take a picture for attendance")
    
    if picture and student_id:
        # Convert image to OpenCV format
        img_bytes = picture.getvalue()
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Check if face is detected
        if detect_faces(img):
            # Check student exists
            student_info = st.session_state.student_data[
                st.session_state.student_data['Student ID'] == student_id
            ]
            
            if not student_info.empty:
                student_name = student_info['Name'].values[0]
                student_email = student_info['Email'].values[0]
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Record attendance
                new_entry = pd.DataFrame([[student_id, student_name, student_email, now, "Face Detection"]], 
                                      columns=['Student ID', 'Name', 'Email', 'Time', 'Method'])
                st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
                st.session_state.attendance.to_csv('data/attendance.csv', index=False)
                st.success(f"Attendance recorded for {student_name}")
                
                # Send email
                send_email(student_email, student_name, time_in=now)
            else:
                st.warning("Student ID not found")
        else:
            st.warning("No face detected - please try again")

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
