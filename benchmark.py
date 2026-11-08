import os
import time
import random
from database import Database

def run_benchmarks(sizes=(100, 500, 1000, 2500, 5000)):
    results = []
    bench_dir = "/tmp/bench_lab2"
    os.makedirs(bench_dir, exist_ok=True)

    categories = ["Электроника", "Периферия", "Бытовая техника", "Аудио", "Аксессуары", "Сетевое оборудование"]
    names_base = ["Ноутбук", "Смартфон", "Монитор", "Клавиатура", "Мышь", "Планшет", "Наушники", "Колонки", "Роутер", "Кабель"]

    for n in sizes:
        db_path = os.path.join(bench_dir, f"bench_{n}.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(db_path.replace(".db", ".idx")):
            os.remove(db_path.replace(".db", ".idx"))

        db = Database()
        db.create(db_path)

        records = []
        for i in range(1, n + 1):
            records.append({
                "id": i,
                "name": f"{random.choice(names_base)} Model-{i}",
                "category": random.choice(categories),
                "price": round(random.uniform(500, 150000), 2),
                "quantity": random.randint(0, 100),
                "in_stock": random.choice([True, False]),
            })

        t0 = time.perf_counter()
        for r in records:
            db.insert(r)
        t_insert_total = time.perf_counter() - t0
        t_insert_avg = (t_insert_total / n) * 1000

        test_keys = random.sample(range(1, n + 1), min(50, n))
        t0 = time.perf_counter()
        for k in test_keys:
            res = db.search_by_id(k)
        t_search_key_avg = ((time.perf_counter() - t0) / len(test_keys)) * 1000

        test_cats = [random.choice(categories) for _ in range(min(10, n))]
        t0 = time.perf_counter()
        for c in test_cats:
            res = db.search_by_field("category", c)
        t_search_nonkey_avg = ((time.perf_counter() - t0) / len(test_cats)) * 1000

        del_keys = random.sample(test_keys, min(20, len(test_keys)))
        t0 = time.perf_counter()
        for k in del_keys:
            db.delete_by_id(k)
        t_del_key_avg = ((time.perf_counter() - t0) / len(del_keys)) * 1000

        db.close()

        results.append({
            "n": n,
            "insert_avg_ms": t_insert_avg,
            "search_key_avg_ms": t_search_key_avg,
            "search_nonkey_avg_ms": t_search_nonkey_avg,
            "del_key_avg_ms": t_del_key_avg,
        })

    print("-" * 88)
    print(f"{'N записей':<10} | {'Вставка (мс)':<14} | {'Поиск ID O(1)':<16} | {'Поиск некатегор. O(N)':<22} | {'Удаление ID O(1)':<16}")
    print("-" * 88)
    for row in results:
        print(
            f"{row['n']:<10} | "
            f"{row['insert_avg_ms']:<14.4f} | "
            f"{row['search_key_avg_ms']:<16.4f} | "
            f"{row['search_nonkey_avg_ms']:<22.4f} | "
            f"{row['del_key_avg_ms']:<16.4f}"
        )
    print("-" * 88)
    return results

if __name__ == "__main__":
    run_benchmarks()
