import environment
"""Public project identifier; database credentials belong in backend secrets."""
import os
SUPABASE_URL=os.getenv('SUPABASE_URL','https://xjezlymsqusvuzrvbaru.supabase.co').rstrip('/')
