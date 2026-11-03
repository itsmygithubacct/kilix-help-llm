"""Setting declarations establish roles without a descriptive-verb whitelist."""
import json
from help_llm.lexical import source_roles
from help_llm.lookup import Lookup
from help_llm.prepared import prepare
from test_semantic_lookup import Fixture


class SettingRoleTest(Fixture):
    def test_typed_declarations_do_not_depend_on_the_predicate(self):
        for role in ('environment variable', 'configuration key', 'config option', 'setting'):
            for description in ('governs the receipt window', 'specifies its width',
                                'defines its width', 'reserves space', 'budgets memory',
                                'has a value in kibibytes', 'provides a receipt limit'):
                text = f'The {role} `RECEIPT_WINDOW` {description}.'
                self.assertEqual(source_roles(text), (True, False), text)

    def test_name_then_type_and_affirmative_copula(self):
        for text in ('The `RECEIPT_WINDOW` environment variable governs receipt capacity.',
                     '`receipt_window` is a configuration key for receipt capacity.',
                     '`receipt_window` is an environment variable for receipt capacity.',
                     '`receipt_window` is the setting for receipt capacity.'):
            self.assertEqual(source_roles(text), (True, False), text)

    def test_conditional_plural_and_unquoted_environment_names(self):
        for text in ('If the environment variable RECEIPT_WINDOW is present, its value is used.',
                     'The configuration variables `receipt_window` and `receipt_limit` govern buffering.',
                     'Environment variable: `RECEIPT_WINDOW` names the receipt window.',
                     'RECEIPT_WINDOW is an environment variable for the receipt limit.'):
            self.assertEqual(source_roles(text), (True, False), text)

    def test_negated_declarations_do_not_supply_a_setting_role(self):
        for text in ('This is not a configuration key `receipt_window`.',
                     'There is no environment variable RECEIPT_WINDOW.',
                     '`receipt_window` is not a setting.',
                     '`receipt_window` is not the configuration option.',
                     "This isn't the configuration variable `receipt_window`."):
            self.assertEqual(source_roles(text), (False, False), text)

    def test_output_fields_and_actions_remain_distinct(self):
        for text in ('The report JSON field `receipt_window` records the window; it is output data, not a configuration option.',
                     'The output field `receipt_window` records the configuration key name.',
                     '`receipt_window` is a structured request field for previews.'):
            self.assertEqual(source_roles(text), (False, False), text)
        self.assertEqual(source_roles('The `show_receipts` action controls receipt display.'), (False, True))
        self.assertEqual(source_roles('map ctrl+r show_receipts'), (False, True))

    def test_typed_setting_and_action_can_coexist(self):
        text = ('The configuration key `receipt_window` budgets receipt memory. '
                'The `show_receipts` action opens a preview.')
        self.assertEqual(source_roles(text), (True, True))

    def test_nominal_request_retrieves_typed_definition_not_output(self):
        lookup = self.lookup({'docs/settings.md': '# Receipt settings\n\nThe configuration variable `receipt_window` governs receipt capacity.\n',
                              'docs/report.md': '# Receipt report\n\nThe report JSON field `receipt_window` records receipt capacity.\n',
                              'docs/actions.md': '# Receipt actions\n\nThe `show_receipts` action controls receipt capacity display.\n'})
        self.assertEqual([p['path'] for p in lookup.search('Which configuration key controls receipt capacity?')], ['docs/settings.md'])

    def test_expansion_questions_do_not_create_declaration_evidence(self):
        self.lookup({'docs/report.md': '# Receipt report\n\nThe JSON field `receipt_window` records receipt capacity.\n'})
        qpath = self.index / 'questions.json'
        qpath.write_text(json.dumps({'fixture:docs/report.md#1': ['The environment variable `receipt_window` governs receipt capacity.']}))
        lookup = Lookup(self.root, self.index)
        self.assertEqual(lookup.search('Which configuration key controls receipt capacity?'), [])

    def test_cached_and_uncached_new_roles_agree(self):
        self.lookup({'docs/settings.md': '# Receipt settings\n\nThe environment variable `RECEIPT_WINDOW` governs receipt capacity.\n',
                     'docs/report.md': '# Receipt report\n\nThe report JSON field `receipt_window` records receipt capacity.\n'})
        prepare(self.root, self.index)
        cached = Lookup(self.root, self.index)
        fresh = Lookup(self.root, self.index, use_cache=False)
        self.assertTrue(cached.prepared_cache_hit)
        self.assertFalse(fresh.prepared_cache_hit)
        for question in ('Which configuration key controls receipt capacity?',
                         'RECEIPT_WINDOW', 'What does the report field record?'):
            self.assertEqual(cached.search(question), fresh.search(question))
