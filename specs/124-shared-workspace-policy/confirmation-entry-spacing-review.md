# Confirmation entry spacing correction

Held for independent review; no reference approval or native passing claim.

Native compact Submit recorded panel top 50.984375 and sticky header bottom 51.390625, a real 0.40625 CSS-pixel overlap. The endpoint receipt correctly failed. This correction reserves the existing half-rem spacing unit above confirmation panels only in the bottom movement layout. Nested confirmation entry uses the rendered header boundary and converts the authored scroll margin into target layout coordinates before one instant alignment. Document-target entry retains its previous call and behavior.

Strict capture visibility, endpoint receipts, focus and mutation guards remain unchanged. Fractional header geometry, rounded scrolling, three scales, invalid scales, all four action entries and document versus nested scope have deterministic regressions. Native compact confirmation validation remains required; these tests do not prove compositor visibility.

The three-file movement correction is a separate frozen candidate. Historical failed captures and reference bytes remain immutable.
