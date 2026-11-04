"""Native usage from fake tensors; no model, tokenizer download, or inference."""
import contextlib
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from help_llm import runtime, published_runtime

class Tensor:
    def __init__(self, rows): self.rows=rows; self.shape=(len(rows),len(rows[0]))
    def __getitem__(self, key):
        row, span=key
        return self.rows[row][span]

class NativeUsageTests(unittest.TestCase):
    chunk={'id':'guide:1','path':'guide.md','line':1,'text':'Use the command.'}
    def generate(self, *, failure=None, observer=None):
        torch=SimpleNamespace(tensor=Tensor,ones_like=lambda ids:ids,no_grad=contextlib.nullcontext)
        tokenizer=SimpleNamespace(eos_token_id=99,decode=lambda ids,**kw:'Use it. [guide:1]')
        def output(**kwargs):
            self.assertEqual(kwargs['input_ids'].shape,(1,3))
            if failure: raise failure
            return Tensor([[1,2,3,4,99]])
        model=SimpleNamespace(generate=output)
        with patch.dict(sys.modules,{'torch':torch}), \
                patch.object(runtime,'encoded',return_value={'input_ids':[1,2,3]}):
            return runtime.generated(model,tokenizer,'How?',self.chunk,32,8,usage_observer=observer)

    def test_native_suffix_includes_eos_before_decode(self):
        events=[];result=self.generate(observer=events.append)
        self.assertEqual(result['answer'],'Use it. [guide:1]')
        self.assertTrue(result['citation_valid'])
        self.assertEqual(result['native_usage']['input_tokens'],3)
        self.assertEqual(result['native_usage']['output_tokens'],2)
        self.assertEqual([x['status'] for x in events],['started','observed'])
        self.assertIsNone(events[0]['output_tokens'])
        self.assertIs(type(events[1]['input_tokens']),int)
        self.assertIs(type(events[1]['output_tokens']),int)

    def test_partial_failure_and_cancellation_have_unknown_output(self):
        for failure in (RuntimeError('partial generation'),KeyboardInterrupt()):
            events=[]
            with self.assertRaises(type(failure)) as caught:
                self.generate(failure=failure,observer=events.append)
            self.assertIs(caught.exception,failure)
            self.assertEqual(events[-1]['status'],'unknown')
            self.assertIsNone(events[-1]['output_tokens'])
            self.assertEqual(events[-1]['input_tokens'],3)
            self.assertEqual(caught.exception.native_usage,events[-1])

    def test_no_evidence_never_loads_or_dispatches_model(self):
        events=[]
        with patch.object(published_runtime.published,'evidence',return_value=(None,{})), \
                patch.object(published_runtime,'present',return_value={}), \
                patch.object(published_runtime,'load') as load:
            result=published_runtime.query('Unknown?',usage_observer=events.append)
        load.assert_not_called()
        self.assertTrue(result['explicit_refusal'])
        self.assertEqual(events,[result['native_usage']])
        self.assertEqual(events[0]['status'],'not-dispatched')
        self.assertEqual(events[0]['model_calls'],0)
        self.assertIsNone(events[0]['input_tokens'])
        self.assertIsNone(events[0]['output_tokens'])

    def test_observer_failure_prevents_dispatch(self):
        with self.assertRaisesRegex(ValueError,'ledger unavailable'):
            self.generate(observer=lambda row: (_ for _ in ()).throw(ValueError('ledger unavailable')))

if __name__ == '__main__':unittest.main()
