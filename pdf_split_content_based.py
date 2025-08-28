# File: pdf_splitter_gui_content_based.py

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from tqdm.tk import tqdm

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
        return None, None
    
    output_folder_path = filedialog.askdirectory(
        title="Select an output folder to save the split PDFs"
    )
    
    if not output_folder_path:
        return None, None
        
    return input_pdf_path, output_folder_path

def split_pdf_by_content(input_pdf_path, output_folder):
    """
    Splits a PDF into multiple smaller PDFs by finding titles in the content.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        with open(input_pdf_path, 'rb') as file:
            reader = PdfReader(file)
            
            # Use a regex pattern to find common title formats
            # This pattern looks for "PART [number]" or "Chapter [number]"
            # or a title with a number and period (e.g., "1. Introduction")
            title_pattern = re.compile(r'^(PART\s+\d+|Chapter\s+\d+|[A-Za-z]+(?:\s+[A-Za-z]+)*$)', re.IGNORECASE)

            # Find all potential split points (titles)
            split_points = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if title_pattern.match(line):
                        # Use the line as the title and the current page as the start page
                        split_points.append({'title': line, 'start_page': i})
                        # Stop after finding the first match on the page
                        break

            if not split_points:
                messagebox.showinfo("Information", "No suitable titles found for splitting. Exiting.")
                return

            # Add the end of the document as the final split point
            split_points.append({'title': 'END', 'start_page': len(reader.pages)})

            for i in range(len(split_points) - 1):
                start_page = split_points[i]['start_page']
                end_page = split_points[i+1]['start_page']
                title = split_points[i]['title']
                
                writer = PdfWriter()
                
                with tqdm(total=end_page - start_page, desc=f"Splitting '{title}'") as pbar:
                    for page_num in range(start_page, end_page):
                        writer.add_page(reader.pages[page_num])
                        pbar.update(1)

                # Sanitize the title to be a valid filename
                filename = f"{title.replace(' ', '_').replace('/', '-').replace(':', '')}.pdf"
                output_path = os.path.join(output_folder, filename)

                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                print(f"Created '{output_path}' with pages {start_page + 1} to {end_page}.")
        
        messagebox.showinfo("Success", "PDF splitting complete!")

    except FileNotFoundError:
        messagebox.showerror("Error", f"The file '{input_pdf_path}' was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    input_file, output_directory = select_file_and_directory()

    if input_file and output_directory:
        print("--- Splitting PDF based on content ---")
        split_pdf_by_content(input_file, output_directory)