import os
from DbConnector import DbConnector
from tabulate import tabulate
from datetime import datetime


class InsertionProgram:

    def __init__(self):
        self.connection = DbConnector()
        self.db_connection = self.connection.db_connection
        self.cursor = self.connection.cursor

    def create_table(self, table_name):
        query = """CREATE TABLE IF NOT EXISTS %s (
                   id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
                   name VARCHAR(30))
                """
        # This adds table_name to the %s variable and executes the query
        self.cursor.execute(query % table_name)
        self.db_connection.commit()

    def create_table_user(self, table_name):
        """Creates a table for the user entity class"""
        query = """CREATE TABLE IF NOT EXISTS %s (
                   id VARCHAR(255) NOT NULL PRIMARY KEY,
                   has_labels BOOLEAN)
                """
        # This adds table_name to the %s variable and executes the query
        self.cursor.execute(query % table_name)
        self.db_connection.commit()

    def create_table_activity(self, table_name):
        """Creates a table for the activity entity class"""
        query = """CREATE TABLE IF NOT EXISTS %s (
               id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
               user_id VARCHAR(255) NOT NULL,
               transportation_mode VARCHAR(255),
               start_date_time DATETIME,
               end_date_time DATETIME,
               FOREIGN KEY (user_id) REFERENCES user(id))
            """
        # This adds table_name to the %s variable and executes the query
        self.cursor.execute(query % table_name)
        self.db_connection.commit()

    def create_table_trackpoint(self, table_name):
        """Creates a table for the trackpoint entity class"""
        query = """CREATE TABLE IF NOT EXISTS %s (
               id INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
               activity_id INT NOT NULL,
               lat DOUBLE,
               lon DOUBLE,
               altitude INT,
               date_days DOUBLE,
               date_time DATETIME,
               FOREIGN KEY (activity_id) REFERENCES activity(id))
            """
        # This executes the query
        self.cursor.execute(query % table_name)
        self.db_connection.commit()

    def fetch_data(self, table_name):
        query = "SELECT * FROM %s"
        self.cursor.execute(query % table_name)
        rows = self.cursor.fetchall()
        print("Data from table %s, raw format:" % table_name)
        print(rows)
        # Using tabulate to show the table in a nice way
        print("Data from table %s, tabulated:" % table_name)
        print(tabulate(rows, headers=self.cursor.column_names))
        return rows

    def drop_table(self, table_name):
        print("Dropping table %s..." % table_name)
        query = "DROP TABLE %s"
        self.cursor.execute(query % table_name)

    def show_tables(self):
        self.cursor.execute("SHOW TABLES")
        rows = self.cursor.fetchall()
        print(tabulate(rows, headers=self.cursor.column_names))

    def locate_trackpoint_files(self, user_id):
        """Locates all trackpoint files for a user, returns a list of paths"""
        with os.scandir(f"dataset/dataset/Data/{user_id}/Trajectory") as entries:
            return [entry.path for entry in entries if entry.is_file()]

    def read_trackpoints_from_plt(self, plt_file_path, activity_id) -> list:
        """Handles reading trackpoints-data from a .plt file, returns a list of trackpoints"""
        with open(plt_file_path, 'r') as file:
            lines = file.readlines()[6:]  # Skip the first 6 lines
        trackpoints = []

        for line in lines:
            lat, lon, _, altitude, _, date_day, date_time = line.strip().split(',')
            trackpoints.append((activity_id, float(lat), float(
                lon), int(float(altitude)), datetime.strptime(f"{date_day} {date_time}", "%Y-%m-%d %H:%M:%S")))
        return trackpoints

    def read_activities_from_labels(self, labels_file_path) -> list:
        """Handles reading activities-data from a .labels file, returns a list of activities"""
        with open(labels_file_path, 'r') as file:
            lines = file.readlines()[1:]  # Skip the first line
        activities = []

        for line in lines:
            start_date_time, end_date_time, transportation_mode = line.strip().split('\t')
            # Convert to datetime objects
            start_date_time = datetime.strptime(
                start_date_time, "%Y/%m/%d %H:%M:%S")
            end_date_time = datetime.strptime(
                end_date_time, "%Y/%m/%d %H:%M:%S")
            activities.append(
                (start_date_time, end_date_time, transportation_mode))
            print("Start date time: ", start_date_time, "End date time: ",
                  end_date_time, "Transportation mode: ", transportation_mode)
        return activities

    def insert_trackpoints(self, trackpoints):
        query = """INSERT INTO trackpoint (activity_id, lat, lon, altitude, date_time)
                   VALUES (%s, %s, %s, %s, %s)"""
        self.cursor.executemany(query, trackpoints)
        self.db_connection.commit()

    def insert_user(self, user_id, has_labels):
        query = """INSERT INTO user (id, has_labels) VALUES (%s, %s)"""
        self.cursor.execute(query, (user_id, has_labels))
        self.db_connection.commit()

    def insert_activity(self, user_id, transportation_mode, start_date_time, end_date_time):
        query = """INSERT INTO activity (user_id, transportation_mode, start_date_time, end_date_time)
                   VALUES (%s, %s, %s, %s)"""
        self.cursor.execute(
            query, (user_id, transportation_mode, start_date_time, end_date_time))
        self.db_connection.commit()

    def check_matching_activity_and_trackpoint(self, activity, trackpoints):
        """For a given activity, check if there are trackpoints that match the activity"""
        id, transportation_mode, start_date_time, end_date_time = activity
        matching_points = []
        for trackpoint in trackpoints:
            _, _, _, _, date_time = trackpoint
            if (end_date_time) == date_time:
                matching_points.append(trackpoint)
            if (start_date_time) == date_time:
                matching_points.append(trackpoint)
        # Now if the exact start and end are found, there should be 2 matching points, indicating the activity
        if len(matching_points) == 2:
            return (matching_points[0], matching_points[1])
        return None

    def extract_trackpoints_period(self, trackpoints: list, start_date_time: datetime, end_date_time: datetime, activity_id: int):
        """Extracts trackpoints between start_date_time and end_date_time"""
        extracted_trackpoints = []
        for trackpoint in trackpoints:
            _, _, _, _, date_time = trackpoint
            if start_date_time <= date_time <= end_date_time:

                # remove the trackpoint from the list to avoid duplicates
                trackpoints.remove(trackpoint)
                trackpoint = (activity_id, *trackpoint[1:])
                extracted_trackpoints.append(trackpoint)
        return extracted_trackpoints, trackpoints

    def load_user(self, user_id):
        """ Function to load a folder, check for labels and subsequently load all trackpoints into memory"""

        # Check if there exists a user already in the db
        query = "SELECT * FROM user WHERE id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchone()

        if result is not None:
            print(f"User {user_id} already exists in the database")
            return

        labels_file_path = f"dataset/dataset/Data/{user_id}/labels.txt"
        has_labels = True
        try:
            activities = self.read_activities_from_labels(labels_file_path)
        except FileNotFoundError:
            has_labels = False
            activities = []
        except Exception as e:  # Handler in case of other exceptions
            print(f"ERROR: Failed to read activities from labels file: {e}")
            return

        # Insertion part
        self.insert_user(user_id, has_labels)
        for activity in activities:
            self.insert_activity(
                user_id, start_date_time=activity[0], end_date_time=activity[1], transportation_mode=activity[2])

    def load_all_users(self):
        """ Function to load all users from the dataset"""
        users = os.listdir("dataset/dataset/Data")
        for user in users:
            print(f"Loading user: {user}")
            self.load_user(user)

    def load_and_insert_trackpoints(self, user_id):
        """ Function to load all trackpoints from the dataset"""
        trackpoints = []
        extracted_trackpoints = []

        # fetch activities by SQL query
        query = "SELECT * FROM activity WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchall()
        activities = [(activity[0], activity[2], activity[3], activity[4])
                      for activity in result]

        paths = self.locate_trackpoint_files(user_id)
        for path_idx, path in enumerate(paths):
            trackpoints = self.read_trackpoints_from_plt(
                path, user_id+str(path_idx))
            if len(trackpoints) > 2500:
                print("Too large trackpoint file, skipping")
            else:
                for activity in activities:
                    match = self.check_matching_activity_and_trackpoint(
                        activity, trackpoints)
                    if match is not None:
                        extracted_trackpoints, trackpoints = self.extract_trackpoints_period(
                            trackpoints, match[0][4], match[1][4], activity_id=activity[0])
                        self.insert_trackpoints(extracted_trackpoints)
                # The remaining trackpoints get binned into a new activity
                if len(trackpoints) > 0:
                    print("Creating new activity for remaining trackpoints")
                    self.insert_activity(user_id, transportation_mode="Unknown", start_date_time=trackpoints[0][4],
                                         end_date_time=trackpoints[-1][4])
                    activity_id = self.cursor.lastrowid
                    if activity_id is not None:
                        self.insert_trackpoints(
                            [(activity_id, *trackpoint[1:]) for trackpoint in trackpoints])

    def load_all_trackpoints(self):
        """ Function to load all trackpoints from the dataset"""
        users = os.listdir("dataset/dataset/Data")
        for user in users:
            print(f"Loading trackpoints for user: {user}")
            self.load_and_insert_trackpoints(user)

    def check_all_activities_for_user(self, user_id):
        """ Function to check all activities for a user"""
        query = "SELECT * FROM activity WHERE user_id = %s"
        self.cursor.execute(query, (user_id,))
        result = self.cursor.fetchall()
        activities = [(activity[0], activity[2], activity[3], activity[4])
                      for activity in result]
        # use tabulate to show the table in a nice way
        print("Activities for user %s:" % user_id)
        print(tabulate(activities, headers=[
              "id", "transportation_mode", "start_date_time", "end_date_time"]))
        return activities

    def check_all_trackpoints_for_activity(self, activity_id):
        """ Function to check all trackpoints for an activity"""
        query = "SELECT * FROM trackpoint WHERE activity_id = %s"
        self.cursor.execute(query, (activity_id,))
        result = self.cursor.fetchall()
        trackpoints = [(trackpoint[0], trackpoint[2], trackpoint[3], trackpoint[4], trackpoint[5])
                       for trackpoint in result]
        # use tabulate to show the table in a nice way
        print("Trackpoints for activity %s:" % activity_id)
        print(tabulate(trackpoints, headers=[
              "id", "lat", "lon", "altitude", "date_time"]))
        return trackpoints

    def drop_all_table_data(self):
        self.drop_table("trackpoint")
        self.drop_table("activity")
        self.drop_table("user")
        self.db_connection.commit()
        print("All tables dropped")


def main():
    program = None
    try:

        program = InsertionProgram()
        user_choice = input(
            "Do you want to drop all tables and reinitialize the database? (y/n): ")
        # return "Program halted due to being incomplete."
        if user_choice == "y":
            program.drop_all_table_data()
            program.show_tables()
            program.create_table_user(table_name="user")
            program.create_table_activity(table_name="activity")
            program.create_table_trackpoint(table_name="trackpoint")
            # program.insert_data(table_name="Person")
            # _ = program.fetch_data(table_name="Person")
            program.show_tables()
            program.load_all_users()
            program.load_all_trackpoints()
        elif user_choice == "n":
            print("Program halted.")
        else:
            print("Invalid input. Program halted.")

    except Exception as e:
        print("ERROR: Failed to use database:", e)
    finally:
        if program:
            program.connection.close_connection()


if __name__ == '__main__':
    main()
