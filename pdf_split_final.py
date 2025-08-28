# File: pdf_splitter_gui_pymupdf_chapter_part_splitter_contextual_text.py

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
    Includes enhanced filename sanitization, page numbers in the filenames, and captures
    contextual text for titles by explicitly searching for text immediately after the heading.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        doc = fitz.open(input_pdf_path)
        
        # Regex to find PART/CHAPTER prefix, with a capturing group for the number (Roman or Arabic)
        # This will help us find the exact match and then extract text AFTER it.
        prefix_pattern = re.compile(
            r'^\s*(PART\s+(?:[IVXLCDM]+\b|\d+\b)|Chapter\s+\d+\b)', 
            re.IGNORECASE | re.MULTILINE 
        )

        split_points = []
        
        print(f"Analyzing PDF for 'PART' and 'CHAPTER' titles in '{input_pdf_path}' using PyMuPDF...")
        for i in tqdm(range(len(doc)), desc="Scanning pages for titles"):
            try:
                page = doc.load_page(i)
                # Extract a larger chunk of text from the page (e.g., first 500 chars)
                # This helps ensure the descriptive text is included even if it's on a new line.
                full_page_text = page.get_text("text") 
                if not full_page_text:
                    continue
                    
                # Search for the prefix pattern within the full page text
                match = prefix_pattern.search(full_page_text)
                if match:
                    # Get the exact matched prefix (e.g., "PART 1" or "Chapter 5")
                    matched_prefix = match.group(0).strip()
                    
                    # Get the text immediately following the prefix match
                    # We'll take a chunk of text to find the descriptive part
                    text_after_prefix = full_page_text[match.end():].strip()
                    
                    # Try to extract a few words for context.
                    # We'll look for the first line of text after the heading, or the first 50 characters.
                    description_match = re.match(r'(.{1,150})(?=\n|$)', text_after_prefix, re.DOTALL | re.IGNORECASE)
                    description_text = ""
                    if description_match:
                        # Clean up the description text, removing extra spaces/newlines
                        description_text = re.sub(r'\s+', ' ', description_match.group(1)).strip()

                    # Combine prefix and description
                    full_title = f"{matched_prefix} {description_text}" if description_text else matched_prefix

                    if not split_points or split_points[-1]['start_page'] != i:
                        split_points.append({'title': full_title, 'start_page': i})
                        
            except Exception as e:
                print(f"Warning: Error extracting text from page {i + 1} with PyMuPDF: {e}. Skipping this page for title detection.")
                continue

        if not split_points:
            messagebox.showinfo("Information", "No suitable 'PART' or 'CHAPTER' titles found for splitting. Please ensure these headings exist in your document and review the PDF content for any unusual formatting.")
            return

        split_points.append({'title': 'END_OF_DOCUMENT', 'start_page': len(doc)})

        print(f"Found {len(split_points) - 1} potential split points. Starting PDF splitting...")
        for i in range(len(split_points) - 1):
            start_page_index = split_points[i]['start_page']
            end_page_index = split_points[i+1]['start_page']
            title = split_points[i]['title']
            
            new_pdf = fitz.open()
            
            if end_page_index > start_page_index:
                with tqdm(total=end_page_index - start_page_index, desc=f"Writing '{title[:30]}...'") as pbar:
                    new_pdf.insert_pdf(doc, 
                                       from_page=start_page_index, 
                                       to_page=end_page_index - 1)
                    pbar.update(end_page_index - start_page_index)

                normalized_title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('utf-8')
                safe_title = re.sub(r'\s+', '_', normalized_title) 
                safe_title = re.sub(r'[^a-zA-Z0-9_\-]', '', safe_title) 
                safe_title = safe_title.strip('_') 
                safe_title = safe_title[:90] 

                page_number_str = f"Page_{start_page_index + 1:04d}"

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
