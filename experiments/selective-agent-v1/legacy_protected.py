"""Read-only checks of all completed Torch campaigns and the original split."""
from pathlib import Path
from design import read,digest
from preservation import capture
from prior_protected import check as prior_check


def check(root,package):
    result=prior_check(root,package)
    name=read(package/'experiment.json')['source_learning_campaign']
    folder=root/name;learning=folder/'learning'
    receipt=read(package/'inputs/original-learning-receipt.json')
    if digest(learning/'learning-receipt.json')!=digest(package/'inputs/original-learning-receipt.json'):
        raise ValueError('Original learning receipt differs')
    for name,field in [('learning-data.jsonl','learning_data_sha256'),('oracle-headroom.json','headroom_sha256'),('fixed-baselines.json','fixed_baselines_sha256')]:
        if digest(learning/name)!=receipt[field]:raise ValueError('Original learning export differs: '+name)
    status=read(learning/'status.json');exit_record=read(learning/'job-exit.json')
    if status['status']!='complete' or status['provider_calls']!=0 or exit_record['exit_code']!=0:
        raise ValueError('Original learning campaign was not successful')
    result[folder.name]=capture(folder)
    # The original query file contains the sealed confirmation split. Hash it on
    # the host for preservation; it is never mounted into the new container.
    source=package.parent/'torch-reviews-policy-learning'
    manifest=read(source/'manifest.json')
    if digest(source/'manifest.json')!=receipt['package_manifest_sha256']:
        raise ValueError('Original study package differs')
    for relative,expected in manifest['files'].items():
        if digest(source/relative)!=expected:raise ValueError('Original study source changed: '+relative)
    result['original-study-package']=capture(source)
    return result
