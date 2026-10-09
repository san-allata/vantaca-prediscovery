import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Removes fully empty rows and columns from a DataFrame."""
    df = df.dropna(how="all")
    df = df.dropna(how="all", axis=1)
    return df


class ExcelConcatenatorApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Excel First-Sheet Concatenator")
        self.geometry("640x520")
        self.minsize(550, 450)

        self.input_files = []
        self.output_file = ""

        self._create_widgets()

    def _create_widgets(self):
        # 1. Input Files Selection
        input_frame = ttk.LabelFrame(self, text=" 1. Input Excel Files ", padding=10)
        input_frame.pack(fill="x", padx=15, pady=10)

        btn_add_files = ttk.Button(
            input_frame, text="Select Files...", command=self.select_files
        )
        btn_add_files.pack(side="left", padx=5)

        btn_clear_files = ttk.Button(
            input_frame, text="Clear List", command=self.clear_files
        )
        btn_clear_files.pack(side="left", padx=5)

        self.lbl_file_count = ttk.Label(input_frame, text="No files selected.")
        self.lbl_file_count.pack(side="right", padx=10)

        # File Listbox
        list_frame = ttk.Frame(self, padding=(15, 0))
        list_frame.pack(fill="both", expand=True)

        self.file_listbox = tk.Listbox(list_frame, height=5, selectmode=tk.EXTENDED)
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.file_listbox.yview
        )
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 2. Output File Selection (-o option)
        output_frame = ttk.LabelFrame(
            self, text=" 2. Output File (-o) ", padding=10
        )
        output_frame.pack(fill="x", padx=15, pady=10)

        self.entry_output = ttk.Entry(output_frame)
        self.entry_output.pack(side="left", fill="x", expand=True, padx=(5, 10))

        btn_browse_output = ttk.Button(
            output_frame, text="Save As...", command=self.select_output
        )
        btn_browse_output.pack(side="right")

        # Process Section
        action_frame = ttk.Frame(self, padding=15)
        action_frame.pack(fill="x")

        self.btn_process = ttk.Button(
            action_frame,
            text="Start Concatenation",
            command=self.start_processing_thread,
        )
        self.btn_process.pack(fill="x", ipady=5)

        self.progress = ttk.Progressbar(
            action_frame, orient="horizontal", mode="determinate"
        )
        self.progress.pack(fill="x", pady=(10, 0))

        # Status/Log Box
        log_frame = ttk.LabelFrame(self, text=" Progress Log ", padding=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.txt_log = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.txt_log.pack(fill="both", expand=True)

    def select_files(self):
        files = filedialog.askopenfilenames(
            title="Select Excel Files",
            filetypes=[("Excel Files", "*.xlsx *.xls *.xlsm"), ("All Files", "*.*")],
        )
        if files:
            self.input_files = [os.path.abspath(f) for f in files]
            self.file_listbox.delete(0, tk.END)
            for f in self.input_files:
                self.file_listbox.insert(tk.END, os.path.basename(f))
            self.lbl_file_count.config(text=f"{len(self.input_files)} file(s) loaded.")

    def clear_files(self):
        self.input_files.clear()
        self.file_listbox.delete(0, tk.END)
        self.lbl_file_count.config(text="No files selected.")

    def select_output(self):
        out = filedialog.asksaveasfilename(
            title="Select Output Excel File",
            defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx"), ("All Files", "*.*")],
            confirmoverwrite=False,
        )
        if out:
            # Ensure path extension is explicitly .xlsx
            if not out.lower().endswith(".xlsx"):
                out += ".xlsx"

            # Normalize path for operating system
            out_path = os.path.abspath(out)
            self.output_file = out_path

            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, out_path)

    def log(self, message: str):
        self.txt_log.config(state="normal")
        self.txt_log.insert(tk.END, message + "\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state="disabled")

    def start_processing_thread(self):
        output = self.entry_output.get().strip()

        if not self.input_files:
            messagebox.showwarning(
                "Missing Input", "Please select at least one input Excel file."
            )
            return
        if not output:
            messagebox.showwarning(
                "Missing Output", "Please set an output file location."
            )
            return

        # Ensure output filename is absolute and properly formatted
        if not output.lower().endswith(".xlsx"):
            output += ".xlsx"
        self.output_file = os.path.abspath(output)

        self.btn_process.config(state="disabled")
        self.progress["value"] = 0

        threading.Thread(target=self.process_files, daemon=True).start()

    def process_files(self):
        header_written = False
        total_files = len(self.input_files)

        self.log("--- Starting Concatenation ---")

        try:
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(self.output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Use openpyxl engine with explicit 'w' mode and target path string
            with pd.ExcelWriter(
                self.output_file, engine="openpyxl", mode="w"
            ) as writer:
                start_row = 0

                for idx, file_path in enumerate(self.input_files, start=1):
                    file_name = os.path.basename(file_path)
                    self.log(f"[{idx}/{total_files}] Processing: {file_name}")

                    try:
                        df = pd.read_excel(file_path, sheet_name=0)
                        df = clean_dataframe(df)

                        if df.empty:
                            self.log(
                                f"  -> Skipped {file_name} (empty after cleaning)."
                            )
                            continue

                        df.to_excel(
                            writer,
                            sheet_name="Concatenated",
                            index=False,
                            header=not header_written,
                            startrow=start_row,
                        )

                        if not header_written:
                            start_row += len(df) + 1
                            header_written = True
                        else:
                            start_row += len(df)

                    except Exception as e:
                        self.log(f"  -> Error reading {file_name}: {e}")

                    self.progress["value"] = (idx / total_files) * 100

            self.log(
                f"\nSUCCESS: Output written to '{os.path.basename(self.output_file)}'"
            )
            messagebox.showinfo(
                "Completed",
                f"All files concatenated successfully!\n\nSaved to:\n{self.output_file}",
            )

        except Exception as e:
            self.log(f"\nCRITICAL ERROR: {e}")
            messagebox.showerror("Error", f"Failed to concatenate files:\n{e}")

        finally:
            self.btn_process.config(state="normal")


if __name__ == "__main__":
    app = ExcelConcatenatorApp()
    app.mainloop()