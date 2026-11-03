import unittest

from help_llm.lookup import cut


class MergedHeadingTest(unittest.TestCase):
    def test_merged_sections_keep_both_titles_without_leaking_to_siblings(self):
        body = ' '.join(['Network details.']*40)
        raw = '# Manual\n\nShort introduction.\n\n## Network\n\n'+body+'\n\n## Storage\n\nDisk details.'
        passages = cut('manual','manual.md',raw)
        self.assertEqual(len(passages),2)
        self.assertEqual(passages[0]['id'],'manual:manual.md#1')
        self.assertEqual(passages[0]['text'],'Short introduction.\n\n'+body)
        self.assertEqual(passages[0]['heading'],'Manual | Manual > Network')
        self.assertEqual(passages[1]['heading'],'Manual > Storage')

    def test_a_chain_of_short_sections_keeps_each_distinct_heading(self):
        passages = cut('manual','manual.md','# Manual\n\nIntro.\n\n## A\n\nFirst.\n\n## B\n\nSecond.')
        self.assertEqual(passages[0]['heading'],'Manual | Manual > A | Manual > B')
        self.assertEqual(passages[0]['text'],'Intro.\n\nFirst.\n\nSecond.')

    def test_headings_inside_fences_do_not_become_search_metadata(self):
        passages = cut('manual','manual.md','# Manual\n\n```sh\n## False heading\n```\n\n## Real\n\nDetails.')
        self.assertEqual(passages[0]['heading'],'Manual | Manual > Real')
        self.assertIn('## False heading',passages[0]['text'])
