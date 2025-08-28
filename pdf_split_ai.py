# File: gemini_bookmark_creator.py

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
import google.generativeai as genai
from tqdm import tqdm

# Configure the Gemini API with your API key
genai.configure(api_key="YOUR_API_KEY")

def select_input_folder():
    """
    Opens a file dialog to allow the user to select the folder with the split PDFs.
    """
    root = tk.Tk()
    root.withdraw()
    
    input_folder_path = filedialog.askdirectory(
        title="Select the folder containing the split PDFs"
    )
    
    return input_folder_path

def add_bookmarks_with_gemini(input_folder):
    """
    Uses Gemini 1.5 Flash to analyze PDFs and add sub-bookmarks.
    """
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    if not input_folder or not os.path.exists(input_folder):
        messagebox.showerror("Error", "Invalid folder selected.")
        return

    # Get a list of all PDF files to process
    pdf_files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]

    # Use tqdm to show a progress bar for the entire process
    with tqdm(total=len(pdf_files), desc="Processing PDFs with Gemini") as pbar:
        for filename in pdf_files:
            pdf_path = os.path.join(input_folder, filename)
            
            try:
                pdf_file_part = genai.upload_file(pdf_path)
                
                prompt = (
                    "Analyze this document and list all chapter titles, section headings, "
                    "and subheadings with their page numbers. "
                    "Format the output as a JSON object where the keys are the titles and the values are the page numbers. "
                    "Example: {'Chapter 1: Introduction': 1, '1.1 A new beginning': 2}"
                )
                
                response = model.generate_content([prompt, pdf_file_part])
                
                try:
                    bookmark_data = json.loads(response.text)
                except json.JSONDecodeError:
                    print(f"Could not decode JSON from Gemini for {filename}. Skipping.")
                    continue
                
                writer = PdfWriter()
                reader = PdfReader(pdf_path)
                
                for page in reader.pages:
                    writer.add_page(page)

                for title, page_num in bookmark_data.items():
                    page_index = page_num - 1
                    if 0 <= page_index < len(reader.pages):
                        writer.add_outline_entry(title, page_index)
                
                with open(pdf_path, 'wb') as output_file:
                    writer.write(output_file)
                
            except Exception as e:
                print(f"An error occurred with Gemini on {filename}: {e}")
            finally:
                pbar.set_description(f"Completed: {filename}")
                pbar.update(1)
                if 'pdf_file_part' in locals():
                    genai.delete_file(pdf_file_part.name)
    
    messagebox.showinfo("Success", "Gemini bookmarking complete!")

if __name__ == "__main__":
    split_pdfs_folder = select_input_folder()
    
    if split_pdfs_folder:
        print("--- Adding new bookmarks with Gemini 1.5 Flash ---")
        add_bookmarks_with_gemini(split_pdfs_folder)