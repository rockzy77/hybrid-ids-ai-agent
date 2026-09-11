import os
import random
from datetime import datetime, timedelta, time

import mysql.connector
from faker import Faker
from dotenv import load_dotenv

load_dotenv()

fake = Faker()
random.seed(42)   # reproducible dataset — helpful for dissertation write-up
Faker.seed(42)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "hybrid_ids"),
}

DEPARTMENTS = ["Engineering", "Finance", "HR", "IT Support", "Sales", "Marketing", "Legal"]

ROLES_BY_DEPT = {
    "Engineering": ["Software Engineer", "DevOps Engineer", "QA Engineer"],
    "Finance": ["Financial Analyst", "Accountant"],
    "HR": ["HR Advisor", "Recruiter"],
    "IT Support": ["IT Support Technician", "Systems Administrator"],
    "Sales": ["Sales Executive", "Account Manager"],
    "Marketing": ["Marketing Executive", "Content Strategist"],
    "Legal": ["Legal Counsel", "Compliance Officer"],
}

CLEARANCE_BY_ROLE_KEYWORD = {
    "Administrator": "admin",
    "Systems": "admin",
    "DevOps": "high",
    "Legal Counsel": "high",
    "Compliance": "high",
    "Manager": "medium",
    "Advisor": "medium",
}

TICKET_TYPES = ["access_request", "it_maintenance", "after_hours_approval", "incident"]
TICKET_STATUSES = ["open", "in_progress", "resolved", "closed"]

TICKET_DESCRIPTIONS = {
    "access_request": [
        "Requesting elevated access to shared project resources.",
        "Requesting access to the staging database for a migration task.",
        "Requesting temporary admin rights to configure a new internal service.",
    ],
    "it_maintenance": [
        "Reported intermittent VPN connectivity issues.",
        "Running scheduled internal vulnerability scan across the subnet as part of the monthly security audit.",
        "Deploying an automated monitoring/health-check agent that periodically polls internal services.",
        "Investigating a reported slow network segment, running diagnostic port scans to isolate the cause.",
        "Rotating service credentials and testing connectivity across multiple internal ports.",
    ],
    "after_hours_approval": [
        "Requesting approval to access systems outside standard work hours for a deadline.",
        "Approved to run an out-of-hours batch job and backup script overnight.",
        "Requesting after-hours access to complete an urgent client deployment.",
    ],
    "incident": [
        "Reported a suspicious login prompt and possible phishing attempt.",
        "Reported unusual pop-ups after opening an email attachment.",
        "Reported their machine running slowly after visiting an unfamiliar website.",
    ],
}

LEAVE_TYPES = ["annual", "sick", "unpaid", "remote_work"]

NUM_EMPLOYEES = 20
NUM_TICKETS = 50
NUM_LEAVE_RECORDS = 30


def clearance_for_role(role: str) -> str:
    for keyword, level in CLEARANCE_BY_ROLE_KEYWORD.items():
        if keyword.lower() in role.lower():
            return level
    return "low"


def random_private_ip(used_ips: set) -> str:
    while True:
        ip = f"10.0.{random.randint(0, 20)}.{random.randint(2, 254)}"
        if ip not in used_ips:
            used_ips.add(ip)
            return ip


def random_work_hours():
    start_hour = random.choice([7, 8, 8, 9, 9, 10])
    duration = random.choice([8, 8, 9])
    end_hour = start_hour + duration
    return time(start_hour, 0, 0), time(min(end_hour, 23), 0, 0)


def seed_employees(cursor, conn):
    used_ips = set()
    employee_ids = []

    for _ in range(NUM_EMPLOYEES):
        name = fake.name()
        department = random.choice(DEPARTMENTS)
        role = random.choice(ROLES_BY_DEPT[department])
        ip_address = random_private_ip(used_ips)
        work_start, work_end = random_work_hours()
        clearance = clearance_for_role(role)

        cursor.execute(
            """
            INSERT INTO employees (name, department, role, ip_address, work_start, work_end, clearance_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name, department, role, ip_address, work_start, work_end, clearance),
        )
        employee_ids.append(cursor.lastrowid)

    conn.commit()
    print(f"Inserted {len(employee_ids)} employees.")
    return employee_ids


def seed_tickets(cursor, conn, employee_ids):
    count = 0
    for _ in range(NUM_TICKETS):
        employee_id = random.choice(employee_ids)
        ticket_type = random.choice(TICKET_TYPES)
        status = random.choice(TICKET_STATUSES)

        created_at = fake.date_time_between(start_date="-60d", end_date="now")
        resolved_at = None
        if status in ("resolved", "closed"):
            resolved_at = created_at + timedelta(hours=random.randint(1, 72))

        description = random.choice(TICKET_DESCRIPTIONS[ticket_type])

        cursor.execute(
            """
            INSERT INTO tickets (employee_id, type, description, status, created_at, resolved_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (employee_id, ticket_type, description, status, created_at, resolved_at),
        )
        count += 1

    conn.commit()
    print(f"Inserted {count} tickets.")


def seed_leave(cursor, conn, employee_ids):
    count = 0
    for _ in range(NUM_LEAVE_RECORDS):
        employee_id = random.choice(employee_ids)
        leave_type = random.choice(LEAVE_TYPES)
        start_date = fake.date_between(start_date="-60d", end_date="+30d")
        end_date = start_date + timedelta(days=random.randint(1, 10))
        approved = random.random() < 0.85  # most leave gets approved

        cursor.execute(
            """
            INSERT INTO leave_records (employee_id, leave_type, start_date, end_date, approved)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (employee_id, leave_type, start_date, end_date, approved),
        )
        count += 1

    conn.commit()
    print(f"Inserted {count} leave records.")


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("alerts", "leave_records", "tickets", "employees"):
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

    employee_ids = seed_employees(cursor, conn)
    seed_tickets(cursor, conn, employee_ids)
    seed_leave(cursor, conn, employee_ids)

    cursor.close()
    conn.close()
    print("Seeding complete.")


if __name__ == "__main__":
    main()