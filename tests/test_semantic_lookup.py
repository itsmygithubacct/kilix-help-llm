"""Independent vocabulary for conservative context, intent and cache behavior."""
import gzip
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import test_lexical as fixtures
from help_llm.lexical import QueryTerms, exact_literals, index_words, requested_roles
from help_llm.lookup import Lookup, STOP
from help_llm import prepared


class Fixture(unittest.TestCase):
    setUp = fixtures.RetrievalTest.setUp
    lookup = fixtures.RetrievalTest.lookup


class SemanticTest(Fixture):
    def test_known_words_keep_exact_counts_and_unknown_forms_can_resolve(self):
        terms = QueryTerms({'file', 'files', 'deliver', 'delivering', 'buffer', 'size', 'policy'}, STOP)
        self.assertEqual(terms.words('files delivering'), ['files', 'delivering'])
        self.assertEqual(terms.words('delivered policies'), ['deliver', 'policy'])
        self.assertEqual(terms.words('buffer-size BufferSize'), ['buffer', 'size', 'buffer', 'size'])
        self.assertEqual(terms.words('buffer_size --buffer-size buffer.size'), ['buffer_size', '--buffer-size', 'buffer.size'])
        self.assertEqual(terms.words('buffer-size', ['buffer-size']), ['buffer-size'])

    def test_unknown_inflection_collision_and_negation(self):
        terms = QueryTerms({'ax', 'axe', 'hop', 'hope', 'allow', 'delete'}, STOP)
        self.assertEqual(terms.words('axes hoping disallow'), ['axes', 'hoping', 'disallow'])
        self.assertEqual(terms.words("don't delete; can't allow; no never without"), ['not', 'delete', 'not', 'allow', 'no', 'never', 'without'])
        self.assertEqual(index_words("can't allow", STOP), ['not', 'allow'])

    def test_key_alone_does_not_mean_keyboard(self):
        for question in ('What key contains the object identifier?', 'Which key in the dictionary contains names?', 'Which key adjusts capacity?'):
            self.assertEqual(requested_roles(question), (False, False))
        for question in ('Which keyboard key adjusts capacity?', 'Which shortcut adjusts capacity?', 'What action adjusts capacity?'):
            self.assertEqual(requested_roles(question), (False, True))

    def test_field_request_keeps_source_without_shortcuts(self):
        lookup = self.lookup({'docs/objects.md': '# Object dictionary\n\nThe object key object_names contains the names.\n',
                              'docs/keys.md': '# Keyboard\n\nCtrl+N selects an object.\n'})
        for question in ('Which key contains names in the object dictionary?', 'What key contains the object names?'):
            self.assertIn('docs/objects.md', [p['path'] for p in lookup.search(question)])
        self.assertNotIn('docs/objects.md', [p['path'] for p in lookup.search('Which keyboard key selects an object?')])

    def test_context_names_are_not_literal_requirements(self):
        for question in ('Can asset.copy set retain_mode?', 'Can `asset.copy` set retain_mode?',
                         'For `asset.copy`, does asset.copy accept retain_mode?'):
            self.assertEqual(exact_literals(question), [])
        self.assertEqual(exact_literals('For asset.copy, which field is named `retain_mode`?'), ['retain_mode'])
        self.assertEqual(exact_literals('Explain `retain_mode`.'), ['retain_mode'])
        self.assertEqual(exact_literals('retain_mode'), ['retain_mode'])

    def test_repeated_context_and_required_answer_literal_are_separate(self):
        introduction = ('The asset.copy operation copies assets and accepts a structured options object. '
                        'Clients call asset.copy for each transfer. ' + 'General transfer context. ' * 25)
        raw = '# Asset transfer\n\n' + introduction + '\n\n## Options\n\nThe field retain_mode selects whether to retain a receipt. Set retain_mode=keep to retain it.\n'
        lookup = self.lookup({'docs/transfer.md': raw,
                              'docs/other.md': '# Other operation\n\nThe field retain_mode_extra applies to asset.rename.\n'})
        question = 'For `asset.copy`, which field is named `retain_mode` and selects receipt retention?'
        hits = lookup.search(question)
        self.assertEqual(len(hits), 1)
        self.assertIn('retain_mode=keep', hits[0]['text'])
        self.assertNotIn('asset.copy', hits[0]['text'])
        # Ambiguous contextual requests must not exclude the same support.
        hits = lookup.search('Can `asset.copy` set retain_mode to keep its receipt?')
        self.assertTrue(any('retain_mode=keep' in p['text'] for p in hits))

    def test_required_literal_cannot_be_satisfied_by_alias_or_expansion(self):
        lookup = self.lookup({'docs/a.md': '# Options\n\nThe value retain_mode_extra=keep preserves receipts.\n'},
                             {'fixture:docs/a.md#1': ['For asset.copy, which field is named retain_mode?']})
        self.assertEqual(lookup.search('Which field is named `retain_mode`?'), [])
        self.assertEqual(lookup.search('Which field is named `RETAIN_MODE_EXTRA`?'), [])

    def test_unknown_compound_does_not_change_known_query_ordering(self):
        lookup = self.lookup({'docs/a.md': '# Capacities\n\nA buffer size has a documented bound.\n',
                              'docs/b.md': '# Delivery\n\nDelivering a document preserves its final marker.\n'})
        self.assertEqual(lookup.search('buffer-size'), lookup.search('buffer size'))
        self.assertEqual(lookup.analyzer.words('delivering'), ['delivering'])


class PreparedTest(Fixture):
    def fixture(self):
        return self.lookup({'docs/a.md': '# Storage\n\nThe `cache_limit` setting controls capacity. cache_limit=24. Ctrl+B changes capacity.\n',
                            'docs/b.md': '# Delivery\n\nThe field delivery_mode controls submission.\n'},
                           {'fixture:docs/a.md#1': ['Which setting controls archive capacity?']})

    def test_prepared_and_fallback_results_are_exact_and_repeatable(self):
        fresh = self.fixture()
        self.assertFalse(fresh.prepared_cache_hit)
        output = prepared.prepare(self.root, self.index)
        first = output.read_bytes()
        prepared.prepare(self.root, self.index)
        self.assertEqual(output.read_bytes(), first)
        cached = Lookup(self.root, self.index)
        self.assertTrue(cached.prepared_cache_hit)
        disabled = Lookup(self.root, self.index, use_cache=False)
        self.assertFalse(disabled.prepared_cache_hit)
        for q in ('capacity', 'archive-capacity', 'cache_limit', 'Which setting controls capacity?',
                  'Which field is named `delivery_mode`?', 'Which shortcut changes capacity?',
                  'In the storage page, capacity', 'In missing.md, capacity', "can't submit"):
            self.assertEqual(cached.search(q), fresh.search(q))
            self.assertEqual(cached.search(q), disabled.search(q))

    def test_each_index_input_invalidates_cache(self):
        self.fixture()
        for name in ('sources.json', 'questions.json', 'external.jsonl'):
            with self.subTest(input=name):
                prepared.prepare(self.root, self.index)
                path = self.index / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                self.assertFalse(Lookup(self.root, self.index).prepared_cache_hit)
                path.write_bytes(original)

    def test_changed_or_missing_source_cannot_reuse_questions_or_citations(self):
        self.fixture()
        prepared.prepare(self.root, self.index)
        path = self.root / 'docs/a.md'
        original = path.read_bytes()
        path.write_text('# Storage\n\nuniquenewword.\n')
        lookup = Lookup(self.root, self.index)
        self.assertFalse(lookup.prepared_cache_hit)
        self.assertEqual(lookup.search('archive'), [])
        self.assertEqual(lookup.search('uniquenewword')[0]['commit'], '')
        path.unlink()
        lookup = Lookup(self.root, self.index)
        self.assertFalse(lookup.prepared_cache_hit)
        self.assertEqual(lookup.search('archive'), [])
        path.write_bytes(original)
        self.assertTrue(Lookup(self.root, self.index).prepared_cache_hit)

    def test_schema_and_implementation_bytes_invalidate_cache(self):
        self.fixture()
        prepared.prepare(self.root, self.index)
        with patch.object(prepared, 'VERSION', b'next-schema'):
            self.assertFalse(Lookup(self.root, self.index).prepared_cache_hit)
        read_bytes = Path.read_bytes
        for name in ('lexical.py', 'lookup.py', 'prepared.py'):
            def changed_code(path):
                raw = read_bytes(path)
                return raw + b'\n# changed implementation\n' if path.name == name else raw
            with self.subTest(implementation=name), patch.object(Path, 'read_bytes', changed_code):
                self.assertFalse(Lookup(self.root, self.index).prepared_cache_hit)
        with patch.object(sys.implementation, 'cache_tag', 'other-python-tag'):
            self.assertFalse(Lookup(self.root, self.index).prepared_cache_hit)

    def test_cache_corruption_is_an_in_memory_fallback_without_writes(self):
        fresh = self.fixture()
        path = prepared.prepare(self.root, self.index)
        original = path.read_bytes()
        damaged = bytearray(original)
        damaged[15] ^= 255
        for bad in (b'invalid', original[:24], bytes(damaged), gzip.compress(b'invalid header'),
                    gzip.compress(gzip.decompress(original).replace(b'cache_limit', b'cache_lomit', 1))):
            with self.subTest(size=len(bad)):
                path.write_bytes(bad)
                lookup = Lookup(self.root, self.index)
                self.assertFalse(lookup.prepared_cache_hit)
                self.assertEqual(lookup.search('capacity'), fresh.search('capacity'))
                self.assertEqual(path.read_bytes(), bad)

    def test_valid_checksum_with_invalid_shape_is_rejected(self):
        self.fixture()
        data = prepared.build(self.root, self.index)
        data['constraints']['roles'] = []
        (self.index / prepared.FILENAME).write_bytes(prepared.encode(data, prepared.fingerprint(self.root, self.index)))
        self.assertFalse(Lookup(self.root, self.index).prepared_cache_hit)
