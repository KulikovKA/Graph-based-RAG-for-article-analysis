"""Run the supplied exporter with psycopg and enforced read-only transactions.

Connection credentials come only from the existing container environment.
This wrapper does not print them or start any application services.
"""
import os
import runpy
from pathlib import Path

from sqlalchemy.engine import make_url

url = make_url(os.environ['DATABASE_URL']).set(drivername='postgresql+psycopg')
url = url.update_query_dict({'options': '-c default_transaction_read_only=on', 'connect_timeout': '10'})
os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
runpy.run_path(str(Path(__file__).with_name('export_pilot24.py')), run_name='__main__')
