import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox
from PyPDF2 import PdfReader, PdfWriter
from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

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
        title="Select an output folder to save the processed PDF"
    )

    if not output_folder_path:
        return None, None

    return input_pdf_path, output_folder_path

def add_bookmarks_with_langchain(input_pdf_path, output_folder):
    """
    Uses LangChain and Gemini to analyze a PDF and add sub-bookmarks.
    This script is designed to process a single PDF.
    """
    try:
        # Step 1: Initialize the AI model and LangChain components
        model = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)
        
        # Step 2: Load and extract text from the PDF using PyPDFLoader
        print("Loading and extracting text from the PDF...")
        loader = PyPDFLoader(input_pdf_path)
        pages = loader.load_and_split()
        
        # Concatenate all page content for the AI to analyze
        full_text = " ".join([page.page_content for page in pages])

        # Step 3: Define the prompt for the AI
        prompt = ChatPromptTemplate.from_messages([
            ("system", 
             "You are a document analysis assistant. Your task is to extract all chapter titles, section headings, "
             "and subheadings from the document and list them with their page numbers. "
             "Provide the output as a JSON object where each key is a title and the value is its corresponding page number."),
            ("user", 
             "Analyze the following document and return a JSON object with a list of all titles and their page numbers. "
             "Here is the content:\n\n{document_text}")
        ])
        
        # Step 4: Create and invoke the chain
        print("Sending content to Gemini for analysis...")
        chain = prompt | model
        
        # Use a simple progress bar for the AI call
        with tqdm(total=1, desc="Analyzing with Gemini") as pbar:
            response = chain.invoke({"document_text": full_text})
            pbar.update(1)

        # Step 5: Parse the AI's JSON response
        try:
            # The response might be enclosed in markdown code block
            json_string = response.content.strip('```json').strip('```').strip()
            bookmark_data = json.loads(json_string)
        except (json.JSONDecodeError, AttributeError):
            messagebox.showerror("Error", "Could not parse Gemini's response. The format might be incorrect.")
            return

        # Step 6: Add the new bookmarks to the PDF using PyPDF2
        print("Adding new bookmarks to the PDF...")
        writer = PdfWriter()
        reader = PdfReader(input_pdf_path)

        for page in reader.pages:
            writer.add_page(page)

        # PyPDF2 uses 0-indexed pages internally
        bookmarks_added = 0
        for title, page_num in bookmark_data.items():
            page_index = page_num - 1
            if 0 <= page_index < len(reader.pages):
                writer.add_outline_entry(title, page_index)
                bookmarks_added += 1
                
        if bookmarks_added == 0:
            messagebox.showinfo("Information", "Gemini analysis complete, but no valid bookmarks were found to add.")
            return

        # Save the updated PDF
        output_path = os.path.join(output_folder, f"updated_{os.path.basename(input_pdf_path)}")
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)

        messagebox.showinfo("Success", f"New bookmarks added to '{os.path.basename(output_path)}'!")

    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {e}")


if __name__ == "__main__":
    input_file, output_directory = select_file_and_directory()

    if input_file and output_directory:
        print("--- Adding bookmarks with LangChain and Gemini ---")
        add_bookmarks_with_langchain(input_file, output_directory)