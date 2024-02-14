from PyPDF2 import PdfFileReader
import io
import streamlit as st
from PIL import Image
import sqlite3
import fitz
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Define sender_email and sender_password globally
sender_email = ""
sender_password = ""

# Function to initialize the database
def initialize_database():
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY, name TEXT, expiry_date TEXT, file_path TEXT, recipient_email TEXT)''')
    # Check if the recipient_email column exists, if not, add it
    c.execute("PRAGMA table_info(documents)")
    columns = c.fetchall()
    column_names = [col[1] for col in columns]
    if 'recipient_email' not in column_names:
        c.execute("ALTER TABLE documents ADD COLUMN recipient_email TEXT")
    conn.commit()
    conn.close()

# Function to add a new document
def add_document(name, expiry_date, file_path, recipient_email):
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute("INSERT INTO documents (name, expiry_date, file_path, recipient_email) VALUES (?, ?, ?, ?)", 
              (name, expiry_date, file_path, recipient_email))
    conn.commit()
    conn.close()

# Function to delete a document
def delete_document(document_id):
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute("DELETE FROM documents WHERE id=?", (document_id,))
    conn.commit()
    conn.close()

# Function to get all documents
def get_documents():
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute("SELECT * FROM documents")
    documents = c.fetchall()
    conn.close()
    return documents

# Function to check for documents approaching expiry within a threshold and send email reminders
def send_expiry_reminder_email(approaching_expiry_documents):
    global sender_email, sender_password
    for document in approaching_expiry_documents:
        if 1 <= len(document) <= 50:  # Check if the length of the tuple is within the specified range
            recipient_email = document[4]  # Assuming the email is stored in the database
            subject = "Document Expiry Reminder"
            body = f"Dear User,\n\nThis is a reminder that your document '{document[1]}' is approaching expiry on {document[2]}.\n\nPlease take necessary action.\n\nRegards,\nYour App"
            
            # Send email
            message = MIMEMultipart()
            message['From'] = sender_email
            message['To'] = recipient_email
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            text = message.as_string()
            server.sendmail(sender_email, recipient_email, text)
            server.quit()
        else:
            print("Error: Tuple length is not within the specified range for sending email reminder.")

# Function to check for documents approaching expiry within a threshold
def check_expiry_reminders(threshold_days=7):
    today = datetime.today().date()
    expiry_threshold = today + timedelta(days=threshold_days)
    conn = sqlite3.connect('documents.db')
    c = conn.cursor()
    c.execute("SELECT * FROM documents WHERE expiry_date <= ?", (expiry_threshold,))
    approaching_expiry_documents = c.fetchall()
    conn.close()
    return approaching_expiry_documents

# Function to extract images from PDF
def extract_images_from_pdf(file_path):
    images = []
    doc = fitz.open(file_path)
    for page in doc:
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            images.append(image_bytes)
    return images

def upload_page():
    st.title('Upload Document')
    name = st.text_input('Document Name')
    expiry_date = st.date_input('Expiry Date')
    file_path = st.file_uploader("Upload PDF File", type="pdf")
    recipient_email = st.text_input('Recipient Email')
    global sender_email, sender_password
    sender_email = st.text_input('Sender Email')
    sender_password = st.text_input('Sender Password', type='password')
    if st.button('Add Document'):
        if file_path is not None:
            add_document(name, expiry_date, file_path.name, recipient_email)
            st.success('Document added successfully!')
            st.balloons()  # Display balloons animation when document is added
        else:
            st.error('Please upload a PDF file')

def display_page():
    st.title('All Documents')
    documents = get_documents()
    for document in documents:
        st.write(f"{document[1]} - Expiry Date: {document[2]}")
        if document[3]:
            images = extract_images_from_pdf(document[3])
            st.write('<div style="display:flex; flex-direction: row;">', unsafe_allow_html=True)
            for i, image in enumerate(images):
                image = Image.open(io.BytesIO(image))
                resized_image = image.resize((150, 150))  # Resize image
                st.image(resized_image, caption=f"Document {document[1]} Image {i+1}")
            st.write('</div>', unsafe_allow_html=True)
        if st.button(f"Delete {document[1]}"):
            delete_document(document[0])
            st.success(f"Document {document[1]} deleted successfully!")
            st.balloons()  # Display balloons animation when document is deleted
            break

    # Expired Documents
    st.header('Expired Documents')
    expired_documents = check_expiry_reminders(0)  # Check for expired documents
    for document in expired_documents:
        st.write(f"{document[1]} - Expiry Date: {document[2]}")

    # Documents Approaching Expiry
    st.header('Documents Approaching Expiry')
    approaching_expiry_documents = check_expiry_reminders(7)  # Check for documents approaching expiry within 7 days
    if approaching_expiry_documents:
        st.write("The following documents are approaching expiry:")
        for document in approaching_expiry_documents:
            st.write(f"{document[1]} - Expiry Date: {document[2]}")
        if st.button('Send Expiry Reminder Email'):
            send_expiry_reminder_email(approaching_expiry_documents)
            st.success('Expiry reminder emails sent successfully!')
            st.balloons()  # Display balloons animation when reminder emails are sent

def main():
    initialize_database()  # Initialize the database schema
    st.sidebar.title('Navigation')
    page = st.sidebar.radio("Go to", ('Upload Document', 'All Documents'))

    if page == 'Upload Document':
        upload_page()
    elif page == 'All Documents':
        display_page()

if __name__ == '__main__':
    main()