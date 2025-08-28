# File: pdf_splitter_gui.py
import sys
import PyPDF2
print("Python Executable Path:", sys.executable)
print("PyPDF2 version:", PyPDF2.__version__)
import os
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

def split_pdf_by_bookmarks(input_pdf_path, output_folder):
    """
    Splits a PDF into multiple smaller PDFs based on all found bookmarks, regardless of nesting.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    try:
        with open(input_pdf_path, 'rb') as file:
            reader = PdfReader(file)
            all_bookmarks = reader.outline

            if not all_bookmarks:
                messagebox.showinfo("Information", "No bookmarks found in the PDF. Exiting.")
                return

            def extract_bookmarks(bookmarks_list, extracted_data):
                for item in bookmarks_list:
                    if isinstance(item, list):
                        # Recursively process nested lists of bookmarks
                        extract_bookmarks(item, extracted_data)
                    else:
                        # Process a single bookmark tuple
                        try:
                            title, page_obj = item
                            page_number = reader.get_page_number(page_obj)
                            extracted_data.append({'title': title, 'start_page': page_number})
                        except (ValueError, TypeError):
                            # Skip items that are not valid bookmark tuples
                            continue

            bookmark_data = []
            extract_bookmarks(all_bookmarks, bookmark_data)
            
            if not bookmark_data:
                messagebox.showinfo("Information", "No valid bookmarks found that can be used for splitting. Exiting.")
                return
            
            # Sort bookmarks by their page number to ensure correct splitting order
            bookmark_data.sort(key=lambda x: x['start_page'])

            # Add the end of the document as a final split point
            bookmark_data.append({'title': 'END', 'start_page': len(reader.pages)})

            for i in range(len(bookmark_data) - 1):
                start_page = bookmark_data[i]['start_page']
                end_page = bookmark_data[i+1]['start_page']
                title = bookmark_data[i]['title']

                writer = PdfWriter()
                with tqdm(total=end_page - start_page, desc=f"Splitting '{title}'") as pbar:
                    for page_num in range(start_page, end_page):
                        writer.add_page(reader.pages[page_num])
                        pbar.update(1)

                filename = f"{title.replace(' ', '_').replace('/', '-')}.pdf"
                output_path = os.path.join(output_folder, filename)

                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
                print(f"Created '{output_path}' with pages {start_page + 1} to {end_page}.")

        messagebox.showinfo("Success", "PDF splitting complete!")

    except FileNotFoundError:
        messagebox.showerror("Error", f"The file '{input_pdf_path}' was not found.")
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {e}")

# The main execution block (if __name__ == "__main__":) remains unchanged.
if __name__ == "__main__":
    input_file, output_directory = select_file_and_directory()

    if input_file and output_directory:
        print("--- Splitting PDF based on existing bookmarks ---")
        split_pdf_by_bookmarks(input_file, output_directory)