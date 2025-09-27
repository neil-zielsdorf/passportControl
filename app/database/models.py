import sqlite3
import json
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from app.utils.encryption import get_encryption

DATABASE_PATH = "data/passport_manager.db"

@dataclass
class Person:
    id: Optional[int]
    name: str
    role: str  # "parent" or "child"
    birth_date: date
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['birth_date'] = self.birth_date.isoformat() if self.birth_date else None
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        return d

@dataclass
class Document:
    id: Optional[int]
    holder_id: int
    type: str  # "passport", "drivers_license", "nexus", etc.
    country: str
    document_number: str  # This will be encrypted
    issue_date: Optional[date]
    expiry_date: date
    status: str  # "current", "application_submitted", "received_new"
    submission_date: Optional[date] = None
    processing_estimate: Optional[str] = None
    photo_filename: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['issue_date'] = self.issue_date.isoformat() if self.issue_date else None
        d['expiry_date'] = self.expiry_date.isoformat() if self.expiry_date else None
        d['submission_date'] = self.submission_date.isoformat() if self.submission_date else None
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        d['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return d

@dataclass
class Setting:
    key: str
    value: str
    updated_at: Optional[datetime] = None

class DatabaseManager:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.encryption = get_encryption()
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # People table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('parent', 'child')),
                birth_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Documents table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                holder_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                country TEXT NOT NULL,
                document_number TEXT NOT NULL,
                issue_date DATE,
                expiry_date DATE NOT NULL,
                status TEXT NOT NULL DEFAULT 'current'
                    CHECK (status IN ('current', 'application_submitted', 'received_new')),
                submission_date DATE,
                processing_estimate TEXT,
                photo_filename TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (holder_id) REFERENCES people (id)
            )
        ''')

        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    # Person CRUD operations
    def add_person(self, person: Person) -> int:
        """Add a person and return their ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO people (name, role, birth_date)
            VALUES (?, ?, ?)
        ''', (person.name, person.role, person.birth_date))

        person_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return person_id

    def get_people(self) -> List[Person]:
        """Get all people"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM people ORDER BY role DESC, name')
        rows = cursor.fetchall()
        conn.close()

        people = []
        for row in rows:
            people.append(Person(
                id=row['id'],
                name=row['name'],
                role=row['role'],
                birth_date=datetime.fromisoformat(row['birth_date']).date(),
                created_at=datetime.fromisoformat(row['created_at'])
            ))
        return people

    def get_person(self, person_id: int) -> Optional[Person]:
        """Get a person by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM people WHERE id = ?', (person_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return Person(
                id=row['id'],
                name=row['name'],
                role=row['role'],
                birth_date=datetime.fromisoformat(row['birth_date']).date(),
                created_at=datetime.fromisoformat(row['created_at'])
            )
        return None

    def update_person(self, person: Person):
        """Update a person"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE people
            SET name = ?, role = ?, birth_date = ?
            WHERE id = ?
        ''', (person.name, person.role, person.birth_date, person.id))

        conn.commit()
        conn.close()

    def delete_person(self, person_id: int):
        """Delete a person and their documents"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Delete documents first (foreign key constraint)
        cursor.execute('DELETE FROM documents WHERE holder_id = ?', (person_id,))
        cursor.execute('DELETE FROM people WHERE id = ?', (person_id,))

        conn.commit()
        conn.close()

    # Document CRUD operations
    def add_document(self, document: Document) -> int:
        """Add a document and return its ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Encrypt sensitive document number
        encrypted_number = self.encryption.encrypt(document.document_number)

        cursor.execute('''
            INSERT INTO documents
            (holder_id, type, country, document_number, issue_date, expiry_date,
             status, submission_date, processing_estimate, photo_filename, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            document.holder_id, document.type, document.country, encrypted_number,
            document.issue_date, document.expiry_date, document.status,
            document.submission_date, document.processing_estimate,
            document.photo_filename, document.notes
        ))

        document_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return document_id

    def get_documents(self, holder_id: Optional[int] = None) -> List[Document]:
        """Get documents, optionally filtered by holder"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if holder_id:
            cursor.execute('SELECT * FROM documents WHERE holder_id = ? ORDER BY expiry_date', (holder_id,))
        else:
            cursor.execute('SELECT * FROM documents ORDER BY expiry_date')

        rows = cursor.fetchall()
        conn.close()

        documents = []
        for row in rows:
            # Decrypt document number
            decrypted_number = self.encryption.decrypt(row['document_number'])

            documents.append(Document(
                id=row['id'],
                holder_id=row['holder_id'],
                type=row['type'],
                country=row['country'],
                document_number=decrypted_number,
                issue_date=datetime.fromisoformat(row['issue_date']).date() if row['issue_date'] else None,
                expiry_date=datetime.fromisoformat(row['expiry_date']).date(),
                status=row['status'],
                submission_date=datetime.fromisoformat(row['submission_date']).date() if row['submission_date'] else None,
                processing_estimate=row['processing_estimate'],
                photo_filename=row['photo_filename'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            ))
        return documents

    def get_document(self, document_id: int) -> Optional[Document]:
        """Get a document by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM documents WHERE id = ?', (document_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            decrypted_number = self.encryption.decrypt(row['document_number'])

            return Document(
                id=row['id'],
                holder_id=row['holder_id'],
                type=row['type'],
                country=row['country'],
                document_number=decrypted_number,
                issue_date=datetime.fromisoformat(row['issue_date']).date() if row['issue_date'] else None,
                expiry_date=datetime.fromisoformat(row['expiry_date']).date(),
                status=row['status'],
                submission_date=datetime.fromisoformat(row['submission_date']).date() if row['submission_date'] else None,
                processing_estimate=row['processing_estimate'],
                photo_filename=row['photo_filename'],
                notes=row['notes'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at'])
            )
        return None

    def update_document(self, document: Document):
        """Update a document"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Encrypt document number
        encrypted_number = self.encryption.encrypt(document.document_number)

        cursor.execute('''
            UPDATE documents
            SET holder_id = ?, type = ?, country = ?, document_number = ?,
                issue_date = ?, expiry_date = ?, status = ?, submission_date = ?,
                processing_estimate = ?, photo_filename = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            document.holder_id, document.type, document.country, encrypted_number,
            document.issue_date, document.expiry_date, document.status,
            document.submission_date, document.processing_estimate,
            document.photo_filename, document.notes, document.id
        ))

        conn.commit()
        conn.close()

    def delete_document(self, document_id: int):
        """Delete a document"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM documents WHERE id = ?', (document_id,))
        conn.commit()
        conn.close()

    # Settings operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return json.loads(row['value'])
            except:
                return row['value']
        return default

    def set_setting(self, key: str, value: Any):
        """Set a setting value"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Convert to JSON if not string
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value_str))

        conn.commit()
        conn.close()

    def clear_all_data(self):
        """Clear all data (for demo purposes)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM documents')
        cursor.execute('DELETE FROM people')
        cursor.execute('DELETE FROM settings')

        conn.commit()
        conn.close()

# Global database instance
_db_instance = None

def get_database() -> DatabaseManager:
    """Get global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance