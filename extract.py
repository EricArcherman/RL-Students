# Run:
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt
# python extract.py

import re
import csv
import pdfplumber

# Define the path to the PDF file
file_path = "RL Directory.pdf"
sep_classes_csv = "sep_classes.csv"
all_students_csv = "all_students.csv"

# Define a function to extract student information from PDF
def extract_students_from_pdf(file_path):
    students = []
    
    # Read the PDF file
    with pdfplumber.open(file_path) as pdf:
        # Extract text from all pages
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"
        
        # Split into lines for processing
        lines = text.split('\n')
        
        # Process lines to match names with their grad years
        # Names are on one line, grad years on the next line
        i = 0
        while i < len(lines) - 1:
            line = lines[i].strip()
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            
            # Skip header lines
            if any(keyword in line.lower() for keyword in ['student directory', 'the roxbury latin school', 'printed:', 'page']):
                i += 1
                continue
            
            # Skip single letter lines (section headers like "A", "B", etc.)
            if len(line) == 1 and line.isalpha():
                i += 1
                continue
            
            # Find all name patterns in the current line: "LastName,FirstName"
            name_pattern = r'([A-Za-z\-\']+),([A-Za-z\-\']+)'
            names = re.findall(name_pattern, line)
            
            # Find all grad year patterns in the next line: "GradYear:YYYY"
            grad_year_pattern = r'GradYear:(\d{4})'
            grad_years = re.findall(grad_year_pattern, next_line)
            
            # Match names with grad years by position
            if names and grad_years:
                # Match up to the minimum of names and grad years found
                for j in range(min(len(names), len(grad_years))):
                    last_name = names[j][0].strip()
                    first_name = names[j][1].strip()
                    grad_year = grad_years[j]
                    
                    # Skip if name parts are too short (likely not a real name)
                    if len(last_name) < 2 or len(first_name) < 2:
                        continue
                    
                    students.append({
                        "Student": f"{last_name}, {first_name}",
                        "Grad Year": grad_year
                    })
            
            i += 1
    
    return students

# Extract students from the PDF file
students = extract_students_from_pdf(file_path)

# Write sep_classes.csv (sorted by graduation year, then by name)
students_by_class = sorted(students, key=lambda x: (x["Grad Year"], x["Student"]))
with open(sep_classes_csv, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["Student", "Grad Year"], extrasaction='ignore')
    writer.writeheader()
    writer.writerows(students_by_class)

# Write all_students.csv (completely alphabetized by student name)
students_alphabetical = sorted(students, key=lambda x: x["Student"])
with open(all_students_csv, mode="w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=["Student", "Grad Year"], extrasaction='ignore')
    writer.writeheader()
    writer.writerows(students_alphabetical)

print(f"Extracted {len(students)} students from {file_path}")
print(f"Student data has been exported to {sep_classes_csv} (sorted by class)")
print(f"Student data has been exported to {all_students_csv} (alphabetized)")