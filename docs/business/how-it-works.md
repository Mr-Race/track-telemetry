# How It Works

*The platform, explained by following one lap of data from the car
to a conversation. No jargon; the technically curious can find the
architecture in the technical docs.*

## 1. The car records everything
During a track session, a GPS lap timer and the car's own engine
data record twenty measurements per second — position, speed,
throttle, RPM. By the end of a twenty-minute session that's roughly
70,000 data points. This part isn't new; every serious track driver
has this data. What's new is everything that happens next.

## 2. The paddock upload
Back in the paddock, helmet still on the roof of the car: share the
session from the phone, tap once. The file travels to the cloud,
where the platform takes over. A few seconds later a confirmation
comes back: track recognized, laps counted, best time computed.
The raw file is archived permanently; nothing is ever lost.

## 3. The platform understands the driving
This is where data becomes information. The platform knows each
track's corners — where every apex is, by name (the Lightbulb, the
Kink). For every lap it works out: the lap time, the minimum speed
through each corner, the speed entering and leaving, the throttle
at the apex, the engine speed at exit. It also knows which laps
*count* — warm-up and cool-down laps are flagged automatically so
statistics reflect real flying laps only.

## 4. The dashboard shows the story
A private, sign-in-protected web app shows the whole driving
history: every event, every session, every lap. Pick a session and
see corner-by-corner numbers, how they compare to the previous
visit to that track, satellite views, personal bests, and friends'
benchmark times. A separate page tracks the car itself — brake
pads, fluids, tires — and warns when a track day would outrun
their remaining life.

## 5. The conversation
The part that changes how the data gets used: the platform is
connected to an AI assistant. Questions are asked in plain English,
from a phone, and answered from the live database:

> "How did my corner speeds improve between May and July?"
> "Where am I losing the most time at Thunderbolt?"
> "What was my optimal lap on Saturday — and which corners kept me
> from driving it?"

No exports, no spreadsheets, no waiting until getting home. The
analysis conversation happens in the paddock, between run groups,
while the driving is still fresh.

## Why this beats the usual way
The usual way is a folder of files and a memory of what they meant.
This platform is a **single source of truth**: every session ever
driven, in one governed database, with the analysis logic applied
identically to all of it. That's why it can answer questions across
months of driving — and why it catches things files never would: a
duplicate upload, a mislabeled event, a personal best that was
actually the instructor driving.

---
*Part of the business documentation set — see [index](index.md).*
