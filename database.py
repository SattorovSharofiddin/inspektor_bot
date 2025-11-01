import sqlite3

DB_NAME = "inspektorbot.db"


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Viloyatlar
    c.execute('''
              CREATE TABLE IF NOT EXISTS viloyatlar
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  nomi
                  TEXT
                  UNIQUE
              )
              ''')

    # Tumanlar
    c.execute('''
              CREATE TABLE IF NOT EXISTS tumanlar
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  nomi
                  TEXT,
                  viloyat_id
                  INTEGER,
                  FOREIGN
                  KEY
              (
                  viloyat_id
              ) REFERENCES viloyatlar
              (
                  id
              )
                  )
              ''')

    # Mahallalar
    c.execute('''
              CREATE TABLE IF NOT EXISTS mahallalar
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  nomi
                  TEXT,
                  tuman_id
                  INTEGER,
                  FOREIGN
                  KEY
              (
                  tuman_id
              ) REFERENCES tumanlar
              (
                  id
              )
                  )
              ''')

    # Uchaskavoy va adminlar
    c.execute('''
              CREATE TABLE IF NOT EXISTS uchaskavoy
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  fio
                  TEXT,
                  telefon
                  TEXT,
                  tg_id
                  INTEGER
                  UNIQUE,
                  mahalla_id
                  INTEGER,
                  role
                  TEXT
                  DEFAULT
                  'uchaskavoy',
                  FOREIGN
                  KEY
              (
                  mahalla_id
              ) REFERENCES mahallalar
              (
                  id
              )
                  )
              ''')

    # Foydalanuvchi murojaatlari
    c.execute('''
              CREATE TABLE IF NOT EXISTS murojaatlar
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  foydalanuvchi_id
                  INTEGER,
                  foydalanuvchi_nick
                  TEXT,
                  holat
                  TEXT,
                  uchaskavoy_id
                  INTEGER,
                  turi
                  TEXT,
                  content
                  TEXT,
                  telefon
                  TEXT,
                  location
                  TEXT,
                  FOREIGN
                  KEY
              (
                  uchaskavoy_id
              ) REFERENCES uchaskavoy
              (
                  id
              )
                  )
              ''')

    conn.commit()
    conn.close()


# --- INSERT FUNKSIYALAR --- #

def add_viloyat(nomi: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO viloyatlar (nomi) VALUES (?)", (nomi,))
    conn.commit()
    conn.close()


def add_tuman(nomi: str, viloyat_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO tumanlar (nomi, viloyat_id) VALUES (?, ?)", (nomi, viloyat_id))
    conn.commit()
    conn.close()


def add_mahalla(nomi: str, tuman_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO mahallalar (nomi, tuman_id) VALUES (?, ?)", (nomi, tuman_id))
    conn.commit()
    conn.close()


def add_uchaskavoy(fio: str, telefon: str, tg_id: int, mahalla_id: int, role="uchaskavoy"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO uchaskavoy (fio, telefon, tg_id, mahalla_id, role) VALUES (?, ?, ?, ?, ?)",
              (fio, telefon, tg_id, mahalla_id, role))
    conn.commit()
    conn.close()


# --- SELECT FUNKSIYALAR --- #

def get_viloyatlar():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, nomi FROM viloyatlar")
    data = c.fetchall()
    conn.close()
    return data


def get_tumanlar(viloyat_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, nomi FROM tumanlar WHERE viloyat_id = ?", (viloyat_id,))
    data = c.fetchall()
    conn.close()
    return data


def get_mahallalar(tuman_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, nomi FROM mahallalar WHERE tuman_id = ?", (tuman_id,))
    data = c.fetchall()
    conn.close()
    return data


def get_uchaskavoy_by_tg_id(tg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT u.id,
                     u.fio,
                     u.telefon,
                     m.nomi AS mahalla,
                     t.nomi AS tuman,
                     v.nomi AS viloyat,
                     u.role,
                     u.mahalla_id
              FROM uchaskavoy u
                       LEFT JOIN mahallalar m ON u.mahalla_id = m.id
                       LEFT JOIN tumanlar t ON m.tuman_id = t.id
                       LEFT JOIN viloyatlar v ON t.viloyat_id = v.id
              WHERE u.tg_id = ?
              """, (tg_id,))
    data = c.fetchone()
    conn.close()
    return data


def get_uchaskavoy_by_mahalla(mahalla_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT id, fio, telefon, tg_id, role
              FROM uchaskavoy
              WHERE mahalla_id = ?
              """, (mahalla_id,))
    data = c.fetchone()
    conn.close()

    return data


def get_mahalla_by_tg_id(tg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT mahalla_id
              FROM uchaskavoy
              WHERE tg_id = ?
                AND role IS NULL
              """, (tg_id,))
    data = c.fetchone()
    conn.close()
    return data  # (mahalla_id,)


def get_user_by_tg_id(tg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, fio, tg_id, role FROM uchaskavoy WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "fio": row[1], "tg_id": row[2], "role": row[3]}
    return None


# --- MUROJAATLAR --- #

def add_murojaat(foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, telefon=None, location=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute('''
              INSERT INTO murojaatlar (foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, telefon,
                                       location)
              VALUES (?, ?, ?, ?, ?, ?, ?)
              ''', (foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, telefon, location))

    conn.commit()
    conn.close()


def get_murojaatlar_by_uchaskavoy(uchaskavoy_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT foydalanuvchi_nick, foydalanuvchi_id FROM murojaatlar WHERE uchaskavoy_id = ?",
              (uchaskavoy_id,))
    foydalanuvchilar = [row for row in c.fetchall()]
    conn.close()
    return foydalanuvchilar


# def get_murojaatlar_by_uchaskavoy(uchaskavoy_id):
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute('''
#         SELECT id, fio, murojaat_text, telefon, location
#         FROM murojaatlar
#         WHERE foydalanuvchi_id IN (
#             SELECT id FROM uchaskavoy WHERE uchaskavoy_id = ?
#         )
#     ''', (uchaskavoy_id,))
#     murojaatlar = c.fetchall()
#     conn.close()
#     return murojaatlar

def get_foydalanuvchi_fio(tg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT fio FROM uchaskavoy WHERE tg_id = ?", (tg_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "Noma’lum fuqaro"


def get_all_murojaatlar():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, fio, murojaat_text, telefon, location FROM murojaatlar')
    murojaatlar = c.fetchall()
    conn.close()
    return murojaatlar


def get_murojaatlar_by_user(foydalanuvchi_id, uchaskavoy_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT turi, content FROM murojaatlar WHERE uchaskavoy_id = ? AND foydalanuvchi_id = ?",
              (uchaskavoy_id, foydalanuvchi_id))
    data = c.fetchall()
    conn.close()
    return data


def delete_uchaskavoy(mahalla_id):
    """Berilgan mahalladagi uchaskavoyni o‘chiradi"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM uchaskavoy WHERE mahalla_id = ?", (mahalla_id,))
    conn.commit()
    conn.close()


# --- Foydalanuvchi role olish ---
def get_user_role(tg_id: int):
    """
    Foydalanuvchining rolini aniqlaydi.
    Agar role=NULL bo‘lsa -> "fuqaro"
    Aks holda role qiymatini qaytaradi.
    """
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT role FROM uchaskavoy WHERE tg_id = ?", (tg_id,))
        row = c.fetchone()
        if not row:
            return "fuqaro"
        role = row[0]
        return "fuqaro" if role is None else role


# --- Uchaskavoy region ma’lumotlarini olish ---
def get_user_region_data(tg_id):
    """Telegram ID bo‘yicha foydalanuvchining mahalla, tuman, viloyat ma’lumotlarini qaytaradi"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT u.fio, u.role, m.nomi AS mahalla, t.nomi AS tuman, v.nomi AS viloyat
              FROM uchaskavoy u
                       LEFT JOIN mahallalar m ON u.mahalla_id = m.id
                       LEFT JOIN tumanlar t ON m.tuman_id = t.id
                       LEFT JOIN viloyatlar v ON t.viloyat_id = v.id
              WHERE u.tg_id = ?
              """, (tg_id,))
    data = c.fetchone()
    conn.close()
    return data


# def add_murojaat(foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, telefon=None, location=None):
#     conn = sqlite3.connect(DB_NAME)
#     c = conn.cursor()
#     c.execute(
#         """
#         INSERT INTO murojaatlar (foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, holat, telefon, location)
#         VALUES (?, ?, ?, ?, ?, ?)
#         """,
#         (foydalanuvchi_id, foydalanuvchi_nick, uchaskavoy_id, turi, content, "kutilmoqda", telefon, location)
#     )
#     conn.commit()
#     conn.close()


def add_fuqarolar(fio: str, telefon: str, tg_id: int, mahalla_id: int, role):
    """
    role=NULL bo'lgan fuqaro sifatida qo'shadi.
    Agar tg_id mavjud bo'lsa, yangilaydi.
    """
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO uchaskavoy (fio, telefon, tg_id, mahalla_id, role)
            VALUES (?, ?, ?, ?, ?)
        """, (fio, telefon, tg_id, mahalla_id, role))
        conn.commit()


def get_fuqarolar_by_tg_id(tg_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM uchaskavoy WHERE tg_id = ? AND role='uchaskavoy'", (tg_id,))
    result = c.fetchone()
    conn.close()
    return result


def get_fuqarolar_by_tg_id_2(tg_id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM uchaskavoy WHERE tg_id = ? and (role is null or role = '')", (tg_id,))
    result = c.fetchone()
    conn.close()
    return result


def get_murojaatlar_by_user(user_id, uchaskavoy_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
              SELECT id, turi, content, holat
              FROM murojaatlar
              WHERE foydalanuvchi_id = ?
                AND uchaskavoy_id = ?
              ORDER BY id DESC
              """, (user_id, uchaskavoy_id))
    data = c.fetchall()
    conn.close()
    return data


def get_fuqarolar_by_uchaskavoy(uchaskavoy_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Avval uchaskavoyning mahalla_id sini topamiz
    c.execute("SELECT mahalla_id FROM uchaskavoy WHERE id = ?", (uchaskavoy_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return []
    mahalla_id = result[0]

    # Endi shu mahalladagi role = NULL bo‘lgan fuqarolarni qaytaramiz
    c.execute("""
              SELECT id, fio, tg_id
              FROM uchaskavoy
              WHERE mahalla_id = ?
                AND (role IS NULL OR role = '')
              """, (mahalla_id,))

    data = c.fetchall()
    conn.close()
    return data


def update_uchaskavoy(mahalla_id):
    conn = sqlite3.connect(DB_NAME)


create_tables()
