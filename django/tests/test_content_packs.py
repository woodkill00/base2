import pytest

from sitecontent.models import ContentRecord


@pytest.mark.django_db
def test_pack_records_share_reviewed_model_but_remain_tenant_and_type_isolated():
    for site_id in ('tenant-one', 'tenant-two'):
        for content_type in ('portfolio-item', 'blog-post', 'doc-page'):
            ContentRecord.objects.create(
                site_id=site_id,
                content_type=content_type,
                slug='entry',
                title=f'{site_id} {content_type}',
                state=ContentRecord.State.PUBLISHED,
            )

    tenant_one_blog = ContentRecord.objects.for_tenant('tenant-one').filter(
        content_type='blog-post'
    )
    assert list(tenant_one_blog.values_list('title', flat=True)) == [
        'tenant-one blog-post'
    ]
    assert ContentRecord.objects.for_tenant('tenant-two').count() == 3
