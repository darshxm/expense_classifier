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
            category TEXT,
            bank TEXT,
            transaction_type TEXT  -- New column for transaction type
        )
    ''')
    conn.commit()
    conn.close()


def insert_expense(transaction_date, amount, description, category, bank, transaction_type):
    """
    Insert a single expense into the 'expenses' table with bank and transaction type information.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO expenses (transaction_date, amount, description, category, bank, transaction_type)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (transaction_date, amount, description, category, bank, transaction_type))
    conn.commit()
    conn.close()


def expense_exists(transaction_date, description, amount, bank, transaction_type):
    """
    Check if an expense with the given details already exists.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM expenses
        WHERE transaction_date = ? AND description = ? AND amount = ? 
          AND bank = ? AND transaction_type = ?
    ''', (transaction_date, description, amount, bank, transaction_type))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0



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

