from pdf_viewer import PDFViewer
from tkinter import filedialog, Tk
from pathlib import Path
import sys

if __name__ == "__main__":
    pdf_path = None
    if len(sys.argv) == 2:
        arg_path = sys.argv[1]
        if not arg_path.lower().endswith('.pdf'):
            print("Error: The provided file is not a PDF.")
            sys.exit(1)
        if not Path(arg_path).is_file():
            print(f"Error: File '{arg_path}' does not exist.")
            sys.exit(1)
        pdf_path = arg_path
    elif len(sys.argv) > 2:
        print("Error: Please provide only one PDF file path as an argument.")
        sys.exit(1)
    if pdf_path is None:
        root = Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select a PDF file to analyze",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not file_path:
            root.destroy()
            sys.exit(0)
        pdf_path = file_path
        root.destroy()
    viewer = PDFViewer(Path(pdf_path))
    viewer.run() 