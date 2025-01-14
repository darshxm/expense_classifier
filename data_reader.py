# data_reader.py

import pandas as pd
import re
import os

def read_transaction_file(filepath, bank):
    """
    Read the transaction file (Excel or CSV) and return the relevant columns as a pandas DataFrame.
    Handle different formats based on the selected bank.

    Parameters:
    - filepath: str, path to the transaction file.
    - bank: str, name of the bank ("ABN Amro" or "ING").

    Returns:
    - pd.DataFrame with standardized columns: ['transactiondate', 'amount', 'description', 'transaction_type']
    """

    # Validate file existence
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"The file {filepath} does not exist.")

    # Determine file extension
    _, file_extension = os.path.splitext(filepath)
    file_extension = file_extension.lower()

    # Read the file based on its extension
    try:
        if file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        elif file_extension == '.csv':
            df = pd.read_csv(filepath)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}. Only Excel and CSV files are supported.")
    except Exception as e:
        raise ValueError(f"Error reading the file: {e}")

    # Process based on bank
    if bank == "ABN Amro":
        df = process_abn_amro(df, file_extension)
    elif bank == "ING":
        df = process_ing(df, file_extension)
    else:
        raise ValueError(f"Unsupported bank: {bank}")

    return df

def process_abn_amro(df, file_extension):
    """
    Process ABN Amro transaction data from Excel or CSV files.

    Parameters:
    - df: pd.DataFrame, raw transaction data.
    - file_extension: str, file extension to determine format-specific processing.

    Returns:
    - pd.DataFrame with standardized columns.
    """

    # Define expected columns based on file type
    if file_extension in ['.xlsx', '.xls']:
        expected_columns = ['transactiondate', 'amount', 'description']
    elif file_extension == '.csv':
        expected_columns = ['Transaction Date', 'Amount', 'Description']
    else:
        raise ValueError(f"Unsupported file extension for ABN Amro: {file_extension}")

    # Check if all expected columns are present
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in ABN Amro data: {missing_columns}")

    # Rename columns to standardized names
    if file_extension in ['.xlsx', '.xls']:
        df = df[expected_columns].copy()
    elif file_extension == '.csv':
        # Rename CSV columns to standardized names
        df = df.rename(columns={
            'Transaction Date': 'transactiondate',
            'Amount': 'amount',
            'Description': 'description'
        })
        df = df[['transactiondate', 'amount', 'description']].copy()

    # Convert 'transactiondate' to datetime
    df['transactiondate'] = pd.to_datetime(df['transactiondate'], format='%Y%m%d', errors='coerce')

    # Handle potential date parsing issues
    if df['transactiondate'].isnull().any():
        raise ValueError("Some transaction dates could not be parsed. Please check the date format.")

    # Extract 'transaction_type' from 'description'
    df['transaction_type'] = df['description'].apply(extract_transaction_type_abn_amro)

    return df

def process_ing(df, file_extension):
    """
    Process ING transaction data from Excel or CSV files.

    Parameters:
    - df: pd.DataFrame, raw transaction data.
    - file_extension: str, file extension to determine format-specific processing.

    Returns:
    - pd.DataFrame with standardized columns and adjusted 'amount' values.
    """

    # Define expected columns based on file type
    expected_columns = ['Date', 'Name / Description', 'Account', 'Counterparty', 'Code', 
                        'Debit/credit', 'Amount (EUR)', 'Transaction type', 'Notifications']

    if file_extension not in ['.xlsx', '.xls', '.csv']:
        raise ValueError(f"Unsupported file extension for ING: {file_extension}")

    # Check if all expected columns are present
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing columns in ING data: {missing_columns}")

    # Rename columns to standardized names
    if file_extension in ['.xlsx', '.xls']:
        df = df[expected_columns].copy()
        # Rename columns to standardized names
        df = df.rename(columns={
            'Date': 'transactiondate',
            'Amount (EUR)': 'amount',
            'Transaction type': 'transaction_type',
            'Notifications': 'description'
        })
    elif file_extension == '.csv':
        # If the CSV uses a different decimal separator (e.g., comma), specify it
        # For example, if decimals are commas and thousands are periods:
        # df = pd.read_csv(filepath, decimal=',', thousands='.')
        df = df.rename(columns={
            'Date': 'transactiondate',
            'Name / Description': 'name_description',
            'Amount (EUR)': 'amount',
            'Transaction type': 'transaction_type',
            'Notifications': 'description'
        })
        df = df[['transactiondate', 'Debit/credit', 'amount', 'description', 'transaction_type']].copy()

    # Convert 'transactiondate' to datetime
    df['transactiondate'] = pd.to_datetime(df['transactiondate'].astype(str), format='%Y%m%d', errors='coerce')

    # Handle potential date parsing issues
    if df['transactiondate'].isnull().any():
        raise ValueError("Some transaction dates could not be parsed. Please check the date format.")

    # Clean the 'amount' column
    # Remove any non-numeric characters (e.g., currency symbols, spaces)
    # This assumes that the amount uses '.' as the decimal separator
    # Adjust the regex pattern if your data uses different formatting
    df['amount'] = df['amount'].astype(str).str.replace(r'[^\d.,-]', '', regex=True)

    # Replace comma with dot if comma is used as decimal separator
    if df['amount'].str.contains(',').any():
        df['amount'] = df['amount'].str.replace(',', '.')

    # Convert 'amount' to numeric, coercing errors to NaN
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    # Check for any NaN values in 'amount' after conversion
    if df['amount'].isnull().any():
        num_invalid = df['amount'].isnull().sum()
        raise ValueError(f"{num_invalid} entries in 'amount' could not be converted to numeric. Please check the data.")

    # Assign positive or negative values to 'amount' based on 'Debit/credit'
    df['amount'] = df.apply(
        lambda row: -row['amount'] if str(row['Debit/credit']).strip().lower() == 'debit' else row['amount'],
        axis=1
    )

    # Optionally, drop the 'Debit/credit' column if it's no longer needed
    df = df.drop(columns=['Debit/credit'])

    return df



def extract_transaction_type_abn_amro(description):
    """
    Extracts the transaction type from ABN Amro transaction descriptions.
    This function uses regular expressions to identify keywords indicating the transaction type.

    Parameters:
    - description: str, transaction description.

    Returns:
    - str, extracted transaction type or 'Unknown' if no pattern matches.
    """
    description_lower = description.lower()

    # Define patterns for different transaction types
    patterns = {
        'iDEAL': r'\bideal\b',
        'SEPA Overboeking': r'\bsepa overboeking\b',
        'SEPA Incasso': r'\bsepa incasso\b',
        'Tikkie': r'\btikkie\b',
        'Payment Terminal': r'\bBEA\b',
        # Add more patterns as needed
    }

    for txn_type, pattern in patterns.items():
        if re.search(pattern, description_lower):
            return txn_type

    return 'Unknown'  # Default if no pattern matches
