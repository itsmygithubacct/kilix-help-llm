"""Page identity and setting noun/verb regressions with independent vocabulary."""
import json
from help_llm.lexical import requested_roles
from help_llm.lookup import Lookup
from help_llm.prepared import prepare
from test_semantic_lookup import Fixture


class FilteringTest(Fixture):
    def test_unlisted_descriptors_do_not_rename_a_known_guide(self):
        lookup = self.lookup({'docs/transfers.md': '# Transfer reference\n\nA parcel has a maximum of 512 bytes.\n',
                              'docs/overview.md': '# Overview\n\nTransfers move parcels.\n'})
        plain = lookup.search('From the transfers guide, what is the maximum parcel size?')
        self.assertEqual([p['path'] for p in plain], ['docs/transfers.md'])
        for adjective in ('concise', 'annotated', 'exhaustive', 'newly revised', 'unfamiliar'):
            with self.subTest(descriptor=adjective):
                self.assertEqual(lookup.search(f'From the {adjective} transfers guide, what is the maximum parcel size?'), plain)

    def test_longer_existing_page_name_wins_over_its_suffix(self):
        lookup = self.lookup({'docs/transfers.md': '# Transfer reference\n\nA parcel has a maximum of 512 bytes.\n',
                              'docs/advanced-transfers.md': '# Advanced reference\n\nA parcel has a maximum of 2048 bytes.\n'})
        hits = lookup.search('From the concise advanced transfers guide, what is the maximum parcel size?')
        self.assertEqual([p['path'] for p in hits], ['docs/advanced-transfers.md'])

    def test_path_scope_disambiguates_duplicate_basenames(self):
        lookup = self.lookup({'docs/alpha/transfers.md': '# Transfer reference\n\nA parcel has a maximum of 512 bytes.\n',
                              'docs/beta/transfers.md': '# Transfer reference\n\nA parcel has a maximum of 2048 bytes.\n'})
        for scope in ('alpha', 'beta'):
            hits = lookup.search(f'From the annotated {scope} transfers guide, what is the maximum parcel size?')
            self.assertEqual([p['path'] for p in hits], [f'docs/{scope}/transfers.md'])
        self.assertEqual({p['path'] for p in lookup.search('From the transfers guide, maximum parcel size')},
                         {'docs/alpha/transfers.md', 'docs/beta/transfers.md'})

    def test_explicit_filename_and_unknown_names_remain_constraints(self):
        lookup = self.lookup({'docs/transfers.md': '# Transfer reference\n\nA parcel has a maximum of 512 bytes.\n'})
        self.assertEqual([p['path'] for p in lookup.search('From transfers.md, maximum parcel size')], ['docs/transfers.md'])
        for question in ('From the nonexistent guide, maximum parcel size', 'From missing.md, maximum parcel size'):
            self.assertEqual(lookup.search(question), [])

    def test_recognized_source_label_is_not_discarded_as_a_descriptor(self):
        lookup = self.lookup({'docs/alpha.md': '# Alpha reference\n\nA parcel holds 512 bytes.\n',
                              'docs/transfers.md': '# Transfer reference\n\nA parcel holds 2048 bytes.\n'})
        records = json.loads((self.index / 'sources.json').read_text())
        for record in records:
            record['label'] = 'north' if record['path'] == 'docs/alpha.md' else 'south'
        (self.index / 'sources.json').write_text(json.dumps(records))
        lookup = Lookup(self.root, self.index)
        self.assertEqual(lookup.search('From the concise north transfers guide, how many bytes?'), [])
        self.assertEqual([p['path'] for p in lookup.search('From the concise south transfers guide, how many bytes?')], ['docs/transfers.md'])

    def test_setting_as_verb_does_not_request_a_configuration_definition(self):
        for question in ('Does setting preview_flag to true request a preview?',
                         'What does setting preview_flag do?', 'What happens after setting preview_flag?',
                         'Can I check a request by setting preview_flag to true?',
                         'Does setting the preview flag change execution?'):
            self.assertEqual(requested_roles(question), (False, False), question)

    def test_nominal_setting_requests_keep_the_role_requirement(self):
        for question in ('Which setting controls memory?', 'Which buffer setting controls memory?',
                         'What configuration key controls memory?', 'Show the memory setting',
                         'Which setting changes memory after setting preview_flag to true?'):
            self.assertEqual(requested_roles(question), (True, False), question)
        self.assertEqual(requested_roles('Which setting and shortcut control memory?'), (True, True))

    def test_structured_field_and_configuration_definition_remain_distinct(self):
        lookup = self.lookup({'docs/requests.md': '# Transfer requests\n\nThe structured field "preview_flag": true requests an optional preview.\n',
                              'docs/config.md': '# Preview configuration\n\n`preview_limit` sets the preview capacity.\n'})
        for verb in ('assigning', 'setting'):
            hits = lookup.search(f'Does {verb} preview_flag to true request an optional preview?')
            self.assertEqual(hits[0]['path'], 'docs/requests.md')
        hits = lookup.search('Which setting controls preview capacity?')
        self.assertEqual([p['path'] for p in hits], ['docs/config.md'])

    def test_new_page_metadata_is_identical_through_prepared_cache(self):
        fresh = self.lookup({'docs/alpha/transfers.md': '# Transfer reference\n\nThe field "preview_flag": true requests an optional preview.\n',
                             'docs/advanced-transfers.md': '# Advanced reference\n\n`preview_limit` sets the capacity.\n'})
        prepare(self.root, self.index)
        cached = Lookup(self.root, self.index)
        self.assertTrue(cached.prepared_cache_hit)
        for q in ('From the annotated alpha transfers guide, does setting preview_flag request a preview?',
                  'From the concise advanced transfers guide, which setting controls capacity?',
                  'From the nonexistent guide, preview capacity'):
            self.assertEqual(fresh.search(q), cached.search(q))
