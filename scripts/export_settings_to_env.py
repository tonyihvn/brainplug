"""Export sensitive settings from the application's database into a .env file.

This script reads settings via the SettingsService and writes sensitive fields
to a `.env` file in the project root. It is interactive and will ask for
confirmation before overwriting an existing `.env`.

Usage:
  python scripts/export_settings_to_env.py
"""
import os
from backend.services.settings_service import SettingsService

ROOT = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(ROOT, '.env')

def gather_env_entries():
    s = SettingsService()
    entries = {}

    # LLM models (store first active google/gemini api key)
    llms = s.get_llm_settings()
    for m in llms:
        mt = (m.get('model_type') or '').lower()
        if mt in ('gemini', 'google') and m.get('api_key'):
            entries['GEMINI_API_KEY'] = m.get('api_key')
            break

    # Database settings - write DATABASE_URL if an active DB exists
    dbs = s.get_database_settings()
    for dbs_item in dbs:
        if dbs_item.get('is_active'):
            db_type = (dbs_item.get('db_type') or '').lower()
            if db_type == 'sqlite':
                entries['DATABASE_URL'] = f"sqlite:///{dbs_item.get('database')}"
            elif db_type == 'mysql':
                entries['DATABASE_URL'] = f"mysql+pymysql://{dbs_item.get('username')}:{dbs_item.get('password')}@{dbs_item.get('host')}:{dbs_item.get('port')}/{dbs_item.get('database')}"
            elif db_type == 'postgresql':
                entries['DATABASE_URL'] = f"postgresql://{dbs_item.get('username')}:{dbs_item.get('password')}@{dbs_item.get('host')}:{dbs_item.get('port')}/{dbs_item.get('database')}"
            break

    # System SMTP/IMAP/POP
    sys = s.get_system_settings()
    smtp = sys.get('smtp')
    imap = sys.get('imap')
    pop = sys.get('pop')

    if smtp:
        entries['SMTP_HOST'] = smtp.get('host','') or ''
        entries['SMTP_PORT'] = str(smtp.get('port','') or '')
        entries['SMTP_USERNAME'] = smtp.get('username','') or ''
        entries['SMTP_PASSWORD'] = smtp.get('password','') or ''

    if imap:
        entries['IMAP_HOST'] = imap.get('host','') or ''
        entries['IMAP_PORT'] = str(imap.get('port','') or '')
        entries['IMAP_USERNAME'] = imap.get('username','') or ''
        entries['IMAP_PASSWORD'] = imap.get('password','') or ''

    if pop:
        entries['POP_HOST'] = pop.get('host','') or ''
        entries['POP_PORT'] = str(pop.get('port','') or '')
        entries['POP_USERNAME'] = pop.get('username','') or ''
        entries['POP_PASSWORD'] = pop.get('password','') or ''

    # API configs - write named keys (not all configs are safe to export)
    apis = s.get_api_configs()
    for idx, a in enumerate(apis):
        name = (a.get('name') or f'API_{idx}').upper().replace(' ', '_')
        if a.get('auth_type') and a.get('auth_value'):
            key = f"{name}_AUTH_VALUE"
            entries[key] = a.get('auth_value')

    return entries

def main():
    entries = gather_env_entries()
    if not entries:
        print('No sensitive settings found to export.')
        return

    print('The following entries will be written to .env:')
    for k, v in entries.items():
        print(f'{k}={"***" if v else ""}')

    if os.path.exists(ENV_PATH):
        print('\n.env already exists at', ENV_PATH)
        ans = input('Overwrite .env? (yes/no) > ')
        if ans.lower() not in ('y','yes'):
            print('Aborting.')
            return

    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        for k, v in entries.items():
            f.write(f'{k}={v}\n')

    print('.env written successfully at', ENV_PATH)

if __name__ == '__main__':
    main()
