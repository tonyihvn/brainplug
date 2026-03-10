#!/usr/bin/env python3
"""
Comprehensive cleanup script to remove all orphaned testing data from the app.
This will clean:
1. Orphaned RAG rules and schemas (from deleted databases)
2. Test database files
3. Orphaned ingested data
4. Test instance data
"""
import json
import shutil
from pathlib import Path
from typing import Set, List, Dict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

class OrphanCleanup:
    """Clean up orphaned data in the BrainPlug application."""
    
    def __init__(self, workspace_root: str = None):
        """Initialize with workspace root."""
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent
        else:
            workspace_root = Path(workspace_root)
        
        self.workspace_root = workspace_root
        self.instance_dir = workspace_root / "instance"
        self.rag_db_dir = self.instance_dir / "rag_db"
        self.store_dir = self.instance_dir / "store"
        self.scripts_dir = workspace_root / "scripts"
        self.test_dbs_dir = self.instance_dir / "test_dbs"
        self.ingested_data_dir = self.instance_dir / "ingested_data"
        
        # Status tracking
        self.cleaned_items = {
            'rules_deleted': 0,
            'schemas_deleted': 0,
            'test_dbs_deleted': 0,
            'ingested_data_deleted': 0,
            'test_files_deleted': 0,
            'orphaned_rules': [],
            'orphaned_schemas': [],
            'valid_database_ids': set()
        }
    
    def get_valid_database_ids(self) -> Set[str]:
        """Get all valid database IDs from database_settings."""
        try:
            settings_file = self.store_dir / "database_settings.json"
            if not settings_file.exists():
                return set()
            
            settings_data = json.loads(settings_file.read_text())
            valid_ids = set()
            
            for setting in settings_data:
                if isinstance(setting, dict) and 'id' in setting:
                    valid_ids.add(setting['id'])
            
            logger.info(f"✓ Found {len(valid_ids)} valid database IDs")
            self.cleaned_items['valid_database_ids'] = valid_ids
            return valid_ids
        except Exception as e:
            logger.error(f"Error reading database settings: {e}")
            return set()
    
    def clean_orphaned_rules(self) -> int:
        """Remove rules for deleted databases."""
        try:
            rules_file = self.rag_db_dir / "rules.json"
            if not rules_file.exists():
                return 0
            
            rules_data = json.loads(rules_file.read_text())
            valid_ids = self.cleaned_items['valid_database_ids']
            
            # Separate orphaned from valid rules
            valid_rules = []
            orphaned = []
            
            for rule in rules_data:
                if not isinstance(rule, dict):
                    continue
                
                metadata = rule.get('metadata', {})
                db_id = metadata.get('database_id') or metadata.get('db_id')
                
                if db_id in valid_ids:
                    valid_rules.append(rule)
                else:
                    orphaned.append(rule)
            
            # Write back only valid rules
            rules_file.write_text(json.dumps(valid_rules, indent=2))
            
            count = len(orphaned)
            self.cleaned_items['rules_deleted'] = count
            self.cleaned_items['orphaned_rules'] = [r.get('id') for r in orphaned]
            
            logger.info(f"✓ Deleted {count} orphaned rules")
            return count
        except Exception as e:
            logger.error(f"Error cleaning orphaned rules: {e}")
            return 0
    
    def clean_orphaned_schemas(self) -> int:
        """Remove schemas for deleted databases."""
        try:
            schemas_file = self.rag_db_dir / "schemas.json"
            if not schemas_file.exists():
                return 0
            
            schemas_data = json.loads(schemas_file.read_text())
            valid_ids = self.cleaned_items['valid_database_ids']
            
            # Separate orphaned from valid schemas
            valid_schemas = []
            orphaned = []
            
            for schema in schemas_data:
                if not isinstance(schema, dict):
                    continue
                
                metadata = schema.get('metadata', {})
                db_id = metadata.get('database_id') or metadata.get('db_id')
                
                if db_id in valid_ids:
                    valid_schemas.append(schema)
                else:
                    orphaned.append(schema)
            
            # Write back only valid schemas
            schemas_file.write_text(json.dumps(valid_schemas, indent=2))
            
            count = len(orphaned)
            self.cleaned_items['schemas_deleted'] = count
            self.cleaned_items['orphaned_schemas'] = [s.get('id') for s in orphaned]
            
            logger.info(f"✓ Deleted {count} orphaned schemas")
            return count
        except Exception as e:
            logger.error(f"Error cleaning orphaned schemas: {e}")
            return 0
    
    def clean_test_databases(self) -> int:
        """Remove test database files."""
        try:
            test_db_files = [
                self.store_dir / "test_db_full_flow.db",
                self.store_dir / "test_integration.db",
                self.store_dir / "test_integration_direct.db",
                self.test_dbs_dir / "test_db_full_flow.db",
                self.test_dbs_dir / "test_integration.db",
                self.test_dbs_dir / "test_integration_direct.db",
            ]
            
            count = 0
            for db_file in test_db_files:
                if db_file.exists():
                    db_file.unlink()
                    logger.info(f"  ✓ Deleted: {db_file.name}")
                    count += 1
            
            self.cleaned_items['test_dbs_deleted'] = count
            logger.info(f"✓ Deleted {count} test database files")
            return count
        except Exception as e:
            logger.error(f"Error cleaning test databases: {e}")
            return 0
    
    def clean_orphaned_ingested_data(self) -> int:
        """Remove ingested data directories for deleted databases."""
        try:
            if not self.ingested_data_dir.exists():
                return 0
            
            valid_ids = self.cleaned_items['valid_database_ids']
            count = 0
            
            for item in self.ingested_data_dir.iterdir():
                if item.is_dir():
                    # Directory name should match a valid database ID
                    db_id = item.name
                    if db_id not in valid_ids:
                        shutil.rmtree(item)
                        logger.info(f"  ✓ Deleted directory: {item.name}/")
                        count += 1
                elif item.is_file() and item.name.startswith('ingested_data_'):
                    # These are JSON backups of ingested data
                    # Extract database ID from filename
                    db_id = item.name.replace('ingested_data_', '').replace('.json', '')
                    if db_id not in valid_ids:
                        item.unlink()
                        logger.info(f"  ✓ Deleted file: {item.name}")
                        count += 1
            
            self.cleaned_items['ingested_data_deleted'] = count
            logger.info(f"✓ Deleted {count} orphaned ingested data entries")
            return count
        except Exception as e:
            logger.error(f"Error cleaning orphaned ingested data: {e}")
            return 0
    
    def clean_test_files(self) -> int:
        """Remove test script output files."""
        try:
            test_files = [
                self.workspace_root / "test_error_messages.py",
                self.workspace_root / "test_rag_display_and_statistics.py",
                self.workspace_root / "test_rag_error_handling.py",
                self.workspace_root / "verify_rag_error_handling.py",
                self.workspace_root / "verify_rag_implementation.py",
            ]
            
            count = 0
            for test_file in test_files:
                # Only remove if it's clearly a test/verify script
                if test_file.exists() and (
                    test_file.name.startswith('test_') or 
                    test_file.name.startswith('verify_')
                ):
                    test_file.unlink()
                    logger.info(f"  ✓ Deleted: {test_file.name}")
                    count += 1
            
            self.cleaned_items['test_files_deleted'] = count
            logger.info(f"✓ Deleted {count} test files")
            return count
        except Exception as e:
            logger.error(f"Error cleaning test files: {e}")
            return 0
    
    def clean_test_documentation(self) -> int:
        """Remove test/temporary documentation files."""
        try:
            doc_files = [
                self.workspace_root / "RAG_ERROR_HANDLING_COMPLETE.md",
                self.workspace_root / "RAG_ERROR_HANDLING_FIX.md",
                self.workspace_root / "RAG_ERROR_HANDLING_QUICKREF.md",
                self.workspace_root / "DATA_INGESTION_IMPLEMENTATION.md",
                self.workspace_root / "DATA_INGESTION_ARCHITECTURE.md",
                self.workspace_root / "DATA_INGESTION_QUICK_REFERENCE.md",
                self.workspace_root / "IMPLEMENTATION_VERIFICATION.md",
            ]
            
            count = 0
            for doc_file in doc_files:
                if doc_file.exists() and doc_file.is_file():
                    doc_file.unlink()
                    logger.info(f"  ✓ Deleted: {doc_file.name}")
                    count += 1
            
            return count
        except Exception as e:
            logger.error(f"Error cleaning test documentation: {e}")
            return 0
    
    def run_full_cleanup(self, remove_docs: bool = False) -> Dict:
        """Run complete cleanup."""
        logger.info("=" * 70)
        logger.info("STARTING COMPREHENSIVE CLEANUP")
        logger.info("=" * 70)
        
        # Step 1: Get valid database IDs
        logger.info("\n[1/5] Scanning valid database IDs...")
        self.get_valid_database_ids()
        
        # Step 2: Clean orphaned rules
        logger.info("\n[2/5] Cleaning orphaned RAG rules...")
        self.clean_orphaned_rules()
        
        # Step 3: Clean orphaned schemas
        logger.info("\n[3/5] Cleaning orphaned RAG schemas...")
        self.clean_orphaned_schemas()
        
        # Step 4: Clean test databases
        logger.info("\n[4/5] Cleaning test database files...")
        self.clean_test_databases()
        
        # Step 5: Clean orphaned ingested data
        logger.info("\n[5/5] Cleaning orphaned ingested data...")
        self.clean_orphaned_ingested_data()
        
        # Optional: Clean test files and docs
        logger.info("\n[OPTIONAL] Cleaning test files...")
        self.clean_test_files()
        
        if remove_docs:
            logger.info("\n[OPTIONAL] Cleaning temporary documentation...")
            self.clean_test_documentation()
        
        return self.cleaned_items
    
    def print_summary(self):
        """Print cleanup summary."""
        logger.info("\n" + "=" * 70)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✓ Valid databases kept: {len(self.cleaned_items['valid_database_ids'])}")
        logger.info(f"✓ Orphaned rules deleted: {self.cleaned_items['rules_deleted']}")
        logger.info(f"✓ Orphaned schemas deleted: {self.cleaned_items['schemas_deleted']}")
        logger.info(f"✓ Test databases deleted: {self.cleaned_items['test_dbs_deleted']}")
        logger.info(f"✓ Orphaned ingested data deleted: {self.cleaned_items['ingested_data_deleted']}")
        logger.info(f"✓ Test files deleted: {self.cleaned_items['test_files_deleted']}")
        
        total = (
            self.cleaned_items['rules_deleted'] +
            self.cleaned_items['schemas_deleted'] +
            self.cleaned_items['test_dbs_deleted'] +
            self.cleaned_items['ingested_data_deleted'] +
            self.cleaned_items['test_files_deleted']
        )
        logger.info(f"\n✓ TOTAL ITEMS CLEANED: {total}")
        logger.info("=" * 70)


def main():
    """Main cleanup entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up orphaned data from BrainPlug')
    parser.add_argument(
        '--workspace',
        default=None,
        help='Workspace root directory (auto-detected if not provided)'
    )
    parser.add_argument(
        '--remove-docs',
        action='store_true',
        help='Also remove temporary documentation files'
    )
    
    args = parser.parse_args()
    
    try:
        cleanup = OrphanCleanup(args.workspace)
        cleanup.run_full_cleanup(remove_docs=args.remove_docs)
        cleanup.print_summary()
        logger.info("\n✓ Cleanup completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Cleanup failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
