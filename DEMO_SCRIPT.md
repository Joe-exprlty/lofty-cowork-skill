# Lofty + Cowork Skill: Demo Script

A follow-along script for showing this skill off live. It covers both versions you built: the basic tier (just an API key, no servers) and the full tier (the Cloudflare worker bots). Type the prompts in bold exactly as written into a Cowork conversation. The skill auto-activates on the word "Lofty," so you do not need to do anything special to turn it on.

A quick note before you start: do this against a test lead, or one you have permission to show. Whatever lead Claude pulls up, the audience sees the name, phone, and notes. Pick someone safe.

---

## The two versions, in one breath

When someone asks "what's the difference," here is the clean answer.

The **basic version** is just Claude plus your Lofty API key and a small Python file on your computer. No servers, no monthly cost. Claude can read and write your CRM live: find leads, log notes, pull activity, search the MLS, draft texts and emails. This is 90 percent of the daily value and takes about 15 minutes to set up.

The **full version** adds Cloudflare worker bots that keep running after you close the laptop. They handle the things that have to happen on a schedule or in the background: a post-showing feedback form, an automatic feedback text that fires the moment a showing ends, and a live lead index that updates the instant a lead acts on your site. Three of the four tiers run free; only the timed-SMS tier needs the $5/month Cloudflare paid plan.

Frame it as a ladder, not two products. Everyone starts on the basic rung. The worker bots are upgrades you add when you want them.

---

## Before the demo (5-minute checklist)

Run through this once, an hour before, so nothing surprises you on camera.

1. Open a fresh Cowork conversation and type **"Run a Lofty health check."** Confirm it reports the API connected and the leads index present. If the index is missing, type **"Refresh my leads index."**
2. Decide on one safe test lead and know their name.
3. Have one real MLS address ready that you know is an active listing.
4. If you are demoing the full tier, confirm your workers are deployed: type **"List my deployed Lofty workers"** or check dash.cloudflare.com. If they are not live, demo the basic tier only and talk through the full tier from the storyboard at the bottom.
5. Close any window with real client data you do not want on screen.

---

## Demo A: The basic tier (the 5-minute "wow")

This is the demo you lead with. It needs nothing but the API key and works every time. The story you are telling: "I talk to my CRM in plain English and it just does the work."

**Beat 1: Find a lead.**
Type: **"Find the lead [first name last name] in Lofty."**
What to point out: Claude pulls the real record live, no clicking through Lofty. Read off the stage and last activity so the audience sees it is real data.

**Beat 2: Pull their activity.**
Type: **"What has [first name] been doing on my site lately?"**
What to point out: this is the part agents love. You get a plain-English summary of what a lead has been browsing without digging through the timeline.

**Beat 3: Log a note, hands-free.**
Type: **"Log a note on [first name]'s record: spoke today, wants to tour this weekend, pre-approved up to 650k."**
What to point out: the note posts straight to the Lofty timeline. Refresh Lofty in another tab to show it landed. This is the "it writes, not just reads" moment.

**Beat 4: Search the MLS.**
Type: **"Search the MLS for active 3-bed homes under 600k in [neighborhood]."**
What to point out: Claude queries Lofty's MLS feed and hands back a clean list. No portal, no filters to fiddle with.

**Beat 5: Draft the follow-up (and show the safety rail).**
Type: **"Draft a text to [first name] following up on those listings."**
What to point out two things. First, the text is written in your voice and signed with your first name. Second, and say this out loud: Claude always asks before it actually sends anything. Nothing goes out without your yes. That confirmation step is the trust feature, so do not skip mentioning it.

That is the whole basic demo. Five prompts, about five minutes, and every one of them is something the viewer does manually today.

---

## Demo B: The full tier (the worker bots)

Run this second, as the "and here is where it gets hands-free" act. The thread that ties it together is the showing workflow, because it touches all three worker tiers at once.

### The showpiece: schedule a showing end-to-end

This single prompt is the best demo in the whole kit. Type:

**"Schedule [client name] tomorrow at 4:30 at [address], then 5:15 at [second address]."**

Narrate what Claude does as it runs:

1. Pins the right client, even if two leads share the name.
2. Looks up each MLS listing.
3. Creates the calendar invites with the client attached.
4. Posts a showing-log note on the lead with the event ID.
5. Queues an automatic feedback text to fire when each showing ends (this is the Tier 3 worker doing its job).

The line to land: "I typed one sentence and it booked a two-stop tour, put it on my calendar, logged it in the CRM, and lined up the follow-up texts. That follow-up fires on its own, even if my laptop is closed."

### What each worker bot adds (explain, then show if live)

**Tier 2, post-showing feedback form (free).** After a showing, the buyer gets a short form. Their answers land back on the lead's Lofty timeline automatically. Show it by pulling up a lead that has feedback already on the timeline and saying "this came in through the form, no data entry."

**Tier 3, the feedback SMS bot ($5/month).** This is the one that needs the Cloudflare paid plan, because it has to wake up at an exact time. It sends the feedback text the moment a showing ends. Show the queue with: **"What showing texts are queued up?"**

**Tier 4, live lead index (free).** Normally the lead list refreshes on a schedule. This bot updates it the instant a lead acts, through a webhook. The payoff line: "the moment a lead favorites a home, this lead is already current when I ask about them."

### Why the worker bots matter (the one-sentence pitch)

The basic tier works while you are typing. The worker bots work while you are sleeping. That is the difference, and it is the reason to climb the ladder.

---

## If something breaks on camera

Stay relaxed and use it. Type **"That threw an error, what happened?"** The skill has a built-in troubleshooting tree and will explain the fix in plain English. Showing the recovery is its own selling point: the tool diagnoses itself. If a worker tier is down, just fall back to narrating it from the storyboard above. The basic tier alone is a complete demo.

---

## Closing line

However you wrap up, end on the install ask: "If you want it, it is one file. You double-click it, tell Claude to set up Lofty, and you are running in about 15 minutes." Then hand them the `.skill` file or your setup page link.

---

## Quick reference: every demo prompt in order

Basic tier:
1. "Find the lead [name] in Lofty."
2. "What has [name] been doing on my site lately?"
3. "Log a note on [name]'s record: [the note]."
4. "Search the MLS for active 3-bed homes under 600k in [neighborhood]."
5. "Draft a text to [name] following up on those listings."

Full tier:
6. "Schedule [client] tomorrow at 4:30 at [address], then 5:15 at [second address]."
7. "What showing texts are queued up?"
8. Pull up a lead with form feedback already on the timeline.

Recovery:
9. "That threw an error, what happened?"
