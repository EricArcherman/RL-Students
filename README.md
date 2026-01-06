# RL Students

`extract.py` extracts student names from the RL directory and prints the data out in csv format.

The CSV data is used for Service Month donation tracking. Future Service Reps:
1. Follow the tutorial in `Create Directory PDF.pdf` to create an updated RL Directory
2. Replace the current `RL Directory.pdf` with your updated one
3. Run the extraction script by entering the following commands in terminal:
   - `python3 -m venv venv`
   - `source venv/bin/activate`
   - `pip install -r requirements.txt`
   - `python extract.py`
4. The script will update `all_students.csv` and `sep_classes.csv`.
   - use `all_students.csv` for the donation tracking Google Form.
   - use `sep_classes.csv` to update individual class subtabs (on the master Google Sheet).