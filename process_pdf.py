import fitz  # PyMuPDF
import json
import sys
import os
import re

def sanitize_filename(filename):
    """Removes problematic characters for filenames."""
    # Remove path component if any
    basename = os.path.basename(filename)
    # Remove extension
    name_without_ext, _ = os.path.splitext(basename)
    # Replace non-alphanumeric characters (excluding hyphen) with underscore
    sanitized = re.sub(r'[^\w-]', '_', name_without_ext)
    return sanitized

def pdf_to_word_json(pdf_path):
    """
    Extracts words and their bounding boxes from a PDF and saves to JSON.

    Args:
        pdf_path (str): Path to the input PDF file.

    Returns:
        str: Path to the generated JSON file, or None if an error occurred.
    """
    json_data = {}
    output_filename = None

    try:
        # Determine output filename based on input PDF
        pdf_dir = os.path.dirname(pdf_path)
        pdf_basename = os.path.basename(pdf_path)
        json_basename = os.path.splitext(pdf_basename)[0] + ".json"
        output_filename = os.path.join(pdf_dir, json_basename)

        print(f"Processing '{pdf_path}' -> '{output_filename}'...")

        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_height = page.rect.height
            page_width = page.rect.width # Store width too

            # Extract words with bounding boxes: list of [x0, y0, x1, y1, "word", block_no, line_no, word_no]
            # Coordinates have origin at TOP-LEFT of the page.
            words_on_page = page.get_text("words")

            word_list_for_json = []
            for w in words_on_page:
                x0, y0, x1, y1, word_text = w[0], w[1], w[2], w[3], w[4]

                # Clean the word text - remove non-printable, excessive whitespace
                cleaned_word = ''.join(char for char in word_text if char.isprintable()).strip()

                if not cleaned_word: # Skip empty strings after cleaning
                    continue

                # Convert PyMuPDF bbox (top-left origin) to PDF.js bbox (bottom-left origin)
                pdf_x0 = x0
                pdf_y0 = page_height - y1 # PDF y0 is PyMuPDF y1 flipped
                pdf_x1 = x1
                pdf_y1 = page_height - y0 # PDF y1 is PyMuPDF y0 flipped

                word_list_for_json.append({
                    "text": cleaned_word,
                    # Store bbox compatible with PDF.js coordinate system (bottom-left origin)
                    "bbox": [round(pdf_x0, 2), round(pdf_y0, 2), round(pdf_x1, 2), round(pdf_y1, 2)]
                })

            # Store page data keyed by page number (1-based index for JS consistency)
            json_data[str(page_num + 1)] = {
                 "page": page_num + 1,
                 "width": round(page_width, 2), # Store page dimensions
                 "height": round(page_height, 2),
                 "words": word_list_for_json
            }
            print(f"  - Page {page_num + 1}: Found {len(word_list_for_json)} words.")

        doc.close()

        # Save the JSON data
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f) # No indentation to save space

        print(f"Successfully created JSON: {output_filename}")
        return output_filename

    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        # Clean up potentially incomplete JSON file if error occurred
        if output_filename and os.path.exists(output_filename):
             try: os.remove(output_filename)
             except OSError: pass
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_pdf.py <path_to_pdf_file1> [path_to_pdf_file2] ...")
        # --- OR --- Find PDFs in default location if no args given
        default_dir = os.path.join("chapters", "ancient-history")
        print(f"\nNo PDF path provided. Searching in default directory: '{default_dir}'")
        if os.path.isdir(default_dir):
            pdf_files_found = [os.path.join(default_dir, f) for f in os.listdir(default_dir) if f.lower().endswith('.pdf')]
            if pdf_files_found:
                 print(f"Found PDF files: {', '.join(os.path.basename(p) for p in pdf_files_found)}")
                 for pdf_file in pdf_files_found:
                     pdf_to_word_json(pdf_file)
            else:
                 print(f"No PDF files found in '{default_dir}'.")
        else:
             print(f"Default directory '{default_dir}' not found.")
        sys.exit(1)

    # Process all PDF files provided as arguments
    for pdf_path_arg in sys.argv[1:]:
        if os.path.isfile(pdf_path_arg) and pdf_path_arg.lower().endswith('.pdf'):
            pdf_to_word_json(pdf_path_arg)
        else:
            print(f"Skipping invalid path or non-PDF file: {pdf_path_arg}")
