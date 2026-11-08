import os
import struct
import zipfile
import csv

try:
    import openpyxl
except ImportError:
    openpyxl = None

DB_MAGIC = b"STORAGE1"
IDX_MAGIC = b"HASHIDX1"
DB_HEADER_FMT = ">8sIIq8s"
IDX_HEADER_FMT = ">8sIIq8s"
REC_FMT = ">?qi80s50sdi?100s"
NODE_FMT = ">?iqqq3s"

DB_HEADER_SIZE = struct.calcsize(DB_HEADER_FMT)
IDX_HEADER_SIZE = struct.calcsize(IDX_HEADER_FMT)
REC_SIZE = struct.calcsize(REC_FMT)
NODE_SIZE = struct.calcsize(NODE_FMT)
BUCKET_COUNT = 2053

class Database:
    def __init__(self, db_path=None):
        self.db_path = None
        self.idx_path = None
        self.db_file = None
        self.idx_file = None
        self.bucket_count = BUCKET_COUNT
        if db_path:
            self.open(db_path)

    def is_open(self):
        return self.db_file is not None and not self.db_file.closed

    def create(self, db_path):
        self.close()
        base_path = os.path.splitext(db_path)[0]
        self.db_path = base_path + ".db"
        self.idx_path = base_path + ".idx"
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with open(self.db_path, "wb") as f:
            header = struct.pack(DB_HEADER_FMT, DB_MAGIC, 0, 0, -1, b"\x00" * 8)
            f.write(header)
        with open(self.idx_path, "wb") as f:
            header = struct.pack(IDX_HEADER_FMT, IDX_MAGIC, self.bucket_count, 0, -1, b"\x00" * 8)
            f.write(header)
            buckets = struct.pack(f">{self.bucket_count}q", *([-1] * self.bucket_count))
            f.write(buckets)
        self.open(self.db_path)

    def open(self, db_path):
        self.close()
        base_path = os.path.splitext(db_path)[0]
        db_file = base_path + ".db"
        idx_file = base_path + ".idx"
        if not os.path.exists(db_file) or not os.path.exists(idx_file):
            raise FileNotFoundError("Database or index file not found")
        f_db = open(db_file, "r+b")
        f_idx = open(idx_file, "r+b")
        db_hdr = f_db.read(DB_HEADER_SIZE)
        if len(db_hdr) < DB_HEADER_SIZE or db_hdr[:8] != DB_MAGIC:
            f_db.close()
            f_idx.close()
            raise ValueError("Invalid database file format")
        idx_hdr = f_idx.read(IDX_HEADER_SIZE)
        if len(idx_hdr) < IDX_HEADER_SIZE or idx_hdr[:8] != IDX_MAGIC:
            f_db.close()
            f_idx.close()
            raise ValueError("Invalid index file format")
        _, b_count, _, _, _ = struct.unpack(IDX_HEADER_FMT, idx_hdr)
        self.db_path = db_file
        self.idx_path = idx_file
        self.db_file = f_db
        self.idx_file = f_idx
        self.bucket_count = b_count

    def close(self):
        if self.db_file and not self.db_file.closed:
            self.db_file.flush()
            self.db_file.close()
        if self.idx_file and not self.idx_file.closed:
            self.idx_file.flush()
            self.idx_file.close()
        self.db_file = None
        self.idx_file = None

    def save(self):
        if not self.is_open():
            return
        self.db_file.flush()
        self.idx_file.flush()
        os.fsync(self.db_file.fileno())
        os.fsync(self.idx_file.fileno())

    def clear(self):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        self.db_file.seek(0)
        self.db_file.truncate()
        header_db = struct.pack(DB_HEADER_FMT, DB_MAGIC, 0, 0, -1, b"\x00" * 8)
        self.db_file.write(header_db)
        self.db_file.flush()
        self.idx_file.seek(0)
        self.idx_file.truncate()
        header_idx = struct.pack(IDX_HEADER_FMT, IDX_MAGIC, self.bucket_count, 0, -1, b"\x00" * 8)
        self.idx_file.write(header_idx)
        buckets = struct.pack(f">{self.bucket_count}q", *([-1] * self.bucket_count))
        self.idx_file.write(buckets)
        self.idx_file.flush()

    def delete_database(self):
        db_p = self.db_path
        idx_p = self.idx_path
        self.close()
        if db_p and os.path.exists(db_p):
            os.remove(db_p)
        if idx_p and os.path.exists(idx_p):
            os.remove(idx_p)
        self.db_path = None
        self.idx_path = None

    def _pack_record(self, data, status=True, next_free=-1):
        name_str = str(data["name"])[:38]
        name_bytes = name_str.encode("utf-8").ljust(80, b"\x00")
        cat_str = str(data["category"])[:24]
        cat_bytes = cat_str.encode("utf-8").ljust(50, b"\x00")
        return struct.pack(
            REC_FMT,
            status,
            next_free,
            int(data["id"]),
            name_bytes,
            cat_bytes,
            float(data["price"]),
            int(data["quantity"]),
            bool(data["in_stock"]),
            b"\x00" * 100,
        )

    def _unpack_record(self, raw_bytes):
        st, nf, rec_id, name_b, cat_b, price, qty, in_stock, _ = struct.unpack(REC_FMT, raw_bytes)
        name = name_b.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        category = cat_b.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        return {
            "id": rec_id,
            "name": name,
            "category": category,
            "price": round(price, 2),
            "quantity": qty,
            "in_stock": in_stock,
        }

    def _find_in_index(self, key):
        bucket = abs(key) % self.bucket_count
        b_offset = IDX_HEADER_SIZE + bucket * 8
        self.idx_file.seek(b_offset)
        curr_offset = struct.unpack(">q", self.idx_file.read(8))[0]
        prev_offset = None
        while curr_offset != -1:
            self.idx_file.seek(curr_offset)
            node_bytes = self.idx_file.read(NODE_SIZE)
            status, k, rec_offset, next_offset, _, _ = struct.unpack(NODE_FMT, node_bytes)
            if status and k == key:
                return rec_offset, curr_offset, prev_offset, b_offset
            prev_offset = curr_offset
            curr_offset = next_offset
        return None, None, None, b_offset

    def _insert_into_index(self, key, record_offset):
        bucket = abs(key) % self.bucket_count
        b_offset = IDX_HEADER_SIZE + bucket * 8
        self.idx_file.seek(b_offset)
        old_head = struct.unpack(">q", self.idx_file.read(8))[0]
        self.idx_file.seek(0)
        magic, b_count, active_entries, free_head, reserved = struct.unpack(IDX_HEADER_FMT, self.idx_file.read(32))
        if free_head != -1:
            new_slot = free_head
            self.idx_file.seek(free_head)
            _, _, _, _, nxt_free, _ = struct.unpack(NODE_FMT, self.idx_file.read(NODE_SIZE))
            free_head = nxt_free
        else:
            self.idx_file.seek(0, os.SEEK_END)
            new_slot = self.idx_file.tell()
        node_data = struct.pack(NODE_FMT, True, key, record_offset, old_head, -1, b"\x00" * 3)
        self.idx_file.seek(new_slot)
        self.idx_file.write(node_data)
        self.idx_file.seek(b_offset)
        self.idx_file.write(struct.pack(">q", new_slot))
        active_entries += 1
        self.idx_file.seek(0)
        self.idx_file.write(struct.pack(IDX_HEADER_FMT, magic, b_count, active_entries, free_head, reserved))

    def _delete_from_index(self, key):
        rec_offset, curr_offset, prev_offset, b_offset = self._find_in_index(key)
        if curr_offset is None:
            return None
        self.idx_file.seek(curr_offset)
        _, _, _, next_offset, _, _ = struct.unpack(NODE_FMT, self.idx_file.read(NODE_SIZE))
        if prev_offset is None:
            self.idx_file.seek(b_offset)
            self.idx_file.write(struct.pack(">q", next_offset))
        else:
            self.idx_file.seek(prev_offset)
            st, pk, pr, _, pf, rs = struct.unpack(NODE_FMT, self.idx_file.read(NODE_SIZE))
            self.idx_file.seek(prev_offset)
            self.idx_file.write(struct.pack(NODE_FMT, st, pk, pr, next_offset, pf, rs))
        self.idx_file.seek(0)
        magic, b_count, active_entries, free_head, reserved = struct.unpack(IDX_HEADER_FMT, self.idx_file.read(32))
        del_node = struct.pack(NODE_FMT, False, key, -1, -1, free_head, b"\x00" * 3)
        self.idx_file.seek(curr_offset)
        self.idx_file.write(del_node)
        active_entries -= 1
        self.idx_file.seek(0)
        self.idx_file.write(struct.pack(IDX_HEADER_FMT, magic, b_count, active_entries, curr_offset, reserved))
        return rec_offset

    def insert(self, record_dict):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        rec_id = int(record_dict["id"])
        existing_offset, _, _, _ = self._find_in_index(rec_id)
        if existing_offset is not None:
            raise ValueError(f"Запись с ключевым полем id={rec_id} уже существует")
        self.db_file.seek(0)
        magic, active_count, total_slots, free_head, reserved = struct.unpack(DB_HEADER_FMT, self.db_file.read(32))
        if free_head != -1:
            rec_offset = free_head
            self.db_file.seek(free_head)
            _, nxt_free, _, _, _, _, _, _, _ = struct.unpack(REC_FMT, self.db_file.read(REC_SIZE))
            free_head = nxt_free
        else:
            self.db_file.seek(0, os.SEEK_END)
            rec_offset = self.db_file.tell()
            total_slots += 1
        data_bytes = self._pack_record(record_dict, status=True, next_free=-1)
        self.db_file.seek(rec_offset)
        self.db_file.write(data_bytes)
        active_count += 1
        self.db_file.seek(0)
        self.db_file.write(struct.pack(DB_HEADER_FMT, magic, active_count, total_slots, free_head, reserved))
        self._insert_into_index(rec_id, rec_offset)
        self.db_file.flush()
        self.idx_file.flush()
        return rec_offset

    def search_by_id(self, record_id):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        rec_offset, _, _, _ = self._find_in_index(int(record_id))
        if rec_offset is None:
            return None
        self.db_file.seek(rec_offset)
        raw = self.db_file.read(REC_SIZE)
        return self._unpack_record(raw)

    def search_by_field(self, field_name, value):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        if field_name == "id":
            r = self.search_by_id(int(value))
            return [r] if r else []
        self.db_file.seek(0)
        _, _, total_slots, _, _ = struct.unpack(DB_HEADER_FMT, self.db_file.read(32))
        results = []
        for i in range(total_slots):
            offset = DB_HEADER_SIZE + i * REC_SIZE
            self.db_file.seek(offset)
            raw = self.db_file.read(REC_SIZE)
            if len(raw) < REC_SIZE:
                break
            status = struct.unpack(">?q", raw[:9])[0]
            if not status:
                continue
            rec = self._unpack_record(raw)
            if field_name in ("name", "category"):
                if str(value).lower() in rec[field_name].lower():
                    results.append(rec)
            elif field_name == "price":
                if abs(rec["price"] - float(value)) < 0.001:
                    results.append(rec)
            elif field_name == "quantity":
                if rec["quantity"] == int(value):
                    results.append(rec)
            elif field_name == "in_stock":
                val_bool = str(value).strip().lower() in ("true", "1", "да", "yes", "+")
                if rec["in_stock"] == val_bool:
                    results.append(rec)
        return results

    def delete_by_id(self, record_id):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        rec_offset = self._delete_from_index(int(record_id))
        if rec_offset is None:
            return False
        self.db_file.seek(0)
        magic, active_count, total_slots, free_head, reserved = struct.unpack(DB_HEADER_FMT, self.db_file.read(32))
        tombstone = struct.pack(REC_FMT, False, free_head, int(record_id), b"\x00" * 80, b"\x00" * 50, 0.0, 0, False, b"\x00" * 100)
        self.db_file.seek(rec_offset)
        self.db_file.write(tombstone)
        active_count -= 1
        self.db_file.seek(0)
        self.db_file.write(struct.pack(DB_HEADER_FMT, magic, active_count, total_slots, rec_offset, reserved))
        self.db_file.flush()
        self.idx_file.flush()
        return True

    def delete_by_field(self, field_name, value):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        if field_name == "id":
            return 1 if self.delete_by_id(int(value)) else 0
        matches = self.search_by_field(field_name, value)
        count = 0
        for m in matches:
            if self.delete_by_id(m["id"]):
                count += 1
        return count

    def update(self, old_id, new_data):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        old_id = int(old_id)
        new_id = int(new_data["id"])
        rec_offset, curr_idx_offset, _, _ = self._find_in_index(old_id)
        if rec_offset is None:
            raise ValueError(f"Запись с id={old_id} не найдена")
        if new_id != old_id:
            chk, _, _, _ = self._find_in_index(new_id)
            if chk is not None:
                raise ValueError(f"Запись с новым id={new_id} уже существует")
            self._delete_from_index(old_id)
            self._insert_into_index(new_id, rec_offset)
        data_bytes = self._pack_record(new_data, status=True, next_free=-1)
        self.db_file.seek(rec_offset)
        self.db_file.write(data_bytes)
        self.db_file.flush()
        self.idx_file.flush()

    def get_all_records(self):
        if not self.is_open():
            return []
        self.db_file.seek(0)
        _, _, total_slots, _, _ = struct.unpack(DB_HEADER_FMT, self.db_file.read(32))
        records = []
        for i in range(total_slots):
            offset = DB_HEADER_SIZE + i * REC_SIZE
            self.db_file.seek(offset)
            raw = self.db_file.read(REC_SIZE)
            if len(raw) < REC_SIZE:
                break
            status = struct.unpack(">?q", raw[:9])[0]
            if status:
                records.append(self._unpack_record(raw))
        return records

    def get_stats(self):
        if not self.is_open():
            return {"active": 0, "total_slots": 0, "file_size": 0}
        self.db_file.seek(0)
        _, active_count, total_slots, free_head, _ = struct.unpack(DB_HEADER_FMT, self.db_file.read(32))
        return {
            "active": active_count,
            "total_slots": total_slots,
            "free_slots": total_slots - active_count,
            "db_size": os.path.getsize(self.db_path),
            "idx_size": os.path.getsize(self.idx_path),
        }

    def create_backup(self, backup_path):
        if not self.is_open():
            raise RuntimeError("Database is not open")
        self.save()
        if not backup_path.endswith(".bak"):
            backup_path += ".bak"
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(self.db_path, os.path.basename(self.db_path))
            zf.write(self.idx_path, os.path.basename(self.idx_path))

    def restore_backup(self, backup_path):
        if not os.path.exists(backup_path):
            raise FileNotFoundError("Backup file not found")
        curr_db = self.db_path
        self.close()
        dest_dir = os.path.dirname(os.path.abspath(curr_db)) if curr_db else os.getcwd()
        db_name = None
        with zipfile.ZipFile(backup_path, "r") as zf:
            for item in zf.namelist():
                if item.endswith(".db"):
                    db_name = item
                zf.extract(item, dest_dir)
        if not db_name:
            raise ValueError("No database file found in backup")
        restored_path = os.path.join(dest_dir, db_name)
        self.open(restored_path)

    def export_to_csv(self, file_path):
        records = self.get_all_records()
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "name", "category", "price", "quantity", "in_stock"])
            writer.writeheader()
            writer.writerows(records)

    def import_from_csv(self, file_path):
        count = 0
        with open(file_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rec = {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "category": row["category"],
                    "price": float(row["price"]),
                    "quantity": int(row["quantity"]),
                    "in_stock": str(row["in_stock"]).strip().lower() in ("true", "1", "yes", "+"),
                }
                self.insert(rec)
                count += 1
        return count

    def export_to_xlsx(self, file_path):
        if openpyxl is None:
            raise ImportError("openpyxl is not installed")
        records = self.get_all_records()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"
        headers = ["ID", "Название", "Категория", "Цена (руб.)", "Количество", "В наличии"]
        ws.append(headers)
        for r in records:
            ws.append([r["id"], r["name"], r["category"], r["price"], r["quantity"], "Да" if r["in_stock"] else "Нет"])
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)
        wb.save(file_path)

    def import_from_xlsx(self, file_path):
        if openpyxl is None:
            raise ImportError("openpyxl is not installed")
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return 0
        header_row = [str(c).strip().lower() for c in rows[0]]
        id_idx = next((i for i, h in enumerate(header_row) if "id" in h), 0)
        name_idx = next((i for i, h in enumerate(header_row) if "название" in h or "name" in h), 1)
        cat_idx = next((i for i, h in enumerate(header_row) if "категор" in h or "category" in h), 2)
        price_idx = next((i for i, h in enumerate(header_row) if "цен" in h or "price" in h), 3)
        qty_idx = next((i for i, h in enumerate(header_row) if "колич" in h or "quantity" in h), 4)
        stock_idx = next((i for i, h in enumerate(header_row) if "налич" in h or "stock" in h), 5)
        count = 0
        for r in rows[1:]:
            if not r or r[id_idx] is None:
                continue
            rec = {
                "id": int(r[id_idx]),
                "name": str(r[name_idx] or ""),
                "category": str(r[cat_idx] or ""),
                "price": float(r[price_idx] or 0.0),
                "quantity": int(r[qty_idx] or 0),
                "in_stock": str(r[stock_idx]).strip().lower() in ("да", "true", "1", "yes", "+"),
            }
            self.insert(rec)
            count += 1
        return count
