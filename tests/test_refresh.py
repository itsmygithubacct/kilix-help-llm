import unittest

from help_llm.refresh import checked_revision, reconcile


def passage(number, text, heading='Guide', path='docs/kilix/example.md'):
    return {'id':f'kilix:{path}#{number}', 'source':'kilix', 'path':path,
            'heading':heading, 'text':text}


class ExpansionReconciliationTest(unittest.TestCase):
    def test_inserted_passage_cannot_inherit_an_old_ordinal(self):
        old = [passage(1,'The original supported operation.')]
        new = [passage(1,'A different operation.'),passage(2,old[0]['text'])]
        retained, rows = reconcile(old,new,{old[0]['id']:['original operation?']})
        self.assertEqual(retained,{new[1]['id']:['original operation?']})
        self.assertEqual(rows[0]['new_id'],new[1]['id'])

    def test_changed_or_removed_passages_lose_their_questions(self):
        old = [passage(1,'Old instructions.'),passage(2,'Removed instructions.')]
        new = [passage(1,'Revised instructions.')]
        retained, rows = reconcile(old,new,{p['id']:['old question?'] for p in old})
        self.assertEqual(retained,{})
        self.assertEqual(sum(r['questions_removed'] for r in rows),2)

    def test_heading_and_document_context_must_match(self):
        old = [passage(1,'An operation.')]
        for new in ([passage(1,'An operation.','Historical')],
                    [passage(1,'An operation.',path='docs/kilix/other.md')]):
            with self.subTest(new=new):
                self.assertEqual(reconcile(old,new,{old[0]['id']:['question?']})[0],{})

    def test_ambiguous_duplicate_text_does_not_reuse_questions(self):
        old = [passage(1,'Repeated text.')]
        new = [passage(2,'Repeated text.'),passage(3,'Repeated text.')]
        self.assertEqual(reconcile(old,new,{old[0]['id']:['question?']})[0],{})

    def test_unchanged_passage_retains_exact_questions(self):
        old = [passage(1,'An operation.')]
        questions = {old[0]['id']:['Exact question?', 'Another question?']}
        self.assertEqual(reconcile(old,old,questions)[0],questions)

    def test_mutable_revision_names_are_rejected(self):
        for value in ('HEAD','main','a'*7,'../other','a'*39+'g'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checked_revision(value)
        self.assertEqual(checked_revision('a'*40),'a'*40)
