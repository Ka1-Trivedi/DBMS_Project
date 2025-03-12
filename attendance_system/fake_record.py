# create fake record 
import pandas as pd
import random
from faker import Faker

# Initialize Faker
fake = Faker()

# Define parameters
departments = {
    "Computer Science and Engineering": "CS",
    "Bachelor of Computer Applications": "BCA"
}
classes = ["Division 1", "Division 2", "Division 3"]
num_records = 100
students_per_division = num_records // len(classes)  # Approximate distribution
password = "456"

# Roll number counters
roll_number_counters = {"CS": 1, "BCA": 1}
division_ranges = {"CS": {}, "BCA": {}}
data = []
unique_emails = set()

# Assign divisions based on roll number range
for dept_short in roll_number_counters.keys():
    count = 1
    for division in classes:
        division_ranges[dept_short][division] = list(range(count, count + students_per_division // 2))
        count += students_per_division // 2

# Generate data
for dept_name, dept_short in departments.items():
    for division, roll_numbers in division_ranges[dept_short].items():
        for roll_num in roll_numbers:
            roll_number = f"{dept_short}{roll_num:03d}"
            
            # Generate a realistic name
            name = fake.first_name() + " " + fake.last_name()
            
            # Ensure unique email
            email = f"{name.lower().replace(' ', '.')}{random.randint(100,999)}@gmail.com"
            while email in unique_emails:
                email = f"{name.lower().replace(' ', '.')}{random.randint(100,999)}@gmail.com"
            unique_emails.add(email)

            data.append([name, email, password, roll_number, division, dept_name])

# Create DataFrame
df = pd.DataFrame(data, columns=["Name", "Email", "Password", "Roll Number", "Class Name", "Department Name"])

# Save to Excel
file_path = "student_records.xlsx"
df.to_excel(file_path, index=False)

print(f"Excel file saved as {file_path}")
