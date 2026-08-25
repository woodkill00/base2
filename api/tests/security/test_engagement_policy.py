import pytest
from api.security.engagement import EngagementPolicyError, community_submission, moderate, notification_payload, support_submission

def test_community_is_pending_and_abuse_is_bounded():
    clean=community_submission('A useful update','A normal community message with enough detail.')
    assert clean['moderationStatus']=='pending' and not clean['requiresReview']
    hostile=community_submission('Repeated links','https://a.test https://b.test and enough context')
    assert hostile['requiresReview'] and hostile['abuseScore']==50

@pytest.mark.parametrize('value', ['<script>alert(1)</script> content','javascript:alert(1) content','short'])
def test_active_or_short_content_fails(value):
    with pytest.raises(EngagementPolicyError): community_submission('Valid title',value)

def test_support_is_private_consent_bound_and_notifications_are_redacted():
    result=support_submission('Need assistance','Please help with this account issue.',True)
    assert result['visibility']=='private' and 'email' not in result
    assert notification_payload(record_id='record-1234',event='support.received')=={'recordId':'record-1234','event':'support.received'}
    with pytest.raises(EngagementPolicyError): support_submission('Need help','Message long enough',False)

def test_moderation_transition_and_reason_are_explicit():
    assert moderate('pending','published',reason_code='reviewed')['to']=='published'
    with pytest.raises(EngagementPolicyError): moderate('rejected','published',reason_code='reviewed')
    with pytest.raises(EngagementPolicyError): moderate('pending','rejected',reason_code='../bad')
