# gui_app.py

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkcalendar import DateEntry  # Import DateEntry from tkcalendar
from database_manager import insert_expense, create_expenses_table, expense_exists
from parser_classifier import (
    classify_expense, extract_merchant_name,
    load_classification_rules, save_classification_rules,
    get_categories  # Import the new function
)
from data_reader import read_transaction_file
import os
import sqlite3
import pandas as pd  # Ensure pandas is imported
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure  # Import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.dates as mdates  # For date formatting
from datetime import datetime, timedelta
from prophet import Prophet
# Use the appropriate backend
matplotlib.use('TkAgg')


class ExpenseClassifierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Expense Classifier")

        # Dynamically load categories from the JSON file
        self.categories = get_categories()
        self.analytics_window = None  # Track analytics window
        self.supported_banks = ["ABN Amro", "ING"]

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
        columns = ("Date", "Amount", "Description", "Category", "Bank", "Transaction Type")

        # Create Treeview with Extended Selection Mode
        columns = ("Date", "Amount", "Description", "Category", "Bank", "Transaction Type")
        self.tree = ttk.Treeview(
            self.unclassified_frame,
            columns=columns,
            show='headings',
            selectmode='extended',
            height=20
        )

        # Define Column Headings and Configuration
        self.tree.heading("Date", text="Date")
        self.tree.heading("Amount", text="Amount")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Bank", text="Bank")
        self.tree.heading("Transaction Type", text="Transaction Type")


        # Configure Column Alignment and Width
        self.tree.column("Date", anchor=tk.CENTER, width=100, stretch=False)
        self.tree.column("Amount", anchor=tk.CENTER, width=100, stretch=False)
        self.tree.column("Description", anchor=tk.W, width=300, stretch=True)  # Left-aligned
        self.tree.column("Category", anchor=tk.CENTER, width=150, stretch=False)
        self.tree.column("Bank", anchor=tk.CENTER, width=150, stretch=False)
        self.tree.column("Transaction Type", anchor=tk.CENTER, width=150, stretch=False)

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
        Open a dialog to select the bank, then open a file dialog to select an Excel file,
        process it, and insert into the database with the selected bank.
        """
        # Prompt user to select a bank
        bank = self.select_bank_dialog()
        if not bank:
            return  # User cancelled

        # Proceed with file selection
        file_path = filedialog.askopenfilename(
            title="Select Transactions File",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not file_path:
            return  # User cancelled

        try:
            df = read_transaction_file(file_path, bank)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read the file.\n{e}")
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
            transaction_type = row.get('transaction_type', 'Unknown')  # Default to 'Unknown' if not present

            # Convert transaction_date to string in 'YYYY-MM-DD' format
            if pd.notnull(transaction_date):
                transaction_date_str = transaction_date.strftime('%Y-%m-%d')
            else:
                transaction_date_str = ''  # or handle as needed

            # Check for duplicates
            if transaction_date_str and description:
                if expense_exists(transaction_date_str, description, amount, bank, transaction_type):
                    duplicates += 1
                    continue  # Skip inserting duplicate
            else:
                duplicates += 1
                continue

            # Classify
            category = classify_expense(description, bank, transaction_type)  # Pass transaction_type to classifier

            # Insert into database with bank and transaction type information
            insert_expense(transaction_date_str, amount, description, category, bank, transaction_type)
            inserted += 1

        # Provide feedback to the user
        message = f"Import completed.\n\nTotal Rows Processed: {total_rows}\n" \
                  f"Successfully Imported: {inserted}\n" \
                  f"Duplicates Skipped: {duplicates}"
        messagebox.showinfo("Import Results", message)
        
        self.update_transaction_type_filter()
        self.refresh_unclassified()
    
    def update_transaction_type_filter(self):
        """
        Populate the transaction type filter dropdown with all distinct transaction types from the DB, plus 'All'.
        """
        with sqlite3.connect('expenses.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT transaction_type
                FROM expenses
                WHERE transaction_type IS NOT NULL AND transaction_type != ''
            """)
            results = cursor.fetchall()
        transaction_types = [row[0] for row in results if row[0]]
        transaction_types.sort()
        self.filter_dropdown['values'] = ["All"] + transaction_types
        
    def select_bank_dialog(self):
        """
        Prompt the user to select a bank from a dropdown.
        Returns the selected bank or None if cancelled.
        """
        dialog = BankSelectionDialog(self.root, self.supported_banks)
        self.root.wait_window(dialog.top)
        return dialog.selected_bank
        
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
            expense_id, transaction_date, amount, description, category, bank = expense
            self.tree.insert("", "end", iid=expense_id, values=(transaction_date, amount, description, category, bank))


    def get_unclassified_expenses(self, transaction_type="All"):
        """
        Retrieves rows from the 'expenses' table where category is 'Unclassified' or NULL.
        Filters by transaction type if specified.
        """
        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()

        if transaction_type == "All":
            cursor.execute("""
                SELECT id, transaction_date, amount, description, category, bank
                FROM expenses
                WHERE category IS NULL OR category = 'Unclassified'
            """)
        else:
            cursor.execute("""
                SELECT id, transaction_date, amount, description, category, bank
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

        # Check the state of the 'Classify all expenses from this business in the same category' checkbox
        classify_all = self.classify_all_checkbox.get()

        # Prepare the confirmation message based on the checkbox state
        num_selected = len(selected_items)
        confirmation_message = f"Are you sure you want to classify {num_selected} expense(s) as '{category}'?"
        if classify_all:
            confirmation_message += f"\nYou will classify all expenses from the selected businesses into {category}."

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
        #messagebox.showinfo("Success", f"Classified {num_selected} expense(s) as '{category}'.")

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
        expenses on a week-by-week basis for selected categories and date range.
        """
        if self.analytics_window and tk.Toplevel.winfo_exists(self.analytics_window):
            self.analytics_window.lift()  # Bring the existing window to front
            return  # Do not create another window

        # Create Analytics Window
        self.analytics_window = tk.Toplevel(self.root)
        self.analytics_window.title("Expense Analytics")
        self.analytics_window.geometry("1000x700")  # Increased size for better layout

        # Ensure the window is properly tracked and can be closed
        self.analytics_window.protocol("WM_DELETE_WINDOW", self.on_close_analytics)

        # Configure grid layout
        self.analytics_window.columnconfigure(0, weight=1)
        self.analytics_window.columnconfigure(1, weight=4)
        self.analytics_window.rowconfigure(0, weight=1)

        # Create frames
        self.create_analytics_control_frame()
        self.create_analytics_plot_frame()

        # Initialize the graph once
        self.refresh_analytics_graph()

    def create_analytics_control_frame(self):
        """Create the left-hand frame (control panel) in the analytics window."""
        control_frame = ttk.Frame(self.analytics_window, padding="10")
        control_frame.grid(row=0, column=0, sticky="NSEW")

        # 1) Categories
        category_label = ttk.Label(control_frame, text="Select Categories:", font=("Helvetica", 12, "bold"))
        category_label.pack(anchor="w", pady=(0, 5))

        # Make scrollable area for checkboxes
        canvas = tk.Canvas(control_frame)
        scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set, height=300)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Grab all categories
        all_categories = get_categories()
        self.analytics_category_vars = {}  # Store references to checkbox variables

        for cat in all_categories:
            var = tk.IntVar(value=1)  # default selected
            chk = ttk.Checkbutton(scrollable_frame, text=cat, variable=var)
            chk.pack(anchor="w")
            self.analytics_category_vars[cat] = var

        # 2) Date Range
        date_label = ttk.Label(control_frame, text="Select Date Range:", font=("Helvetica", 12, "bold"))
        date_label.pack(anchor="w", pady=(10, 5))

        date_frame = ttk.Frame(control_frame)
        date_frame.pack(anchor="w", pady=(0, 10))

        # Start date
        ttk.Label(date_frame, text="Start Date:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")
        self.analytics_start_cal = DateEntry(
            date_frame, width=12, background='darkblue',
            foreground='white', borderwidth=2, date_pattern='y-mm-dd'
        )
        self.analytics_start_cal.grid(row=0, column=1, pady=5, sticky="w")
        
        # Plot Granularity
        ttk.Label(control_frame, text="Plot Granularity:").pack(anchor="w", pady=(5, 2))
        self.plot_granularity_var = tk.StringVar(value="Daily")
        plot_granularity_options = ["Daily", "Weekly", "Monthly"]
        self.plot_granularity_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self.plot_granularity_var,
            values=plot_granularity_options,
            state="readonly"
        )
        self.plot_granularity_dropdown.pack(anchor="w", pady=(0, 10))        

        # End date
        ttk.Label(date_frame, text="End Date:").grid(row=1, column=0, padx=(0, 5), pady=5, sticky="e")
        self.analytics_end_cal = DateEntry(
            date_frame, width=12, background='darkblue',
            foreground='white', borderwidth=2, date_pattern='y-mm-dd'
        )
        self.analytics_end_cal.grid(row=1, column=1, pady=5, sticky="w")

        # 3) Select / Deselect All Buttons
        select_all_button = ttk.Button(control_frame, text="Select All", command=self.analytics_select_all_categories)
        select_all_button.pack(anchor="w", pady=(5, 0))

        deselect_all_button = ttk.Button(control_frame, text="Deselect All", command=self.analytics_deselect_all_categories)
        deselect_all_button.pack(anchor="w", pady=(2, 10))

        # 4) Refresh Button
        refresh_button = ttk.Button(control_frame, text="Refresh Graph", command=self.refresh_analytics_graph)
        refresh_button.pack(anchor="w", pady=(10, 0))
        
        # ---------------------------
        # Forecasting Section
        # ---------------------------
        forecast_label = ttk.Label(control_frame, text="Forecasting Options:", font=("Helvetica", 12, "bold"))
        forecast_label.pack(anchor="w", pady=(20, 5))

        # Select Category for Forecasting
        ttk.Label(control_frame, text="Select Category:").pack(anchor="w", pady=(5, 2))
        self.forecast_category_var = tk.StringVar()
        self.forecast_category_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self.forecast_category_var,
            values=self.categories,
            state="readonly"
        )
        self.forecast_category_dropdown.pack(anchor="w", pady=(0, 10))

        # Select Forecast Period
        ttk.Label(control_frame, text="Forecast Period (days):").pack(anchor="w", pady=(5, 2))
        self.forecast_period_var = tk.IntVar(value=30)  # Default to 30 days
        self.forecast_period_entry = ttk.Entry(control_frame, textvariable=self.forecast_period_var, width=10)
        self.forecast_period_entry.pack(anchor="w", pady=(0, 10))

        # Forecast Button
        forecast_button = ttk.Button(control_frame, text="Generate Forecast", command=self.generate_forecast)
        forecast_button.pack(anchor="w", pady=(5, 10))   


        # Forecast Granularity
        ttk.Label(control_frame, text="Forecast Granularity:").pack(anchor="w", pady=(5, 2))
        self.forecast_granularity_var = tk.StringVar(value="Daily")
        granularity_options = ["Daily", "Weekly", "Monthly"]
        self.forecast_granularity_dropdown = ttk.Combobox(
            control_frame,
            textvariable=self.forecast_granularity_var,
            values=granularity_options,
            state="readonly"
        )
        self.forecast_granularity_dropdown.pack(anchor="w", pady=(0, 10))
        
        # Seasonality Options
        ttk.Label(control_frame, text="Seasonality Options:", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(20, 5))

        self.daily_seasonality_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Daily Seasonality", variable=self.daily_seasonality_var).pack(anchor="w")

        self.weekly_seasonality_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Weekly Seasonality", variable=self.weekly_seasonality_var).pack(anchor="w")

        self.yearly_seasonality_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="Yearly Seasonality", variable=self.yearly_seasonality_var).pack(anchor="w")
        

    def create_analytics_plot_frame(self):
        """Create the right-hand frame where the plot will be displayed."""
        self.plot_frame = ttk.Frame(self.analytics_window, padding="10")
        self.plot_frame.grid(row=0, column=1, sticky="NSEW")

    def analytics_select_all_categories(self):
        """Set all category checkboxes in analytics control frame to 1 (checked)."""
        for var in self.analytics_category_vars.values():
            var.set(1)

    def analytics_deselect_all_categories(self):
        """Set all category checkboxes in analytics control frame to 0 (unchecked)."""
        for var in self.analytics_category_vars.values():
            var.set(0)

    def refresh_analytics_graph(self):
        """Generate and display the analytics graph based on selected categories and date range."""
        # 1) Validate user selections
        selected_categories = [cat for cat, var in self.analytics_category_vars.items() if var.get() == 1]
        if not selected_categories:
            messagebox.showwarning("No Categories Selected", "Please select at least one category.")
            self.clear_plot()
            return

        start_date = self.analytics_start_cal.get_date()
        end_date = self.analytics_end_cal.get_date()
        if start_date > end_date:
            messagebox.showwarning("Invalid Date Range", "Start date must be before (or equal to) end date.")
            self.clear_plot()
            return

        # 2) Query the data
        try:
            conn = sqlite3.connect('expenses.db')
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(selected_categories))
            query = f"""
                SELECT transaction_date, amount, category
                FROM expenses
                WHERE category IS NOT NULL AND category != 'Unclassified'
                  AND transaction_date BETWEEN ? AND ?
                  AND category IN ({placeholders})
            """
            params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')] + selected_categories
            cursor.execute(query, params)
            data = cursor.fetchall()
            conn.close()
        except Exception as e:
            messagebox.showerror("Analytics Error", f"Database query failed:\n{e}")
            self.clear_plot()
            return

        if not data:
            messagebox.showinfo("No Data", "No expenses found for the selected criteria.")
            self.clear_plot()
            return

        # 3) Build a DataFrame
        df = pd.DataFrame(data, columns=['transaction_date', 'amount', 'category'])
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], format='%Y-%m-%d', errors='coerce')
        df.dropna(subset=['transaction_date'], inplace=True)
        if df.empty:
            messagebox.showinfo("No Valid Dates", "No valid transaction dates found.")
            self.clear_plot()
            return

        # Invert signs: Expenses as positive, Incomes as negative
        df['amount'] = df['amount'].apply(lambda x: -x)

        # Set the date as the index and group by week and category
        df.set_index('transaction_date', inplace=True)
        granularity = self.plot_granularity_var.get()

        # Modify the grouping based on granularity
        if granularity == "Daily":
            graph_data = df.groupby(['category'])['amount'].sum().reset_index()
        elif granularity == "Weekly":
            graph_data = df.groupby(['category', pd.Grouper(freq='W')])['amount'].sum().reset_index()
        elif granularity == "Monthly":
            graph_data = df.groupby(['category', pd.Grouper(freq='ME')])['amount'].sum().reset_index()            

        # Pivot the data to have categories as columns
        pivot_df = graph_data.pivot(index='transaction_date', columns='category', values='amount').fillna(0)
        if pivot_df.empty:
            messagebox.showinfo("No Data After Processing", "No expenditure data after pivot.")
            self.clear_plot()
            return

        # 4) Plot
        self.clear_plot()  # Remove any previous figure
        try:
            fig = Figure(figsize=(10, 6), dpi=100)
            ax = fig.add_subplot(111)

            # Plot each category
            for category in pivot_df.columns:
                ax.plot(pivot_df.index, pivot_df[category], marker='o', label=category)

            ax.set_title(f'{granularity} Net Expenses by Category')
            ax.set_xlabel('Week')
            ax.set_ylabel('Net Amount (€)')
            ax.legend()
            ax.grid(True)

            # Format X-axis labels
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

            fig.autofmt_xdate()  # Auto-format date labels

            # Embed the plot into Tk
            self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Add Matplotlib Navigation Toolbar
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.plot_frame)
            self.toolbar.update()
            self.canvas.get_tk_widget().pack()

            # Add Export Button
            export_button = ttk.Button(self.plot_frame, text="Save Graph", command=lambda: self.export_graph(fig))
            export_button.pack(pady=10)

            plt.close(fig)

        except Exception as e:
            messagebox.showerror("Plotting Error", f"An error occurred while generating the plot:\n{e}")
            self.clear_plot()


    def generate_forecast(self):
        """
        Generate and display a forecast for the selected category over the specified period.
        """
        category = self.forecast_category_var.get()
        periods = self.forecast_period_var.get()

        if not category:
            messagebox.showwarning("No Category Selected", "Please select a category to forecast.")
            return

        if periods <= 0:
            messagebox.showwarning("Invalid Period", "Please enter a positive number of days for the forecast period.")
            return


        try:
            # Fetch historical expense data for the selected category
            df = self.get_historical_data(category)

            if df.empty:
                messagebox.showinfo("No Data", f"No historical data found for category '{category}'.")
                return

            # Prepare data for Prophet
            #prophet_df = df.groupby('transaction_date')['amount'].sum().reset_index()
            granularity = self.forecast_granularity_var.get()

            # Modify the grouping based on granularity
            if granularity == "Daily":
                prophet_df = df.groupby('transaction_date')['amount'].sum().reset_index()
            elif granularity == "Weekly":
                prophet_df = df.groupby(pd.Grouper(key='transaction_date', freq='W'))['amount'].sum().reset_index()
            elif granularity == "Monthly":
                prophet_df = df.groupby(pd.Grouper(key='transaction_date', freq='ME'))['amount'].sum().reset_index()            
            prophet_df.rename(columns={'transaction_date': 'ds', 'amount': 'y'}, inplace=True)

            # Seasonality settings
            daily_seasonality = self.daily_seasonality_var.get()
            weekly_seasonality = self.weekly_seasonality_var.get()
            yearly_seasonality = self.yearly_seasonality_var.get()

            # Initialize Prophet with selected seasonality
            model = Prophet(
                daily_seasonality=daily_seasonality,
                weekly_seasonality=weekly_seasonality,
                yearly_seasonality=yearly_seasonality
            )
            model.fit(prophet_df)

            # Create a dataframe to hold predictions
            future = model.make_future_dataframe(periods=periods)
            forecast = model.predict(future)

            # Plot the forecast using matplotlib
            fig = model.plot(forecast)
            plt.title(f'Forecast for {category}')
            plt.xlabel('Date')
            plt.ylabel('Amount')

            # Create a new window to display the plot
            forecast_window = tk.Toplevel(self.analytics_window)
            forecast_window.title(f"Forecast for {category}")

            # Embed the plot in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=forecast_window)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # Add a toolbar for interactivity
            toolbar = NavigationToolbar2Tk(canvas, forecast_window)
            toolbar.update()
            canvas.get_tk_widget().pack()

            # Optionally, add a button to save the forecast plot
            save_button = ttk.Button(forecast_window, text="Save Plot", command=lambda: self.save_plot(fig))
            save_button.pack(pady=10)

        except Exception as e:
            messagebox.showerror("Forecasting Error", f"An error occurred during forecasting:\n{e}")

    def save_plot(self, fig):
        """Save the given matplotlib figure to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        if file_path:
            try:
                fig.savefig(file_path)
                messagebox.showinfo("Export Successful", f"Forecast plot saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save plot:\n{e}")

    def get_historical_data(self, category):
        """
        Retrieve historical expense data for a specific category.
        
        Parameters:
        - category: str, the category to fetch data for.
        
        Returns:
        - pd.DataFrame with columns ['transaction_date', 'amount'].
        """
        conn = sqlite3.connect('expenses.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT transaction_date, amount
            FROM expenses
            WHERE category = ?
        """, (category,))
        rows = cursor.fetchall()
        conn.close()

        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=['transaction_date', 'amount'])

        # Convert 'transaction_date' to datetime
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], format='%Y-%m-%d', errors='coerce')

        # Drop rows with invalid dates
        df.dropna(subset=['transaction_date'], inplace=True)

        return df

    def clear_plot(self):
        """Remove any previously drawn canvas/toolbar from the plot_frame."""
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

    def export_graph(self, fig):
        """Save the current plot to an image file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")]
        )
        if file_path:
            try:
                fig.savefig(file_path)
                messagebox.showinfo("Export Successful", f"Graph saved to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save graph:\n{e}")

    def on_close_analytics(self):
        """Handle the closing of the analytics window."""
        if self.analytics_window:
            self.analytics_window.destroy()
            self.analytics_window = None

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

# Define the BankSelectionDialog
class BankSelectionDialog:
    def __init__(self, parent, banks):
        top = self.top = tk.Toplevel(parent)
        top.title("Select Bank")
        top.grab_set()  # Make the dialog modal

        ttk.Label(top, text="Select the bank for the transaction statements:").pack(padx=20, pady=10)

        self.bank_var = tk.StringVar()
        self.bank_combobox = ttk.Combobox(top, textvariable=self.bank_var, values=banks, state="readonly")
        self.bank_combobox.pack(padx=20, pady=5)
        self.bank_combobox.current(0)  # Set default selection

        button_frame = ttk.Frame(top)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)

        self.selected_bank = None

    def ok(self):
        self.selected_bank = self.bank_var.get()
        self.top.destroy()

    def cancel(self):
        self.top.destroy()
        
        
def run_gui_classification_app():
    root = tk.Tk()
    app = ExpenseClassifierApp(root)
    root.mainloop()
