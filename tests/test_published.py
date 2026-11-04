"""Default delivery integrity, offline setup, and source-bound retrieval."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from help_llm import published
from help_llm.presentation import present


class PublishedTests(unittest.TestCase):
    def fixture(self, root):
        value = copy.deepcopy(published.manifest())
        value['parent']['files'] = {}
        value['adapter']['files'] = {}
        config = {'base_model_name_or_path': value['parent']['model_id'],
                  'revision': value['parent']['revision'], 'r': 16, 'lora_alpha': 32}
        for group, files in [('parent', {'config.json': b'{}'}),
                             ('adapter', {'adapter_config.json': json.dumps(config).encode(),
                                          'adapter_model.safetensors': b'fixture tensor bytes'})]:
            directory = root / group
            directory.mkdir()
            for name, data in files.items():
                (directory / name).write_bytes(data)
                value[group]['files'][name] = {'bytes': len(data),
                    'sha256': hashlib.sha256(data).hexdigest(), 'url': 'https://github.com/unused'}
        return value

    def test_offline_setup_rejects_corruption_then_verifies_every_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self.fixture(root)
            with patch.dict(os.environ, {'GPU_TERMINAL_HOME': str(root / 'state')}):
                tensor = root / 'adapter/adapter_model.safetensors'
                original = tensor.read_bytes()
                tensor.write_bytes(b'x' * len(original))
                with self.assertRaisesRegex(ValueError, 'hash/size'):
                    published.acquire(value, root / 'parent', root / 'adapter')
                destination = published.model_root(value) / 'adapter'
                self.assertFalse((destination / tensor.name).exists())
                self.assertEqual(list(destination.glob('.download-*')), [])
                tensor.write_bytes(original)
                installed = published.acquire(value, root / 'parent', root / 'adapter')
                self.assertEqual(published.verify(value), installed)
                installed_tensor = installed / 'adapter' / tensor.name
                installed_tensor.write_bytes(b'y' * len(original))
                with self.assertRaisesRegex(ValueError, 'missing or damaged'):
                    published.verify(value)

    def test_symlink_and_parent_substitution_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self.fixture(root)
            with patch.dict(os.environ, {'GPU_TERMINAL_HOME': str(root / 'state')}):
                installed = published.acquire(value, root / 'parent', root / 'adapter')
                target = installed / 'parent/config.json'
                target.unlink()
                target.symlink_to(root / 'parent/config.json')
                with self.assertRaisesRegex(ValueError, 'symlinks'):
                    published.verify(value)
                target.unlink()
                target.write_bytes(b'{}')
                value['parent']['revision'] = 'f' * 40
                with self.assertRaisesRegex(ValueError, 'pinned parent'):
                    published.verify(value)

    def test_concurrent_setup_or_answer_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'GPU_TERMINAL_HOME': directory}):
                with published.model_lock():
                    with self.assertRaisesRegex(ValueError, 'another Help'):
                        with published.model_lock():
                            self.fail('lock should be exclusive')

    def test_manifest_rejects_traversal_and_mutable_parent(self):
        value = published.manifest()
        for bad in ('../config.json', '/tmp/config.json'):
            altered = copy.deepcopy(value)
            altered['parent']['files'][bad] = altered['parent']['files']['config.json']
            with patch.object(published, 'read_json', return_value=altered):
                with self.assertRaises(ValueError):
                    published.manifest()
        value['parent']['revision'] = 'main'
        with patch.object(published, 'read_json', return_value=value):
            with self.assertRaisesRegex(ValueError, 'immutable'):
                published.manifest()

    def test_everyday_questions_find_command_sources_and_bound_links(self):
        questions = {'How do I launch a kilix pane?': 'panes-open:1',
                     'How do I list panes?': 'panes-list:1',
                     'How do I use the TUI?': 'tui-use:1',
                     'How do I launch agents?': 'agents-codex:1'}
        for question, expected in questions.items():
            with self.subTest(question=question):
                source, registry = published.evidence(question)
                self.assertEqual(source['id'], expected)
                output = {'answer': 'Run `example`. Example. [' + source['id'] + ']',
                          'citation_valid': True, 'source': source}
                rendered = present(output, registry)
                self.assertEqual(rendered['command'], 'example')
                self.assertTrue(rendered['help'])
                output['source'] = dict(source, text=source['text'] + ' changed')
                self.assertEqual(present(output, registry)['status'], 'withheld')
        self.assertIsNone(published.evidence('xyzzyqwerty')[0])
        for question in ('', 'x' * 2001, 'nul\0'):
            with self.assertRaises(ValueError):
                published.evidence(question)
