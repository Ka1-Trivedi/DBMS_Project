import sqlite3
import pandas as pd

# Load the Excel file (change filename for DAA)
file_path = "attendance_system/questions.xlsx"  # Use "DAA_Questions.xlsx" for DAA
df = pd.read_excel(file_path)

# Map correct answer to just 'A', 'B', 'C', 'D'
df["Correct Answer"] = df["Correct Answer"].str[0]  

# Assign difficulty level (Example: First 33 -> Easy, Next 33 -> Medium, Last 34 -> Hard)
difficulty_levels = ["Easy"] * 33 + ["Medium"] * 33 + ["Hard"] * 34
df["Difficulty"] = difficulty_levels[:len(df)]

# Connect to SQLite Database
conn = sqlite3.connect("database/attendance.db")  # Updated database path
cursor = conn.cursor()

# Insert query
insert_query = """
INSERT INTO Question_Database (question, option_A, option_B, option_C, option_D, ans, difficulty, subject)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

# Insert each row into the database
for _, row in df.iterrows():
    cursor.execute(insert_query, (row["Question"], row["Option_A"], row["Option_B"], row["Option_C"], row["Option_D"], row["Correct Answer"], row["Difficulty"], row["Subject"]))

# Commit and close connection
conn.commit()
cursor.close()
conn.close()

print("Data inserted successfully into SQLite3!")
