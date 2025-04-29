import sqlite3

def create_and_populate_database(database_path="library.db"):
    """
    Creates a SQLite database, a 'books' table, and inserts sample data.

    Args:
        database_path (str): The path to the SQLite database file.
    """

    conn = None  # Initialize outside the try block
    try:
        # Connect to the database (creates the file if it doesn't exist)
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        # Create the 'books' table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY,
                title TEXT,
                author TEXT,
                publication_year INTEGER
            )
        """)

        # Insert sample data (clear existing data to prevent duplicates)
        cursor.execute("DELETE FROM books;")
        books_data = [
             ('The Hitchhiker\'s Guide to the Galaxy', 'Douglas Adams', 1979),
            ('Pride and Prejudice', 'Jane Austen', 1813),
            ('1984', 'George Orwell', 1949),
            ('To Kill a Mockingbird', 'Harper Lee', 1960),
            ('The Lord of the Rings', 'J.R.R. Tolkien', 1954),
            ('Dune', 'Frank Herbert', 1965)
        ]
        cursor.executemany("INSERT INTO books (title, author, publication_year) VALUES (?, ?, ?)", books_data)
        conn.commit()
        print(f"Database '{database_path}' created successfully, table 'books' populated with sample data.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
             conn.close()  # Close the database connection if it exists

if __name__ == "__main__":
    create_and_populate_database()