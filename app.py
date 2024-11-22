from flask import Flask, render_template, request, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
from PIL import Image
import os
import zipfile
from io import BytesIO
import magic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')  # Use .env for sensitive keys
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'static/uploads/')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp', 'heic', 'bmp', 'tiff', 'tif'}
ALLOWED_MIME_TYPES = {
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/svg+xml',
    'image/webp',
    'image/heic',
    'image/bmp',
    'image/tiff'
}



def allowed_file(filename, file, allowed_extensions=ALLOWED_EXTENSIONS):
    # Check if the file has a valid extension
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return False

    # Check MIME type using python-magic
    file.seek(0)  # Reset file pointer to the beginning
    mime = magic.Magic(mime=True)
    file_type = mime.from_buffer(file.read(2048))
    file.seek(0)  # Reset file pointer to the beginning

    # Validate MIME type
    if file_type not in ALLOWED_MIME_TYPES:
        return False

    return True




@app.route('/')
def landing_page():
    # Render the landing page (index.html) with links to tools and blogs
    return render_template('index.html')


@app.route('/favicon-generator', methods=['GET', 'POST'])
def favicon_generator():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type and size
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file
            session['uploaded_image'] = filename
            return redirect(url_for('crop_image'))
        else:
            return "Invalid file type. Please upload a valid image.", 400
    return render_template('favicon-generator.html')

@app.route('/crop', methods=['GET', 'POST'])
def crop_image():
    filename = session.get('uploaded_image', None)
    if not filename:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Handle cropping inputs
            x = float(request.form.get('x'))
            y = float(request.form.get('y'))
            width = float(request.form.get('width'))
            height = float(request.form.get('height'))
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Open image and crop
            image = Image.open(filepath)
            cropped_image = image.crop((x, y, x + width, y + height))

            # Sizes for .ico generation
            ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

            # Generate .ico file
            ico_path = os.path.join(app.config['UPLOAD_FOLDER'], 'favicon.ico')
            cropped_image.save(ico_path, format='ICO', sizes=ico_sizes)

            # Generate individual PNG favicons
            sizes = [
                (16, 'favicon-16x16.png'),
                (32, 'favicon-32x32.png'),
                (48, 'favicon-48x48.png'),
                (180, 'apple-touch-icon.png'),
                (192, 'android-chrome-192x192.png'),
                (512, 'android-chrome-512x512.png')
            ]

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zip_file:
                # Add .ico file to the ZIP archive
                with open(ico_path, 'rb') as ico_file:
                    zip_file.writestr('favicon.ico', ico_file.read())

                # Add individual PNG files
                for size, icon_filename in sizes:
                    resized_image = cropped_image.resize((size, size), Image.Resampling.LANCZOS)
                    img_byte_arr = BytesIO()
                    resized_image.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)
                    zip_file.writestr(icon_filename, img_byte_arr.read())

            zip_buffer.seek(0)

            # Save ZIP temporarily
            zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'favicons.zip')
            with open(zip_path, 'wb') as f:
                f.write(zip_buffer.getvalue())

            return redirect(url_for('download'))
        except Exception as e:
            return f"An error occurred during cropping or favicon generation: {str(e)}", 500
    return render_template('crop.html', filename=filename)


# Image to PDF Routes

@app.route('/jpg-to-pdf', methods=['GET', 'POST'])
def jpg_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the JPG to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid JPG or JPEG image.", 400

    return render_template('jpg-to-pdf.html')

@app.route('/png-to-pdf', methods=['GET', 'POST'])
def png_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'png'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the PNG to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid PNG image.", 400

    return render_template('png-to-pdf.html')

# SVG to PDF Route
@app.route('/svg-to-pdf', methods=['GET', 'POST'])
def svg_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'svg'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the SVG to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid SVG file.", 400

    return render_template('svg-to-pdf.html')


# WebP to PDF Route
@app.route('/webp-to-pdf', methods=['GET', 'POST'])
def webp_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'webp'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the WebP to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid WebP file.", 400

    return render_template('webp-to-pdf.html')


# HEIC to PDF Route
@app.route('/heic-to-pdf', methods=['GET', 'POST'])
def heic_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'heic'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the HEIC to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid HEIC file.", 400

    return render_template('heic-to-pdf.html')

@app.route('/bmp-to-pdf', methods=['GET', 'POST'])
def bmp_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'bmp'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the BMP to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid BMP file.", 400

    return render_template('bmp-to-pdf.html')


@app.route('/tiff-to-pdf', methods=['GET', 'POST'])
def tiff_to_pdf():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file, allowed_extensions={'tiff', 'tif'}):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the TIFF to PDF
            try:
                image = Image.open(filepath)
                pdf_path = os.path.splitext(filepath)[0] + ".pdf"  # Replace extension with .pdf
                image.save(pdf_path, "PDF", resolution=100.0)

                # Return the PDF for download
                return send_file(pdf_path, mimetype='application/pdf', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.pdf")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid TIFF file.", 400

    return render_template('tiff-to-pdf.html')


# Image Conversion between types

@app.route('/convert-to-jpeg', methods=['GET', 'POST'])
def convert_to_jpeg():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the image to JPEG
            try:
                image = Image.open(filepath)
                rgb_image = image.convert('RGB')  # Ensure compatibility with JPEG
                jpeg_path = os.path.splitext(filepath)[0] + ".jpeg"  # Replace extension with .jpeg
                rgb_image.save(jpeg_path, "JPEG", quality=95)  # High-quality JPEG

                # Return the JPEG for download
                return send_file(jpeg_path, mimetype='image/jpeg', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.jpeg")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid image.", 400

    return render_template('convert-to-jpeg.html')

@app.route('/convert-to-tiff', methods=['GET', 'POST'])
def convert_to_tiff():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the image to TIFF
            try:
                image = Image.open(filepath)
                tiff_path = os.path.splitext(filepath)[0] + ".tiff"  # Replace extension with .tiff
                image.save(tiff_path, "TIFF", compression="tiff_deflate")  # TIFF format with compression

                # Return the TIFF for download
                return send_file(tiff_path, mimetype='image/tiff', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.tiff")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid image.", 400

    return render_template('convert-to-tiff.html')


@app.route('/convert-to-png', methods=['GET', 'POST'])
def convert_to_png():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the image to PNG
            try:
                image = Image.open(filepath)
                png_path = os.path.splitext(filepath)[0] + ".png"  # Replace extension with .png
                image.save(png_path, "PNG")  # PNG format

                # Return the PNG for download
                return send_file(png_path, mimetype='image/png', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.png")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid image.", 400

    return render_template('convert-to-png.html')


@app.route('/convert-to-heic', methods=['GET', 'POST'])
def convert_to_heic():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the image to HEIC
            try:
                image = Image.open(filepath)
                heic_path = os.path.splitext(filepath)[0] + ".heic"  # Replace extension with .heic
                image.save(heic_path, "HEIC")  # HEIC format

                # Return the HEIC for download
                return send_file(heic_path, mimetype='image/heic', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.heic")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid image.", 400

    return render_template('convert-to-heic.html')


@app.route('/convert-to-webp', methods=['GET', 'POST'])
def convert_to_webp():
    if request.method == 'POST':
        # Validate file presence in request
        if 'file' not in request.files:
            return "No file part in the request", 400

        file = request.files['file']
        if file.filename == '':
            return "No file selected for upload", 400

        # Validate file type
        if file and allowed_file(file.filename, file):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            os.chmod(filepath, 0o600)  # Set secure permissions for uploaded file

            # Convert the image to WebP
            try:
                image = Image.open(filepath)
                webp_path = os.path.splitext(filepath)[0] + ".webp"  # Replace extension with .webp
                image.save(webp_path, "WEBP", quality=95)  # WebP format with high quality

                # Return the WebP for download
                return send_file(webp_path, mimetype='image/webp', as_attachment=True, download_name=f"{os.path.splitext(filename)[0]}.webp")
            except Exception as e:
                return f"An error occurred during conversion: {str(e)}", 500
        else:
            return "Invalid file type. Please upload a valid image.", 400

    return render_template('convert-to-webp.html')


@app.route('/download')
def download():
    return render_template('download.html')

@app.route('/download_zip')
def download_zip():
    try:
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], 'favicons.zip')
        return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name='favicons.zip')
    except FileNotFoundError:
        return "ZIP file not found. Please regenerate the favicons.", 404

@app.errorhandler(413)
def file_too_large(error):
    return "File size exceeds the 16MB limit. Please upload a smaller file.", 413

@app.route('/blog')
def blog():
    return render_template('blog.html')


if __name__ == '__main__':
    app.run(debug=True)
