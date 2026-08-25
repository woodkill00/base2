import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.python.operations_telemetry import AlertLedger, TelemetryError, diagnostic_bundle, event


class OperationsTelemetryTests(unittest.TestCase):
    def test_log_metric_trace_attributes_are_redacted_and_bounded(self):
        item = event(
            kind='adapter', level='error', code='provider.timeout', correlation_id='request-0001',
            attributes={'authorization': 'Bearer exposed', 'message': 'token=exposed', 'nested': {'password': 'bad'}},
        )
        encoded = json.dumps(item)
        self.assertNotIn('exposed', encoded)
        self.assertNotIn('bad', encoded)
        self.assertEqual('[REDACTED]', item['attributes']['authorization'])
        with self.assertRaisesRegex(TelemetryError, 'classification'):
            event(kind='unknown', level='info', code='bad.code', correlation_id='request-0001', attributes={})
        with self.assertRaisesRegex(TelemetryError, 'correlation'):
            event(kind='health', level='info', code='health.ok', correlation_id='../bad', attributes={})

    def test_incident_alerts_once_then_emits_one_recovery(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'private' / 'alerts.json'
            ledger = AlertLedger(path)
            self.assertTrue(ledger.observe(incident_id='incident-0001', failing=True, code='queue.stalled')['notify'])
            self.assertFalse(ledger.observe(incident_id='incident-0001', failing=True, code='queue.stalled')['notify'])
            self.assertTrue(ledger.observe(incident_id='incident-0001', failing=False, code='queue.recovered')['notify'])
            self.assertFalse(ledger.observe(incident_id='incident-0001', failing=False, code='queue.recovered')['notify'])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)

    def test_safe_diagnostic_bundle_covers_health_queue_and_adapter_faults(self):
        item = event(kind='queue', level='warning', code='queue.backpressure', correlation_id='request-0002', attributes={'depth': 99})
        result = diagnostic_bundle(
            source_commit='a' * 40, boot_id='boot-id-0001', events=[item],
            health={'api': 'degraded'}, queues={'outbox': 99}, adapters={'payment': 'disabled', 'secret': 'never'},
        )
        self.assertEqual(64, len(result['digest']))
        self.assertEqual('[REDACTED]', result['adapters']['secret'])
        with self.assertRaisesRegex(TelemetryError, 'events'):
            diagnostic_bundle(source_commit='a' * 40, boot_id='boot-id-0001', events=[{}], health={}, queues={}, adapters={})

    def test_corrupt_or_unsafe_alert_state_fails_closed(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'alerts.json'
            path.write_text('{bad', encoding='utf-8')
            with self.assertRaisesRegex(TelemetryError, 'state_invalid'):
                AlertLedger(path).observe(incident_id='incident-0001', failing=True, code='api.failed')


if __name__ == '__main__':
    unittest.main()
