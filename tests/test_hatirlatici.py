"""Sohbetten hatırlatıcı oluşturma testleri."""
import contextlib
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import hatirlatici  # noqa: E402

NOW = datetime(2026, 11, 2, 10, 0)


class HatirlaticiTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('CREATE TABLE reminders (id INTEGER PRIMARY KEY, text TEXT, due TEXT, done INTEGER DEFAULT 0)')
        self.conn.execute('CREATE TABLE ledger (id INTEGER PRIMARY KEY, person TEXT, kind TEXT, amount INTEGER, note TEXT, due TEXT, created TEXT)')
        self.conn.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, note TEXT)')
        self.conn.execute("INSERT INTO accounts(name,note) VALUES ('Ahmet','')")

    def tearDown(self):
        self.conn.close()

    def db(self):
        @contextlib.contextmanager
        def _db():
            yield self.conn
            self.conn.commit()
        return _db()

    def reminders(self):
        return self.conn.execute('SELECT text, due FROM reminders ORDER BY id').fetchall()

    def test_creates_reminder_with_clear_date(self):
        cevap = hatirlatici.direct_reminder_action('yarın 09:00 Ahmeti ara diye hatırlat', self.db, now=NOW)
        self.assertIn('Hatırlatıcı kuruldu', cevap)
        self.assertEqual(self.reminders(), [('Ahmeti ara', '2026-11-03T09:00')])

    def test_ambiguous_date_is_refused(self):
        cevap = hatirlatici.direct_reminder_action('toplantı var diye hatırlat', self.db, now=NOW)
        self.assertIn('anlayamadım', cevap)
        self.assertEqual(self.reminders(), [])

    def test_past_date_is_refused(self):
        cevap = hatirlatici.direct_reminder_action('bugün 08:00 spor diye hatırlat', self.db, now=NOW)
        self.assertIn('geçmişte', cevap)
        self.assertEqual(self.reminders(), [])

    def test_no_intent_returns_none(self):
        self.assertIsNone(hatirlatici.direct_reminder_action('bugün hava güzel', self.db, now=NOW))
        self.assertEqual(self.reminders(), [])

    def test_combined_with_ledger_entry(self):
        cevap = hatirlatici.direct_reminder_action(
            "Ahmete 1.500 TL alacak ekle yarın 09:00'da hatırlat", self.db, now=NOW)
        self.assertIn('kaydedildi', cevap.casefold())
        self.assertIn('Hatırlatıcı kuruldu', cevap)
        kayitlar = self.conn.execute('SELECT person,kind,amount FROM ledger').fetchall()
        self.assertEqual(kayitlar, [('Ahmet', 'receivable', 150000)])
        self.assertEqual(self.reminders(), [('Ahmete 1.500 TL alacak ekle', '2026-11-03T09:00')])

    def test_reminder_tool_via_execute(self):
        import ledger_tools
        cevap = ledger_tools.execute('reminder_create', {'text': 'fatura öde', 'remind_at': '2026-11-05T18:00'},
                                     self.db, 'hatırlat')
        self.assertIn('Kayıt no', cevap)
        self.assertEqual(self.reminders(), [('fatura öde', '2026-11-05T18:00')])

    def test_reminder_tool_rejects_past(self):
        import ledger_tools
        gecmis = (datetime.now() - timedelta(hours=1)).isoformat(timespec='minutes')
        with self.assertRaises(ValueError):
            ledger_tools.execute('reminder_create', {'text': 'x', 'remind_at': gecmis}, self.db, 'hatırlat')


if __name__ == '__main__':
    unittest.main()
