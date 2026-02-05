"""
Comprehensive Football Knowledge Base for AI Video Analysis

This file contains detailed definitions for:
- Player positions (offense and defense)
- Types of plays (run vs pass)
- Route tree and route types
- Blocking schemes (run block vs pass block)
- Tackle identification
- Field position terminology
- Sack identification
- Turnover types
- Run concepts (inside vs outside)

These definitions are used to provide context to the Gemini AI model
for accurate football video analysis.

FILE: backend/knowledge/football.py
"""

# =============================================================================
# OFFENSIVE POSITIONS
# =============================================================================

OFFENSIVE_POSITIONS = """
## OFFENSIVE POSITIONS

### Quarterback (QB)
- Lines up behind center, receives the snap
- Makes pre-snap reads and calls audibles
- Hands off to running backs or throws passes
- Visual identifiers: Takes snap, drops back, or hands off

### Running Back (RB) / Halfback (HB)
- Lines up in backfield behind or beside QB
- Receives handoffs and runs with the ball
- Also catches passes out of backfield (checkdowns, screens)
- Visual identifiers: In backfield, receives handoff, runs through holes

### Fullback (FB)
- Lines up in backfield, typically closer to line than RB
- Primary role is blocking for RB
- Occasionally carries ball on short-yardage plays
- Visual identifiers: Leads through hole, blocks linebackers

### Wide Receiver (WR)
- Lines up on or near line of scrimmage, split out wide
- Runs routes and catches passes
- X receiver: Typically on weak side, runs deeper routes
- Z receiver: Typically on strong side, often in motion
- Slot receiver: Lines up between tackle and outside WR
- Visual identifiers: Split wide, runs routes, targets for passes

### Tight End (TE)
- Lines up on line of scrimmage next to offensive tackle
- Hybrid role: blocks like lineman, catches like receiver
- Y tight end: In-line, primary blocker
- F tight end: Flexed out, more receiver-like
- Visual identifiers: On line next to tackle, can release into routes or block

### Offensive Line (OL)
- **Center (C)**: Snaps ball to QB, blocks middle
- **Guard (LG/RG)**: Inside linemen, block defensive tackles
- **Tackle (LT/RT)**: Outside linemen, protect QB's blind side (LT) and right side (RT)
- Visual identifiers: In 3-point stance, engage defenders at snap
"""

# =============================================================================
# DEFENSIVE POSITIONS
# =============================================================================

DEFENSIVE_POSITIONS = """
## DEFENSIVE POSITIONS

### Defensive Line (DL)

#### Defensive End (DE)
- Lines up on edge of offensive line
- Contains outside runs, rushes passer
- Visual identifiers: On edge, crashes down or speed rushes

#### Defensive Tackle (DT)
- Lines up over guards or center
- Stops inside runs, creates interior pressure
- Nose Tackle (NT): Lines up directly over center in 3-4 defense
- Visual identifiers: Inside alignment, engages offensive linemen

### Linebackers (LB)

#### Middle Linebacker (MLB/MIKE)
- Lines up behind defensive line, center of defense
- Calls defensive plays, stops runs up middle
- Visual identifiers: Central position, reads play, fills gaps

#### Outside Linebacker (OLB/WILL/SAM)
- WILL: Weak side linebacker
- SAM: Strong side linebacker
- Contains outside runs, covers TEs/RBs, rushes passer
- Visual identifiers: Outside alignment, drops in coverage or blitzes

### Defensive Backs (DB)

#### Cornerback (CB)
- Lines up across from wide receivers
- Primary job: Cover receivers in man or zone
- Visual identifiers: Wide alignment, mirrors WR movements

#### Safety
- **Free Safety (FS)**: Deep middle coverage, center fielder
- **Strong Safety (SS)**: Closer to line, run support and coverage
- Visual identifiers: Deep alignment, reads QB, breaks on ball

#### Nickel/Dime
- Nickel: 5th defensive back, replaces linebacker
- Dime: 6th defensive back, extra coverage
- Visual identifiers: Extra DBs on field in passing situations
"""

# =============================================================================
# ROUTE TREE AND ROUTE TYPES
# =============================================================================

ROUTE_TREE = """
## ROUTE TREE (Standard 9-Route Tree)

Routes are numbered 0-9, with odd numbers breaking outside and even numbers breaking inside.

### 0 Route - Hitch/Curl
- Receiver runs 5-8 yards, stops, turns back to QB
- Quick timing route, high completion percentage
- Visual: WR plants feet, pivots toward sideline

### 1 Route - Flat
- Receiver runs to flat area near sideline, 1-3 yards deep
- Used for quick dumps, RB/TE checkdowns
- Visual: Short horizontal route toward sideline

### 2 Route - Slant
- Receiver takes 3 steps, breaks sharply inside at 45 degrees
- Quick timing route, dangerous in zone coverage
- Visual: Sharp inside cut after short stem

### 3 Route - Comeback
- Receiver runs 12-15 yards, plants, comes back toward sideline
- Timing route, ball thrown before break
- Visual: Deep stem, plant, comeback to sideline

### 4 Route - Curl/Hook
- Receiver runs 10-12 yards, curls back inside toward QB
- Sits in soft spot of zone coverage
- Visual: Medium depth, turns inside toward QB

### 5 Route - Out
- Receiver runs 10-12 yards, breaks sharply toward sideline
- 90-degree cut, thrown to outside shoulder
- Visual: Square cut to sideline at medium depth

### 6 Route - In/Dig
- Receiver runs 10-12 yards, breaks sharply inside
- Crosses field horizontally
- Visual: Square cut inside at medium depth

### 7 Route - Corner/Flag
- Receiver runs 12-15 yards, breaks toward corner of end zone
- 45-degree angle toward pylon
- Visual: Angled break toward corner, often in red zone

### 8 Route - Post
- Receiver runs 12-15 yards, breaks inside toward goalposts
- Deep route, attacks middle of field
- Visual: Angled break inside toward center of field

### 9 Route - Go/Fly/Streak
- Receiver runs straight down field at full speed
- Pure vertical route, stretches defense deep
- Visual: No break, straight line down sideline or seam

### Additional Routes

#### Wheel Route
- RB/TE starts flat, wheels up sideline
- Creates mismatch with linebackers
- Visual: Out of backfield, curves up sideline

#### Seam Route
- TE/slot runs straight up seam between safety and corner
- Attacks void in Cover 2
- Visual: Vertical route between hash and numbers

#### Drag/Shallow Cross
- Receiver runs shallow cross, 3-5 yards depth
- Often combined with deeper crossing route
- Visual: Low horizontal route across field

#### Skinny Post
- Tighter angle post, between post and seam
- Visual: Slight inside break, less angle than full post

#### Double Move Routes
- Stutter-go: Fake hitch, go deep
- Out-and-up: Fake out, go deep
- Sluggo: Slant-and-go
- Visual: Initial fake, then vertical release
"""

# =============================================================================
# RUN VS PASS DIFFERENTIATION
# =============================================================================

RUN_VS_PASS = """
## RUN VS PASS PLAY DIFFERENTIATION

### Pass Play Indicators
1. QB drops back from line of scrimmage
2. Offensive linemen set in pass protection (vertical sets)
3. Wide receivers release into routes
4. QB's eyes downfield, ball held high
5. Pocket forms around QB
6. RB may stay in to block or release

### Run Play Indicators
1. QB turns/pivots to hand off immediately
2. Offensive linemen fire off line (drive blocking) or pull
3. RB takes handoff and runs toward line
4. Wide receivers block defenders (crack blocks, stalk blocks)
5. Tight ends often block down
6. No pocket forms, action moves toward line

### Play Action (Fake Run, Then Pass)
1. QB fakes handoff to RB
2. RB sells run fake, hits hole empty-handed
3. QB continues back after fake, sets up to pass
4. Linemen may initially show run block, then convert
5. Visual: Initial run action, then passing motion

### RPO (Run-Pass Option)
1. Line blocks for run
2. QB reads defender post-snap
3. Either hands off OR pulls and throws quick pass
4. Visual: Run blocking but quick throw possible

### Screen Pass
1. Linemen allow rushers through initially
2. Then release to set up screen
3. QB throws short to RB or WR behind line
4. Blockers set up in front of receiver
5. Visual: Pocket breaks down intentionally, short throw, blockers ahead
"""

# =============================================================================
# BLOCKING SCHEMES
# =============================================================================

BLOCKING_SCHEMES = """
## BLOCKING SCHEMES

### Pass Blocking Identification

#### Pass Protection Sets
- **Kick Slide**: Tackle kicks back at 45 degrees, mirrors rusher
- **Vertical Set**: Lineman sets vertically, punches at contact
- **Half Slide**: Interior line slides one direction, other side man blocks
- **Full Slide**: Entire line slides one direction

#### Pass Block Visual Cues
1. Linemen move BACKWARD from line of scrimmage
2. Hands inside, absorbing rushers
3. Weight on back foot, reactive posture
4. Eyes on assigned defender
5. Creating pocket/cup around QB

### Run Blocking Identification

#### Zone Blocking Schemes
- **Inside Zone (IZ)**: Linemen step playside, combo to linebacker
- **Outside Zone (OZ)**: Linemen reach block, aiming for outside hip
- **Stretch**: Aggressive outside zone, gets to perimeter

#### Gap/Power Blocking Schemes
- **Power**: Backside guard pulls, kick out defender
- **Counter**: Misdirection, pulling linemen opposite way
- **Trap**: Allow defender through, pulling lineman traps
- **Duo**: Double teams at point of attack

#### Run Block Visual Cues
1. Linemen move FORWARD aggressively at snap
2. Fire off line, engage defenders
3. Double teams at point of attack
4. Pulling linemen moving laterally
5. Aggressive, attacking posture

### Key Differences Summary
| Aspect | Pass Block | Run Block |
|--------|------------|-----------|
| Direction | Backward/holding | Forward/attacking |
| Posture | Reactive, absorbing | Aggressive, driving |
| Hands | Punching, resetting | Locking on, driving |
| Feet | Mirroring, sliding | Churning, driving |
| Intent | Create pocket | Create movement/holes |
"""

# =============================================================================
# TACKLE IDENTIFICATION
# =============================================================================

TACKLE_IDENTIFICATION = """
## TACKLE IDENTIFICATION

### Types of Tackles

#### Form Tackle
- Defender wraps arms around ball carrier
- Head up, drives through ball carrier
- Textbook technique, secure tackle
- Visual: Arms wrap, controlled contact, ball carrier goes down

#### Wrap-Up Tackle
- Arms fully encircle ball carrier
- May bring down from behind or side
- Visual: Arms around waist/legs, bringing down

#### Diving Tackle
- Defender launches body at ball carrier
- Last resort when out of position
- Visual: Horizontal body position, often at legs

#### Shoe-String Tackle
- Tackle at ankles/feet
- Trips up ball carrier
- Visual: Low contact, grab at feet

#### Gang Tackle
- Multiple defenders converge on ball carrier
- Visual: 2+ defenders making contact simultaneously

#### Tackle for Loss (TFL)
- Tackle behind line of scrimmage on run play
- Visual: Ball carrier taken down in backfield

### Tackle Location Indicators
1. **In bounds**: Player taken down on field
2. **Out of bounds**: Player pushed/driven out
3. **In end zone**: Touchdown or safety
4. **At first down marker**: Critical tackle
5. **In backfield**: TFL or sack

### Who Made the Tackle
- Watch for jersey numbers at point of contact
- First defender to make contact vs. assist
- Official stats credit primary tackler + assists
"""

# =============================================================================
# FIELD POSITION IDENTIFICATION
# =============================================================================

FIELD_POSITION = """
## FIELD POSITION IDENTIFICATION

### Field Zones

#### Own Territory (1-50)
- **Deep own territory (1-10)**: Backed up, conservative play calling
- **Own 10-20**: Still danger zone, limited playcalling
- **Own 20-35**: Normal operations, full playbook
- **Own 35-50**: Crossing midfield range

#### Opponent Territory (50-1)
- **Opponent 40-50**: Midfield area
- **Opponent 25-40**: Field goal range begins (~57 yard FG)
- **Opponent 20-25**: Scoring territory
- **Red Zone (20-1)**: High percentage scoring area
- **Goal Line (5-1)**: Tight formations, power runs

### Visual Field Position Markers

#### Yard Lines
- Every 5 yards: White line across field
- Every 10 yards: Numbered (10, 20, 30, 40, 50)
- Numbers face toward nearest end zone

#### Hash Marks
- Short lines between numbers
- Mark each individual yard
- Ball spotted on or between hashes

#### Key Field Locations
1. **Goal Line**: Front of end zone, plane to break
2. **End Zone**: 10 yards deep, scoring area
3. **Sidelines**: Boundary, white line
4. **First Down Marker**: Yellow line (broadcast), orange marker (field)
5. **Line of Scrimmage**: Where ball is spotted

### Reading Field Position in Video
1. Look for nearest yard line number
2. Identify which direction offense is going
3. Count lines from visible number
4. Hash mark position indicates ball placement
"""

# =============================================================================
# SACK IDENTIFICATION
# =============================================================================

SACK_IDENTIFICATION = """
## SACK IDENTIFICATION

### What Qualifies as a Sack
A sack occurs when:
1. QB is tackled BEHIND the line of scrimmage
2. During an attempted PASS play
3. Before the QB can throw the ball

### NOT a Sack
- QB tackled on a designed run play
- QB throws incomplete pass, then contacted
- QB runs and tackled at or past line of scrimmage
- Intentional grounding (different stat)

### Types of Sacks

#### Pressure Sack
- Pass rusher beats blocker with speed/power
- Gets to QB through normal rush
- Visual: Rusher wins individual battle

#### Cleanup Sack
- QB holds ball too long
- Coverage forces QB to wait
- Rusher gets there on delayed pressure
- Visual: QB looking, no one open, rusher arrives

#### Strip Sack
- Defender sacks QB AND causes fumble
- Ball comes loose during tackle
- Visual: Ball on ground after sack

#### Coverage Sack
- Secondary covers all receivers
- QB has no one to throw to
- Eventually taken down
- Visual: QB scrambling, looking, then tackled

### Sack Visual Identifiers
1. QB in passing posture (ball up, looking downfield)
2. Defender makes contact and takes QB down
3. Contact point is BEHIND line of scrimmage
4. Ball is NOT thrown before contact
5. Play was designed pass, not QB run
"""

# =============================================================================
# TURNOVER IDENTIFICATION
# =============================================================================

TURNOVER_IDENTIFICATION = """
## TURNOVER IDENTIFICATION

### Interception

#### What Qualifies
- Forward pass caught by defensive player
- Before ball touches ground
- Defense gains possession

#### Visual Identifiers
1. QB throws pass
2. Defensive player (usually DB) catches it
3. Ball never touches ground
4. Defender secures possession
5. Play continues with defense as offense

#### Types of Interceptions
- **Jump ball INT**: Defender out-jumps receiver
- **Undercut INT**: Defender jumps route, steps in front
- **Tipped ball INT**: Ball deflected, caught by defense
- **Overthrow INT**: Pass too far, safety catches
- **Pick-six**: Interception returned for touchdown

### Fumble

#### What Qualifies
- Ball carrier loses possession
- Ball hits ground or controlled by defense
- Not an incomplete pass (arm moving forward)

#### Visual Identifiers
1. Ball comes loose from player
2. Either hits ground OR directly to defender
3. Clear separation between player and ball
4. Can be caused by hit or mishandling

#### Types of Fumbles
- **Strip fumble**: Defender punches/rips ball out
- **Ground fumble**: Loose ball on ground
- **Muffed punt/kick**: Special teams fumble
- **Fumble into end zone**: Results in touchback if out
- **Fumble-six**: Returned for touchdown

#### Fumble vs Incomplete Pass
- **Key**: Was arm moving forward when ball came out?
- Arm forward = incomplete pass (even if contact caused it)
- No forward motion = fumble
- Visual: Watch QB's arm at moment ball comes loose

### Turnover on Downs

#### What Qualifies
- Offense fails to gain first down
- On 4th down attempt
- Ball awarded to defense

#### Visual Identifiers
1. 4th down situation
2. Ball carrier tackled short of first down line
3. Offense did not convert
4. Possession changes
"""

# =============================================================================
# INSIDE RUN VS OUTSIDE RUN
# =============================================================================

INSIDE_VS_OUTSIDE_RUN = """
## INSIDE RUN VS OUTSIDE RUN IDENTIFICATION

### Inside Run Plays

#### Definition
Runs that attack between the offensive tackles (A and B gaps)

#### Gap Terminology
- **A Gap**: Between center and guard
- **B Gap**: Between guard and tackle

#### Common Inside Run Plays
1. **Inside Zone**: Linemen combo block, RB reads hole
2. **Dive**: Quick handoff straight ahead
3. **Trap**: Pull blocker traps defender inside
4. **Power**: Kick out + pull, downhill run
5. **Iso**: Fullback leads through A gap

#### Visual Identifiers - Inside Runs
1. RB aims for area between tackles
2. Tight splits by offensive line
3. Double teams at point of attack
4. RB may cut back inside
5. Designed to hit interior gaps

### Outside Run Plays

#### Definition
Runs that attack outside the offensive tackles (C gap and beyond)

#### Gap Terminology
- **C Gap**: Outside the tackle
- **D Gap**: Outside the tight end (if present)
- **Perimeter**: Edge of formation

#### Common Outside Run Plays
1. **Outside Zone/Stretch**: Reach blocks, RB presses edge
2. **Toss/Sweep**: Pitch to RB, runs to perimeter
3. **Jet Sweep**: WR in motion takes handoff
4. **Pitch**: Option play, QB pitches outside
5. **Crack Toss**: WR cracks inside, toss to edge

#### Visual Identifiers - Outside Runs
1. RB takes wider path/angle
2. Reach blocks by offensive line
3. RB pressing sideline
4. Pulling linemen getting to edge
5. Often involves motion or misdirection

### Key Differences Summary

| Aspect | Inside Run | Outside Run |
|--------|------------|-------------|
| Target | A/B gaps | C gap/perimeter |
| RB Path | Downhill, between tackles | Lateral, toward sideline |
| Blocking | Drive blocks, double teams | Reach blocks, pulls |
| Timing | Quick hitting | May take longer to develop |
| Space | Tight, congested | More open field |
"""

# =============================================================================
# COMBINED KNOWLEDGE PROMPT
# =============================================================================

FOOTBALL_KNOWLEDGE = f"""
# COMPREHENSIVE FOOTBALL KNOWLEDGE BASE

This knowledge base provides detailed definitions and visual identifiers
for analyzing football video footage.

{OFFENSIVE_POSITIONS}

{DEFENSIVE_POSITIONS}

{ROUTE_TREE}

{RUN_VS_PASS}

{BLOCKING_SCHEMES}

{TACKLE_IDENTIFICATION}

{FIELD_POSITION}

{SACK_IDENTIFICATION}

{TURNOVER_IDENTIFICATION}

{INSIDE_VS_OUTSIDE_RUN}
"""


def get_full_knowledge_prompt() -> str:
    """Return the complete football knowledge prompt for AI context."""
    return FOOTBALL_KNOWLEDGE


# For quick reference during development
if __name__ == "__main__":
    print("Football Knowledge Base")
    print("=" * 50)
    print(f"Total characters: {len(FOOTBALL_KNOWLEDGE):,}")
    print(f"Approximate tokens: {len(FOOTBALL_KNOWLEDGE) // 4:,}")
    print("\nSections included:")
    print("- Offensive Positions")
    print("- Defensive Positions")
    print("- Route Tree (0-9 routes + additional)")
    print("- Run vs Pass Differentiation")
    print("- Blocking Schemes (Pass vs Run)")
    print("- Tackle Identification")
    print("- Field Position")
    print("- Sack Identification")
    print("- Turnover Identification")
    print("- Inside vs Outside Run")
