# Implementation Plan

1. Inventory the historical design source and map every component, interaction, selector, and visual test to its current counterpart.
2. Port the complete interaction controller into the current navigation component while retaining current routing and data contracts.
3. Reconcile the historical CSS with current tokens, site profiles, public shell, accessibility contracts, and responsive breakpoints.
4. Adapt section components only where historical markup is required for the intended design; retain current manifest-driven content and actions.
5. Expand component, interaction, accessibility, responsive, and visual tests, including failure-path coverage.
6. Run iterative analysis and task refinement until every requirement has an implementing task and test evidence.
7. Run local production gates, publish a PR, merge only after green CI, deploy a bounded preview, run public and authenticated browser gates, and verify teardown.
