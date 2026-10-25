import json
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from werkzeug.security import generate_password_hash
from app import create_app


class BrowserIngestTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.app=create_app(self.temp.name,True)
        self.client=self.app.test_client()
        with closing(sqlite3.connect(Path(self.temp.name)/"mini_pi.sqlite")) as db:
            with db:
                db.execute("INSERT INTO settings VALUES('browser_token_hash',?)",(json.dumps(generate_password_hash('browser-test-key')),))
                db.execute("INSERT INTO settings VALUES('ingest_token_hash',?)",(json.dumps(generate_password_hash('codex-test-key')),))
        self.headers={"Authorization":"Bearer browser-test-key"}

    def tearDown(self):
        self.temp.cleanup()

    def test_scoped_tokens_cannot_update_other_cards(self):
        self.assertEqual(self.client.post('/api/ingest/browser',json={'cards':[{'id':'grok','value':30}]}).status_code,401)
        wrong={'Authorization':'Bearer codex-test-key'}
        self.assertEqual(self.client.post('/api/ingest/browser',json={'cards':[{'id':'grok','value':30}]},headers=wrong).status_code,401)
        self.assertEqual(self.client.post('/api/ingest/codex',json={'cards':[{'id':'codex_primary','remaining':30}]},headers=self.headers).status_code,401)
        self.assertEqual(self.client.post('/api/ingest/browser',json={'cards':[{'id':'grok','value':30},{'id':'codex_primary','value':20}]},headers=self.headers).status_code,400)
        self.assertIsNone(next(c for c in self.client.get('/api/display').json['cards'] if c['id']=='grok')['value'])

    def test_zero_missing_and_invalid_values_are_distinct(self):
        for value in [None,-1,101,'nan']:
            self.assertEqual(self.client.post('/api/ingest/browser',json={'cards':[{'id':'grok','value':value}]},headers=self.headers).status_code,400)
        payload={'cards':[{'id':'grok','value':0},{'id':'instagram','value':835},{'id':'tiktok','value':953}]}
        self.assertEqual(self.client.post('/api/ingest/browser',json=payload,headers=self.headers).status_code,200)
        cards={c['id']:c for c in self.client.get('/api/display').json['cards']}
        self.assertEqual(cards['grok']['value'],'0')
        self.assertEqual(cards['instagram']['source'],'browser')
        self.assertEqual(self.client.post('/api/ingest/browser',json={'cards':[{'id':'instagram','value':2.5}]},headers=self.headers).status_code,400)

    def test_manual_override_is_preserved(self):
        with closing(sqlite3.connect(Path(self.temp.name)/"mini_pi.sqlite")) as db:
            with db: db.execute("UPDATE cards SET source='manual',value='12' WHERE id='instagram'")
        self.client.post('/api/ingest/browser',json={'cards':[{'id':'instagram','value':835}]},headers=self.headers)
        card=next(c for c in self.client.get('/api/display').json['cards'] if c['id']=='instagram')
        self.assertEqual((card['source'],card['value']),('manual','12'))

    def test_preflight_is_only_enabled_for_extension_origins(self):
        response=self.client.options('/api/ingest/browser',headers={'Origin':'chrome-extension://testid'})
        self.assertEqual(response.headers['Access-Control-Allow-Origin'],'chrome-extension://testid')
        response=self.client.options('/api/ingest/browser',headers={'Origin':'https://unrelated.example'})
        self.assertNotIn('Access-Control-Allow-Origin',response.headers)

    def test_collector_package_requires_admin_and_is_not_cached(self):
        self.assertEqual(self.client.get('/admin/collector-download').status_code,302)
        root=Path(self.temp.name)
        (root/'steel-collector.zip').write_bytes(b'test-only-installer')
        with closing(sqlite3.connect(root/'mini_pi.sqlite')) as db:
            with db:
                db.execute("INSERT INTO settings VALUES('admin_password',?)",(json.dumps(generate_password_hash('test-only-password')),))
                db.execute("INSERT INTO settings VALUES('admin_version',?)",(json.dumps('test-version'),))
        with self.client.session_transaction() as session:
            session['admin']=True
            session['admin_version']='test-version'
        response=self.client.get('/admin/collector-download')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.data,b'test-only-installer')
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        response.close()
