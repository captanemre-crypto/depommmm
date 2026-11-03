"""Ledger tool unit tests (stdlib unittest; no extra dependencies)."""
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ledger_tools  # noqa: E402


class LedgerToolsTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('CREATE TABLE ledger (id INTEGER PRIMARY KEY, person TEXT, kind TEXT, amount INTEGER, note TEXT, due TEXT, created TEXT)')
        self.conn.execute('CREATE TABLE accounts (id INTEGER PRIMARY KEY, name TEXT, note TEXT)')
        self.conn.execute('CREATE TABLE reminders (id INTEGER PRIMARY KEY, text TEXT, due TEXT, done INTEGER DEFAULT 0)')

    def tearDown(self):
        self.conn.close()

    def db(self):
        # `with db() as c` deseni: sunucudaki sözleşmenin aynısı.
        import contextlib

        @contextlib.contextmanager
        def _db():
            yield self.conn
            self.conn.commit()

        return _db()

    def rows(self):
        return self.conn.execute('SELECT person, kind, amount FROM ledger ORDER BY id').fetchall()

    def test_ledger_record_with_explicit_amount(self):
        reply = ledger_tools.execute('ledger_record', {'person': 'Ahmet', 'kind': 'receivable', 'amount_kurus': 150000},
                                     self.db, 'Ahmete 1500 TL alacak kaydet')
        self.assertIn('Kaydedildi', reply)
        self.assertEqual(self.rows(), [('Ahmet', 'receivable', 150000)])

    def test_ledger_record_rejects_amount_not_in_utterance(self):
        with self.assertRaises(ValueError):
            ledger_tools.execute('ledger_record', {'person': 'Ahmet', 'kind': 'receivable', 'amount_kurus': 999900},
                                 self.db, 'Ahmete 1500 TL alacak kaydet')
        self.assertEqual(self.rows(), [])

    def test_ledger_record_rejects_person_missing_from_utterance(self):
        with self.assertRaises(ValueError):
            ledger_tools.execute('ledger_record', {'person': 'Mehmet', 'kind': 'payable', 'amount_kurus': 10000},
                                 self.db, 'Ahmete 100 TL borç yaz')
        self.assertEqual(self.rows(), [])

    def test_ledger_record_requires_explicit_request(self):
        with self.assertRaises(ValueError):
            ledger_tools.execute('ledger_record', {'person': 'Ahmet', 'kind': 'receivable', 'amount_kurus': 10000},
                                 self.db, 'Ahmet 100 TL alacağı var mı?')
        self.assertEqual(self.rows(), [])

    def test_tahsil_creates_received_entry(self):
        """'tahsil' kelimesi 'sil' içerdiği için silme sanılıyordu (sessiz veri kaybı)."""
        self.conn.execute("INSERT INTO accounts(name,note) VALUES ('Ahmet','')")
        self.conn.commit()
        reply = ledger_tools.direct_ledger_action('Ahmetten 250 TL tahsil ettim', self.db)
        self.assertIn('tahsilat', reply.lower())
        self.assertEqual(self.rows(), [('Ahmet', 'received', 25000)])

    def test_thousand_separators_supported(self):
        self.conn.execute("INSERT INTO accounts(name,note) VALUES ('Ahmet','')")
        self.conn.commit()
        reply = ledger_tools.direct_ledger_action('Ahmete 1.000.000 TL alacak ekle', self.db)
        self.assertIn('kaydedildi', reply.lower())
        self.assertEqual(self.rows(), [('Ahmet', 'receivable', 100000000)])

    def test_multiple_amounts_refused(self):
        self.conn.execute("INSERT INTO accounts(name,note) VALUES ('Ahmet','')")
        self.conn.commit()
        reply = ledger_tools.direct_ledger_action('Ahmete 100 TL alacak ekle ve 200 TL verecek ekle', self.db)
        self.assertIn('tek tek', reply.lower())
        self.assertEqual(self.rows(), [])

    def test_parse_amount_variants(self):
        cases = {'1.250,50': 125050, '1250,50': 125050, '1.000.000': 100000000,
                 '1500': 150000, '1.500': 150000, '1.50': 150, '0,01': 1}
        for raw, expected in cases.items():
            self.assertEqual(ledger_tools.parse_amount(raw), expected, raw)
        for bad in ('', 'abc', '-5', '0', '1.234,567'):
            with self.assertRaises(ValueError, msg=bad):
                ledger_tools.parse_amount(bad)

    def test_ledger_list_totals(self):
        self.conn.executemany(
            'INSERT INTO ledger(person,kind,amount,note,due,created) VALUES (?,?,?,?,?,?)',
            [('Ahmet', 'receivable', 10000, '', None, '2026-01-01T10:00:00'),
             ('Ahmet', 'received', 4000, '', None, '2026-01-02T10:00:00')])
        reply = ledger_tools.execute('ledger_list', {'person': 'ahmet'}, self.db, 'Ahmet bakiyesi')
        self.assertIn('Ahmet', reply)
        self.assertIn('60,00', reply)

    def test_ledger_list_empty(self):
        self.assertIn('bulunamadı', ledger_tools.execute('ledger_list', {}, self.db, 'defter'))

    def test_direct_action_creates_unique_entry(self):
        self.conn.execute("INSERT INTO accounts(name,note) VALUES ('Ahmet','')")
        self.conn.commit()
        reply = ledger_tools.direct_ledger_action('Ahmete 250 TL alacak ekle', self.db)
        self.assertIn('kaydedildi', reply.lower())
        self.assertEqual(self.rows(), [('Ahmet', 'receivable', 25000)])

    def test_direct_action_unknown_account(self):
        reply = ledger_tools.direct_ledger_action('Veliye 100 TL alacak ekle', self.db)
        self.assertIn('bulamadım', reply)
        self.assertEqual(self.rows(), [])

    def test_direct_action_ignores_plain_chat(self):
        self.assertIsNone(ledger_tools.direct_ledger_action('Bugün hava çok güzel', self.db))

    def test_create_account_from_text(self):
        reply = ledger_tools.create_account_from_text('Ahmet Yılmaz adında yeni hesap oluştur', self.db)
        self.assertIn('oluşturdum', reply)
        names = [r[0] for r in self.conn.execute('SELECT name FROM accounts')]
        self.assertEqual(names, ['Ahmet Yılmaz'])

    def test_create_account_requires_amount_when_entry_requested(self):
        reply = ledger_tools.create_account_from_text('Ayşe adında hesap aç ve alacak kaydet', self.db)
        self.assertIn('tutarı', reply)
        self.assertEqual(len([r for r in self.conn.execute('SELECT name FROM accounts')]), 0)


if __name__ == '__main__':
    unittest.main()
