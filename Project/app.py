from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from rembg import remove
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import os
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For secure session cookies

# Configure logging
logging.basicConfig(level=logging.INFO)

# Limit file size (max 10 MB)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

# Allowed file extensions for images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uploads.db'  # Using SQLite
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# User Uploads Table
class UploadedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)

# Initialize database
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            flash('Invalid file format. Only PNG, JPG, and JPEG are allowed.', 'danger')
            return redirect(request.url)
        
        try:
            input_image = Image.open(file.stream)
        except UnidentifiedImageError:
            flash('Invalid image file. Please upload a valid image.', 'danger')
            return redirect(request.url)
        
        try:
            output_image = remove(input_image, post_process_mask=True)
            img_io = BytesIO()
            output_image.save(img_io, 'PNG')
            img_io.seek(0)
            
            # Save file locally
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            input_image.save(filepath)
            
            # Save to Database
            new_upload = UploadedImage(filename=filename)
            db.session.add(new_upload)
            db.session.commit()
            
            return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='image_rmbg.png')
        
        except Exception as e:
            logging.error(f"Error during background removal: {e}")
            flash('Failed to remove background from the image. The background might not be suitable for removal.', 'danger')
            return redirect(request.url)
    
    uploads = UploadedImage.query.all()
    return render_template('index.html', uploads=uploads)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure database is initialized
    app.run(host='0.0.0.0', debug=False, port=5100)
