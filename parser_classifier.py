# parser_classifier.py

import re
import json
from datetime import datetime

# Path to the classification rules JSON file
CLASSIFICATION_RULES_FILE = 'classification_rules.json'

def extract_tikkie_omschrijving(description):
    """
    Extract the 'Omschrijving' field from a Tikkie transaction description.
    """
    pattern = r"Omschrijving:\s*(.*?)\s*Kenmerk:"
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_sepa_omschrijving(description):
    """
    Extract the 'Omschrijving' field from a SEPA transaction description.
    """
    pattern = r"Naam:\s*(.*?)\s*(?:Machtiging|Omschrijving|IBAN|Kenmerk|Voor:|$)"
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_naam_field(description):
    """
    Extract the 'Naam' field from a transaction description.
    Captures multiple words if present.
    """
    pattern = r"Naam:\s*(.+?)\s*(?:Omschrijving|IBAN|Kenmerk|Voor:|$)"
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_pas_transaction(description):
    """
    Extract the merchant name from PAS transactions (e.g., VLOUW BV,PAS041).
    """
    pattern = r'(?:Google Pay\s+|\s*Betaalpas\s+)([^,]+),PAS'
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_merchant_name(description):
    """
    Extract the merchant name from the transaction description.
    Handles various description formats including Tikkie, SEPA, and PAS transactions.
    Returns the merchant name in lowercase.
    """
    # First, check for Tikkie transactions
    if 'sepa ideal' in description.lower():
        if 'tikkie' in description.lower():
            tikkie_omschrijving = extract_tikkie_omschrijving(description)
            if tikkie_omschrijving:
                return tikkie_omschrijving.lower()
        merchant = extract_naam_field(description)
        if merchant:
            return merchant.lower()
    
    # Check for SEPA Incasso
    if 'sepa incasso' in description.lower():
        sepa_omschrijving = extract_sepa_omschrijving(description)
        if sepa_omschrijving:
            return sepa_omschrijving.lower()
    
    # Extract from 'Naam' field
    naam = extract_naam_field(description)
    if naam:
        return naam.lower()
    
    # Extract from PAS transactions (similar to Google Pay)
    pas_merchant = extract_pas_transaction(description)
    if pas_merchant:
        return pas_merchant.lower()
    
    # If all else fails, return None
    return None

def load_classification_rules():
    """
    Load classification rules from the JSON config file.
    If the file does not exist, initialize it with default categories.
    """
    try:
        with open(CLASSIFICATION_RULES_FILE, 'r') as f:
            rules = json.load(f)
    except FileNotFoundError:
        # Initialize with default categories and empty keyword lists
        rules = {}
        default_categories = [
            'Groceries',
            'Eating Out',
            'Alcohol',
            'Transport',
            'Housing',
            'Utilities',
            'Entertainment',
            'Healthcare',
            'Personal Care',
            'Miscellaneous'
        ]
        for category in default_categories:
            rules[category] = []
        with open(CLASSIFICATION_RULES_FILE, 'w') as f:
            json.dump(rules, f, indent=4)
    return rules

def save_classification_rules(rules):
    """
    Save the updated classification rules to the JSON config file.
    """
    with open(CLASSIFICATION_RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=4)

def get_categories():
    """
    Retrieve the list of categories from the classification_rules.json file.
    """
    rules = load_classification_rules()
    return list(rules.keys())

def classify_expense(description):
    """
    Classify the expense based on the transaction description.
    - Uses classification_rules.json for automatic categorization.
    - Handles Tikkie transactions by extracting 'Omschrijving'.
    - Defaults to 'Unclassified' if no rules match.
    """
    lower_desc = description.lower()

    # Load current classification rules
    rules = load_classification_rules()

    # Dynamically retrieve categories
    categories = list(rules.keys())

    # Check each category's keywords
    for category in categories:
        keywords = rules.get(category, [])
        for keyword in keywords:
            if keyword in lower_desc:
                return category

    # Handle Tikkie transactions
    if 'tikkie' in lower_desc:
        tikkie_omschrijving = extract_tikkie_omschrijving(description)
        if tikkie_omschrijving:
            tikkie_omschrijving_lower = tikkie_omschrijving.lower()
            if "groceries" in tikkie_omschrijving_lower:
                return 'Groceries'
            elif "beer" in tikkie_omschrijving_lower or "wine" in tikkie_omschrijving_lower:
                return 'Alcohol'
            elif "restaurant" in tikkie_omschrijving_lower or "cafe" in tikkie_omschrijving_lower:
                return 'Eating Out'
            # Add more Tikkie-specific keywords as needed
            return 'Unclassified'
        return 'Unclassified'

    # Default category if no rules match
    return 'Unclassified'
