# data_reader.py
import pandas as pd

def read_excel_file(filepath):
    """
    Read the Excel file and return the relevant columns as a pandas DataFrame.
    """
    df = pd.read_excel(filepath)

    # Keep only columns we care about; rename them to standard names if necessary
    df = df[['transactiondate', 'amount', 'description']].copy()

    # Convert 'transactiondate' to a standard datetime format if necessary
    # Handle different date formats if needed
    df['transactiondate'] = pd.to_datetime(df['transactiondate'], format='%Y%m%d', errors='coerce')

    return df
