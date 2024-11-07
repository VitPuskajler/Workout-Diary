from server import Users, Mesocycles, WorkoutPlan, current_user, desc, db

class WorkoutManagement():
    def find_users_weeks():
            user = Users.query.filter_by(username=current_user.username).first()
            user_id_db = user.user_id
            # Retrieve last mesocycle's data from my table
            per_week_db = (
                db.session.query(Mesocycles.workouts_per_week)
                .filter(Mesocycles.user_id == user_id_db)
                .order_by(Mesocycles.mesocycle_id.desc())
                .first()
            )

            last_workouts = (
                WorkoutPlan.query.filter_by(user_id=user_id_db)
                .order_by(desc(WorkoutPlan.created_at))
                .limit(per_week_db[0])
                .all()
            )

            try:
                last_workouts_id = (
                    db.session.query(WorkoutPlan.workout_id)
                    .filter(WorkoutPlan.user_id == user_id_db)
                    .order_by(WorkoutPlan.created_at.desc())
                    .limit(per_week_db[0])
                    .all()
                )

                workouts_id = [x[0] for x in last_workouts_id] if last_workouts_id else []
            except Exception as e:
                print(f"Probably no workout created yet {e}")
                workouts_id = None

            workout_names_in_db = [workout.workout_name for workout in last_workouts]

            return per_week_db[0], workout_names_in_db, workouts_id