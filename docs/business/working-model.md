# The Working Model

*How this platform was actually built: AI-assisted engineering with
a deliberate division of labor. This page is the leadership story —
the technology is documented elsewhere; this is about how the work
itself was organized.*

## The division of labor
Every line of production code on this platform was written by AI
(Claude, working as a pair programmer inside the repository). Every
decision was made by a human. That sentence sounds like a slogan;
in practice it was a discipline with a clear boundary:

**Human side — where judgment lives:**
- Architecture and technology selection (and their trade-offs:
  serverless SQL vs. alternatives, React vs. licensed BI tooling)
- The security model (passwordless managed identities everywhere —
  including reversing course mid-build when a better door opened)
- Domain vocabulary — corner names and numbering follow how drivers
  at the track actually talk, not how a database would prefer
- Scope and sequencing: what ships in v1.0, what waits, what gets
  killed
- Review: reading what was built, testing it against reality,
  catching what's wrong

**AI side — where throughput lives:**
- Implementation, across every layer: SQL, Python, TypeScript,
  infrastructure configuration
- Testing, deployment, debugging its own failures
- Documentation, maintained in the same commits as the changes

## What the reviews caught (why the human matters)
The clearest argument for this division is the list of things
domain judgment caught that no tooling would have:

- **A flawed analysis method that produced impressive nonsense.**
  The first "optimal lap" calculation claimed 13 seconds of
  improvement was available in one session. Plausible-looking,
  mathematically valid, and wrong — boundary jitter in the method
  inflated it. The corrected method (validated against real data)
  showed 3 seconds. The difference between those numbers is the
  difference between analytics and fiction.
- **A personal best that wasn't.** The database briefly believed a
  lap time 3 seconds faster than reality — an instructor-driven
  session, ingested without attribution. Only someone who knew who
  was driving could catch it; fixing it properly forced the
  multi-user data model to mature early.
- **A track that was mislabeled by confident AI.** Early on, the AI
  asserted the wrong identity for a famous corner complex. The
  driver's local knowledge overruled it, and the correction is now
  permanent in the data model. The lesson generalizes: AI states
  wrong things fluently; review is domain knowledge applied with
  skepticism.

## Governance became conversational
The project's backlog, specifications, decision log, and this
documentation live in version control — and are maintained by
talking. Feature ideas filed from a phone in a paddock. A backlog
reorganized into a versioned roadmap during a lunch break. A page
specification created by reacting to a tappable mockup rather than
reading a requirements document. The overhead that normally kills
side projects — and bloats enterprise ones — approached zero, not
because process was skipped, but because process became cheap.

## What this suggests for teams
One person, spare-time hours, one month: a launched, versioned,
secured, documented cloud platform at effectively zero
infrastructure cost. The multiplier wasn't the AI's speed alone —
it was the *design of the collaboration*: judgment concentrated in
the human, throughput delegated to the machine, and review treated
as a first-class skill rather than an afterthought.

Teams that only adopt the tools will get incremental gains. Teams
that redesign the division of labor — who decides, who implements,
who reviews, and how cheaply governance can run — will move at a
different speed entirely.

---
*Part of the business documentation set — see [index](index.md).*
