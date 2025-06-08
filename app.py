import os
import uuid
import shutil
import io
from flask import Flask, request, render_template, send_file, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import zipfile
import threading
import logging
import sys

# Import the necessary classes from your main application
from api_factory import create_ai_api
from text_extractor import TextExtractor
from page_classifier import PageClassifier
from chapter_generator import ChapterGenerator
from yaml_metadata_generator import YamlMetadataGenerator
from thesis_compiler import ThesisCompiler
from citation_generator import CitationGenerator
from figure_generator import FigureGenerator

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload and results directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('results', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track job status
jobs = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdf_file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['pdf_file']
    api_key = request.form.get('api_key', '')
    email = request.form.get('email', '')
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if not api_key:
        flash('API key is required')
        return redirect(request.url)
    
    if file and file.filename.endswith('.pdf'):
        # Create a unique job ID
        job_id = str(uuid.uuid4())
        
        # Create job directory
        job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(job_dir, filename)
        file.save(file_path)
        
        # Initialize job status
        jobs[job_id] = {
            'status': 'processing',
            'message': 'Job started',
            'filename': filename,
            'file_path': file_path,
            'result_path': None
        }
        
        # Start processing in a background thread
        thread = threading.Thread(
            target=process_pdf_background,
            args=(job_id, file_path, api_key, email)
        )
        thread.daemon = True
        thread.start()
        
        return redirect(url_for('job_status', job_id=job_id))
    
    flash('Invalid file type. Please upload a PDF file.')
    return redirect(request.url)

def process_pdf_background(job_id, file_path, api_key, email):
    try:
        # Get the debug folder path
        pdf_basename = os.path.splitext(os.path.basename(file_path))[0]
        debug_folder = os.path.join(os.path.dirname(file_path), f"{pdf_basename}_debug")
        os.makedirs(debug_folder, exist_ok=True)
        
        # Set up logging handler to capture log messages
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger = logging.getLogger()
        logger.addHandler(ch)
        
        # Update job status based on log messages
        def update_status_from_logs():
            log_contents = log_capture_string.getvalue()
            lines = log_contents.strip().split('\n')
            if lines:
                latest_line = lines[-1]
                jobs[job_id]['message'] = latest_line
        
        # Create AI API instance using factory (default to Gemini for web interface)
        ai_api = create_ai_api(
            provider='gemini',  # Default to Gemini for web interface
            model='gemini-2.5-pro-preview-06-05',
            gemini_api_key=api_key
        )
        
        # Call the main processing function with periodic status updates
        try:
            # Step 1: Extract text
            jobs[job_id]['message'] = "Step 1: Extracting text from PDF..."
            extractor = TextExtractor(file_path, ai_api)
            extracted_text_file = os.path.join(debug_folder, "extracted_text.txt")
            extracted_data = extractor.extract_text(extracted_text_file)
            if not extracted_data:
                raise RuntimeError("Text extraction failed")
            update_status_from_logs()
            
            # Step 2: Categorize pages
            jobs[job_id]['message'] = "Step 2: Categorizing pages..."
            classifier = PageClassifier(ai_api)
            categorized_content = classifier.classify_pages(extracted_text_file, debug_folder)
            if not categorized_content:
                raise RuntimeError("Page categorization failed")
            update_status_from_logs()
            
            # Step 3: Generate chapters
            jobs[job_id]['message'] = "Step 3: Generating chapters..."
            generator = ChapterGenerator(ai_api)
            generated_chapters = generator.generate_all_chapters(debug_folder, threads=4)
            if not generated_chapters:
                raise RuntimeError("Chapter generation failed")
            update_status_from_logs()
            
            # Step 4: Add citations
            jobs[job_id]['message'] = "Step 4: Adding citations to chapters..."
            citation_gen = CitationGenerator(ai_api, email)
            if not citation_gen.process_chapters(debug_folder, threads=4):
                raise RuntimeError("Citation generation failed")
            update_status_from_logs()
            
            # Step 5: Add figures
            jobs[job_id]['message'] = "Step 5: Adding figure references to chapters..."
            figure_gen = FigureGenerator(ai_api)
            if not figure_gen.process_chapters(debug_folder, threads=4):
                raise RuntimeError("Figure reference generation failed")
            update_status_from_logs()
            
            # Step 6: Generate YAML metadata
            jobs[job_id]['message'] = "Step 6: Generating YAML metadata..."
            metadata_gen = YamlMetadataGenerator(ai_api)
            metadata_file = os.path.join(debug_folder, "thesis_metadata.yaml")
            if not metadata_gen.generate_metadata(debug_folder, metadata_file):
                raise RuntimeError("YAML metadata generation failed")
            update_status_from_logs()
            
            # Step 7: Compile thesis
            jobs[job_id]['message'] = "Step 7: Compiling thesis..."
            compiler = ThesisCompiler()
            output_pdf = os.path.join(debug_folder, "thesis.pdf")
            if not compiler.compile_thesis(debug_folder, metadata_file, output_pdf):
                raise RuntimeError("Thesis compilation failed")
            update_status_from_logs()
            
            # All steps completed
            jobs[job_id]['message'] = "All steps completed successfully!"
            
        except Exception as e:
            # Update the message with the error
            error_message = f"Error: {str(e)}"
            jobs[job_id]['message'] = error_message
            jobs[job_id]['status'] = "failed"
            logger.error(error_message)
            logger.removeHandler(ch)
            return
        
        # Remove the log handler
        logger.removeHandler(ch)
        
        # Create a zip file with all results
        result_dir = os.path.join('results', job_id)
        os.makedirs(result_dir, exist_ok=True)
        
        zip_path = os.path.join(result_dir, 'thesis_package.zip')
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(debug_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, debug_folder)
                    zipf.write(file_path, arcname)
        
        # Update job status
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['result_path'] = zip_path
        jobs[job_id]['message'] = 'Processing completed successfully!'
        
    except Exception as e:
        jobs[job_id]['status'] = 'failed'
        jobs[job_id]['message'] = f'Error: {str(e)}'
        logger.error(f"Job {job_id} failed: {str(e)}")

@app.route('/job/<job_id>')
def job_status(job_id):
    if job_id not in jobs:
        flash('Job not found')
        return redirect(url_for('index'))
    
    job = jobs[job_id]
    return render_template('job_status.html', job=job, job_id=job_id)

@app.route('/api/job/<job_id>')
def api_job_status(job_id):
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(jobs[job_id])

@app.route('/download/<job_id>')
def download_results(job_id):
    if job_id not in jobs or jobs[job_id]['status'] != 'completed':
        flash('Results not available')
        return redirect(url_for('index'))
    
    result_path = jobs[job_id]['result_path']
    if not os.path.exists(result_path):
        flash('Result file not found')
        return redirect(url_for('index'))
    
    return send_file(result_path, as_attachment=True, download_name='thesis_package.zip')

if __name__ == '__main__':
    app.run(debug=True) 