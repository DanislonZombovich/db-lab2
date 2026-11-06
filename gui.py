import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import Database

class DatabaseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Файловая база данных: Склад товаров (Лаб. №2)")
        self.root.geometry("980x620")
        self.root.minsize(750, 480)

        self.db = Database()

        self._setup_menu()
        self._setup_toolbar()
        self._setup_table()
        self._setup_statusbar()

        default_dir = os.path.dirname(os.path.abspath(__file__))
        default_db = os.path.join(default_dir, "warehouse.db")
        if os.path.exists(default_db):
            try:
                self.db.open(default_db)
                self.refresh_table()
            except Exception:
                pass
        else:
            try:
                self.db.create(default_db)
                sample_data = [
                    {"id": 101, "name": "Ноутбук ThinkPad", "category": "Компьютеры", "price": 89900.0, "quantity": 12, "in_stock": True},
                    {"id": 102, "name": "Монитор UltraSharp 27", "category": "Мониторы", "price": 34500.5, "quantity": 7, "in_stock": True},
                    {"id": 103, "name": "Клавиатура Механическая", "category": "Периферия", "price": 7200.0, "quantity": 25, "in_stock": True},
                    {"id": 104, "name": "Мышь Беспроводная", "category": "Периферия", "price": 2800.0, "quantity": 40, "in_stock": True},
                    {"id": 105, "name": "Наушники Студийные", "category": "Аудио", "price": 14900.0, "quantity": 0, "in_stock": False},
                ]
                for item in sample_data:
                    self.db.insert(item)
                self.refresh_table()
            except Exception:
                pass

    def _setup_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Создать БД...", accelerator="Ctrl+N", command=self.on_create_db)
        file_menu.add_command(label="Открыть БД...", accelerator="Ctrl+O", command=self.on_open_db)
        file_menu.add_command(label="Сохранить изменения", accelerator="Ctrl+S", command=self.on_save_db)
        file_menu.add_separator()
        file_menu.add_command(label="Очистить БД", command=self.on_clear_db)
        file_menu.add_command(label="Удалить файл БД", command=self.on_delete_db)
        file_menu.add_separator()
        file_menu.add_command(label="Создать резервную копию (Backup)...", command=self.on_backup_db)
        file_menu.add_command(label="Восстановить из копии (Restore)...", command=self.on_restore_db)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт в Excel (*.xlsx)...", command=self.on_export_xlsx)
        file_menu.add_command(label="Импорт из Excel (*.xlsx)...", command=self.on_import_xlsx)
        file_menu.add_command(label="Экспорт в CSV (*.csv)...", command=self.on_export_csv)
        file_menu.add_command(label="Импорт из CSV (*.csv)...", command=self.on_import_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)

        record_menu = tk.Menu(menubar, tearoff=False)
        record_menu.add_command(label="Добавить запись...", command=self.on_add_record)
        record_menu.add_command(label="Редактировать выбранную...", command=self.on_edit_record)
        record_menu.add_command(label="Удалить выбранную...", command=self.on_delete_selected)
        record_menu.add_separator()
        record_menu.add_command(label="Поиск по значению поля...", command=self.on_search)
        record_menu.add_command(label="Удалить по значению поля...", command=self.on_delete_by_field)
        menubar.add_cascade(label="Записи", menu=record_menu)

        self.root.config(menu=menubar)

        self.root.bind("<Control-n>", lambda e: self.on_create_db())
        self.root.bind("<Control-o>", lambda e: self.on_open_db())
        self.root.bind("<Control-s>", lambda e: self.on_save_db())

    def _setup_toolbar(self):
        toolbar = ttk.Frame(self.root, padding=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(toolbar, text="➕ Добавить", command=self.on_add_record).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="✏️ Изменить", command=self.on_edit_record).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="❌ Удалить", command=self.on_delete_selected).pack(side=tk.LEFT, padx=3)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(toolbar, text="🔍 Поиск", command=self.on_search).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="🗑️ Удалить по полю", command=self.on_delete_by_field).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="🔄 Показать все", command=self.refresh_table).pack(side=tk.LEFT, padx=3)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)

        ttk.Button(toolbar, text="💾 Backup", command=self.on_backup_db).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="📂 Restore", command=self.on_restore_db).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="📊 Excel", command=self.on_export_xlsx).pack(side=tk.LEFT, padx=3)

    def _setup_table(self):
        frame = ttk.Frame(self.root)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("id", "name", "category", "price", "quantity", "in_stock")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID (Ключ)", anchor=tk.CENTER)
        self.tree.heading("name", text="Название товара", anchor=tk.W)
        self.tree.heading("category", text="Категория", anchor=tk.W)
        self.tree.heading("price", text="Цена (руб.)", anchor=tk.E)
        self.tree.heading("quantity", text="Кол-во на складе", anchor=tk.CENTER)
        self.tree.heading("in_stock", text="В наличии", anchor=tk.CENTER)

        self.tree.column("id", width=90, anchor=tk.CENTER)
        self.tree.column("name", width=260, anchor=tk.W)
        self.tree.column("category", width=180, anchor=tk.W)
        self.tree.column("price", width=120, anchor=tk.E)
        self.tree.column("quantity", width=120, anchor=tk.CENTER)
        self.tree.column("in_stock", width=100, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda e: self.on_edit_record())

    def _setup_statusbar(self):
        self.statusbar = ttk.Frame(self.root, padding=3)
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_file_lbl = ttk.Label(self.statusbar, text="Файл: нет")
        self.status_file_lbl.pack(side=tk.LEFT, padx=5)

        self.status_stats_lbl = ttk.Label(self.statusbar, text="Записей: 0 | Свободных слотов: 0")
        self.status_stats_lbl.pack(side=tk.RIGHT, padx=5)

    def refresh_table(self, records=None):
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.db.is_open():
            self.status_file_lbl.config(text="Файл: нет открытой БД")
            self.status_stats_lbl.config(text="")
            return

        if records is None:
            records = self.db.get_all_records()

        for r in records:
            stock_str = "Да" if r["in_stock"] else "Нет"
            price_str = f"{r['price']:,.2f}".replace(",", " ")
            self.tree.insert("", tk.END, values=(r["id"], r["name"], r["category"], price_str, r["quantity"], stock_str))

        stats = self.db.get_stats()
        self.status_file_lbl.config(text=f"Файл: {os.path.basename(self.db.db_path)} ({stats['db_size']} байт)")
        self.status_stats_lbl.config(
            text=f"Активных записей: {stats['active']} | Свободных слотов: {stats['free_slots']} | Всего слотов: {stats['total_slots']}"
        )

    def on_create_db(self):
        path = filedialog.asksaveasfilename(
            title="Создать новую базу данных",
            defaultextension=".db",
            filetypes=[("Файлы базы данных", "*.db"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.db.create(path)
            self.refresh_table()
            messagebox.showinfo("Успех", f"База данных успешно создана:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать базу данных:\n{e}")

    def on_open_db(self):
        path = filedialog.askopenfilename(
            title="Открыть базу данных",
            filetypes=[("Файлы базы данных", "*.db"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.db.open(path)
            self.refresh_table()
            messagebox.showinfo("Успех", f"База данных открыта:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть базу данных:\n{e}")

    def on_save_db(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        try:
            self.db.save()
            messagebox.showinfo("Успех", "Все изменения сброшены и синхронизированы на диск!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить БД:\n{e}")

    def on_clear_db(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        if not messagebox.askyesno("Подтверждение", "Вы действительно хотите удалить все записи из базы данных?"):
            return
        try:
            self.db.clear()
            self.refresh_table()
            messagebox.showinfo("Успех", "База данных успешно очищена.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось очистить БД:\n{e}")

    def on_delete_db(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        if not messagebox.askyesno("Удаление файла", f"Удалить файл базы данных с диска?\n{self.db.db_path}"):
            return
        try:
            self.db.delete_database()
            self.refresh_table()
            messagebox.showinfo("Успех", "Файлы базы данных удалены с диска.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить базу данных:\n{e}")

    def on_backup_db(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        path = filedialog.asksaveasfilename(
            title="Создать резервную копию",
            defaultextension=".bak",
            filetypes=[("Backup файлы", "*.bak"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.db.create_backup(path)
            messagebox.showinfo("Успех", f"Резервная копия создана:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось создать копию:\n{e}")

    def on_restore_db(self):
        path = filedialog.askopenfilename(
            title="Восстановить из резервной копии",
            filetypes=[("Backup файлы", "*.bak"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        if not messagebox.askyesno("Подтверждение", "Текущие несохраненные данные будут заменены содержимым копии. Продолжить?"):
            return
        try:
            self.db.restore_backup(path)
            self.refresh_table()
            messagebox.showinfo("Успех", "База данных успешно восстановлена!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось восстановить базу данных:\n{e}")

    def on_export_xlsx(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        path = filedialog.asksaveasfilename(
            title="Экспорт в Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.db.export_to_xlsx(path)
            messagebox.showinfo("Успех", f"Таблица успешно экспортирована в Excel:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта в Excel:\n{e}")

    def on_import_xlsx(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        path = filedialog.askopenfilename(
            title="Импорт из Excel",
            filetypes=[("Excel файлы", "*.xlsx"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            count = self.db.import_from_xlsx(path)
            self.refresh_table()
            messagebox.showinfo("Успех", f"Импортировано записей из Excel: {count}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка импорта из Excel:\n{e}")

    def on_export_csv(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        path = filedialog.asksaveasfilename(
            title="Экспорт в CSV",
            defaultextension=".csv",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            self.db.export_to_csv(path)
            messagebox.showinfo("Успех", f"Таблица успешно экспортирована в CSV:\n{path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка экспорта в CSV:\n{e}")

    def on_import_csv(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Нет открытой базы данных")
            return
        path = filedialog.askopenfilename(
            title="Импорт из CSV",
            filetypes=[("CSV файлы", "*.csv"), ("Все файлы", "*.*")],
        )
        if not path:
            return
        try:
            count = self.db.import_from_csv(path)
            self.refresh_table()
            messagebox.showinfo("Успех", f"Импортировано записей из CSV: {count}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка импорта из CSV:\n{e}")

    def on_add_record(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Сначала откройте или создайте базу данных")
            return
        self._record_dialog(title="Добавление новой записи", is_edit=False)

    def on_edit_record(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Сначала откройте или создайте базу данных")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Подсказка", "Выберите запись для редактирования в таблице")
            return
        vals = self.tree.item(selected[0], "values")
        rec_id = int(vals[0])
        rec = self.db.search_by_id(rec_id)
        if not rec:
            messagebox.showerror("Ошибка", f"Запись с ID {rec_id} не найдена в файле БД")
            return
        self._record_dialog(title="Редактирование записи", is_edit=True, initial_data=rec)

    def on_delete_selected(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Сначала откройте или создайте базу данных")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Подсказка", "Выберите запись в таблице для удаления")
            return
        vals = self.tree.item(selected[0], "values")
        rec_id = int(vals[0])
        if not messagebox.askyesno("Подтверждение", f"Удалить запись с ID={rec_id} ({vals[1]})?"):
            return
        try:
            self.db.delete_by_id(rec_id)
            self.refresh_table()
            messagebox.showinfo("Успех", f"Запись ID={rec_id} удалена из файла БД")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка удаления записи:\n{e}")

    def _record_dialog(self, title, is_edit, initial_data=None):
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.geometry("420x330")
        dlg.transient(self.root)
        dlg.grab_set()

        fields_frame = ttk.Frame(dlg, padding=15)
        fields_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(fields_frame, text="ID товара (Ключ, int):").grid(row=0, column=0, sticky=tk.W, pady=4)
        id_entry = ttk.Entry(fields_frame)
        id_entry.grid(row=0, column=1, sticky="ew", pady=4)

        ttk.Label(fields_frame, text="Название (str):").grid(row=1, column=0, sticky=tk.W, pady=4)
        name_entry = ttk.Entry(fields_frame)
        name_entry.grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(fields_frame, text="Категория (str):").grid(row=2, column=0, sticky=tk.W, pady=4)
        category_entry = ttk.Entry(fields_frame)
        category_entry.grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(fields_frame, text="Цена (float):").grid(row=3, column=0, sticky=tk.W, pady=4)
        price_entry = ttk.Entry(fields_frame)
        price_entry.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(fields_frame, text="Количество (int):").grid(row=4, column=0, sticky=tk.W, pady=4)
        quantity_entry = ttk.Entry(fields_frame)
        quantity_entry.grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Label(fields_frame, text="В наличии (bool):").grid(row=5, column=0, sticky=tk.W, pady=4)
        stock_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fields_frame, text="Да / Нет", variable=stock_var).grid(row=5, column=1, sticky=tk.W, pady=4)

        fields_frame.columnconfigure(1, weight=1)

        if initial_data:
            id_entry.insert(0, str(initial_data["id"]))
            name_entry.insert(0, initial_data["name"])
            category_entry.insert(0, initial_data["category"])
            price_entry.insert(0, str(initial_data["price"]))
            quantity_entry.insert(0, str(initial_data["quantity"]))
            stock_var.set(initial_data["in_stock"])

        def submit():
            try:
                rec_id = int(id_entry.get().strip())
                name = name_entry.get().strip()
                category = category_entry.get().strip()
                price = float(price_entry.get().strip().replace(",", "."))
                quantity = int(quantity_entry.get().strip())
                in_stock = stock_var.get()
            except ValueError as ve:
                messagebox.showerror("Ошибка валидации", f"Неверный формат числового поля:\n{ve}", parent=dlg)
                return

            if not name:
                messagebox.showerror("Ошибка валидации", "Название товара не может быть пустым", parent=dlg)
                return

            record = {
                "id": rec_id,
                "name": name,
                "category": category,
                "price": price,
                "quantity": quantity,
                "in_stock": in_stock,
            }

            try:
                if is_edit:
                    old_id = initial_data["id"]
                    self.db.update(old_id, record)
                    messagebox.showinfo("Успех", f"Запись ID={rec_id} успешно обновлена в файле БД", parent=dlg)
                else:
                    self.db.insert(record)
                    messagebox.showinfo("Успех", f"Запись ID={rec_id} добавлена в файл БД", parent=dlg)
                dlg.destroy()
                self.refresh_table()
            except Exception as ex:
                messagebox.showerror("Ошибка операции", str(ex), parent=dlg)

        btn_box = ttk.Frame(dlg, padding=10)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Сохранить", command=submit).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_box, text="Отмена", command=dlg.destroy).pack(side=tk.RIGHT, padx=5)

    def on_search(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Сначала откройте или создайте базу данных")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Поиск по базе данных")
        dlg.geometry("700x480")
        dlg.transient(self.root)

        top_f = ttk.Frame(dlg, padding=10)
        top_f.pack(side=tk.TOP, fill=tk.X)

        field_labels = {
            "id": "ID (Ключевое поле, O(1))",
            "name": "Название товара",
            "category": "Категория",
            "price": "Цена",
            "quantity": "Количество",
            "in_stock": "В наличии (True/False)",
        }
        field_keys = list(field_labels.keys())

        ttk.Label(top_f, text="Поле для поиска:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        cb_field = ttk.Combobox(top_f, values=list(field_labels.values()), state="readonly", width=25)
        cb_field.current(0)
        cb_field.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(top_f, text="Значение:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        val_entry = ttk.Entry(top_f, width=20)
        val_entry.grid(row=0, column=3, padx=5, pady=5)

        info_lbl = ttk.Label(dlg, text="Введите значение и нажмите 'Искать'", foreground="gray")
        info_lbl.pack(side=tk.TOP, fill=tk.X, padx=10)

        tree_f = ttk.Frame(dlg, padding=10)
        tree_f.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        res_tree = ttk.Treeview(tree_f, columns=("id", "name", "category", "price", "quantity", "in_stock"), show="headings")
        res_tree.heading("id", text="ID")
        res_tree.heading("name", text="Название")
        res_tree.heading("category", text="Категория")
        res_tree.heading("price", text="Цена")
        res_tree.heading("quantity", text="Кол-во")
        res_tree.heading("in_stock", text="В наличии")

        res_tree.column("id", width=60, anchor=tk.CENTER)
        res_tree.column("name", width=180, anchor=tk.W)
        res_tree.column("category", width=120, anchor=tk.W)
        res_tree.column("price", width=80, anchor=tk.E)
        res_tree.column("quantity", width=70, anchor=tk.CENTER)
        res_tree.column("in_stock", width=70, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(tree_f, orient=tk.VERTICAL, command=res_tree.yview)
        res_tree.configure(yscrollcommand=vsb.set)
        res_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def do_search():
            for item in res_tree.get_children():
                res_tree.delete(item)
            selected_idx = cb_field.current()
            field_name = field_keys[selected_idx]
            query = val_entry.get().strip()
            if not query:
                messagebox.showwarning("Внимание", "Введите значение для поиска", parent=dlg)
                return

            t_start = time.perf_counter()
            try:
                matches = self.db.search_by_field(field_name, query)
            except Exception as e:
                messagebox.showerror("Ошибка поиска", str(e), parent=dlg)
                return
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000

            for r in matches:
                stock_str = "Да" if r["in_stock"] else "Нет"
                res_tree.insert("", tk.END, values=(r["id"], r["name"], r["category"], f"{r['price']:.2f}", r["quantity"], stock_str))

            complexity_info = "O(1) [Хэш-индекс на диске]" if field_name == "id" else "O(N) [Прямое сканирование файла]"
            info_lbl.config(
                text=f"Найдено записей: {len(matches)} | Время: {t_elapsed_ms:.4f} мс | Сложность: {complexity_info}",
                foreground="black"
            )

        ttk.Button(top_f, text="🔍 Искать", command=do_search).grid(row=0, column=4, padx=5, pady=5)
        val_entry.bind("<Return>", lambda e: do_search())

    def on_delete_by_field(self):
        if not self.db.is_open():
            messagebox.showwarning("Внимание", "Сначала откройте или создайте базу данных")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Удаление по значению поля")
        dlg.geometry("450x220")
        dlg.transient(self.root)
        dlg.grab_set()

        top_f = ttk.Frame(dlg, padding=15)
        top_f.pack(fill=tk.BOTH, expand=True)

        field_labels = {
            "id": "ID (Ключевое поле, O(1))",
            "name": "Название товара",
            "category": "Категория",
            "price": "Цена",
            "quantity": "Количество",
            "in_stock": "В наличии (True/False)",
        }
        field_keys = list(field_labels.keys())

        ttk.Label(top_f, text="Выберите поле:").grid(row=0, column=0, sticky=tk.W, pady=6)
        cb_field = ttk.Combobox(top_f, values=list(field_labels.values()), state="readonly", width=25)
        cb_field.current(0)
        cb_field.grid(row=0, column=1, sticky="ew", pady=6)

        ttk.Label(top_f, text="Значение для удаления:").grid(row=1, column=0, sticky=tk.W, pady=6)
        val_entry = ttk.Entry(top_f)
        val_entry.grid(row=1, column=1, sticky="ew", pady=6)

        ttk.Label(
            top_f,
            text="Внимание: для неключевых полей будут удалены\nВСЕ совпадающие по значению записи!",
            foreground="darkred",
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=8)

        def do_delete():
            selected_idx = cb_field.current()
            field_name = field_keys[selected_idx]
            query = val_entry.get().strip()
            if not query:
                messagebox.showwarning("Внимание", "Введите значение для удаления", parent=dlg)
                return

            if not messagebox.askyesno(
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить все записи, где {field_labels[field_name]} = '{query}'?",
                parent=dlg,
            ):
                return

            t_start = time.perf_counter()
            try:
                del_count = self.db.delete_by_field(field_name, query)
            except Exception as e:
                messagebox.showerror("Ошибка удаления", str(e), parent=dlg)
                return
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000

            dlg.destroy()
            self.refresh_table()
            messagebox.showinfo(
                "Результат",
                f"Успешно удалено записей: {del_count}\nВремя операции: {t_elapsed_ms:.4f} мс"
            )

        btn_box = ttk.Frame(dlg, padding=10)
        btn_box.pack(fill=tk.X)
        ttk.Button(btn_box, text="Удалить записи", command=do_delete).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_box, text="Отмена", command=dlg.destroy).pack(side=tk.RIGHT, padx=5)
