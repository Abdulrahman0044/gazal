"""Local configuration loading. Process/hosting secrets always take precedence."""
import os
from pathlib import Path
from dotenv import load_dotenv
ROOT=Path(__file__).parent
if os.getenv('GAZAL_ENV','development')!='production':
    load_dotenv(ROOT/'.env.local',override=False)
    load_dotenv(ROOT/'.env',override=False)

def production_errors():
    if os.getenv('GAZAL_ENV')!='production':return []
    errors=[]
    if not os.getenv('SUPABASE_DB_URL'):errors.append('SUPABASE_DB_URL is required in production')
    cert=os.getenv('SUPABASE_SSLROOTCERT')
    if not cert or not Path(cert).is_file():errors.append('A valid SUPABASE_SSLROOTCERT file is required in production')
    if not os.getenv('GAZAL_PUBLIC_URL','').startswith('https://'):errors.append('GAZAL_PUBLIC_URL must use HTTPS in production')
    hosts=os.getenv('GAZAL_ALLOWED_HOSTS','')
    if not hosts or '*' in hosts:errors.append('Set explicit GAZAL_ALLOWED_HOSTS in production')
    return errors

def validate_runtime():
    errors=production_errors()
    if errors:raise RuntimeError('Invalid production configuration: '+'; '.join(errors))
