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
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method', 'Photo'])
        
if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Registered'])

if 'registered_students' not in st.session_state:
    st.session_state.registered_students = {}

# Create data directory
os.makedirs('data', exist_ok=True)
os.makedirs('data/faces', exist_ok=True)

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "your_password"       # Replace with your password

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

def record_attendance(student_id, method, photo_path=None):
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
            new_entry = pd.DataFrame([[student_id, student_name, student_email, now, None, method, photo_path]], 
                                  columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method', 'Photo'])
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

def get_image_download_link(img_path, student_id):
    with open(img_path, "rb") as f:
        img_data = f.read()
    b64 = base64.b64encode(img_data).decode()
    href = f'<a href="data:image/jpg;base64,{b64}" download="{student_id}.jpg">Download Photo</a>'
    return href

# Main App Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Login/Register", "Mark Attendance", "View Attendance", "Professor Portal"])

with tab1:
    st.header("Student Registration/Login")
    
    # Check if student is already registered
    student_id = st.text_input("Enter Student ID")
    
    if student_id:
        # Check if student exists
        student_exists = not st.session_state.student_data[
            st.session_state.student_data['Student ID'] == student_id
        ].empty
        
        if student_exists:
            st.success("Student ID found. Please mark your attendance in the 'Mark Attendance' tab.")
        else:
            st.warning("Student ID not found. Please register below.")
            
            with st.form("registration_form"):
                student_name = st.text_input("Full Name")
                student_email = st.text_input("Email Address")
                
                submitted = st.form_submit_button("Register")
                if submitted:
                    if student_name and student_email:
                        new_student = pd.DataFrame([[student_id, student_name, student_email, False]], 
                                                 columns=['Student ID', 'Name', 'Email', 'Registered'])
                        st.session_state.student_data = pd.concat([st.session_state.student_data, new_student], ignore_index=True)
                        st.session_state.student_data.to_csv('data/students.csv', index=False)
                        st.success(f"Student {student_name} registered! Please take your photo for face recognition.")
                        
                        # Take photo after registration
                        picture = st.camera_input("Take a picture for face recognition")
                        if picture:
                            img_path = f"data/faces/{student_id}.jpg"
                            with open(img_path, "wb") as f:
                                f.write(picture.getbuffer())
                            st.session_state.registered_students[student_id] = True
                            st.session_state.student_data.loc[
                                st.session_state.student_data['Student ID'] == student_id, 'Registered'
                            ] = True
                            st.session_state.student_data.to_csv('data/students.csv', index=False)
                            st.success("Face registered! You can now mark your attendance.")

with tab2:
    st.header("Mark Attendance")
    
    if 'student_id' not in st.session_state:
        st.session_state.student_id = ""
    
    student_id = st.text_input("Enter Student ID", key="attendance_id")
    
    if student_id:
        # Check if student is registered
        student_info = st.session_state.student_data[
            st.session_state.student_data['Student ID'] == student_id
        ]
        
        if not student_info.empty:
            if student_info['Registered'].values[0]:
                method = st.radio("Authentication Method", ["Face Recognition", "Fingerprint"])
                
                if method == "Face Recognition":
                    picture = st.camera_input("Take a picture for attendance")
                    
                    if picture:
                        # Convert image to OpenCV format
                        img_bytes = picture.getvalue()
                        img_array = np.frombuffer(img_bytes, np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        # Check if face is detected
                        if detect_faces(img):
                            # Save the attendance photo
                            photo_path = f"data/faces/attendance_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            with open(photo_path, "wb") as f:
                                f.write(picture.getbuffer())
                            record_attendance(student_id, "Face Recognition", photo_path)
                        else:
                            st.warning("No face detected - please try again")
                
                elif method == "Fingerprint":
                    # Simulate fingerprint authentication (in a real app, this would connect to a fingerprint sensor)
                    if st.button("Authenticate with Fingerprint"):
                        # In a real implementation, this would interface with the device's fingerprint sensor
                        st.info("Fingerprint authentication would be performed here")
                        st.warning("This is a simulation. In a real app, this would connect to the device's fingerprint sensor.")
                        
                        # For demo purposes, we'll just record the attendance
                        record_attendance(student_id, "Fingerprint")
            else:
                st.warning("Please complete registration by taking your photo in the Registration tab")
        else:
            st.warning("Student ID not found. Please register first.")

with tab3:
    st.header("Attendance Records")
    st.dataframe(st.session_state.attendance)
    
    if not st.session_state.attendance.empty:
        # Download CSV
        csv = st.session_state.attendance.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="attendance.csv">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

with tab4:
    st.header("Professor Portal")
    password = st.text_input("Enter password", type="password")
    
    if password == "admin123":  # Change this to a secure password in production
        st.success("Logged in as Professor")
        
        # View all attendance
        st.subheader("All Attendance Records")
        st.dataframe(st.session_state.attendance)
        
        # Search functionality
        st.subheader("Search Student")
        search_id = st.text_input("Search by Student ID")
        if search_id:
            results = st.session_state.attendance[st.session_state.attendance['Student ID'] == search_id]
            st.dataframe(results)
            
            # Show student photo if available
            photo_entries = results[results['Photo'].notna()]
            if not photo_entries.empty:
                latest_photo = photo_entries.iloc[-1]['Photo']
                if os.path.exists(latest_photo):
                    st.image(latest_photo, caption=f"Latest attendance photo for {search_id}", width=300)
                    st.markdown(get_image_download_link(latest_photo, search_id), unsafe_allow_html=True)
        
        # Download all photos
        st.subheader("Download All Photos")
        if st.button("Generate Photo Archive"):
            with st.spinner("Creating archive..."):
                # Create a zip file of all photos
                import zipfile
                from io import BytesIO
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk('data/faces'):
                        for file in files:
                            if file.startswith('attendance_'):
                                student_id = file.split('_')[1]
                                zipf.write(os.path.join(root, file), file)
                
                zip_buffer.seek(0)
                b64 = base64.b64encode(zip_buffer.read()).decode()
                href = f'<a href="data:file/zip;base64,{b64}" download="attendance_photos.zip">Download All Attendance Photos</a>'
                st.markdown(href, unsafe_allow_html=True)
    elif password:
        st.error("Incorrect password")
