import json
from pathlib import Path

import pytest

from digital_ocean.scripts.python.generated_child_canary_preflight import build
from digital_ocean.scripts.python.live_canary import validate_plan


ROOT=Path(__file__).parents[2]


def env(path):
    path.write_text('PROJECT_NAME=project1\nDO_DOMAIN=woodkilldev.com\nDO_API_REGION=nyc3\nDO_API_SIZE=s-2vcpu-4gb\nDO_API_IMAGE=ubuntu-24-04-x64\nDO_PROJECT_ID=test-project\nDO_API_TOKEN=vaultwarden://base2/DO_API_TOKEN\nDO_CANARY_HOURLY_COST_MINOR_UNITS_CEILING=4\n')


def test_generated_child_plan_and_archive_are_exact_and_live_runner_compatible(tmp_path):
    source=tmp_path/'plan.env'; env(source); output=tmp_path/'acceptance'
    plan=build(env_path=source,profile_path=ROOT/'factory_profiles/blog-portfolio.json',output_dir=output)
    binding=validate_plan(plan,output/'source.tar')
    assert binding['sourceCommit']==plan['sourceCommit']
    assert plan['childId']=='base2-child-blog-portfolio'
    assert plan['stateMode']=='encrypted-snapshot-restore-required'
    assert plan['networkRequests']==0 and plan['secretValuesEmitted']==0
    assert not (output/'child').exists()


def test_changed_archive_and_reused_output_fail_closed(tmp_path):
    source=tmp_path/'plan.env'; env(source); output=tmp_path/'acceptance'
    plan=build(env_path=source,profile_path=ROOT/'factory_profiles/blog-portfolio.json',output_dir=output)
    with pytest.raises(ValueError,match='absent'): build(env_path=source,profile_path=ROOT/'factory_profiles/blog-portfolio.json',output_dir=output)
    with (output/'source.tar').open('ab') as stream: stream.write(b'changed')
    with pytest.raises(Exception,match='differs'): validate_plan(plan,output/'source.tar')
