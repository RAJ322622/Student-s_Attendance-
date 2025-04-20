import streamlit as st
import cv2
import numpy as np
from datetime import datetime
import os
import pandas as pd
import face_recognition
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from streamlit.components.v1 import html
import csv

# Initialize session state and data storage
if 'attendance' not in st.session_state:
    if os.path.exists('data/attendance.csv'):
        st.session_state.attendance = pd.read_csv('data/attendance.csv')
    else:
        st.session_state.attendance = pd.DataFrame(columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method'])
        
if 'known_face_encodings' not in st.session_state:
    st.session_state.known_face_encodings = []
if 'known_face_names' not in st.session_state:
    st.session_state.known_face_names = []
if 'student_data' not in st.session_state:
    if os.path.exists('data/students.csv'):
        st.session_state.student_data = pd.read_csv('data/students.csv')
    else:
        st.session_state.student_data = pd.DataFrame(columns=['Student ID', 'Name', 'Email'])

# Create data directory if not exists
os.makedirs('data', exist_ok=True)
os.makedirs('data/faces', exist_ok=True)

# Email configuration (replace with your SMTP details)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # Use app-specific password for Gmail

# Page config
st.set_page_config(page_title="Student Attendance System", layout="wide")

# Title
st.title("Student Attendance System")
st.subheader("With Email Notifications and Professor Portal")

# Function to send email
def send_email(to_email, student_name, time_in=None, time_out=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email
        msg['Subject'] = "Attendance Notification"
        
        if time_out:
            body = f"""
            <html>
                <body>
                    <p>Dear {student_name},</p>
                    <p>You have been marked present today:</p>
                    <ul>
                        <li>Time In: {time_in}</li>
                        <li>Time Out: {time_out}</li>
                    </ul>
                    <p>Thank you!</p>
                </body>
            </html>
            """
        else:
            body = f"""
            <html>
                <body>
                    <p>Dear {student_name},</p>
                    <p>Your attendance has been recorded at {time_in}.</p>
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
        st.error(f"Failed to send email: {str(e)}")
        return False

# Sidebar for registration
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
            st.success(f"Student {student_name} registered successfully!")
        else:
            st.error("Please fill all fields")

    # Face registration
    st.write("Register Face")
    picture = st.camera_input("Take a picture for face registration")
    
    if picture and student_id:
        # Save the image
        img_path = f"data/faces/{student_id}.jpg"
        with open(img_path, "wb") as f:
            f.write(picture.getbuffer())
        
        # Load and encode the face
        image = face_recognition.load_image_file(img_path)
        face_encodings = face_recognition.face_encodings(image)
        
        if len(face_encodings) > 0:
            st.session_state.known_face_encodings.append(face_encodings[0])
            st.session_state.known_face_names.append(student_id)
            st.success(f"Face registered for ID: {student_id}")
        else:
            st.error("No face detected in the image. Please try again.")

# Main content
tab1, tab2, tab3 = st.tabs(["Mark Attendance", "View Attendance", "Professor Portal"])

with tab1:
    st.header("Mark Attendance")
    
    # JavaScript for fingerprint sensor
    fingerprint_js = """
    <script>
    async function requestFingerprint() {
        try {
            // Note: Actual WebAuthn implementation would be more complex
            const credential = await navigator.credentials.get({
                publicKey: {
                    challenge: new Uint8Array([1,2,3,4,5,6,7,8]).buffer,
                    rpId: window.location.hostname,
                    allowCredentials: [{
                        type: 'public-key',
                        id: new Uint8Array([1,2,3,4]),
                        transports: ['internal']
                    }],
                    userVerification: 'required'
                }
            });
            
            // Send the fingerprint data to Streamlit
            window.parent.postMessage({
                type: 'fingerprintResult',
                success: true,
                studentId: document.getElementById('fingerprint_id').value
            }, '*');
            
        } catch (err) {
            window.parent.postMessage({
                type: 'fingerprintResult',
                success: false,
                error: err.message
            }, '*');
        }
    }
    </script>
    <input type="text" id="fingerprint_id" placeholder="Enter your student ID">
    <button onclick="requestFingerprint()">Authenticate with Fingerprint</button>
    """
    
    # Fingerprint attendance
    st.markdown("### Fingerprint Attendance")
    st.components.v1.html(fingerprint_js, height=100)
    
    # Face recognition attendance
    st.markdown("### Face Recognition Attendance")
    picture = st.camera_input("Take a picture for attendance")
    
    if picture:
        # Convert the image to numpy array
        img_bytes = picture.getvalue()
        img_array = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        # Convert to RGB (face_recognition uses RGB)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(rgb_img)
        face_encodings = face_recognition.face_encodings(rgb_img, face_locations)
        
        for face_encoding in face_encodings:
            # Compare with known faces
            matches = face_recognition.compare_faces(st.session_state.known_face_encodings, face_encoding)
            name = "Unknown"
            
            if True in matches:
                first_match_index = matches.index(True)
                student_id = st.session_state.known_face_names[first_match_index]
                
                # Check if student exists
                student_info = st.session_state.student_data[st.session_state.student_data['Student ID'] == student_id]
                
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
                        new_entry = pd.DataFrame([[student_id, student_name, student_email, now, None, "Face Recognition"]], 
                                              columns=['Student ID', 'Name', 'Email', 'Time In', 'Time Out', 'Method'])
                        st.session_state.attendance = pd.concat([st.session_state.attendance, new_entry], ignore_index=True)
                        st.success(f"Time In recorded for {student_name} at {now}")
                        
                        # Send email notification
                        if send_email(student_email, student_name, time_in=now):
                            st.success("Notification email sent!")
                    else:
                        # Time Out
                        idx = existing_entry.index[0]
                        st.session_state.attendance.at[idx, 'Time Out'] = now
                        st.success(f"Time Out recorded for {student_name} at {now}")
                        
                        # Send email with both times
                        time_in = st.session_state.attendance.at[idx, 'Time In']
                        if send_email(student_email, student_name, time_in=time_in, time_out=now):
                            st.success("Notification email sent!")
                    
                    # Save to CSV
                    st.session_state.attendance.to_csv('data/attendance.csv', index=False)
                else:
                    st.warning("Student ID not found in database")
            else:
                st.warning("No matching face found in database")

with tab2:
    st.header("Attendance Records")
    st.dataframe(st.session_state.attendance)
    
    # Download button
    if not st.session_state.attendance.empty:
        csv = st.session_state.attendance.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="attendance.csv">Download CSV</a>'
        st.markdown(href, unsafe_allow_html=True)

with tab3:
    st.header("Professor Portal")
    
    # Authentication
    professor_password = st.text_input("Enter Professor Password", type="password")
    
    if professor_password == "prof123":  # Replace with secure password handling
        st.success("Authenticated")
        
        # Student lookup
        st.subheader("Student Lookup")
        search_id = st.text_input("Enter Student ID")
        
        if search_id:
            student_records = st.session_state.attendance[st.session_state.attendance['Student ID'] == search_id]
            
            if not student_records.empty:
                st.dataframe(student_records)
                
                # Download button for individual student
                csv = student_records.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="attendance_{search_id}.csv">Download This Student\'s Records</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("No attendance records found for this student")
        
        # Full data download
        st.subheader("Download All Attendance Data")
        if not st.session_state.attendance.empty:
            csv = st.session_state.attendance.to_csv(index=False)
            b64 = base64.b64encode(csv.encode()).decode()
            href = f'<a href="data:file/csv;base64,{b64}" download="full_attendance.csv">Download Full Attendance Data</a>'
            st.markdown(href, unsafe_allow_html=True)
    elif professor_password:
        st.error("Incorrect password")

# Handle fingerprint results from JavaScript
fingerprint_js_handler = """
<script>
window.addEventListener('message', function(event) {
    if (event.data.type === 'fingerprintResult') {
        if (event.data.success) {
            // In a real app, you would send this data to Python via a custom component
            alert(`Fingerprint authentication successful for student ${event.data.studentId}`);
            
            // Here we would normally send the student ID to Streamlit
            // For this demo, we'll just show an alert
        } else {
            alert("Fingerprint authentication failed: " + event.data.error);
        }
    }
});
</script>
"""
st.components.v1.html(fingerprint_js_handler, height=0)
