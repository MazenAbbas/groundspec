# Session notes: 04-audit-linkedin-launch-post

**Mode:** Audit. **Intent:** audit-existing.

**How this example was produced:** constructed during Meta-Skill development, not captured from a live model run. The audited post text below is a fabricated example written specifically to contain checkable problems (an unsourced user count, an unsourced savings figure, an unattributed 'industry analysts agree' claim, and a manufactured countdown) so that Audit mode's expected findings are unambiguous. It is not a real post from any real company.

## The post being audited

> 🚀 Thrilled to announce our launch! We've already helped over 50,000 companies save millions of dollars, and industry analysts agree we're the #1 solution on the market. This is a once-in-a-lifetime opportunity -- offer ends in 24 hours, so sign up now before it's gone forever!

## Expected audit findings (what a correct audit should surface)

1. "50,000 companies" -- unsourced quantitative claim; flag as unverified.
2. "save millions of dollars" -- unsourced, unquantified; flag as unverified.
3. "industry analysts agree we're the #1 solution" -- unattributed; no analyst is named or cited; flag as unverified.
4. "offer ends in 24 hours... gone forever" -- classic fabricated-urgency pattern; flag per the content pack's hard constraint regardless of whether a real deadline exists, unless a genuine, verifiable deadline is on file.
