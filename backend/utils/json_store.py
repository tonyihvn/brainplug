"""Local JSON-based storage for settings, RAG items, and business rules."""
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class JSONStore:
    """Persistent JSON storage for configurations and RAG data."""
    
    def __init__(self, store_dir: str = "instance/store"):
        """Initialize JSON store with directory for storage files."""
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths for different data types
        self.db_settings_file = self.store_dir / "database_settings.json"
        self.llm_settings_file = self.store_dir / "llm_models.json"
        self.api_configs_file = self.store_dir / "api_configs.json"
        self.rag_items_file = self.store_dir / "rag_items.json"
        self.business_rules_file = self.store_dir / "business_rules.json"
        
        # Initialize files if they don't exist
        self._init_files()
    
    def _init_files(self):
        """Initialize JSON files if they don't exist."""
        files = [
            self.db_settings_file,
            self.llm_settings_file,
            self.api_configs_file,
            self.rag_items_file,
            self.business_rules_file,
        ]
        
        for file_path in files:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump([], f, indent=2)
                logger.info(f"Created {file_path.name}")
    
    def _read_file(self, file_path: Path) -> List[Dict]:
        """Read JSON file safely."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []
    
    def _write_file(self, file_path: Path, data: List[Dict]):
        """Write JSON file safely."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            raise
    
    # Database Settings Management
    def get_database_settings(self) -> List[Dict]:
        """Get all database settings."""
        return self._read_file(self.db_settings_file)
    
    def get_database_setting(self, db_id: str) -> Optional[Dict]:
        """Get database setting by ID."""
        settings = self.get_database_settings()
        return next((s for s in settings if s.get('id') == db_id), None)
    
    def get_active_database(self) -> Optional[Dict]:
        """Get the active database setting."""
        settings = self.get_database_settings()
        return next((s for s in settings if s.get('is_active')), None)
    
    def add_database_setting(self, name: str, db_type: str, host: str, port: int, 
                            database: str, username: str, password: str, is_active: bool = False) -> Dict:
        """Add a new database setting."""
        settings = self.get_database_settings()
        
        # If this is being set as active, deactivate others
        if is_active:
            for s in settings:
                s['is_active'] = False
        
        new_setting = {
            'id': str(uuid.uuid4()),
            'name': name,
            'db_type': db_type,
            'host': host,
            'port': port,
            'database': database,
            'username': username,
            'password': password,
            'is_active': is_active,
            'created_at': datetime.utcnow().isoformat()
        }
        
        settings.append(new_setting)
        self._write_file(self.db_settings_file, settings)
        logger.info(f"Added database setting: {name}")
        return new_setting
    
    def update_database_setting(self, db_id: str, **kwargs) -> Optional[Dict]:
        """Update database setting."""
        settings = self.get_database_settings()
        setting = next((s for s in settings if s.get('id') == db_id), None)
        
        if not setting:
            return None
        
        # If activating this one, deactivate others
        if kwargs.get('is_active') and not setting.get('is_active'):
            for s in settings:
                s['is_active'] = False
        
        # Update fields
        for key, value in kwargs.items():
            if key in setting:
                setting[key] = value
        
        setting['updated_at'] = datetime.utcnow().isoformat()
        self._write_file(self.db_settings_file, settings)
        logger.info(f"Updated database setting: {setting.get('name')}")
        return setting
    
    def delete_database_setting(self, db_id: str) -> bool:
        """Delete database setting."""
        settings = self.get_database_settings()
        initial_len = len(settings)
        settings = [s for s in settings if s.get('id') != db_id]
        
        if len(settings) < initial_len:
            self._write_file(self.db_settings_file, settings)
            logger.info(f"Deleted database setting: {db_id}")
            return True
        return False
    
    # LLM Models Management
    def get_llm_models(self) -> List[Dict]:
        """Get all LLM models."""
        models = self._read_file(self.llm_settings_file)
        return sorted(models, key=lambda x: x.get('priority', 999))
    
    def get_llm_model(self, model_id: str) -> Optional[Dict]:
        """Get LLM model by ID."""
        models = self.get_llm_models()
        return next((m for m in models if m.get('id') == model_id), None)
    
    def get_active_llm_model(self) -> Optional[Dict]:
        """Get the first active LLM model (by priority)."""
        models = self.get_llm_models()
        return next((m for m in models if m.get('is_active')), None)
    
    def add_llm_model(self, name: str, model_type: str, model_id: str, 
                     api_key: Optional[str] = None, api_endpoint: Optional[str] = None,
                     priority: int = 0, is_active: bool = True, config: Optional[Dict] = None) -> Dict:
        """Add a new LLM model."""
        models = self.get_llm_models()
        
        new_model = {
            'id': str(uuid.uuid4()),
            'name': name,
            'model_type': model_type,
            'model_id': model_id,
            'api_key': api_key,
            'api_endpoint': api_endpoint,
            'priority': priority,
            'is_active': is_active,
            'config': config or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        models.append(new_model)
        self._write_file(self.llm_settings_file, models)
        logger.info(f"Added LLM model: {name}")
        return new_model
    
    def update_llm_model(self, model_id: str, **kwargs) -> Optional[Dict]:
        """Update LLM model."""
        models = self.get_llm_models()
        model = next((m for m in models if m.get('id') == model_id), None)
        
        if not model:
            return None
        
        for key, value in kwargs.items():
            if key in model:
                model[key] = value
        
        model['updated_at'] = datetime.utcnow().isoformat()
        self._write_file(self.llm_settings_file, models)
        logger.info(f"Updated LLM model: {model.get('name')}")
        return model
    
    def delete_llm_model(self, model_id: str) -> bool:
        """Delete LLM model."""
        models = self.get_llm_models()
        initial_len = len(models)
        models = [m for m in models if m.get('id') != model_id]
        
        if len(models) < initial_len:
            self._write_file(self.llm_settings_file, models)
            logger.info(f"Deleted LLM model: {model_id}")
            return True
        return False
    
    # API Configs Management
    def get_api_configs(self) -> List[Dict]:
        """Get all API configurations."""
        return self._read_file(self.api_configs_file)
    
    def get_api_config(self, config_id: str) -> Optional[Dict]:
        """Get API config by ID."""
        configs = self.get_api_configs()
        return next((c for c in configs if c.get('id') == config_id), None)
    
    def add_api_config(self, name: str, api_type: str, endpoint: str, 
                      method: str = 'GET', headers: Optional[Dict] = None,
                      auth_type: Optional[str] = None, auth_value: Optional[str] = None,
                      params_template: Optional[Dict] = None) -> Dict:
        """Add API configuration."""
        configs = self.get_api_configs()
        
        new_config = {
            'id': str(uuid.uuid4()),
            'name': name,
            'api_type': api_type,
            'endpoint': endpoint,
            'method': method,
            'headers': headers or {},
            'auth_type': auth_type,
            'auth_value': auth_value,
            'params_template': params_template or {},
            'created_at': datetime.utcnow().isoformat()
        }
        
        configs.append(new_config)
        self._write_file(self.api_configs_file, configs)
        logger.info(f"Added API config: {name}")
        return new_config
    
    def update_api_config(self, config_id: str, **kwargs) -> Optional[Dict]:
        """Update API configuration."""
        configs = self.get_api_configs()
        config = next((c for c in configs if c.get('id') == config_id), None)
        
        if not config:
            return None
        
        for key, value in kwargs.items():
            if key in config:
                config[key] = value
        
        config['updated_at'] = datetime.utcnow().isoformat()
        self._write_file(self.api_configs_file, configs)
        logger.info(f"Updated API config: {config.get('name')}")
        return config
    
    def delete_api_config(self, config_id: str) -> bool:
        """Delete API configuration."""
        configs = self.get_api_configs()
        initial_len = len(configs)
        configs = [c for c in configs if c.get('id') != config_id]
        
        if len(configs) < initial_len:
            self._write_file(self.api_configs_file, configs)
            logger.info(f"Deleted API config: {config_id}")
            return True
        return False
    
    # RAG Items Management
    def get_rag_items(self, category: Optional[str] = None) -> List[Dict]:
        """Get RAG items, optionally filtered by category."""
        items = self._read_file(self.rag_items_file)
        if category:
            items = [i for i in items if i.get('category') == category]
        return sorted(items, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def get_rag_item(self, item_id: str) -> Optional[Dict]:
        """Get RAG item by ID."""
        items = self.get_rag_items()
        return next((i for i in items if i.get('id') == item_id), None)
    
    def add_rag_item(self, category: str, title: str, content: str, 
                    source: str = 'manual') -> Dict:
        """Add RAG item."""
        items = self.get_rag_items()
        
        new_item = {
            'id': str(uuid.uuid4()),
            'category': category,
            'title': title,
            'content': content,
            'source': source,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        items.append(new_item)
        self._write_file(self.rag_items_file, items)
        logger.info(f"Added RAG item: {title}")
        return new_item
    
    def add_rag_items_batch(self, items_data: List[Dict]) -> List[Dict]:
        """Add multiple RAG items at once."""
        items = self.get_rag_items()
        now = datetime.utcnow().isoformat()
        
        new_items = []
        for item_data in items_data:
            new_item = {
                'id': str(uuid.uuid4()),
                'category': item_data.get('category'),
                'title': item_data.get('title'),
                'content': item_data.get('content'),
                'source': item_data.get('source', 'manual'),
                'created_at': now,
                'updated_at': now
            }
            items.append(new_item)
            new_items.append(new_item)
        
        self._write_file(self.rag_items_file, items)
        logger.info(f"Added {len(new_items)} RAG items")
        return new_items
    
    def update_rag_item(self, item_id: str, **kwargs) -> Optional[Dict]:
        """Update RAG item."""
        items = self.get_rag_items()
        item = next((i for i in items if i.get('id') == item_id), None)
        
        if not item:
            return None
        
        for key, value in kwargs.items():
            if key in item:
                item[key] = value
        
        item['updated_at'] = datetime.utcnow().isoformat()
        self._write_file(self.rag_items_file, items)
        logger.info(f"Updated RAG item: {item.get('title')}")
        return item
    
    def delete_rag_item(self, item_id: str) -> bool:
        """Delete RAG item."""
        items = self.get_rag_items()
        initial_len = len(items)
        items = [i for i in items if i.get('id') != item_id]
        
        if len(items) < initial_len:
            self._write_file(self.rag_items_file, items)
            logger.info(f"Deleted RAG item: {item_id}")
            return True
        return False
    
    def clear_rag_items(self, category: Optional[str] = None) -> int:
        """Clear RAG items, optionally by category."""
        items = self.get_rag_items()
        initial_len = len(items)
        
        if category:
            items = [i for i in items if i.get('category') != category]
        else:
            items = []
        
        self._write_file(self.rag_items_file, items)
        deleted = initial_len - len(items)
        logger.info(f"Cleared {deleted} RAG items")
        return deleted
    
    # Business Rules Management
    def get_business_rules(self, active_only: bool = False) -> List[Dict]:
        """Get business rules."""
        rules = self._read_file(self.business_rules_file)
        if active_only:
            rules = [r for r in rules if r.get('is_active')]
        return sorted(rules, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def get_business_rule(self, rule_id: str) -> Optional[Dict]:
        """Get business rule by ID."""
        rules = self.get_business_rules()
        return next((r for r in rules if r.get('id') == rule_id), None)
    
    def add_business_rule(self, name: str, rule_type: str, content: str,
                         description: Optional[str] = None, category: Optional[str] = None,
                         is_active: bool = True) -> Dict:
        """Add business rule."""
        rules = self.get_business_rules()
        
        new_rule = {
            'id': str(uuid.uuid4()),
            'name': name,
            'description': description,
            'rule_type': rule_type,
            'content': content,
            'category': category,
            'is_active': is_active,
            'created_at': datetime.utcnow().isoformat()
        }
        
        rules.append(new_rule)
        self._write_file(self.business_rules_file, rules)
        logger.info(f"Added business rule: {name}")
        return new_rule
    
    def add_business_rules_batch(self, rules_data: List[Dict]) -> List[Dict]:
        """Add multiple business rules at once."""
        rules = self.get_business_rules()
        now = datetime.utcnow().isoformat()
        
        new_rules = []
        for rule_data in rules_data:
            new_rule = {
                'id': str(uuid.uuid4()),
                'name': rule_data.get('name'),
                'description': rule_data.get('description'),
                'rule_type': rule_data.get('rule_type'),
                'content': rule_data.get('content'),
                'category': rule_data.get('category'),
                'is_active': rule_data.get('is_active', True),
                'created_at': now
            }
            rules.append(new_rule)
            new_rules.append(new_rule)
        
        self._write_file(self.business_rules_file, rules)
        logger.info(f"Added {len(new_rules)} business rules")
        return new_rules
    
    def update_business_rule(self, rule_id: str, **kwargs) -> Optional[Dict]:
        """Update business rule."""
        rules = self.get_business_rules()
        rule = next((r for r in rules if r.get('id') == rule_id), None)
        
        if not rule:
            return None
        
        for key, value in kwargs.items():
            if key in rule:
                rule[key] = value
        
        self._write_file(self.business_rules_file, rules)
        logger.info(f"Updated business rule: {rule.get('name')}")
        return rule
    
    def delete_business_rule(self, rule_id: str) -> bool:
        """Delete business rule."""
        rules = self.get_business_rules()
        initial_len = len(rules)
        rules = [r for r in rules if r.get('id') != rule_id]
        
        if len(rules) < initial_len:
            self._write_file(self.business_rules_file, rules)
            logger.info(f"Deleted business rule: {rule_id}")
            return True
        return False
