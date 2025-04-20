import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import os
import pandas as pd
from deepface import DeepFace  # Replaced face_recognition
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email'])

# Create data directory
os.makedirs('data', exist_ok=True)
os.makedirs('data/faces', exist_ok=True)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"

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
    picture = st.camera_input("Take a picture for attendance")
    
    if picture:
        # Save temp image
        temp_img = "data/temp_attendance.jpg"
        with open(temp_img, "wb") as f:
            f.write(picture.getbuffer())
        
        # Find closest match in database
        try:
            db_path = "data/faces"
            if os.path.exists(db_path) and len(os.listdir(db_path)) > 0:
                df = DeepFace.find(img_path=temp_img, db_path=db_path, enforce_detection=False)
                
                if len(df) > 0 and not df[0].empty:
                    best_match = df[0].iloc[0]
                    student_id = os.path.splitext(os.path.basename(best_match['identity']))[0]
                    student_info = st.session_state.student_data[st.session_state.student_data['Student ID'] == student_id]
                    
                    if not student_info.empty:
                        student_name = student_info['Name'].values[0]
                        student_email = student_info['Email'].values[0]
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Check existing attendance
                        existing = st.session_state.attendance[
                            (st.session_state.attendance['Student ID'] == student_id) & 
                            (st.session_state.attendance['Time Out'].isna())
                        ]
                        
                        if existing.empty:
                            # Time In
                            new_entry = pd.DataFrame([[student_id, student_name, student_email, now, None, "Face Recognition"]], 
                                                  columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method'])
                            st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
                            st.success(f"Time In: {student_name} at {now}")
                            send_email(student_email, student_name, time_in=now)
                        else:
                            # Time Out
                            idx = existing.index[0]
                            st.session_state.attendance.at[idx, 'Time Out'] = now
                            st.success(f"Time Out: {student_name} at {now}")
                            send_email(student_email, student_name, 
                                     time_in=st.session_state.attendance.at[idx, 'Time In'], 
                                     time_out=now)
                        
                        st.session_state.attendance.to_csv('data/attendance.csv', index=False)
                    else:
                        st.warning("Student not found in database")
                else:
                    st.warning("No matching face found")
            else:
                st.warning("No faces registered in database")
        except Exception as e:
            st.error(f"Face detection error: {str(e)}")

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
