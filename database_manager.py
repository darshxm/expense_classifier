# database_manager.py
import sqlite3

DB_NAME = 'expenses.db'

def create_expenses_table():
    """
    Create an 'expenses' table if it does not already exist.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_date TEXT,
            amount REAL,
            description TEXT,
            category TEXT
        )
    ''')
    conn.commit()
    conn.close()


def insert_expense(transaction_date, amount, description, category):
    """
    Insert a single expense into the 'expenses' table.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (transaction_date, amount, description, category)
        VALUES (?, ?, ?, ?)
    ''', (transaction_date, amount, description, category))
    conn.commit()
    conn.close()


def get_all_expenses():
    """
    Retrieve all expenses from the table.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT transaction_date, amount, description, category FROM expenses')
    rows = cursor.fetchall()
    conn.close()
    return rows


def expense_exists(transaction_date, description, amount):
    """
    Check if an expense with the given transaction_date and description already exists.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM expenses
        WHERE transaction_date = ? AND description = ? AND amount = ?
    ''', (transaction_date, description, amount))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0
