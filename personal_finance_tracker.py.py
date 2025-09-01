import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
from typing import List, Dict, Tuple
import os

class FinanceDatabase:
    """Handles all database operations for the finance application"""
    
    def __init__(self, db_path: str = "finance.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT 'INR',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create currency settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS currency_settings (
                id INTEGER PRIMARY KEY,
                default_currency TEXT NOT NULL DEFAULT 'INR'
            )
        ''')
        
        # Insert default currency if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO currency_settings (id, default_currency) 
            VALUES (1, 'INR')
        ''')
        
        # Create budgets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                allocated_amount REAL NOT NULL,
                spent_amount REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(month, category)
            )
        ''')
        
        # Create savings goals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_transaction(self, date: str, trans_type: str, category: str, 
                        amount: float, currency: str = 'INR', description: str = "") -> bool:
        """Add a new transaction to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO transactions (date, type, category, amount, currency, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, trans_type, category, amount, currency, description))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding transaction: {e}")
            return False
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a specific transaction"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            rows_affected = cursor.rowcount
            
            conn.commit()
            conn.close()
            return rows_affected > 0
        except Exception as e:
            print(f"Error deleting transaction: {e}")
            return False
    
    def clear_all_data(self) -> bool:
        """Clear all transaction data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM transactions')
            cursor.execute('DELETE FROM budgets')
            cursor.execute('DELETE FROM savings_goals')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error clearing data: {e}")
            return False
    
    def get_default_currency(self) -> str:
        """Get the default currency setting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT default_currency FROM currency_settings WHERE id = 1')
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 'INR'
    
    def set_default_currency(self, currency: str) -> bool:
        """Set the default currency"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE currency_settings SET default_currency = ? WHERE id = 1
            ''', (currency,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error setting currency: {e}")
            return False
    
    def get_transactions(self, limit: int = None) -> List[Dict]:
        """Retrieve transactions from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, date, type, category, amount, currency, description
            FROM transactions
            ORDER BY date DESC, created_at DESC
        '''
        
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': row[0], 'date': row[1], 'type': row[2],
                'category': row[3], 'amount': row[4], 'currency': row[5], 'description': row[6]
            }
            for row in rows
        ]
    
    def get_balance(self, currency: str = None) -> Dict[str, float]:
        """Calculate current balance and totals for a specific currency or all"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        currency_filter = f"AND currency = '{currency}'" if currency else ""
        
        # Get total income
        cursor.execute(f"SELECT SUM(amount) FROM transactions WHERE type = 'income' {currency_filter}")
        total_income = cursor.fetchone()[0] or 0
        
        # Get total expenses
        cursor.execute(f"SELECT SUM(amount) FROM transactions WHERE type = 'expense' {currency_filter}")
        total_expenses = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': total_income - total_expenses
        }
    
    def get_monthly_data(self, month: str) -> Dict:
        """Get financial data for a specific month (YYYY-MM format)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get income for the month
        cursor.execute('''
            SELECT SUM(amount) FROM transactions 
            WHERE type = 'income' AND date LIKE ?
        ''', (f'{month}%',))
        monthly_income = cursor.fetchone()[0] or 0
        
        # Get expenses for the month
        cursor.execute('''
            SELECT SUM(amount) FROM transactions 
            WHERE type = 'expense' AND date LIKE ?
        ''', (f'{month}%',))
        monthly_expenses = cursor.fetchone()[0] or 0
        
        # Get expenses by category
        cursor.execute('''
            SELECT category, SUM(amount) FROM transactions 
            WHERE type = 'expense' AND date LIKE ?
            GROUP BY category
        ''', (f'{month}%',))
        expense_categories = dict(cursor.fetchall())
        
        # Get income by category
        cursor.execute('''
            SELECT category, SUM(amount) FROM transactions 
            WHERE type = 'income' AND date LIKE ?
            GROUP BY category
        ''', (f'{month}%',))
        income_categories = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'income': monthly_income,
            'expenses': monthly_expenses,
            'expense_categories': expense_categories,
            'income_categories': income_categories
        }

class FinanceVisualizer:
    """Handles all data visualization using matplotlib"""
    
    @staticmethod
    def create_pie_chart(data: Dict[str, float], title: str, figure, subplot_pos):
        """Create a pie chart for categorical data"""
        ax = figure.add_subplot(subplot_pos)
        
        if not data or sum(data.values()) == 0:
            ax.text(0.5, 0.5, 'No Data Available', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            ax.set_title(title)
            return
        
        labels = list(data.keys())
        sizes = list(data.values())
        colors = plt.cm.Set3(range(len(labels)))
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                           autopct='%1.1f%%', startangle=90)
        ax.set_title(title, fontsize=12, fontweight='bold')
        
        # Improve text readability
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    
    @staticmethod
    def create_balance_chart(balance_data: Dict[str, float], figure, subplot_pos, currency_symbol: str = ''):
        """Create a bar chart showing current balances"""
        ax = figure.add_subplot(subplot_pos)
        
        categories = ['Total Income', 'Total Expenses', 'Current Balance']
        values = [balance_data['total_income'], balance_data['total_expenses'], 
                  balance_data['balance']]
        colors = ['green', 'red', 'blue' if balance_data['balance'] >= 0 else 'red']
        
        bars = ax.bar(categories, values, color=colors, alpha=0.7)
        ax.set_title('Financial Overview', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Amount ({currency_symbol})')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.annotate(f'{currency_symbol}{value:,.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3 if height >= 0 else -15),
                        textcoords="offset points",
                        ha='center', va='bottom' if height >= 0 else 'top',
                        fontweight='bold')
        
        plt.xticks(rotation=45, ha='right')
    
    @staticmethod
    def create_trend_chart(transactions: List[Dict], figure, subplot_pos, currency_symbol: str = ''):
        """Create a line chart showing financial trends over time"""
        ax = figure.add_subplot(subplot_pos)
        
        if not transactions:
            ax.text(0.5, 0.5, 'No Transaction Data', 
                    horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes, fontsize=12)
            ax.set_title('Financial Trends')
            return
        
        # Group transactions by month
        monthly_data = {}
        for trans in transactions:
            month = trans['date'][:7]  # YYYY-MM
            if month not in monthly_data:
                monthly_data[month] = {'income': 0, 'expenses': 0}
            
            if trans['type'] == 'income':
                monthly_data[month]['income'] += trans['amount']
            else:
                monthly_data[month]['expenses'] += trans['amount']
        
        # Sort months and calculate net income
        sorted_months = sorted(monthly_data.keys())
        incomes = [monthly_data[month]['income'] for month in sorted_months]
        expenses = [monthly_data[month]['expenses'] for month in sorted_months]
        net_income = [inc - exp for inc, exp in zip(incomes, expenses)]
        
        # Plot the trends
        ax.plot(sorted_months, incomes, 'g-', label='Income', linewidth=2, marker='o')
        ax.plot(sorted_months, expenses, 'r-', label='Expenses', linewidth=2, marker='s')
        ax.plot(sorted_months, net_income, 'b-', label='Net Income', linewidth=2, marker='^')
        
        ax.set_title('Financial Trends Over Time', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Amount ({currency_symbol})')
        ax.set_xlabel('Month')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45, ha='right')

class PersonalFinanceApp:
    """Main application class for the Personal Finance Management System"""
    
    def __init__(self):
        self.db = FinanceDatabase()
        self.currencies = ['INR', 'USD', 'EUR', 'GBP']
        self.currency_symbols = {'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£'}
        self.current_currency = self.db.get_default_currency()
        self.root = tk.Tk()
        self.setup_main_window()
        self.create_widgets()
        self.refresh_dashboard()
    
    def setup_main_window(self):
        """Configure the main application window"""
        self.root.title("Personal Finance Management System")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
    
    def create_widgets(self):
        """Create and arrange all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Personal Finance Dashboard", 
                               style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Currency selector
        currency_frame = ttk.Frame(main_frame)
        currency_frame.grid(row=0, column=1, sticky=tk.E, pady=(0, 10))
        
        ttk.Label(currency_frame, text="Currency:").pack(side=tk.LEFT, padx=(0, 5))
        self.currency_var = tk.StringVar(value=self.current_currency)
        currency_combo = ttk.Combobox(currency_frame, textvariable=self.currency_var,
                                     values=self.currencies, state='readonly', width=8)
        currency_combo.pack(side=tk.LEFT)
        currency_combo.bind('<<ComboboxSelected>>', self.on_currency_change)
        
        # Configure title style
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        
        # Left panel for controls
        self.create_control_panel(main_frame)
        
        # Right panel for dashboard
        self.create_dashboard_panel(main_frame)
    
    def create_control_panel(self, parent):
        """Create the control panel with buttons and forms"""
        control_frame = ttk.LabelFrame(parent, text="Financial Operations", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Add Transaction Section
        ttk.Label(control_frame, text="Add Transaction", 
                  font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10))
        
        # Transaction type
        ttk.Label(control_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.trans_type = ttk.Combobox(control_frame, values=['income', 'expense'], 
                                       state='readonly', width=15)
        self.trans_type.grid(row=1, column=1, pady=2, sticky=(tk.W, tk.E))
        self.trans_type.set('expense')
        
        # Category
        ttk.Label(control_frame, text="Category:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.category = ttk.Combobox(control_frame, width=15)
        self.category.grid(row=2, column=1, pady=2, sticky=(tk.W, tk.E))
        self.update_categories()
        
        # Amount
        ttk.Label(control_frame, text=f"Amount ({self.get_currency_symbol()}):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.amount = ttk.Entry(control_frame, width=15)
        self.amount.grid(row=3, column=1, pady=2, sticky=(tk.W, tk.E))
        
        # Currency for this transaction
        ttk.Label(control_frame, text="Currency:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.trans_currency = ttk.Combobox(control_frame, values=self.currencies, 
                                           state='readonly', width=15)
        self.trans_currency.grid(row=4, column=1, pady=2, sticky=(tk.W, tk.E))
        self.trans_currency.set(self.current_currency)
        
        # Description
        ttk.Label(control_frame, text="Description:").grid(row=5, column=0, sticky=tk.W, pady=2)
        self.description = ttk.Entry(control_frame, width=15)
        self.description.grid(row=5, column=1, pady=2, sticky=(tk.W, tk.E))
        
        # Add button
        ttk.Button(control_frame, text="Add Transaction", 
                   command=self.add_transaction).grid(row=6, column=0, columnspan=2, 
                                                      pady=10, sticky=(tk.W, tk.E))
        
        # Separator
        ttk.Separator(control_frame, orient='horizontal').grid(row=7, column=0, 
                                                               columnspan=2, sticky=(tk.W, tk.E), 
                                                               pady=15)
        
        # Quick Actions
        ttk.Label(control_frame, text="Quick Actions", 
                  font=("Arial", 12, "bold")).grid(row=8, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(control_frame, text="View All Transactions", 
                   command=self.show_transactions).grid(row=9, column=0, columnspan=2, 
                                                        pady=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Delete Transaction", 
                   command=self.delete_selected_transaction).grid(row=10, column=0, columnspan=2, 
                                                                  pady=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Monthly Report", 
                   command=self.show_monthly_report).grid(row=11, column=0, columnspan=2, 
                                                          pady=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Currency Settings", 
                   command=self.show_currency_settings).grid(row=12, column=0, columnspan=2, 
                                                             pady=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Clear All Data", 
                   command=self.clear_all_data).grid(row=13, column=0, columnspan=2, 
                                                     pady=2, sticky=(tk.W, tk.E))
        
        ttk.Button(control_frame, text="Refresh Dashboard", 
                   command=self.refresh_dashboard).grid(row=14, column=0, columnspan=2, 
                                                        pady=2, sticky=(tk.W, tk.E))
        
        # Recent Transactions
        ttk.Label(control_frame, text="Recent Transactions", 
                  font=("Arial", 12, "bold")).grid(row=15, column=0, columnspan=2, 
                                                   pady=(20, 10))
        
        # Transactions listbox
        self.trans_listbox = tk.Listbox(control_frame, height=8, width=40)
        self.trans_listbox.grid(row=16, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for listbox
        scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=self.trans_listbox.yview)
        scrollbar.grid(row=16, column=2, sticky=(tk.N, tk.S))
        self.trans_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Configure column weights
        control_frame.columnconfigure(1, weight=1)
        control_frame.rowconfigure(16, weight=1)
    
    def create_dashboard_panel(self, parent):
        """Create the dashboard panel with charts"""
        dashboard_frame = ttk.LabelFrame(parent, text="Financial Dashboard", padding="10")
        dashboard_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure dashboard frame
        dashboard_frame.columnconfigure(0, weight=1)
        dashboard_frame.rowconfigure(0, weight=1)
        
        # Create matplotlib figure
        self.fig = plt.Figure(figsize=(10, 8), dpi=100)
        self.fig.patch.set_facecolor('#f0f0f0')
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, dashboard_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def get_currency_symbol(self) -> str:
        """Get the symbol for current currency"""
        return self.currency_symbols.get(self.current_currency, self.current_currency)
    
    def on_currency_change(self, event):
        """Handle currency change event"""
        new_currency = self.currency_var.get()
        self.current_currency = new_currency
        self.db.set_default_currency(new_currency)
        self.refresh_dashboard()
        
        # Update amount label
        for widget in self.root.winfo_children():
            self.update_amount_labels(widget)
    
    def update_amount_labels(self, widget):
        """Recursively update amount labels with new currency symbol"""
        try:
            if isinstance(widget, ttk.Label) and "Amount" in widget.cget("text"):
                widget.configure(text=f"Amount ({self.get_currency_symbol()}):")
        except:
            pass
        
        for child in widget.winfo_children():
            self.update_amount_labels(child)

    def update_categories(self):
        """Update category dropdown based on transaction type"""
        income_categories = ['Salary', 'Freelance', 'Investment', 'Gift', 'Other Income']
        expense_categories = ['Food', 'Transportation', 'Housing', 'Entertainment', 
                              'Healthcare', 'Shopping', 'Utilities', 'Other Expense']
        
        current_type = self.trans_type.get() if hasattr(self, 'trans_type') else 'expense'
        categories = income_categories if current_type == 'income' else expense_categories
        
        if hasattr(self, 'category'):
            self.category['values'] = categories
            if categories:
                self.category.set(categories[0])
    
    def delete_selected_transaction(self):
        """Delete the selected transaction from the listbox"""
        selection = self.trans_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a transaction to delete")
            return
        
        # Get the transaction ID from the selected item
        recent_transactions = self.db.get_transactions(limit=10)
        if selection[0] < len(recent_transactions):
            trans_id = recent_transactions[selection[0]]['id']
            trans_info = recent_transactions[selection[0]]
            
            # Confirm deletion
            result = messagebox.askyesno("Confirm Deletion", 
                                       f"Are you sure you want to delete this transaction?\n\n"
                                       f"Date: {trans_info['date']}\n"
                                       f"Type: {trans_info['type'].title()}\n"
                                       f"Amount: {self.currency_symbols[trans_info['currency']]}{trans_info['amount']:.2f}\n"
                                       f"Category: {trans_info['category']}")
            
            if result:
                if self.db.delete_transaction(trans_id):
                    messagebox.showinfo("Success", "Transaction deleted successfully!")
                    self.refresh_dashboard()
                else:
                    messagebox.showerror("Error", "Failed to delete transaction")
    
    def clear_all_data(self):
        """Clear all financial data after confirmation"""
        result = messagebox.askyesnocancel("Clear All Data", 
                                           "This will permanently delete ALL financial data including:\n"
                                           "• All transactions\n"
                                           "• All budgets\n"
                                           "• All savings goals\n\n"
                                           "This action cannot be undone. Are you sure?")
        
        if result:
            if self.db.clear_all_data():
                messagebox.showinfo("Data Cleared", "All data has been cleared successfully!")
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", "Failed to clear data")
    
    def show_currency_settings(self):
        """Show currency settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Currency Settings")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Currency Settings", 
                  font=("Arial", 14, "bold")).pack(pady=(0, 20))
        
        # Default currency selection
        ttk.Label(main_frame, text="Default Currency:").pack(anchor=tk.W, pady=(0, 5))
        
        currency_var = tk.StringVar(value=self.current_currency)
        currency_frame = ttk.Frame(main_frame)
        currency_frame.pack(fill=tk.X, pady=(0, 20))
        
        for currency in self.currencies:
            ttk.Radiobutton(currency_frame, text=f"{currency} ({self.currency_symbols[currency]})", 
                            variable=currency_var, value=currency).pack(anchor=tk.W, pady=2)
        
        # Currency information
        info_text = """
Currency Information:
• INR (₹) - Indian Rupee
• USD ($) - US Dollar  
• EUR (€) - Euro
• GBP (£) - British Pound

Note: Currency conversion is not automatic. 
Each transaction is stored in its original currency.
        """
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT, 
                               background='#f8f8f8', relief='sunken', padding="10")
        info_label.pack(fill=tk.X, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def save_settings():
            new_currency = currency_var.get()
            self.current_currency = new_currency
            self.currency_var.set(new_currency)
            self.db.set_default_currency(new_currency)
            self.refresh_dashboard()
            settings_window.destroy()
            messagebox.showinfo("Settings Saved", f"Default currency set to {new_currency}")
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT)
    
    def add_transaction(self):
        """Add a new transaction"""
        try:
            # Validate inputs
            if not self.amount.get() or not self.category.get():
                messagebox.showerror("Error", "Please fill in all required fields")
                return
            
            amount = float(self.amount.get())
            if amount <= 0:
                messagebox.showerror("Error", "Amount must be positive")
                return
            
            # Get current date
            current_date = datetime.date.today().strftime("%Y-%m-%d")
            
            # Add to database
            success = self.db.add_transaction(
                date=current_date,
                trans_type=self.trans_type.get(),
                category=self.category.get(),
                amount=amount,
                currency=self.trans_currency.get(),
                description=self.description.get()
            )
            
            if success:
                messagebox.showinfo("Success", "Transaction added successfully!")
                # Clear form
                self.amount.delete(0, tk.END)
                self.description.delete(0, tk.END)
                # Refresh dashboard
                self.refresh_dashboard()
            else:
                messagebox.showerror("Error", "Failed to add transaction")
                
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid amount")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
    
    def refresh_dashboard(self):
        """Refresh all dashboard visualizations"""
        # Clear previous plots
        self.fig.clear()
        
        # Get current data
        balance_data = self.db.get_balance(currency=self.current_currency)
        current_month = datetime.date.today().strftime("%Y-%m")
        monthly_data = self.db.get_monthly_data(current_month)
        recent_transactions = self.db.get_transactions(limit=10)
        
        # Create visualizations
        # 1. Current Balances (top left)
        FinanceVisualizer.create_balance_chart(balance_data, self.fig, 221, self.get_currency_symbol())
        
        # 2. Monthly Income Breakdown (top right)
        FinanceVisualizer.create_pie_chart(monthly_data['income_categories'], 
                                           f'Income Breakdown - {current_month}', 
                                           self.fig, 222)
        
        # 3. Monthly Expense Breakdown (bottom left)
        FinanceVisualizer.create_pie_chart(monthly_data['expense_categories'], 
                                           f'Expense Breakdown - {current_month}', 
                                           self.fig, 223)
        
        # 4. Financial Trends (bottom right)
        FinanceVisualizer.create_trend_chart(self.db.get_transactions(), self.fig, 224, self.get_currency_symbol())
        
        # Adjust layout and refresh
        self.fig.tight_layout(pad=3.0)
        self.canvas.draw()
        
        # Update recent transactions list
        self.update_recent_transactions(recent_transactions)
        
        # Update category dropdown
        self.trans_type.bind('<<ComboboxSelected>>', lambda e: self.update_categories())
    
    def update_recent_transactions(self, transactions: List[Dict]):
        """Update the recent transactions listbox"""
        self.trans_listbox.delete(0, tk.END)
        
        for trans in transactions[:10]:  # Show last 10
            symbol = self.currency_symbols.get(trans.get('currency', 'INR'), trans.get('currency', 'INR'))
            trans_text = f"{trans['date']} | {trans['type'].upper()} | {symbol}{trans['amount']:.2f} | {trans['category']}"
            self.trans_listbox.insert(tk.END, trans_text)
    
    def show_transactions(self):
        """Show all transactions in a new window"""
        trans_window = tk.Toplevel(self.root)
        trans_window.title("All Transactions")
        trans_window.geometry("800x600")
        
        # Create treeview for transactions
        columns = ('Date', 'Type', 'Category', 'Amount', 'Currency', 'Description')
        tree = ttk.Treeview(trans_window, columns=columns, show='headings', height=20)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(trans_window, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        
        # Load transactions
        transactions = self.db.get_transactions()
        for trans in transactions:
            tree.insert('', tk.END, values=(
                trans['date'], trans['type'].title(), trans['category'],
                f"{self.currency_symbols.get(trans['currency'], '')}{trans['amount']:.2f}",
                trans['currency'], trans['description']
            ))
    
    def show_monthly_report(self):
        """Show detailed monthly report"""
        month = simpledialog.askstring("Monthly Report", 
                                       "Enter month (YYYY-MM):",
                                       initialvalue=datetime.date.today().strftime("%Y-%m"))
        
        if not month:
            return
        
        monthly_data = self.db.get_monthly_data(month)
        
        report_window = tk.Toplevel(self.root)
        report_window.title(f"Monthly Report - {month}")
        report_window.geometry("600x400")
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(report_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=70, height=20)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Generate report content
        report = f"""
MONTHLY FINANCIAL REPORT - {month}
{'='*50}

SUMMARY:
Total Income: {self.get_currency_symbol()}{monthly_data['income']:,.2f}
Total Expenses: {self.get_currency_symbol()}{monthly_data['expenses']:,.2f}
Net Income: {self.get_currency_symbol()}{monthly_data['income'] - monthly_data['expenses']:,.2f}

INCOME BREAKDOWN:
"""
        
        for category, amount in monthly_data['income_categories'].items():
            report += f"  {category}: {self.get_currency_symbol()}{amount:,.2f}\n"
        
        report += "\nEXPENSE BREAKDOWN:\n"
        for category, amount in monthly_data['expense_categories'].items():
            report += f"  {category}: {self.get_currency_symbol()}{amount:,.2f}\n"
        
        if monthly_data['expenses'] > 0:
            savings_rate = ((monthly_data['income'] - monthly_data['expenses']) / 
                            monthly_data['income'] * 100) if monthly_data['income'] > 0 else 0
            report += f"\nSAVINGS RATE: {savings_rate:.1f}%"
        
        text_widget.insert(tk.END, report)
        text_widget.configure(state=tk.DISABLED)
    
    def export_data(self):
        """Export financial data to CSV"""
        transactions = self.db.get_transactions()
        
        if not transactions:
            messagebox.showinfo("Export", "No data to export")
            return
        
        try:
            filename = f"finance_export_{datetime.date.today().strftime('%Y%m%d')}.csv"
            
            with open(filename, 'w', newline='') as file:
                file.write("Date,Type,Category,Amount,Currency,Description\n")
                for trans in transactions:
                    file.write(f"{trans['date']},{trans['type']},{trans['category']},"
                               f"{trans['amount']},{trans['currency']},\"{trans['description']}\"\n")
            
            messagebox.showinfo("Export Successful", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main function to run the application"""
    # Create application instance
    app = PersonalFinanceApp()
    
    # Add some sample data if database is empty
    sample_transactions = [
        ('2024-12-01', 'income', 'Salary', 3000, 'INR', 'Monthly salary'),
        ('2024-12-02', 'expense', 'Food', 50, 'USD', 'Grocery shopping'),
        ('2024-12-03', 'expense', 'Transportation', 30, 'EUR', 'Gas'),
        ('2024-12-04', 'expense', 'Entertainment', 25, 'GBP', 'Movie tickets'),
        ('2024-12-05', 'income', 'Freelance', 500, 'INR', 'Web development project'),
        ('2025-01-01', 'income', 'Salary', 3000, 'INR', 'Monthly salary'),
        ('2025-01-02', 'expense', 'Housing', 800, 'INR', 'Rent payment'),
        ('2025-01-03', 'expense', 'Utilities', 150, 'USD', 'Electric and water'),
        ('2025-01-04', 'expense', 'Food', 75, 'INR', 'Grocery shopping'),
    ]
    
    # Check if database has any transactions
    existing_transactions = app.db.get_transactions(limit=1)
    if not existing_transactions:
        for date, trans_type, category, amount, currency, description in sample_transactions:
            app.db.add_transaction(date, trans_type, category, amount, currency, description)
        messagebox.showinfo("Welcome", "Sample data has been added to get you started!")
    
    # Run the application
    app.run()

if __name__ == "__main__":
    main()