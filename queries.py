from DbConnector import DbConnector
from tabulate import tabulate
import haversine as hs


class QueryProgram:

    def __init__(self):
        self.connection = DbConnector()
        self.db_connection = self.connection.db_connection
        self.cursor = self.connection.cursor

    def present_rows_and_headers(self, query):
        """Function that prints the rows and headers of a query.
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        print(tabulate(rows, headers=self.cursor.column_names, tablefmt='github'))

    def count_rows_for_table(self, table_name):
        query = "SELECT COUNT(*) FROM %s"
        self.cursor.execute(query % table_name)
        rows = self.cursor.fetchall()
        return rows[0][0]

    def count_rows_all_tables(self):
        self.cursor.execute("SHOW TABLES")
        tables = self.cursor.fetchall()
        table_names = [table[0] for table in tables]
        table_rows = {}
        for table_name in table_names:
            table_rows[table_name] = self.count_rows_for_table(table_name)
        return table_rows

    def present_table_rows(self):
        """Function that prints the number of rows in each table. \n
        Completes Task 2.1
        """
        table_rows = self.count_rows_all_tables()
        print(tabulate(table_rows.items(), headers=['Table', 'Rows'], tablefmt='github'))

    def avg_activities_per_user(self):
        """Function that prints the average number of activities per user. \n
        Completes Task 2.2
        """
        query = """SELECT COUNT(*)/COUNT(DISTINCT user_id) AS 'Average activities per user'
                   FROM activity"""
        return query

    def top_n_users_with_most_activities(self, n):
        """Function that prints the n users with the most activities. \n
        Completes Task 2.3
        """
        query = """SELECT user_id, COUNT(*) AS 'Number of activities'
                   FROM activity
                   GROUP BY user_id
                   ORDER BY COUNT(*) DESC
                   LIMIT %s"""
        return query % n

    def users_taking_taxi(self):
        """Function that prints the users that have taken a taxi. \n
        Completes Task 2.4
        """
        query = """SELECT user_id as 'User'
                   FROM activity
                   WHERE transportation_mode = 'taxi'
                   GROUP BY user_id
                   ORDER BY user_id ASC"""
        return query

    def count_activities_by_transportation_mode(self):
        """Function that counts the number of activities for each transportation mode. \n
        Completes Task 2.5
        """
        query = """SELECT transportation_mode, COUNT(*) AS 'Number of activities'
               FROM activity
               WHERE transportation_mode != 'Unknown'
               GROUP BY transportation_mode
               ORDER BY COUNT(*) DESC"""
        return query

    def year_with_most_activities(self):
        """Function that finds the year with the most activities. \n
        Completes Task 2.6a
        """
        query = """SELECT YEAR(start_date_time) as 'Year', COUNT(*) as 'Number of activities'
                   FROM activity
                   GROUP BY YEAR(start_date_time)
                   ORDER BY COUNT(*) DESC
                   LIMIT 1"""
        return query

    def count_hours_per_activity_per_year(self):
        """Function that counts the hours spent on each activity, grouped by year \n
        Completes Task 2.6b
        """
        query = """SELECT YEAR(start_date_time) as 'Year', 
        SUM(TIME_TO_SEC(TIMEDIFF(end_date_time, start_date_time))/3600) as 'Hours'
                   FROM activity
                   GROUP BY YEAR(start_date_time)
                   ORDER BY 'Hours' DESC"""
        return query

    def calculate_distance_for_activity(self, activity_id: int):
        """Function that calculates the distance for an activity.
        """
        # first, find all the trackpoints for the activity
        query = """SELECT lat, lon
                            FROM trackpoint
                            WHERE activity_id = %s"""
        trackpoints = query % activity_id

        fetched_trackpoints = self.cursor.execute(trackpoints)
        fetched_trackpoints = self.cursor.fetchall()

        distance = 0
        for i in range(len(fetched_trackpoints) - 1):
            distance += hs.haversine(fetched_trackpoints[i],
                                     fetched_trackpoints[i + 1], unit=hs.Unit.METERS)

        return distance

    def total_distance_walked_by_user(self, user_id):
        """Function that calculates the total distance walked by a user. \n
        Completes Task 2.7
        """
        query = """SELECT id
                   FROM activity
                   WHERE user_id = %s AND transportation_mode = 'walk'"""
        activity_ids = query % user_id

        fetched_activity_ids = self.cursor.execute(activity_ids)
        fetched_activity_ids = self.cursor.fetchall()
        total_distance = 0

        for activity_id in fetched_activity_ids:
            distance = self.calculate_distance_for_activity(activity_id[0])
            total_distance += distance

        return total_distance

    def top_20_users_with_most_altitude(self):
        """Function that prints the 20 users with the most altitude. \n
        Completes Task 2.8
        """
        # First we join all tables to get the altitude for each activity
        joins = """FROM TrackPoint tp
            JOIN Activity a ON tp.activity_id = a.id
            JOIN User u ON a.user_id = u.id"""
        # Then we calculate the total altitude for each user

        altitude_logic = """
                WITH altitude_differences AS (
                    SELECT 
                        a.user_id,
                        CASE 
                            WHEN tp.altitude > LAG(tp.altitude) OVER (PARTITION BY tp.activity_id ORDER BY tp.date_time)
                            AND tp.altitude - LAG(tp.altitude) OVER (PARTITION BY tp.activity_id ORDER BY tp.date_time) <= 100
                            THEN tp.altitude - LAG(tp.altitude) OVER (PARTITION BY tp.activity_id ORDER BY tp.date_time)
                            ELSE 0
                        END AS altitude_gain
                    """ + joins + """
                    WHERE 
                        tp.altitude > -777
                )
            """

        final_query = """
                SELECT 
                    user_id,
                    SUM(altitude_gain) AS total_feet_gained
                FROM 
                    altitude_differences
                GROUP BY 
                    user_id
                ORDER BY 
                    total_feet_gained DESC
                LIMIT 20;
                """

        query = altitude_logic + final_query

        return query

    def find_invalid_activities(self):
        """Function that finds invalid activities. \n
        Completes Task 2.9
        """
        # Find the case for all activities where there are more than 5 minutes between each trackpoint
        query = """WITH trackpoint_differences AS (
    SELECT 
        a.user_id,
        tp.activity_id,
        tp.date_time,
        LAG(tp.date_time) OVER (PARTITION BY tp.activity_id ORDER BY tp.date_time) AS previous_date_time
    FROM 
        TrackPoint tp
    JOIN 
        Activity a ON tp.activity_id = a.id
),
invalid_activities AS (
    SELECT 
        user_id,
        activity_id
    FROM 
        trackpoint_differences
    WHERE 
        previous_date_time IS NOT NULL
        AND TIMESTAMPDIFF(MINUTE, previous_date_time, date_time) >= 5
    GROUP BY 
        user_id, activity_id
)
SELECT 
    user_id,
    COUNT(activity_id) AS invalid_activity_count
FROM 
    invalid_activities
GROUP BY 
    user_id
ORDER BY 
    invalid_activity_count DESC;"""

        return query
    
    def find_users_who_have_been_at_location(self, lat, lon):
        """Function that finds users who have been at a specific location. \n
        Completes Task 2.10
        """
        query = """SELECT DISTINCT activity.user_id
                   FROM trackpoint
                   JOIN activity on trackpoint.activity_id = activity.id
                   WHERE ROUND(lat, 3) = %s AND ROUND(lon,3) = %s
                   GROUP BY activity.user_id
                   """
        return query % (lat, lon)
    
    def find_most_used_transportation_mode_by_users(self):
        """Function that finds the most used transportation mode by users. \n
        Completes Task 2.11
        """
        query = """WITH ranked_modes AS (
                   SELECT user_id, transportation_mode, 
                      ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY COUNT(*) DESC) as placement
                   FROM activity
                   WHERE transportation_mode != 'Unknown'
                   GROUP BY user_id, transportation_mode
               )
               SELECT user_id, transportation_mode as 'Most used transportation mode'
               FROM ranked_modes
               WHERE placement = 1
               ORDER BY user_id
               """
        return query



def main():
    program = None
    try:
        program = QueryProgram()
        # make switch case for the different tasks

        print("Welcome, please choose a task:")

        while True:
            print("1. Present number of rows in each table")
            print("2. Present average number of activities per user")
            print("3. Present top n users with most activities")
            print("4. Present users that have taken a taxi")
            print("5. Present number of activities for each transportation mode")
            print("6. Present the year with the most activities")
            print("7. Present the hours spent on each activity, grouped by year")
            print("8. Present the total distance walked by a user")
            print("9. Calculate the distance for an activity")
            print("10. Present the 20 users with the most altitude")
            print("11. Find invalid activities")
            print("12. Find users who have been at a specific location")
            print("13. Find the most used transportation mode by users")
            print("0. Exit")
            choice = input("Enter your choice: ")

            if choice == "1":
                program.present_table_rows()
            elif choice == "2":
                program.present_rows_and_headers(
                    program.avg_activities_per_user())
            elif choice == "3":
                n = input("Enter the number of users you want to see: ")
                program.present_rows_and_headers(
                    program.top_n_users_with_most_activities(n))

            elif choice == "4":
                program.present_rows_and_headers(
                    program.users_taking_taxi())
            elif choice == "5":
                program.present_rows_and_headers(
                    program.count_activities_by_transportation_mode())
            elif choice == "6":
                program.present_rows_and_headers(
                    program.year_with_most_activities())
            elif choice == "7":
                program.present_rows_and_headers(
                    program.count_hours_per_activity_per_year())
            elif choice == "8":
                user_id = input("Enter the user id: ")
                total_distance = program.total_distance_walked_by_user(user_id)
                print("Total distance walked by user %s: %s meters" %
                      (user_id, total_distance))
            elif choice == "9":
                activity_id = input("Enter the activity id: ")
                program.calculate_distance_for_activity(activity_id)
            elif choice == "10":
                program.present_rows_and_headers(
                    program.top_20_users_with_most_altitude())
            elif choice == "11":
                program.present_rows_and_headers(
                    program.find_invalid_activities())
            elif choice == "12":
                lat = input("Enter the latitude: ")
                lon = input("Enter the longitude: ")
                program.present_rows_and_headers(
                    program.find_users_who_have_been_at_location(lat, lon))
            elif choice == "13":
                program.present_rows_and_headers(
                    program.find_most_used_transportation_mode_by_users())
            elif choice == "0":
                break
            else:
                print("Invalid choice, please try again")

    except Exception as e:
        print("ERROR: Failed to use database:", e)
    finally:
        if program:
            program.connection.close_connection()


if __name__ == '__main__':
    main()
