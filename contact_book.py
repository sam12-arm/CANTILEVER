import tkinter as tk
from tkinter import messagebox
import json
import os

CONTACTS_FILE = "contacts.json"

class ContactBookApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Contact Book")
        self.root.geometry("800x500")
        self.root.configure(bg="white")

        # Header
        header = tk.Frame(self.root, bg="#0d6efd", height=60)
        header.pack(fill="x")
        tk.Label(header, text="My Contacts", fg="white", bg="#0d6efd",
                 font=("Segoe UI", 18, "bold")).pack(pady=10)

        # Search bar
        search_frame = tk.Frame(self.root, bg="white")
        search_frame.pack(fill="x", pady=5)
        tk.Label(search_frame, text="Search:", bg="white", font=("Segoe UI", 11)).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_list)
        tk.Entry(search_frame, textvariable=self.search_var, width=30,
                 font=("Segoe UI", 11)).pack(side="left", padx=5)

        # Main frame
        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left - Contact list
        list_frame = tk.Frame(main_frame, bg="white")
        list_frame.pack(side="left", fill="both", expand=True)
        tk.Label(list_frame, text="Contacts", bg="white",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=5)
        self.contact_listbox = tk.Listbox(list_frame, font=("Segoe UI", 11))
        self.contact_listbox.pack(fill="both", expand=True)
        self.contact_listbox.bind("<<ListboxSelect>>", self.load_contact)

        # Right - Details
        form_frame = tk.Frame(main_frame, bg="white")
        form_frame.pack(side="right", fill="y", padx=20)

        tk.Label(form_frame, text="Name", bg="white", font=("Segoe UI", 11)).pack(anchor="w")
        self.name_entry = tk.Entry(form_frame, font=("Segoe UI", 11), width=30)
        self.name_entry.pack(pady=5)

        tk.Label(form_frame, text="Phone", bg="white", font=("Segoe UI", 11)).pack(anchor="w")
        self.phone_entry = tk.Entry(form_frame, font=("Segoe UI", 11), width=30)
        self.phone_entry.pack(pady=5)

        tk.Label(form_frame, text="Email", bg="white", font=("Segoe UI", 11)).pack(anchor="w")
        self.email_entry = tk.Entry(form_frame, font=("Segoe UI", 11), width=30)
        self.email_entry.pack(pady=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Add", width=8, bg="#0d6efd", fg="white",
                  command=self.add_contact).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update", width=8, bg="#198754", fg="white",
                  command=self.update_contact).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Delete", width=8, bg="#dc3545", fg="white",
                  command=self.delete_contact).grid(row=0, column=2, padx=5)

        # Load contacts
        self.contacts = self.load_contacts()
        self.update_list()

    # Load contacts from JSON
    def load_contacts(self):
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r") as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                except:
                    pass
        return []

    # Save contacts to JSON
    def save_contacts(self):
        with open(CONTACTS_FILE, "w") as f:
            json.dump(self.contacts, f, indent=4)

    # Update listbox display
    def update_list(self, *args):
        search_term = self.search_var.get().lower()
        self.contact_listbox.delete(0, tk.END)
        for contact in sorted(self.contacts, key=lambda x: x["name"].lower()):
            if search_term in contact["name"].lower():
                self.contact_listbox.insert(tk.END, contact["name"])

    # Load selected contact into entry fields
    def load_contact(self, event):
        selection = self.contact_listbox.curselection()
        if selection:
            selected_name = self.contact_listbox.get(selection[0])
            contact = next((c for c in self.contacts if c["name"] == selected_name), None)
            if contact:
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, contact["name"])
                self.phone_entry.delete(0, tk.END)
                self.phone_entry.insert(0, contact["phone"])
                self.email_entry.delete(0, tk.END)
                self.email_entry.insert(0, contact["email"])

    # Add new contact
    def add_contact(self):
        name = self.name_entry.get().strip()
        phone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        if not name or not phone:
            messagebox.showwarning("Error", "Name and Phone are required")
            return
        if any(c["name"] == name for c in self.contacts):
            messagebox.showwarning("Error", "Contact already exists")
            return
        self.contacts.append({"name": name, "phone": phone, "email": email})
        self.save_contacts()
        self.update_list()
        self.clear_fields()

    # Update selected contact
    def update_contact(self):
        selection = self.contact_listbox.curselection()
        if not selection:
            messagebox.showwarning("Error", "Select a contact to update")
            return
        selected_name = self.contact_listbox.get(selection[0])
        contact = next((c for c in self.contacts if c["name"] == selected_name), None)
        if contact:
            contact["name"] = self.name_entry.get().strip()
            contact["phone"] = self.phone_entry.get().strip()
            contact["email"] = self.email_entry.get().strip()
            self.save_contacts()
            self.update_list()
            self.clear_fields()

    # Delete selected contact
    def delete_contact(self):
        selection = self.contact_listbox.curselection()
        if not selection:
            messagebox.showwarning("Error", "Select a contact to delete")
            return
        selected_name = self.contact_listbox.get(selection[0])
        self.contacts = [c for c in self.contacts if c["name"] != selected_name]
        self.save_contacts()
        self.update_list()
        self.clear_fields()

    # Clear entry fields
    def clear_fields(self):
        self.name_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = ContactBookApp(root)
    root.mainloop()
