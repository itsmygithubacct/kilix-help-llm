"""Conventional variable definitions and contrary role boundaries."""
from help_llm.lexical import source_roles
from help_llm.lookup import Lookup
from help_llm.prepared import prepare
from test_semantic_lookup import Fixture


class EnvironmentRoleTest(Fixture):
    def test_unlisted_predicates_for_quoted_and_unquoted_subjects(self):
        for name in ('RECEIPT_QUOTA', '`RECEIPT_QUOTA`'):
            for description in ('governs receipt capacity', 'specifies the window',
                                'budgets receipt memory', 'allocates receipt slots',
                                'has a value in kibibytes', 'quantifies the receipt limit'):
                self.assertEqual(source_roles(f'{name} {description}.'), (True, False))

    def test_subject_boundaries_bullets_and_wrapped_prose(self):
        for text in ('The `RECEIPT_QUOTA` governs receipt capacity.',
                     'Receipt limits are configurable. RECEIPT_QUOTA budgets memory.',
                     '- `RECEIPT_QUOTA` quantifies receipt capacity.',
                     '`RECEIPT_QUOTA`\ngoverns receipt capacity.'):
            self.assertEqual(source_roles(text), (True, False), text)

    def test_bare_other_name_shapes_do_not_gain_environment_role(self):
        for text in ('`receipt_quota` governs receipt capacity.',
                     'RECEIPTS govern receipt capacity.',
                     '`Receipt_Quota` governs receipt capacity.',
                     'The report mentions RECEIPT_QUOTA without a definition.',
                     '`RECEIPT_QUOTA`'):
            self.assertEqual(source_roles(text), (False, False), text)

    def test_explicit_output_types_remain_excluded_in_both_orders(self):
        for text in ('The report JSON field `RECEIPT_QUOTA` records receipt capacity.',
                     '`RECEIPT_QUOTA` is a report JSON field for receipt capacity.',
                     'RECEIPT_QUOTA is just an output field for receipt capacity.',
                     'RECEIPT_QUOTA is a constant in the report schema.',
                     'RECEIPT_QUOTA is read-only response data.'):
            self.assertEqual(source_roles(text), (False, False), text)

    def test_negated_setting_types_and_action_names_do_not_gain_role(self):
        for text in ('RECEIPT_QUOTA is not a configuration key.',
                     '`RECEIPT_QUOTA` is not an environment variable.',
                     '`RECEIPT_QUOTA` is not a\nconfiguration option.'):
            self.assertEqual(source_roles(text), (False, False), text)
        self.assertEqual(source_roles('The `SHOW_RECEIPTS` action opens a preview. SHOW_RECEIPTS governs receipt display.'), (False, True))

    def test_independent_setting_evidence_survives_an_output_statement(self):
        text = 'OUTPUT_QUOTA is a JSON field. INPUT_QUOTA governs receipt buffering.'
        self.assertEqual(source_roles(text), (True, False))

    def test_nominal_lookup_retains_definition_and_rejects_report(self):
        lookup = self.lookup({'docs/config.md': '# Receipt capacity\n\n`RECEIPT_QUOTA` governs receipt capacity.\n',
                              'docs/report.md': '# Receipt capacity\n\nThe JSON field `RECEIPT_QUOTA` records receipt capacity.\n'},
                             {'fixture:docs/report.md#1': ['RECEIPT_QUOTA governs receipt capacity.']})
        self.assertEqual([p['path'] for p in lookup.search('Which configuration key controls receipt capacity?')], ['docs/config.md'])

    def test_new_environment_role_matches_cached_and_uncached(self):
        self.lookup({'docs/config.md': '# Receipt capacity\n\nRECEIPT_QUOTA allocates receipt capacity.\n',
                     'docs/report.md': '# Receipt report\n\nRECEIPT_QUOTA is an output field.\n'})
        prepare(self.root, self.index)
        cached = Lookup(self.root, self.index)
        fresh = Lookup(self.root, self.index, use_cache=False)
        self.assertTrue(cached.prepared_cache_hit)
        for question in ('Which setting controls receipt capacity?', 'RECEIPT_QUOTA', 'What does the output field report?'):
            self.assertEqual(cached.search(question), fresh.search(question))
