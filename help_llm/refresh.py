"""Deterministically refresh a committed documentation snapshot and its expansions.

Run after committing the documents. Existing expansion questions move only with
an unambiguous, byte-identical heading/text pair in the same document. No model
is used and no questions are generated. Search behavior is not modified.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from .lookup import cut


def reconcile(old, new, questions):
    """Return retained questions and an explicit passage-ID crosswalk."""
    destinations = defaultdict(list)
    for p in new:
        destinations[(p['source'], p['path'], p['heading'], p['text'])].append(p['id'])
    retained, crosswalk = {}, []
    for p in old:
        matches = destinations[(p['source'], p['path'], p['heading'], p['text'])]
        target = matches[0] if len(matches) == 1 else None
        values = questions.get(p['id'], [])
        if target and values:
            if target in retained:
                raise ValueError('ambiguous old passage correspondence: ' + target)
            retained[target] = values
        crosswalk.append({'old_id':p['id'], 'new_id':target,
                          'text_sha256':hashlib.sha256(p['text'].encode()).hexdigest(),
                          'questions_retained':len(values) if target else 0,
                          'questions_removed':0 if target else len(values),
                          'reason':'exact-heading-and-text' if target else 'changed-removed-or-ambiguous'})
    return retained, crosswalk


def git_blob(root, revision, path):
    return subprocess.check_output(['git','-C',str(root),'show',revision+':'+path])


def checked_revision(value):
    if not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('use a full immutable Git revision')
    return value


def refresh(root, base, documents_revision):
    base, documents_revision = checked_revision(base), checked_revision(documents_revision)
    index = root/'help_llm/index'
    old_sources = json.loads(git_blob(root,base,'help_llm/index/sources.json'))
    old_questions = json.loads(git_blob(root,base,'help_llm/index/questions.json'))
    snapshot = json.loads(git_blob(root,documents_revision,'docs/kilix/SNAPSHOT.json'))
    changed_paths = {d['path'] for d in snapshot['documents']}
    if len(changed_paths) != len(snapshot['documents']):
        raise ValueError('duplicate document in snapshot')
    sources = {s['path']:dict(s) for s in old_sources}
    old_passages, new_passages = [], []
    for s in old_sources:
        raw = git_blob(root,base,s['path'])
        if hashlib.sha256(raw).hexdigest() != s['sha256']:
            raise ValueError('base document does not match expansion source: '+s['path'])
        old_passages.extend(cut(s['label'],s['path'],raw.decode()))
        if s['path'] not in changed_paths and (root/s['path']).read_bytes() != raw:
            raise ValueError('unlisted document changed: '+s['path'])
    for d in snapshot['documents']:
        path = PurePosixPath(d['path'])
        if path.is_absolute() or '..' in path.parts or path.parts[:2] != ('docs','kilix'):
            raise ValueError('snapshot path must be inside docs/kilix')
        raw = git_blob(root,documents_revision,d['path'])
        if raw != (root/d['path']).read_bytes() or hashlib.sha256(raw).hexdigest() != d['bundled_sha256']:
            raise ValueError('document differs from committed snapshot: '+d['path'])
        sources[d['path']] = {'label':'kilix','path':d['path'],'commit':documents_revision,
                              'sha256':hashlib.sha256(raw).hexdigest()}
    for s in sources.values():
        new_passages.extend(cut(s['label'],s['path'],(root/s['path']).read_text(encoding='utf-8')))
    external = git_blob(root,base,'help_llm/index/external.jsonl')
    if (index/'external.jsonl').read_bytes() != external:
        raise ValueError('external passages changed')
    ext = [json.loads(line) for line in external.splitlines() if line.strip()]
    old_passages.extend(ext); new_passages.extend(ext)
    for name, passages in [('old',old_passages),('new',new_passages)]:
        if len({p['id'] for p in passages}) != len(passages):
            raise ValueError('duplicate '+name+' passage ID')
    if set(old_questions)-{p['id'] for p in old_passages}:
        raise ValueError('orphan base expansion questions')
    questions, crosswalk = reconcile(old_passages,new_passages,old_questions)
    (index/'sources.json').write_text(json.dumps(list(sources.values()),indent=1,ensure_ascii=False)+'\n')
    (index/'questions.json').write_text(json.dumps(questions,indent=1,ensure_ascii=False)+'\n')
    return {'schema':'help-corpus-refresh/v1','base':base,'documents_revision':documents_revision,
            'old_passages':len(old_passages),'new_passages':len(new_passages),
            'old_questions':sum(map(len,old_questions.values())),
            'retained_questions':sum(map(len,questions.values())), 'generated_questions':0,
            'removed_questions':sum(x['questions_removed'] for x in crosswalk),
            'crosswalk':crosswalk,'new_without_exact_predecessor':[
                {'id':p['id'],'heading':p['heading'],'text_sha256':hashlib.sha256(p['text'].encode()).hexdigest()}
                for p in new_passages if p['id'] not in {x['new_id'] for x in crosswalk if x['new_id']}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--base',required=True)
    parser.add_argument('--documents-revision',required=True)
    parser.add_argument('--report',type=Path,required=True,help='write audit JSON outside the source checkout')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.report.resolve().is_relative_to(root):
        parser.error('--report must be outside the source checkout')
    report = refresh(root,args.base,args.documents_revision)
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('crosswalk','new_without_exact_predecessor')}))


if __name__ == '__main__':
    main()
