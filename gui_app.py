# gui_app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from database_manager import insert_expense, create_expenses_table, expense_exists
from parser_classifier import (
    classify_expense, extract_merchant_name,
    load_classification_rules, save_classification_rules,
    get_categories  # Import the new function
)
from data_reader import read_excel_file
import os
import sqlite3
import pandas as pd  # Ensure pandas is imported
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timedelta


class ExpenseClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Expense Classifier")

        # Dynamically load categories from the JSON file
        self.categories = get_categories()

        self.create_widgets()
        create_expenses_table()  # Ensure the database table exists

    def create_widgets(self):
        """
        Create and layout all the widgets in the application, including buttons,
        Treeview for displaying unclassified expenses, category selection dropdown,
        classification checkbox, and additional controls for filtering and analytics.
        """
        # -----------------------------------
        # Top Frame: Import Data, Add Category, Show Analytics, Filter
        # -----------------------------------
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # Import Data Button
        import_button = ttk.Button(top_frame, text="Import Data", command=self.import_data)
        import_button.pack(side=tk.LEFT, padx=5)

        # Add Category Button
        add_cat_button = ttk.Button(top_frame, text="Add Category", command=self.add_new_category)
        add_cat_button.pack(side=tk.LEFT, padx=5)

        # Show Analytics Button
        show_analytics_button = ttk.Button(top_frame, text="Show Analytics", command=self.show_analytics)
        show_analytics_button.pack(side=tk.LEFT, padx=5)

        # Filter by Transaction Type Label
        ttk.Label(top_frame, text="Filter by Type:").pack(side=tk.LEFT, padx=5)

        # Filter Dropdown
        self.transaction_type_filter = tk.StringVar()
        self.filter_dropdown = ttk.Combobox(
            top_frame,
            textvariable=self.transaction_type_filter,
            values=["All", "SEPA iDEAL", "SEPA Overboeking", "PAS", "Tikkie"],
            state="readonly"
        )
        self.filter_dropdown.set("All")  # Default filter
        self.filter_dropdown.pack(side=tk.LEFT, padx=5)
        self.filter_dropdown.bind("<<ComboboxSelected>>", lambda e: self.refresh_unclassified())

        # Refresh Button
        refresh_button = ttk.Button(top_frame, text="Refresh", command=self.refresh_unclassified)
        refresh_button.pack(side=tk.LEFT, padx=5)

        # -----------------------------------
        # Unclassified Expenses Frame with Treeview and Scrollbars
        # -----------------------------------
        self.unclassified_frame = ttk.LabelFrame(self.root, text="Unclassified Expenses", padding="10")
        self.unclassified_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Define Treeview Columns
        columns = ("Date", "Amount", "Description", "Category")

        # Create Treeview with Extended Selection Mode
        self.tree = ttk.Treeview(
            self.unclassified_frame,
            columns=columns,
            show='headings',
            selectmode='extended',  # Enable multiple selection
            height=20  # Set a reasonable default height
        )

        # Define Column Headings and Configuration
        self.tree.heading("Date", text="Date")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Category", text="Category")

        # Configure Column Alignment and Width
        self.tree.column("Date", anchor=tk.CENTER, width=100, stretch=False)
        self.tree.column("Amount", anchor=tk.CENTER, width=100, stretch=False)
        self.tree.column("Description", anchor=tk.W, width=300, stretch=True)  # Left-aligned
        self.tree.column("Category", anchor=tk.CENTER, width=150, stretch=False)

        # Add Vertical Scrollbar
        vsb = ttk.Scrollbar(self.unclassified_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Add Horizontal Scrollbar
        hsb = ttk.Scrollbar(self.unclassified_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hsb.set)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        # Pack the Treeview
        self.tree.pack(fill=tk.BOTH, expand=True)

        # -----------------------------------
        # Category Selection and Classification Controls
        # -----------------------------------
        category_frame = ttk.Frame(self.root, padding="10")
        category_frame.pack(fill=tk.X)

        # Selected Category Label
        ttk.Label(category_frame, text="Selected Category:").pack(side=tk.LEFT, padx=5)

        # Category Dropdown
        self.selected_category = tk.StringVar()
        self.category_dropdown = ttk.Combobox(
            category_frame,
            textvariable=self.selected_category,
            values=self.categories,
            state="readonly"
        )
        self.category_dropdown.pack(side=tk.LEFT, padx=5)

        # Classify All Checkbox
        self.classify_all_checkbox = tk.BooleanVar()
        self.classify_all_checkbox.set(False)  # Default is unchecked
        classify_all_checkbutton = ttk.Checkbutton(
            category_frame,
            text="Classify all expenses from this business in the same category",
            variable=self.classify_all_checkbox
        )
        classify_all_checkbutton.pack(side=tk.LEFT, padx=5)

        # Classify Selected Button
        classify_button = ttk.Button(category_frame, text="Classify Selected", command=self.classify_selected)
        classify_button.pack(side=tk.LEFT, padx=5)


        


    def import_data(self):
        """
        Open a file dialog to select an Excel file, process it, and insert into the database.
        Avoid inserting duplicates based on transaction_date and description.
        """
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )
        if not file_path:
            return  # User cancelled

        try:
            df = read_excel_file(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read the Excel file.\n{e}")
            return

        # Counters for feedback
        total_rows = len(df)
        inserted = 0
        duplicates = 0

        # Process each row
        for _, row in df.iterrows():
            transaction_date = row['transactiondate']
            amount = row['amount']
            description = str(row['description'])  # ensure it's a string

            # Convert transaction_date to string in 'YYYY-MM-DD' format
            if pd.notnull(transaction_date):
                transaction_date_str = transaction_date.strftime('%Y-%m-%d')
            else:
                transaction_date_str = ''  # or handle as needed

            # Check for duplicates
            if transaction_date_str and description:
                if expense_exists(transaction_date_str, description, amount):
                    duplicates += 1
                    continue  # Skip inserting duplicate
            else:
                # Optionally, decide how to handle missing date or description
                # For now, we'll skip entries with missing critical info
                duplicates += 1
                continue

            # Classify
            category = classify_expense(description)

            # Insert into database
            insert_expense(transaction_date_str, amount, description, category)
            inserted += 1

        # Provide feedback to the user
        message = f"Import completed.\n\nTotal Rows Processed: {total_rows}\n" \
                  f"Successfully Imported: {inserted}\n" \
                  f"Duplicates Skipped: {duplicates}"
        messagebox.showinfo("Import Results", message)
        self.refresh_unclassified()

    def refresh_unclassified(self):
        """
        Refresh the treeview to display current unclassified expenses based on the selected filter.
        """
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Fetch filtered unclassified expenses
        transaction_type = self.transaction_type_filter.get()
        unclassified_expenses = self.get_unclassified_expenses(transaction_type)

        for expense in unclassified_expenses:
            expense_id, transaction_date, amount, description, category = expense
            self.tree.insert("", "end", iid=expense_id, values=(transaction_date, amount, description, category))

    def get_unclassified_expenses(self, transaction_type="All"):
        """
        Retrieves rows from the 'expenses' table where category is 'Unclassified' or NULL.
        Filters by transaction type if specified.
        """
        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()

        if transaction_type == "All":
            cursor.execute("""
                SELECT id, transaction_date, amount, description, category
                FROM expenses
                WHERE category IS NULL OR category = 'Unclassified'
            """)
        else:
            cursor.execute("""
                SELECT id, transaction_date, amount, description, category
                FROM expenses
                WHERE (category IS NULL OR category = 'Unclassified')
                AND description LIKE ?
            """, (f"%{transaction_type}%",))
        
        rows = cursor.fetchall()
        conn.close()
        return rows


    def classify_selected(self):
        """
        Classify the selected expense(s) with the chosen category from the dropdown.
        If the 'Classify all expenses from this business in the same category' checkbox is checked,
        classify all expenses from the same business.
        """
        # Retrieve all selected items from the Treeview
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more expenses to classify.")
            return

        # Retrieve the selected category from the dropdown
        category = self.selected_category.get()
        if not category:
            messagebox.showwarning("No Category", "Please select a category.")
            return

        # Check the state of the 'Classify all expenses from this business' checkbox
        classify_all = self.classify_all_checkbox.get()

        # Prepare the confirmation message based on the checkbox state
        num_selected = len(selected_items)
        confirmation_message = f"Are you sure you want to classify {num_selected} expense(s) as '{category}'?"
        if classify_all:
            confirmation_message += "\nYou will classify all expenses from the selected businesses into this category."

        # Display the confirmation dialog
        confirm = messagebox.askyesno("Confirm Classification", confirmation_message)
        if not confirm:
            return  # User chose to cancel the operation

        # Initialize a set to store unique merchant names (in lowercase)
        merchant_names = set()

        # Iterate through each selected expense to extract merchant names if needed
        for expense_id in selected_items:
            item = self.tree.item(expense_id)
            description = item['values'][2]  # Assuming 'Description' is the third column
            merchant_name = extract_merchant_name(description)
            if classify_all and merchant_name:
                merchant_names.add(merchant_name.lower())

        # If 'Classify all' is checked and there are merchant names, update classification rules
        if classify_all and merchant_names:
            # Load existing classification rules
            rules = load_classification_rules()
            updated = False  # Flag to track if rules are updated

            for merchant_name in merchant_names:
                # Check if the merchant is already in the selected category's keywords
                if merchant_name not in (kw.lower() for kw in rules.get(category, [])):
                    # Add the merchant name to the category's keyword list
                    rules[category].append(merchant_name)
                    updated = True

            # Save the updated classification rules if any changes were made
            if updated:
                save_classification_rules(rules)

        # Classify each selected expense
        for expense_id in selected_items:
            self.update_expense_category(expense_id, category)  # Update the category in the database

        # If 'Classify all' is checked, update all related transactions in the database
        if classify_all and merchant_names:
            for merchant_name in merchant_names:
                self.update_related_transactions(merchant_name, category)

        # Refresh the Treeview to reflect the changes
        self.refresh_unclassified()

        # Display a success message to the user
        messagebox.showinfo("Success", f"Classified {num_selected} expense(s) as '{category}'.")



    def update_related_transactions(self, keyword, category):
        """
        Find all unclassified transactions that contain the keyword and set their category.
        """
        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()
        # Use case-insensitive search
        cursor.execute("""
            UPDATE expenses
            SET category = ?
            WHERE (category IS NULL OR category = 'Unclassified')
            AND LOWER(description) LIKE ?
        """, (category, f'%{keyword}%'))
        conn.commit()
        conn.close()
        self.refresh_unclassified()

    def update_expense_category(self, expense_id, category):
        """
        Updates the category of a specific expense.
        """
        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE expenses
            SET category = ?
            WHERE id = ?
        """, (category, expense_id))
        conn.commit()
        conn.close()

    def show_analytics(self):
        """
        Open a new window to display analytics with a line graph showing
        expenses on a week-by-week basis for all categories.
        """
        analytics_window = tk.Toplevel(self.root)
        analytics_window.title("Expense Analytics")
        analytics_window.geometry("800x600")

        try:
            # Fetch all classified expenses (exclude 'Unclassified' and NULL)
            conn = sqlite3.connect('expenses.db')
            cursor = conn.cursor()
            cursor.execute("""
                SELECT transaction_date, amount, category
                FROM expenses
                WHERE category IS NOT NULL AND category != 'Unclassified'
            """)
            data = cursor.fetchall()
            conn.close()

            if not data:
                messagebox.showinfo("No Data", "There are no classified expenses to display.")
                analytics_window.destroy()
                return

            # Create DataFrame
            df = pd.DataFrame(data, columns=['transaction_date', 'amount', 'category'])

            # Convert 'transaction_date' to datetime
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], format='%Y-%m-%d', errors='coerce')

            # Drop rows with invalid dates
            df = df.dropna(subset=['transaction_date'])

            if df.empty:
                messagebox.showinfo("No Valid Dates", "No valid transaction dates found.")
                analytics_window.destroy()
                return

            # Set 'transaction_date' as the DataFrame index
            df.set_index('transaction_date', inplace=True)

            # Resample data on a weekly basis and sum amounts using pd.Grouper
            weekly_data = df.groupby(['category', pd.Grouper(freq='W')]).sum().reset_index()

            # Pivot the data to have categories as columns
            pivot_df = weekly_data.pivot(index='transaction_date', columns='category', values='amount')
            pivot_df = pivot_df.fillna(0)  # Replace NaN with 0

            # Plotting
            fig, ax = plt.subplots(figsize=(10, 6))

            for category in pivot_df.columns:
                ax.plot(pivot_df.index, pivot_df[category], marker='o', label=category)

            ax.set_title('Weekly Expenses by Category')
            ax.set_xlabel('Week')
            ax.set_ylabel('Total Amount')
            ax.legend()
            ax.grid(True)

            fig.autofmt_xdate()  # Auto-format date labels

            # Embed the plot in the Tkinter window
            canvas = FigureCanvasTkAgg(fig, master=analytics_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Optionally, add a toolbar for interactivity
            toolbar = ttk.Frame(analytics_window)
            toolbar.pack()
            # Uncomment the following lines to add the navigation toolbar
            # from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            # nav_toolbar = NavigationToolbar2Tk(canvas, analytics_window)
            # nav_toolbar.update()
            # canvas.get_tk_widget().pack()

        except Exception as e:
            messagebox.showerror("Analytics Error", f"An error occurred while generating analytics:\n{e}")
            analytics_window.destroy()

    

    def add_new_category(self):
        """
        Prompt the user to enter a new category name, then add it to the
        classification_rules.json and the category dropdown list.
        """
        new_cat = simpledialog.askstring("Add New Category", "Enter new category name:")
        if new_cat:
            new_cat = new_cat.strip()
            if not new_cat:
                messagebox.showwarning("Invalid Name", "Category name cannot be empty.")
                return

            # Load existing rules
            rules = load_classification_rules()

            # Normalize existing category names for case-insensitive comparison
            existing_categories = [cat.lower() for cat in rules.keys()]

            # If category already exists, just warn the user
            if new_cat.lower() in existing_categories:
                messagebox.showinfo("Category Exists", f"'{new_cat}' already exists.")
            else:
                # Create the category with an empty list of keywords
                rules[new_cat] = []
                save_classification_rules(rules)

                # Update the local categories list and the combobox
                self.categories = get_categories()  # Reload categories
                self.category_dropdown['values'] = self.categories
                messagebox.showinfo("Success", f"Added new category '{new_cat}'.")

def run_gui_classification_app():
    root = tk.Tk()
    app = ExpenseClassifierApp(root)
    root.mainloop()
