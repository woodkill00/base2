import pytest
from api.security.engagement import EngagementPolicyError
from api.services.site_content import SiteContentService

class Repository:
    def __init__(self): self.kwargs=None
    def create_community_post(self,**kwargs): self.kwargs=kwargs; return {'moderationStatus':'pending'}
    def submit_form(self,**kwargs): self.kwargs=kwargs; return {'status':'queued'}

def test_community_is_durable_pending_and_author_bound():
    repo=Repository(); service=SiteContentService(repo)
    result=service.submit_community(site_id='tenant-one',author_ref='user-1',title='Useful title',body='A useful community contribution.')
    assert result['moderationStatus']=='pending'
    assert repo.kwargs['site_id']=='tenant-one' and repo.kwargs['author_ref']=='user-1'
    assert repo.kwargs['payload']['moderationStatus']=='pending'

def test_support_requires_processing_consent_and_stores_private_shape():
    repo=Repository(); service=SiteContentService(repo)
    with pytest.raises(EngagementPolicyError,match='consent'):
        service.submit_form(site_id='tenant-one',form_key='support',replay_key='x',payload={'subject':'Need help','message':'A sufficiently long support message.'},consent={},request_id='r')
    service.submit_form(site_id='tenant-one',form_key='support',replay_key='x',payload={'subject':'Need help','message':'A sufficiently long support message.'},consent={'supportProcessing':True},request_id='r')
    assert repo.kwargs['payload']['visibility']=='private'
