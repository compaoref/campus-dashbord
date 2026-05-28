"""
auth.py — Authentification sécurisée + gestion utilisateurs
Utilise PBKDF2-HMAC-SHA256 pour le hachage des mots de passe.
"""
import sqlite3
import hashlib
import secrets
import re
from datetime import datetime

DB_PATH = "decoupe_activites.db"

ROLES = {
    "admin":     {"label": "Administrateur", "color": "#ff6b35", "icon": "👑"},
    "manager":   {"label": "Manager",         "color": "#3b82f6", "icon": "📊"},
    "operateur": {"label": "Opérateur",       "color": "#22c55e", "icon": "⚙️"},
}

PERMISSIONS = {
    "admin": {
        "dashboard", "saisie", "historique", "statistiques",
        "factures", "gestion_users",
    },
    "manager": {
        "dashboard", "saisie", "historique", "statistiques", "factures",
    },
    "operateur": {
        "saisie", "mes_activites",
    },
}


# ── Init DB utilisateurs ────────────────────────────────────────────────────────
def init_users_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    NOT NULL UNIQUE,
            nom_complet  TEXT    NOT NULL,
            email        TEXT,
            role         TEXT    NOT NULL DEFAULT 'operateur',
            password_hash TEXT   NOT NULL,
            salt         TEXT    NOT NULL,
            actif        INTEGER NOT NULL DEFAULT 1,
            last_login   TEXT,
            created_at   TEXT    DEFAULT (datetime('now'))
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT,
            success    INTEGER,
            ip_hint    TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    # Seed comptes par défaut si vide
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        _seed_default_users(c)
    conn.commit()
    conn.close()


def _seed_default_users(c):
    defaults = [
        ("admin",     "Administrateur Système", "admin@imprimerie.bf",    "admin",     "Admin@2024!"),
        ("manager",   "Responsable Production", "manager@imprimerie.bf",  "manager",   "Manager@2024!"),
        ("operateur", "Opérateur Machine",       "operateur@imprimerie.bf","operateur", "Operateur@2024!"),
    ]
    for username, nom, email, role, pwd in defaults:
        salt = secrets.token_hex(32)
        phash = _hash_password(pwd, salt)
        c.execute(
            "INSERT INTO users (username, nom_complet, email, role, password_hash, salt) VALUES (?,?,?,?,?,?)",
            (username, nom, email, role, phash, salt),
        )


# ── Hachage ────────────────────────────────────────────────────────────────────
def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        310_000,  # iterations NIST 2023
    ).hex()


# ── Authentification ────────────────────────────────────────────────────────────
def authenticate(username: str, password: str) -> dict | None:
    """Retourne le user dict si authentifié, None sinon."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND actif=1", (username.strip(),))
    user = c.fetchone()
    if user is None:
        _log(c, username, False)
        conn.commit(); conn.close()
        return None
    expected = _hash_password(password, user["salt"])
    if not secrets.compare_digest(expected, user["password_hash"]):
        _log(c, username, False)
        conn.commit(); conn.close()
        return None
    # Succès
    c.execute("UPDATE users SET last_login=? WHERE id=?",
              (datetime.now().isoformat(timespec="seconds"), user["id"]))
    _log(c, username, True)
    conn.commit(); conn.close()
    return dict(user)


def _log(c, username, success):
    c.execute("INSERT INTO login_logs (username, success) VALUES (?,?)", (username, int(success)))


# ── CRUD utilisateurs ───────────────────────────────────────────────────────────
def get_all_users() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, username, nom_complet, email, role, actif, last_login, created_at FROM users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_user(username: str, nom_complet: str, email: str, role: str, password: str) -> tuple[bool, str]:
    err = _validate_password(password)
    if err:
        return False, err
    if not username.strip():
        return False, "Le nom d'utilisateur est requis."
    conn = sqlite3.connect(DB_PATH)
    try:
        salt  = secrets.token_hex(32)
        phash = _hash_password(password, salt)
        conn.execute(
            "INSERT INTO users (username, nom_complet, email, role, password_hash, salt) VALUES (?,?,?,?,?,?)",
            (username.strip().lower(), nom_complet.strip(), email.strip(), role, phash, salt),
        )
        conn.commit()
        return True, "Utilisateur créé avec succès."
    except sqlite3.IntegrityError:
        return False, f"Le nom d'utilisateur « {username} » est déjà pris."
    finally:
        conn.close()


def update_user(user_id: int, nom_complet: str, email: str, role: str, actif: bool) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "UPDATE users SET nom_complet=?, email=?, role=?, actif=? WHERE id=?",
            (nom_complet.strip(), email.strip(), role, int(actif), user_id),
        )
        conn.commit()
        return True, "Utilisateur mis à jour."
    finally:
        conn.close()


def change_password(user_id: int, new_password: str) -> tuple[bool, str]:
    err = _validate_password(new_password)
    if err:
        return False, err
    salt  = secrets.token_hex(32)
    phash = _hash_password(new_password, salt)
    conn  = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET password_hash=?, salt=? WHERE id=?", (phash, salt, user_id))
    conn.commit()
    conn.close()
    return True, "Mot de passe modifié avec succès."


def delete_user(user_id: int) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        return True, "Utilisateur supprimé."
    finally:
        conn.close()


# ── Validation mot de passe ─────────────────────────────────────────────────────
def _validate_password(pwd: str) -> str | None:
    """Retourne un message d'erreur ou None si valide."""
    if len(pwd) < 8:
        return "Le mot de passe doit faire au moins 8 caractères."
    if not re.search(r"[A-Z]", pwd):
        return "Le mot de passe doit contenir au moins une majuscule."
    if not re.search(r"[0-9]", pwd):
        return "Le mot de passe doit contenir au moins un chiffre."
    return None


# ── Vérification de permission ──────────────────────────────────────────────────
def has_perm(user: dict, perm: str) -> bool:
    role = user.get("role", "operateur")
    return perm in PERMISSIONS.get(role, set())
