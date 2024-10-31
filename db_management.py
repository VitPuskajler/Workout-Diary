import sqlite3

# from exercises.db export all data from table exercises to workout database table exercises
path_exercises = r"Projekty\Workout Periodization\instance\exercises.db"
path_workout  = r"Projekty\Workout Periodization\instance\workout.db"
conn_one = sqlite3.connect(path_exercises)
cur_one = conn_one.cursor()

cur_one.execute("SELECT exercise_name, muscle_group FROM exercises")
rows_one = cur_one.fetchall()

conn_two = sqlite3.connect(path_workout)
cur_two = conn_two.cursor()

# Insert data into the exercises table in the second database
def insert_into_db():
    try:
        for i, row in enumerate(rows_one):
            # If the exercise is not in the db, insert it into workout db
            cur_two.execute('SELECT 1 FROM exercises WHERE "exercise_name" = ?', (row[0],))
            if not cur_two.fetchone():
                cur_two.execute('INSERT INTO exercises ("exercise_name", "muscle_group") VALUES (?, ?)', (row[0], row[1]))
                print(f"Inserted exercise: {row[0]}")
    except Exception as e:
        print(f"Error inserting data: {e}")


insert_into_db()

# Commit the changes to the second database
conn_two.commit()

# Close the connections
conn_one.close()
conn_two.close()