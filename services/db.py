import os
import json
import sqlite3
import uuid
import time
from config import Config

class DatabaseInterface:
    def get(self, collection, doc_id):
        raise NotImplementedError

    def set(self, collection, doc_id, data, merge=False):
        raise NotImplementedError

    def update(self, collection, doc_id, data):
        raise NotImplementedError

    def delete(self, collection, doc_id):
        raise NotImplementedError

    def where(self, collection, field, operator, value):
        raise NotImplementedError

    def get_all(self, collection):
        raise NotImplementedError

class SQLiteDB(DatabaseInterface):
    def __init__(self, db_path='instance/local_data.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                collection TEXT,
                doc_id TEXT,
                data TEXT,
                PRIMARY KEY (collection, doc_id)
            )
        ''')
        conn.commit()
        conn.close()

    def get(self, collection, doc_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('SELECT data FROM documents WHERE collection = ? AND doc_id = ?', (collection, doc_id))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row['data'])
        return None

    def set(self, collection, doc_id, data, merge=False):
        current_data = {}
        if merge:
            current_data = self.get(collection, doc_id) or {}

        current_data.update(data)

        conn = self._get_conn()
        c = conn.cursor()
        c.execute('REPLACE INTO documents (collection, doc_id, data) VALUES (?, ?, ?)',
                  (collection, doc_id, json.dumps(current_data)))
        conn.commit()
        conn.close()
        return current_data

    def update(self, collection, doc_id, data):
        return self.set(collection, doc_id, data, merge=True)

    def delete(self, collection, doc_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('DELETE FROM documents WHERE collection = ? AND doc_id = ?', (collection, doc_id))
        conn.commit()
        conn.close()

    def delete_collection(self, collection):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('DELETE FROM documents WHERE collection = ?', (collection,))
        conn.commit()
        conn.close()

    def where(self, collection, field, operator, value):
        # Naive implementation: fetch all and filter in python
        # Because JSON querying in SQLite requires extensions or complex SQL
        all_docs = self.get_all(collection)
        results = []
        for doc_id, doc in all_docs:
            doc_val = doc.get(field)
            if operator == '==':
                if doc_val == value: results.append(doc)
            elif operator == '>':
                if doc_val is not None and doc_val > value: results.append(doc)
            elif operator == '<':
                if doc_val is not None and doc_val < value: results.append(doc)
            elif operator == '>=':
                if doc_val is not None and doc_val >= value: results.append(doc)
            elif operator == '<=':
                if doc_val is not None and doc_val <= value: results.append(doc)
            elif operator == 'in':
                if doc_val in value: results.append(doc)
        return results

    def get_all(self, collection):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute('SELECT doc_id, data FROM documents WHERE collection = ?', (collection,))
        rows = c.fetchall()
        conn.close()
        return [(row['doc_id'], json.loads(row['data'])) for row in rows]

    def collection(self, collection):
        return CollectionWrapper(self, collection)

class CollectionWrapper:
    def __init__(self, db, name):
        self.db = db
        self.name = name

    def document(self, doc_id=None):
        if not doc_id:
            doc_id = str(uuid.uuid4())
        return DocumentWrapper(self.db, self.name, doc_id)

    def where(self, field, operator, value):
        return self.db.where(self.name, field, operator, value)

    def stream(self):
        results = self.db.get_all(self.name)
        return [DocumentSnapshot(doc_id, data) for doc_id, data in results]

class DocumentWrapper:
    def __init__(self, db, collection, doc_id):
        self.db = db
        self.collection_name = collection
        self.id = doc_id

    def get(self):
        data = self.db.get(self.collection_name, self.id)
        if data:
            return DocumentSnapshot(self.id, data)
        return DocumentSnapshot(self.id, None, exists=False)

    def set(self, data, merge=False):
        self.db.set(self.collection_name, self.id, data, merge)

    def update(self, data):
        self.db.update(self.collection_name, self.id, data)

    def delete(self):
        self.db.delete(self.collection_name, self.id)

    def collection(self, sub_collection_name):
        # Support for subcollections: "users/123/portfolio" -> stored as collection "users/123/portfolio"
        return CollectionWrapper(self.db, f"{self.collection_name}/{self.id}/{sub_collection_name}")

class DocumentSnapshot:
    def __init__(self, doc_id, data, exists=True):
        self.id = doc_id
        self._data = data
        self.exists = exists

    def to_dict(self):
        return self._data

# Firebase Implementation
class FirestoreDB(DatabaseInterface):
    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            cred_path = Config.FIREBASE_CONFIG_PATH
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                print(f"Warning: {cred_path} not found. Firebase will fail if used.")

        self.client = firestore.client()

    def collection(self, collection):
        return self.client.collection(collection)

# Factory
def get_db():
    if Config.DB_TYPE == 'firebase':
        return FirestoreDB()
    else:
        return SQLiteDB()

db = get_db()
