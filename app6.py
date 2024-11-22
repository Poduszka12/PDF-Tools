from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import fitz  # PyMuPDF
import logging
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE_OUTPUT_PATH = r"Your_output_path"  # Output folder path
FOLDERS = {
    "csv_links": os.path.join(BASE_OUTPUT_PATH, "CSV Links")
}

# Create main folders if they do not exist
for folder in FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

# Logging settings
logging.basicConfig(level=logging.DEBUG)


def remove_spaces(text):
    return text.replace(" ", "")

LOG_FOLDER = r"Logs_path"  # Logs folder path
os.makedirs(LOG_FOLDER, exist_ok=True)

def get_output_path(input_path):
    base, ext = os.path.splitext(input_path)
    return f"{base}_OCR{ext}"

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Retrieve action from the form
        action = request.form.get('action')
        if action == 'csv_search':
            directory_paths = request.form.get('directory_paths', '')
            base_link = request.form.get('base_link', '').strip()

            if not directory_paths:
                flash('Please provide directory paths to process.')
                return redirect(url_for('index'))

            if not base_link:
                flash('Please provide the base link.')
                return redirect(url_for('index'))

            # Ensure the base link ends with '/'
            if not base_link.endswith('/'):
                base_link += '/'

            csv_path = r"CSV_path"  # CSV file path
            directory_list = [d.strip() for d in directory_paths.split(',') if d.strip()]
            total_links = 0
            manufacturer_stats = {}  # Dictionary to store statistics for each manufacturer
            manufacturer_files = {}

            try:
                # Collect PDF files by manufacturer
                for directory in directory_list:
                    if not os.path.exists(directory):
                        flash(f'Folder does not exist: {directory}')
                        continue

                    for root, dirs, files in os.walk(directory):
                        dirs.sort()
                        files.sort()
                        for file in files:
                            if file.lower().endswith('.pdf'):
                                pdf_path = os.path.join(root, file)
                                producer = os.path.basename(os.path.dirname(pdf_path))

                                if producer not in manufacturer_files:
                                    manufacturer_files[producer] = []
                                manufacturer_files[producer].append(pdf_path)

                # Clear the summary log at the beginning
                total_log_path = os.path.join(LOG_FOLDER, "log.txt")
                with open(total_log_path, 'w', encoding='utf-8') as f:
                    pass  # Clear the file

                # Processing files for each manufacturer
                for producer, files in manufacturer_files.items():
                    csv_symbols = load_csv_symbols(csv_path, producer)
                    if not csv_symbols:
                        logging.error(f"No symbols found for manufacturer: {producer}")
                        flash(f"No symbols found for manufacturer: {producer}")
                        continue

                    # Initialize statistics for the manufacturer
                    manufacturer_stats[producer] = {
                        'total_pages': 0,
                        'pages_with_text': 0,
                        'total_links_added': 0,
                        'pdfs': [],
                        'error_pdfs': []
                    }

                    for pdf_path in files:
                        # Process the PDF file with error handling
                        links_added, pdf_stats = process_pdf_with_csv(pdf_path, producer, csv_symbols, base_link)

                        if pdf_stats['total_pages'] == 0:
                            # Add the file to the list of erroneous files
                            manufacturer_stats[producer]['error_pdfs'].append(os.path.basename(pdf_path))
                        else:
                            # Update manufacturer statistics
                            manufacturer_stats[producer]['total_pages'] += pdf_stats['total_pages']
                            manufacturer_stats[producer]['pages_with_text'] += pdf_stats['pages_with_text']
                            manufacturer_stats[producer]['total_links_added'] += links_added
                            manufacturer_stats[producer]['pdfs'].append({
                                'pdf_name': os.path.basename(pdf_path),
                                'total_pages': pdf_stats['total_pages'],
                                'pages_with_text': pdf_stats['pages_with_text'],
                                'ratio': pdf_stats['pages_with_text'] / pdf_stats['total_pages'] if pdf_stats['total_pages'] > 0 else 0,
                                'links_in_pdf': links_added  # Add the number of links in this PDF
                            })

                    # Save logs for the current manufacturer
                    save_logs(producer, manufacturer_stats[producer])

                flash('PDF processing with CSV completed.')
                return redirect(url_for('index'))

            except Exception as e:
                logging.error(f"Error during PDF processing with CSV: {e}")
                flash(f"An error occurred: {e}")
                return redirect(url_for('index'))

    return render_template('index.html')

def load_csv_symbols(csv_path, producer):
    try:
        # Load data from CSV with semicolon delimiter
        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            csv_data = [row for row in reader]

        # Filter data for the specified manufacturer
        producer_lower = producer.lower()
        producer_symbols = {}
        for row in csv_data:
            name = row.get('Name', '').strip().lower()
            if name == producer_lower:
                symbol = remove_spaces(row.get('Symbol', '').strip())
                symbol_1 = remove_spaces(row.get('Symbol_1', '').strip())
                if symbol and symbol_1:
                    producer_symbols[symbol] = symbol_1

        return producer_symbols

    except Exception as e:
        logging.error(f"Error loading CSV data for manufacturer {producer}: {e}")
        return {}

def process_pdf_with_csv(pdf_path, producer, producer_symbols, base_link):
    try:
        logging.info(f"Starting PDF processing with CSV: {pdf_path}, Manufacturer: {producer}")

        producer_folder = producer.strip().title()
        output_folder = os.path.join(FOLDERS["csv_links"], producer_folder)
        os.makedirs(output_folder, exist_ok=True)

        if not producer_symbols:
            logging.error(f"No symbols found for manufacturer: {producer}")
            return 0, {'total_pages': 0, 'pages_with_text': 0}

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logging.error(f"Error opening PDF file '{pdf_path}': {e}")
            return 0, {'total_pages': 0, 'pages_with_text': 0}

        found_items = {}
        total_links_added = 0
        total_pages = len(doc)
        pages_with_text = 0

        text_blocks = []
        for page in doc:
            text_instances = page.get_text("dict")["blocks"]
            has_text = False
            for instance in text_instances:
                if instance["type"] == 0:
                    has_text = True
                    lines = instance.get("lines", [])
                    for line in lines:
                        spans = line.get("spans", [])
                        for span in spans:
                            text_blocks.append((page.number, span))
            if has_text:
                pages_with_text += 1

        search_texts_set = set(producer_symbols.keys())
        logging.info(f"Found {len(search_texts_set)} unique codes to search for.")

        for page_number, span in text_blocks:
            text = span.get("text", "").strip()
            search_text = remove_spaces(text)

            if search_text in producer_symbols:
                link_code = producer_symbols[search_text]
                link = f"{base_link}{link_code}"  # Use the base link provided by the user
                if page_number not in found_items:
                    found_items[page_number] = []
                found_items[page_number].append(search_text)
                page = doc.load_page(page_number)
                rect = fitz.Rect(span["bbox"])

                annot_fill = page.add_rect_annot(rect)
                annot_fill.set_colors(stroke=[1, 0, 0], fill=[1, 0, 0])
                annot_fill.set_border(width=0)
                annot_fill.set_opacity(0.3)
                annot_fill.update()

                link_dict = {"kind": fitz.LINK_URI, "uri": link, "from": rect}
                page.insert_link(link_dict)

                total_links_added += 1

        output_path = os.path.join(output_folder, os.path.basename(pdf_path))
        doc.save(output_path)
        doc.close()

        logging.info(f"Processing completed. PDF saved as: {output_path}")
        logging.info(f"Total number of links added: {total_links_added}")

        pdf_stats = {
            'total_pages': total_pages,
            'pages_with_text': pages_with_text
        }

        return total_links_added, pdf_stats

    except Exception as e:
        logging.error(f"Error processing PDF file '{pdf_path}': {e}")
        return 0, {'total_pages': 0, 'pages_with_text': 0}

def save_logs(producer, stats):
    try:
        producer_log_path = os.path.join(LOG_FOLDER, f"{producer}.txt")
        with open(producer_log_path, 'w', encoding='utf-8') as f:
            # Sort PDFs by the ratio of pages with text to total pages
            sorted_pdfs = sorted(stats['pdfs'], key=lambda x: x['ratio'], reverse=True)
            for pdf_info in sorted_pdfs:
                # Change the separator from '/' to ';' and add the number of links
                f.write(f"{pdf_info['pdf_name']} - {pdf_info['total_pages']};{pdf_info['pages_with_text']};{pdf_info['links_in_pdf']}\n")

            # If there are erroneous files, add them to the log
            if stats.get('error_pdfs'):
                f.write("\nErroneous Files:\n")
                for error_pdf in stats['error_pdfs']:
                    f.write(f"{error_pdf}\n")

        # Update the summary log
        total_log_path = os.path.join(LOG_FOLDER, "log.txt")
        with open(total_log_path, 'a', encoding='utf-8') as f:
            total_pdfs = len(stats['pdfs']) + len(stats.get('error_pdfs', []))
            f.write(f"{producer} - {total_pdfs};{stats['total_pages']};{stats['pages_with_text']};{stats['total_links_added']}\n")

        logging.info(f"Logs for manufacturer {producer} saved in folder: {LOG_FOLDER}")

    except Exception as e:
        logging.error(f"Error saving logs for manufacturer {producer}: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
