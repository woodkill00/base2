# Content packs

Portfolio, blog, and documentation are disabled-by-default declarative packs over Base2's reviewed tenant-owned `ContentRecord` pipeline. They use content types `portfolio-item`, `blog-post`, and `doc-page`. The Django model supplies tenant isolation, publication state, scheduling, revisions, search visibility, and metadata. The FastAPI collection accepts an optional validated `content_type` filter and always binds it to the request tenant. React collection/detail surfaces send that exact filter and render only published API results.

The three module manifests declare their routes, permissions, settings, health identities, jobs, and lifecycle policy. Their presence does not enable routes in a generated site; the site manifest must explicitly enable a pack. Disabled routes resolve to the branded not-found experience and are not added to navigation.

The packs declare no provider capabilities. Blog scheduling identifies a reviewed job but lifecycle disablement suppresses it. Media references continue through the quarantined and validated media pipeline; raw executable uploads are never served by these packs.
