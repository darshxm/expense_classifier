# Expense Classifier

## Overview
Expense Classifier is a Python-based application designed to help users categorize and analyze their financial transactions efficiently. The application supports importing transaction data from Excel files, dynamically classifying expenses using predefined or user-defined rules, and providing visual analytics to help track spending trends.

This project is licensed under the **GNU General Public License v3.0**.

---

## Features

- **Expense Import**: Import transaction data from Excel files with support for handling duplicate entries.
- **Dynamic Classification**: Automatically classify transactions based on rules stored in a JSON configuration file. Users can also manually categorize expenses.
- **Category Management**: Add, edit, and manage categories for transaction classification.
- **Visual Analytics**: Generate weekly visual reports of expenses by category using matplotlib.
- **Intuitive GUI**: Easy-to-use interface built with Tkinter, featuring dynamic filtering and selection tools.

---

## Installation

### Prerequisites
Ensure you have the following installed:

- Python 3.8+
- pip (Python package manager)

### Dependencies
Install the required Python libraries using:

```bash
pip install -r requirements.txt
```

### Clone the Repository
Clone this repository to your local machine:

```bash
git clone https://github.com/darshxm/expense-classifier.git
cd expense-classifier
```

---

## Usage

1. **Run the Application**:
   Launch the main script to start the application:
   
   ```bash
   python main.py
   ```

2. **Import Data**:
   - Click on the "Import Data" button to load an Excel file containing your transaction data.
   - Ensure the Excel file has the following columns:
     - `transactiondate`: The date of the transaction.
     - `amount`: The transaction amount.
     - `description`: The transaction description.

3. **Classify Expenses**:
   - Select unclassified transactions and assign them to categories using the dropdown menu.
   - Use the "Classify All" option to apply rules to all similar transactions automatically.

4. **Add New Categories**:
   - Use the "Add Category" button to define new categories and manage classification rules.

5. **View Analytics**:
   - Click on the "Show Analytics" button to view weekly spending trends by category.

---

## File Structure

```plaintext
.
├── main.py                 # Entry point for the application
├── gui_app.py              # GUI implementation for the application
├── parser_classifier.py    # Functions for expense classification and merchant extraction
├── data_reader.py          # Handles reading and processing Excel files
├── database_manager.py     # Manages SQLite database operations
├── classification_rules.json  # Stores classification rules (auto-generated)
├── expenses.db             # SQLite database file (auto-generated)
└── requirements.txt        # Python dependencies
```

---

## Configuration

- **Classification Rules**:
  - Classification rules are stored in the `classification_rules.json` file.
  - You can manually edit this file to add or modify rules.

---

## Analytics

- Visual analytics are generated using `matplotlib` and displayed in a separate window.
- Weekly trends are plotted for all classified categories, with each category represented as a separate line in the graph.

---

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements or bug fixes.

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a detailed description of your changes.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for more details.

---

## Acknowledgments

- Python community for their amazing libraries and tools.
- matplotlib for data visualization.
- Tkinter for the GUI framework.

---

## Contact

If you have any questions or feedback, please feel free to contact me!

