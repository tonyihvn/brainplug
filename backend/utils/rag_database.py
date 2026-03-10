"""RAG database wrapper.

This module prefers Qdrant as the vector database (recommended for production/local Docker).
If a Qdrant server or the client library is not available, it falls back to a
lightweight file-backed store (JSON) that supports the same API but without
semantic vector search.

Notes:
- To use Qdrant: run a local Qdrant server (Docker recommended) and set
  `QDRANT_URL` (e.g. 'http://localhost:6333') or rely on default localhost.
- The fallback is convenient for development and CI when installing native
  dependencies is difficult.
"""
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


# Try Qdrant first
QDRANT_AVAILABLE = False
try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False

# Try ChromaDB
CHROMADB_AVAILABLE = False
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except Exception:
    CHROMADB_AVAILABLE = False

# Try sentence-transformers for embeddings (optional)
# NOTE: Lazy-load the embedder to avoid blocking on model download during app startup
EMBEDDING_AVAILABLE = False
_embedder = None
SENTENCE_TRANSFORMER_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMER_AVAILABLE = False

def get_embedder():
    """Lazily load and return the embedder instance."""
    global _embedder, EMBEDDING_AVAILABLE
    if _embedder is None and SENTENCE_TRANSFORMER_AVAILABLE:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading SentenceTransformer embedder on first use...")
            _embedder = SentenceTransformer('all-MiniLM-L6-v2')
            EMBEDDING_AVAILABLE = True
            logger.info("✓ SentenceTransformer embedder loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            EMBEDDING_AVAILABLE = False
    return _embedder


class RAGDatabase:
    """RAG database with pluggable backend (Qdrant preferred, JSON fallback)."""

    def __init__(self, persist_dir: str = "instance/rag_db"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.use_chroma = False
        self.chroma = None
        self.use_qdrant = False
        self.qdrant = None

        # JSON fallback files
        self._schemas_file = self.persist_dir / "schemas.json"
        self._rules_file = self.persist_dir / "rules.json"
        self._settings_file = self.persist_dir / "database_settings.json"

        # Load or initialize fallback stores
        for f in (self._schemas_file, self._rules_file, self._settings_file):
            if not f.exists():
                f.write_text("[]")

        # Prefer ChromaDB if available
        if CHROMADB_AVAILABLE:
            try:
                self.chroma = chromadb.Client()
                # ensure collections exist
                for coll in ('schemas', 'business_rules', 'database_settings'):
                    try:
                        self.chroma.get_collection(coll)
                    except Exception:
                        try:
                            self.chroma.create_collection(coll)
                        except Exception:
                            pass
                self.use_chroma = True
                logger.info("✓ ChromaDB client initialized (will use ChromaDB)")
            except Exception as e:
                logger.warning(f"ChromaDB init failed, falling back: {e}")
                self.use_chroma = False

        # If Chroma not available, try Qdrant
        if not self.use_chroma and QDRANT_AVAILABLE:
            try:
                import os
                qdrant_host = os.environ.get('QDRANT_URL', 'http://localhost:6333')
                # QdrantClient will accept either host/port or url
                self.qdrant = QdrantClient(url=qdrant_host)
                # Ensure collections exist
                try:
                    existing = self.qdrant.get_collections()
                    existing_names = set(existing.collections.keys())
                except Exception:
                    existing_names = set()
                for coll in ('schemas', 'business_rules', 'database_settings'):
                    try:
                        if coll not in existing_names:
                            # create collection with a default vector size
                            size = 384 if coll != 'database_settings' else 1
                            self.qdrant.recreate_collection(collection_name=coll, vectors_config=qmodels.VectorsConfig(size=size, distance=qmodels.Distance.COSINE))
                    except Exception:
                        # ignore if creation fails
                        pass

                # If we reach here, Qdrant client is usable
                self.use_qdrant = True
                logger.info("✓ Qdrant client initialized (will use Qdrant if server reachable)")
            except Exception as e:
                logger.warning(f"Qdrant client init failed, falling back to JSON store: {e}")
                self.use_qdrant = False
        else:
            logger.info("Qdrant client not installed; using JSON fallback for RAG storage")

    # ----------------- Embeddings -----------------
    def _embed_text(self, text: str) -> Optional[List[float]]:
        try:
            embedder = get_embedder()
            if embedder is not None:
                v = embedder.encode(text)
                return v.tolist() if hasattr(v, 'tolist') else list(map(float, v))
        except Exception as e:
            logger.debug(f"Embedding failed: {e}")
        return None

    # ----------------- Helpers for JSON fallback -----------------
    def _read_json(self, path: Path) -> List[Dict[str, Any]]:
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    def _write_json(self, path: Path, data: List[Dict[str, Any]]):
        path.write_text(json.dumps(data, indent=2))

    # ----------------- Schemas -----------------
    def add_schema(self, table_name: str, schema_content: str, db_id: str) -> bool:
        item_id = f"{db_id}_{table_name}_schema"
        metadata = {
            'table_name': table_name,
            'type': 'schema',
            'database_id': db_id,
            'category': f"{table_name}_schema"
        }

        embedding = self._embed_text(schema_content)

        # Prefer ChromaDB if available
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('schemas')
                if embedding is not None:
                    coll.add(ids=[item_id], documents=[schema_content], metadatas=[metadata], embeddings=[embedding])
                else:
                    coll.add(ids=[item_id], documents=[schema_content], metadatas=[metadata])
                logger.debug(f"Added schema to ChromaDB: {item_id}")
                return True
            except Exception as e:
                logger.error(f"Error adding schema to ChromaDB: {e}")

        if self.use_qdrant and self.qdrant:
            try:
                vectors_payload = [embedding if embedding is not None else [0.0]]
                self.qdrant.upsert(collection_name='schemas', points=[qmodels.PointStruct(id=item_id, vector=vectors_payload[0], payload={**metadata, 'content': schema_content})])
                logger.debug(f"Added schema to Qdrant: {item_id}")
                return True
            except Exception as e:
                logger.error(f"Error adding schema to Qdrant: {e}")
                # fall through to JSON fallback

        # JSON fallback
        try:
            items = self._read_json(self._schemas_file)
            # remove existing with same id
            items = [i for i in items if i.get('id') != item_id]
            items.append({'id': item_id, 'content': schema_content, 'metadata': metadata, 'embedding': embedding})
            self._write_json(self._schemas_file, items)
            logger.debug(f"Saved schema to JSON fallback: {item_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving schema fallback: {e}")
            return False

    # ----------------- Database settings -----------------
    def save_database_setting(self, setting_id: str, setting: Dict[str, Any]) -> Dict[str, Any]:
        # Attempt to save into Qdrant payload collection (as metadata)
        doc = {**setting}
        doc_id = str(setting_id)
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('database_settings')
                # store the setting as a document and keep full dict in metadata
                coll.add(ids=[doc_id], documents=[json.dumps(doc)], metadatas=[doc])
                logger.debug(f"Saved database setting to ChromaDB: {setting.get('name')}")
                return setting
            except Exception as e:
                logger.warning(f"Failed to save setting to ChromaDB, falling back: {e}")

        if self.use_qdrant and self.qdrant:
            try:
                # store minimal vector to satisfy qdrant; store full setting in payload
                v = [0.0]
                self.qdrant.upsert(collection_name='database_settings', points=[qmodels.PointStruct(id=doc_id, vector=v, payload=doc)])
                logger.debug(f"Saved database setting to Qdrant: {setting.get('name')}")
                return setting
            except Exception as e:
                logger.warning(f"Failed to save setting to Qdrant, falling back: {e}")

        # JSON fallback
        try:
            items = self._read_json(self._settings_file)
            items = [i for i in items if i.get('id') != doc_id]
            items.append(doc)
            self._write_json(self._settings_file, items)
            logger.debug(f"Saved database setting to JSON fallback: {setting.get('name')}")
            return setting
        except Exception as e:
            logger.error(f"Error saving database setting fallback: {e}")
            return setting

    def save_setting(self, setting_id: str, setting: Dict[str, Any]) -> Dict[str, Any]:
        """Generic save for arbitrary settings (LLM models, API configs, etc.).

        Stores the payload into the `database_settings` collection/payload store or
        writes to the JSON fallback file.
        """
        doc = {**setting}
        doc_id = str(setting_id)

        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('database_settings')
                coll.add(ids=[doc_id], documents=[json.dumps(doc)], metadatas=[doc])
                logger.debug(f"Saved generic setting to ChromaDB: {doc.get('name')}")
                return setting
            except Exception as e:
                logger.warning(f"Failed to save generic setting to ChromaDB, falling back: {e}")

        if self.use_qdrant and self.qdrant:
            try:
                v = [0.0]
                self.qdrant.upsert(collection_name='database_settings', points=[qmodels.PointStruct(id=doc_id, vector=v, payload=doc)])
                logger.debug(f"Saved generic setting to Qdrant: {doc.get('name')}")
                return setting
            except Exception as e:
                logger.warning(f"Failed to save generic setting to Qdrant, falling back: {e}")

        try:
            items = self._read_json(self._settings_file)
            items = [i for i in items if i.get('id') != doc_id]
            items.append(doc)
            self._write_json(self._settings_file, items)
            logger.debug(f"Saved generic setting to JSON fallback: {doc.get('name')}")
            return setting
        except Exception as e:
            logger.error(f"Error saving generic setting fallback: {e}")
            return setting

    def get_database_setting(self, setting_id: str) -> Optional[Dict[str, Any]]:
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('database_settings')
                res = coll.get(ids=[str(setting_id)])
                # result format: dict with 'metadatas' and 'documents'
                if res and res.get('metadatas'):
                    md = res['metadatas'][0]
                    return md
            except Exception:
                pass

        if self.use_qdrant and self.qdrant:
            try:
                res = self.qdrant.retrieve(collection_name='database_settings', ids=[str(setting_id)])
                if res and res[0].payload:
                    return res[0].payload
            except Exception:
                pass

        items = self._read_json(self._settings_file)
        for it in items:
            if it.get('id') == str(setting_id):
                return it
        return None

    def get_all_database_settings(self) -> List[Dict[str, Any]]:
        # Try ChromaDB
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('database_settings')
                res = coll.get(include=['metadatas', 'documents', 'ids'])
                items = []
                for md in (res.get('metadatas') or []):
                    items.append(md)
                return items
            except Exception:
                pass

        if self.use_qdrant and self.qdrant:
            try:
                col = self.qdrant.get_collection(collection_name='database_settings')
            except Exception:
                pass

        return self._read_json(self._settings_file)

    def delete_database_setting(self, setting_id: str) -> bool:
        """Delete database setting and ALL associated data (rules, schemas, ingested data)."""
        try:
            # Delete from database_settings collection
            if self.use_qdrant and self.qdrant:
                try:
                    self.qdrant.delete(collection_name='database_settings', point_ids=[str(setting_id)])
                except Exception:
                    pass
            
            # Delete ALL rules for this database
            self._delete_all_rules_for_database(setting_id)
            
            # Delete ALL schemas for this database
            self._delete_all_schemas_for_database(setting_id)
            
            # Delete all ingested data associated with this database
            self._delete_ingested_data_for_database(setting_id)
            
            # Delete from JSON fallback
            try:
                items = self._read_json(self._settings_file)
                new_items = [i for i in items if i.get('id') != str(setting_id)]
                self._write_json(self._settings_file, new_items)
            except Exception as e:
                logger.warning(f"Error deleting from JSON settings: {e}")
            
            logger.info(f"✓ Deleted database setting and all associated data: {setting_id}")
            return True
        except Exception as e:
            logger.error(f"Error in cascade delete for database setting: {e}")
            return False
    
    def _delete_all_rules_for_database(self, database_id: str) -> bool:
        """Delete ALL rules for a database from all backends (except JSON rules file).)
        
        NOTE: rules.json is NOT deleted - it's preserved until user explicitly deletes database.
        """
        try:
            if self.use_qdrant and self.qdrant:
                try:
                    self.qdrant.delete(
                        collection_name='business_rules',
                        points_selector=qmodels.FilterSelector(
                            filter=qmodels.Filter(
                                must=[
                                    qmodels.FieldCondition(
                                        key="metadata.database_id",
                                        match=qmodels.MatchValue(value=database_id)
                                    )
                                ]
                            )
                        )
                    )
                    logger.debug(f"Deleted all rules for database from Qdrant: {database_id}")
                except Exception as e:
                    logger.debug(f"Could not delete rules from Qdrant: {e}")
            
            # NOTE: Do NOT clean JSON fallback (rules.json) - preserve for user
            logger.debug(f"Preserved rules.json for database: {database_id}")
            
            return True
        except Exception as e:
            logger.warning(f"Error deleting all rules for database {database_id}: {e}")
            return False
    
    def _delete_all_schemas_for_database(self, database_id: str) -> bool:
        """Delete ALL schemas for a database from all backends."""
        try:
            if self.use_qdrant and self.qdrant:
                try:
                    self.qdrant.delete(
                        collection_name='schemas',
                        points_selector=qmodels.FilterSelector(
                            filter=qmodels.Filter(
                                must=[
                                    qmodels.FieldCondition(
                                        key="metadata.database_id",
                                        match=qmodels.MatchValue(value=database_id)
                                    )
                                ]
                            )
                        )
                    )
                    logger.debug(f"Deleted all schemas for database from Qdrant: {database_id}")
                except Exception as e:
                    logger.debug(f"Could not delete schemas from Qdrant: {e}")
            
            # Also clean JSON fallback
            try:
                schemas = self._read_json(self._schemas_file)
                filtered_schemas = []
                for schema in schemas:
                    metadata = schema.get('metadata', {})
                    db_id = metadata.get('database_id') or metadata.get('db_id')
                    if db_id != database_id:
                        filtered_schemas.append(schema)
                self._write_json(self._schemas_file, filtered_schemas)
                logger.debug(f"Cleaned schemas from JSON store: {database_id}")
            except Exception as e:
                logger.debug(f"Could not clean schemas from JSON: {e}")
            
            return True
        except Exception as e:
            logger.warning(f"Error deleting all schemas for database {database_id}: {e}")
            return False
    
    def _delete_ingested_data_for_database(self, database_id: str) -> bool:
        """Delete all ingested data (vectors and raw data) for a database."""
        try:
            deleted_count = 0
            
            if self.use_qdrant and self.qdrant:
                try:
                    # List all collections that might contain ingested data
                    collections = self.qdrant.get_collections()
                    for collection in collections.collections:
                        collection_name = collection.name
                        # Delete vectors with filter on database_id
                        if collection_name.startswith('ingested_'):
                            try:
                                self.qdrant.delete(
                                    collection_name=collection_name,
                                    points_selector=qmodels.FilterSelector(
                                        filter=qmodels.Filter(
                                            must=[
                                                qmodels.FieldCondition(
                                                    key="metadata.database_id",
                                                    match=qmodels.MatchValue(value=database_id)
                                                )
                                            ]
                                        )
                                    )
                                )
                                logger.debug(f"✓ Deleted ingested data from collection: {collection_name}")
                                deleted_count += 1
                            except Exception as e:
                                logger.debug(f"Could not delete from collection {collection_name}: {e}")
                except Exception as e:
                    logger.debug(f"Could not access Qdrant collections: {e}")
            
            # Delete file-based raw data backups (JSON format)
            try:
                raw_data_file = Path(self.persist_dir) / f"ingested_data_{database_id}.json"
                if raw_data_file.exists():
                    raw_data_file.unlink()
                    logger.debug(f"✓ Deleted raw ingested data file: {raw_data_file.name}")
                    deleted_count += 1
            except Exception as e:
                logger.debug(f"Could not delete raw data file: {e}")
            
            # Delete directory-based ingested data (created by ingestion pipeline)
            try:
                import shutil
                ingested_dir = Path(self.persist_dir.parent) / "ingested_data" / database_id
                if ingested_dir.exists():
                    shutil.rmtree(ingested_dir)
                    logger.debug(f"✓ Deleted ingested data directory: {ingested_dir.name}/")
                    deleted_count += 1
            except Exception as e:
                logger.debug(f"Could not delete ingested data directory: {e}")
            
            if deleted_count > 0:
                logger.info(f"✓ Cleaned up {deleted_count} ingested data entries for database: {database_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting ingested data: {e}")
            return False
    
    def delete_ingested_data_for_table(self, database_id: str, table_name: str) -> bool:
        """Delete ingested data for a specific table in a database."""
        try:
            if self.use_qdrant and self.qdrant:
                collections = self.qdrant.get_collections()
                for collection in collections.collections:
                    collection_name = collection.name
                    if collection_name.startswith('ingested_'):
                        try:
                            self.qdrant.delete(
                                collection_name=collection_name,
                                points_selector=qmodels.FilterSelector(
                                    filter=qmodels.Filter(
                                        must=[
                                            qmodels.FieldCondition(
                                                key="metadata.database_id",
                                                match=qmodels.MatchValue(value=database_id)
                                            ),
                                            qmodels.FieldCondition(
                                                key="metadata.table_name",
                                                match=qmodels.MatchValue(value=table_name)
                                            )
                                        ]
                                    )
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Could not delete table data from {collection_name}: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting table ingested data: {e}")
            return False

    # ----------------- Business rules -----------------
    def add_business_rule(self, rule_name: str, rule_content: str, db_id: str,
                          rule_type: str = "optional", category: str = None, meta_type: str = None) -> bool:
        # Create unique rule_id that includes meta_type to avoid overwriting when both relationship and sample_data exist for same table
        type_suffix = f"_{meta_type}" if meta_type else ""
        rule_id = f"{category or rule_name}{type_suffix}_rule"
        metadata = {
            'rule_name': rule_name,
            'rule_type': rule_type,
            # allow callers to specify a semantic type (e.g. 'sample_data') stored in metadata['type']
            'type': meta_type if meta_type is not None else 'rule',
            'database_id': db_id,
            'category': category or rule_name,
            'is_active': True,
            'name': rule_name  # Add 'name' field to metadata for easier querying/display
        }

        emb = self._embed_text(rule_content)
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('business_rules')
                if emb is not None:
                    coll.add(ids=[rule_id], documents=[rule_content], metadatas=[metadata], embeddings=[emb])
                else:
                    coll.add(ids=[rule_id], documents=[rule_content], metadatas=[metadata])
                return True
            except Exception as e:
                logger.error(f"Error adding business rule to ChromaDB: {e}")

        if self.use_qdrant and self.qdrant:
            try:
                vec = emb if emb is not None else [0.0]
                self.qdrant.upsert(collection_name='business_rules', points=[qmodels.PointStruct(id=rule_id, vector=vec, payload={**metadata, 'content': rule_content})])
                return True
            except Exception as e:
                logger.error(f"Error adding business rule to Qdrant: {e}")

        try:
            items = self._read_json(self._rules_file)
            items = [i for i in items if i.get('id') != rule_id]
            items.append({'id': rule_id, 'content': rule_content, 'metadata': metadata, 'embedding': emb})
            self._write_json(self._rules_file, items)
            return True
        except Exception as e:
            logger.error(f"Error saving business rule fallback: {e}")
            return False

    # ----------------- Querying -----------------
    def query_schemas(self, query: str, n_results: int = 5) -> List[Dict]:
        # Semantic search using vectors if available, otherwise substring matching
        emb = self._embed_text(query)
        # Try ChromaDB semantic query
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('schemas')
                # chroma returns dicts with lists inside
                res = coll.query(query_texts=[query], n_results=n_results)
                items = []
                docs = res.get('documents', [[]])[0]
                mds = res.get('metadatas', [[]])[0]
                ids = res.get('ids', [[]])[0]
                for i, d in enumerate(docs):
                    items.append({'id': ids[i] if ids and i < len(ids) else None, 'content': d, 'metadata': mds[i] if mds and i < len(mds) else {}})
                return items
            except Exception as e:
                logger.debug(f"ChromaDB query failed: {e}")

        if self.use_qdrant and self.qdrant and emb is not None:
            try:
                res = self.qdrant.search(collection_name='schemas', query_vector=emb, limit=n_results)
                items = []
                for hit in res:
                    items.append({'id': str(hit.id), 'content': hit.payload.get('content'), 'metadata': hit.payload})
                return items
            except Exception as e:
                logger.debug(f"Qdrant query failed: {e}")

        # Fallback: substring search in stored contents
        items = self._read_json(self._schemas_file)
        matches = [i for i in items if query.lower() in (i.get('content') or '').lower()]
        return matches[:n_results]

    def query_rules(self, query: str, n_results: int = 10) -> List[Dict]:
        emb = self._embed_text(query)
        if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
            try:
                coll = self.chroma.get_collection('business_rules')
                res = coll.query(query_texts=[query], n_results=n_results)
                items = []
                docs = res.get('documents', [[]])[0]
                mds = res.get('metadatas', [[]])[0]
                ids = res.get('ids', [[]])[0]
                for i, d in enumerate(docs):
                    items.append({'id': ids[i] if ids and i < len(ids) else None, 'content': d, 'metadata': mds[i] if mds and i < len(mds) else {}})
                return items
            except Exception as e:
                logger.debug(f"ChromaDB rules query failed: {e}")

        if self.use_qdrant and self.qdrant and emb is not None:
            try:
                res = self.qdrant.search(collection_name='business_rules', query_vector=emb, limit=n_results)
                items = []
                for hit in res:
                    items.append({'id': str(hit.id), 'content': hit.payload.get('content'), 'metadata': hit.payload})
                return items
            except Exception as e:
                logger.debug(f"Qdrant rules query failed: {e}")

        items = self._read_json(self._rules_file)
        matches = [i for i in items if query.lower() in (i.get('content') or '').lower()]
        return matches[:n_results]

    # ----------------- Get all / delete -----------------
    def get_all_schemas(self) -> List[Dict]:
        if self.use_qdrant and self.qdrant:
            try:
                # Qdrant does not have a simple list-points API in all clients; fall back to JSON if needed
                pass
            except Exception:
                pass
        return self._read_json(self._schemas_file)

    def get_all_rules(self) -> List[Dict]:
        if self.use_qdrant and self.qdrant:
            try:
                pass
            except Exception:
                pass
        return self._read_json(self._rules_file)
    
    def get_rule(self, rule_id: str) -> Optional[Dict]:
        """Get a single rule by ID."""
        try:
            rules = self.get_all_rules()
            return next((r for r in rules if r.get('id') == rule_id), None)
        except Exception as e:
            logger.error(f"Error getting rule {rule_id}: {str(e)}")
            return None

    def delete_schema(self, table_name: str) -> bool:
        item_id = f"{table_name}_schema"
        if self.use_qdrant and self.qdrant:
            try:
                self.qdrant.delete(collection_name='schemas', point_ids=[item_id])
                return True
            except Exception:
                pass
        try:
            items = self._read_json(self._schemas_file)
            new_items = [i for i in items if i.get('id') != item_id]
            self._write_json(self._schemas_file, new_items)
            return True
        except Exception as e:
            logger.error(f"Error deleting schema fallback: {e}")
            return False

    def delete_rule(self, rule_id: str) -> bool:
        if self.use_qdrant and self.qdrant:
            try:
                self.qdrant.delete(collection_name='business_rules', point_ids=[rule_id])
                return True
            except Exception:
                pass
        try:
            items = self._read_json(self._rules_file)
            new_items = [i for i in items if i.get('id') != rule_id]
            self._write_json(self._rules_file, new_items)
            return True
        except Exception as e:
            logger.error(f"Error deleting rule fallback: {e}")
            return False

    def update_rule(self, rule_id: str, rule_content: str, rule_name: str = None, **metadata) -> bool:
        """Update an existing business rule by deleting and re-adding it."""
        try:
            # Get old rule first
            items = self._read_json(self._rules_file)
            old_rule = next((i for i in items if i.get('id') == rule_id), None)
            if not old_rule:
                logger.warning(f"Rule {rule_id} not found for update")
                return False
            
            # Preserve metadata if not provided
            old_metadata = old_rule.get('metadata', {})
            updated_metadata = {**old_metadata, **metadata}
            if rule_name:
                updated_metadata['rule_name'] = rule_name
            
            # Delete old rule
            self.delete_rule(rule_id)
            
            # Re-add with updated content
            emb = self._embed_text(rule_content)
            
            if getattr(self, 'use_chroma', False) and getattr(self, 'chroma', None):
                try:
                    coll = self.chroma.get_collection('business_rules')
                    if emb is not None:
                        coll.add(ids=[rule_id], documents=[rule_content], metadatas=[updated_metadata], embeddings=[emb])
                    else:
                        coll.add(ids=[rule_id], documents=[rule_content], metadatas=[updated_metadata])
                    return True
                except Exception as e:
                    logger.error(f"Error updating business rule in ChromaDB: {e}")
            
            if self.use_qdrant and self.qdrant:
                try:
                    vec = emb if emb is not None else [0.0]
                    from qdrant_client import models as qmodels
                    self.qdrant.upsert(collection_name='business_rules', points=[qmodels.PointStruct(id=rule_id, vector=vec, payload={**updated_metadata, 'content': rule_content})])
                    return True
                except Exception as e:
                    logger.error(f"Error updating business rule in Qdrant: {e}")
            
            # Fallback: JSON store
            try:
                items = self._read_json(self._rules_file)
                items.append({'id': rule_id, 'content': rule_content, 'metadata': updated_metadata, 'embedding': emb})
                self._write_json(self._rules_file, items)
                return True
            except Exception as e:
                logger.error(f"Error updating business rule fallback: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error in update_rule: {str(e)}")
            return False

    def health_check(self) -> Dict[str, Any]:
        if self.use_qdrant and self.qdrant:
            try:
                collections = self.qdrant.get_collections()
                # provide a minimal health summary
                return {'available': True, 'collections': list(collections.collections.keys())}
            except Exception as e:
                return {'available': False, 'error': str(e)}

        # fallback stats
        schemas = len(self._read_json(self._schemas_file))
        rules = len(self._read_json(self._rules_file))
        return {'available': False, 'schemas': schemas, 'rules': rules, 'persist_dir': str(self.persist_dir)}

