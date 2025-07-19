import sqlite3

path_workout  = r".\instance\workout.db"

conn_two = sqlite3.connect(path_workout)
cur_two = conn_two.cursor()

# Add column to sessions table
def add_column_to_sessions():
    try:
        cur_two.execute('ALTER TABLE sessions ADD COLUMN "session_end" DATETIME')
        print("Column 'exercise_id' added to sessions table.")
    except sqlite3.OperationalError as e:
        print(f"Error adding column: {e}")


add_column_to_sessions()
# Commit the changes to the second database
conn_two.commit()

conn_two.close()