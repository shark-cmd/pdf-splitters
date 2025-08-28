# File: pdf_splitter_gui_pymupdf_chapter_part_splitter_enhanced.py

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF is imported as fitz
from tqdm.tk import tqdm # Using tqdm.tk for a tkinter-compatible progress bar
import unicodedata # For more robust character sanitization

def select_file_and_directory():
    """
    Opens file dialogs for the user to select an input PDF and an output folder.
    Returns the file path and directory path as a tuple.
    """
    # Initialize Tkinter root window but keep it hidden
    root = tk.Tk()
    root.withdraw() 
    
    input_pdf_path = filedialog.askopenfilename(
        title="Select a PDF file",
        filetypes=[("PDF files", "*.pdf")]
    )
    
    if not input_pdf_path:
        messagebox.showinfo("Cancelled", "PDF file selection cancelled.")
        return None, None
    
    output_folder_path = filedialog.askdirectory(
        title="Select an output folder to save the split PDFs"
    )
    
    if not output_folder_path:
        messagebox.showinfo("Cancelled", "Output folder selection cancelled.")
        return None, None
        
    return input_pdf_path, output_folder_path

def split_pdf_by_content(input_pdf_path, output_folder):
    """
    Splits a PDF into multiple smaller PDFs by finding only 'PART' and 'CHAPTER' titles in the content.
    Includes enhanced filename sanitization and page numbers in the filenames.
    This version has a more flexible regex to catch more variations.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        # Open the PDF document using PyMuPDF
        doc = fitz.open(input_pdf_path)
        
        # --- REVISED REGEX PATTERN: More flexible for CHAPTER and PART headings ---
        # This regex is designed to be more forgiving with whitespace and potential leading/trailing characters
        # that might be part of the text extraction but not the core title.
        # It still prioritizes lines that clearly start with "PART" or "CHAPTER".
        title_pattern = re.compile(
            r'^\s*(?:'  # Optional leading whitespace
            r'PART\s+(?:[IVXLCDM]+\b|\d+\b)|'  # Matches "PART I", "PART 1", etc.
            r'Chapter\s+\d+\b'  # Matches "Chapter 1", "Chapter 2", etc.
            r')'
            r'(.{0,100})$', # Captures the rest of the line as the title (now allows 0 chars for just "PART X")
            re.IGNORECASE | re.MULTILINE 
        )

        split_points = []
        
        print(f"Analyzing PDF for 'PART' and 'CHAPTER' titles in '{input_pdf_path}' using PyMuPDF...")
        # Iterate through pages using PyMuPDF's page loading
        for i in tqdm(range(len(doc)), desc="Scanning pages for titles"):
            try:
                page = doc.load_page(i)
                # Use get_text("text") for a plain text representation
                text = page.get_text("text") 
                if not text:
                    continue
                    
                # Process lines to find titles, prioritizing the first strong match on the page
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    match = title_pattern.match(line)
                    if match:
                        # Use the full matched line as the title
                        title = match.group(0).strip() 
                        # Ensure we don't add duplicate split points if multiple matches on same page
                        if not split_points or split_points[-1]['start_page'] != i:
                            split_points.append({'title': title, 'start_page': i})
                        break # Move to the next page after finding the first title on this page
                        
            except Exception as e:
                print(f"Warning: Error extracting text from page {i + 1} with PyMuPDF: {e}. Skipping this page for title detection.")
                continue

        if not split_points:
            messagebox.showinfo("Information", "No suitable 'PART' or 'CHAPTER' titles found for splitting. Please ensure these headings exist in your document and try adjusting the regex pattern further if needed.")
            return

        # Add the end of the document as the final split point
        split_points.append({'title': 'END_OF_DOCUMENT', 'start_page': len(doc)})

        print(f"Found {len(split_points) - 1} potential split points. Starting PDF splitting...")
        for i in range(len(split_points) - 1):
            start_page_index = split_points[i]['start_page']
            end_page_index = split_points[i+1]['start_page']
            title = split_points[i]['title']
            
            # Create a new blank PDF document for the current split
            new_pdf = fitz.open()
            
            # Check if there are pages to add for the current section
            if end_page_index > start_page_index:
                with tqdm(total=end_page_index - start_page_index, desc=f"Writing '{title[:30]}...'") as pbar:
                    # Insert pages from the original document into the new document
                    new_pdf.insert_pdf(doc, 
                                       from_page=start_page_index, 
                                       to_page=end_page_index - 1)
                    pbar.update(end_page_index - start_page_index) # Update progress bar once for the block

                # --- ENHANCED FILENAME SANITIZATION AND PAGE NUMBER ADDITION ---
                normalized_title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8')
                safe_title = re.sub(r'\s+', '_', normalized_title) 
                safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '', safe_title) 
                safe_title = safe_title.strip('_') 
                safe_title = safe_title[:90] # Reduced length slightly to accommodate page number

                # Format the page number for inclusion
                page_number_str = f"Page_{start_page_index + 1:04d}" # Formats as "Page_0001", "Page_0010" etc.

                # Construct the final filename with page number prefix
                filename = f"{page_number_str}_{safe_title}.pdf"
                output_path = os.path.join(output_folder, filename)

                new_pdf.save(output_path)
                print(f"Created '{output_path}' with pages {start_page_index + 1} to {end_page_index}.")
            else:
                print(f"Skipping empty section: '{title}' (pages {start_page_index + 1} to {end_page_index}).")
            
            new_pdf.close()
        
        doc.close()
        messagebox.showinfo("Success", "PDF splitting complete!")

    except FileNotFoundError:
        messagebox.showerror("Error", f"The file '{input_pdf_path}' was not found.")
    except fitz.FileDataError as e:
        print(f"PyMuPDF File Data Error: {e}")
        messagebox.showerror("Error", f"PyMuPDF encountered a data error in the PDF: {e}. The file might be corrupted or password-protected.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        messagebox.showerror("Error", f"An unexpected error occurred. Check the console for details: {e}")

if __name__ == "__main__":
    input_file, output_directory = select_file_and_directory()

    if input_file and output_directory:
        print("--- Splitting PDF based on 'PART' and 'CHAPTER' headings using PyMuPDF and Regex ---")
        split_pdf_by_content(input_file, output_directory)
