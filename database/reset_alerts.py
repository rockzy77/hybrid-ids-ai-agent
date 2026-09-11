import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hybrid_ids"),
}


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("TRUNCATE TABLE alerts")
    conn.commit()

    cursor.close()
    conn.close()
    print("alerts table cleared. employees / tickets / leave_records left untouched.")


if __name__ == "__main__":
    main()
