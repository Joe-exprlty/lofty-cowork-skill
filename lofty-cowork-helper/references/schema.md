# Lofty API Response Shapes

Field-by-field catalog of what comes back from the Lofty read endpoints. Load this when you need to know "what fields exist on a lead?" or "what does a `leadPropertyList` row look like?" before writing filters, mappers, or a new helper.

All shapes were verified live against a real Lofty account in May 2026. Specific ID values (stage IDs, source IDs, tag IDs) are per-team and will differ on every account, so this doc only documents shapes, not values.

---

## `GET /v1.0/leads` response wrapper

```text
{
  "_metadata": {
    "collection": "leads",
    "limit": 25,            # always 25, even if you ask for more
    "offset": 0,
    "total": <int>,         # total leads matching the query, full count, not page size
    "scrollId": "<token>"   # pass back as ?scrollId=... for next 25
  },
  "leads": [ <lead>, <lead>, ... ]
}
```

Useful properties of this shape:

- `_metadata.total` gives the full lead count without paginating (quirk #31).
- `_metadata.scrollId` is the only working pagination cursor (`page` is silently ignored, quirk #29).
- `_metadata.limit` echoes 25 even when you request 50 or 100. Hard cap, server-side (quirk #2).

## `GET /v1.0/leads/{leadId}` response

Wrapped in `{"lead": {...}}` (quirk #8). The starter client auto-unwraps via `get_lead`.

### Lead object top-level fields

Around 60 fields total. Grouped for readability.

**Identity**
```text
leadId            int   # the canonical ID, large 15-digit integer (quirk #25)
leadUserId        int   # internal user ID for the lead, used in leadPropertyList rows
firstName         str
lastName          str
emails            list[str]    # plain strings, not objects (quirk #7)
phones            list[str]    # plain strings, not objects (quirk #7)
phoneStatuses     list[int]    # parallel to phones, one int per phone
birthday          str or null
language          str   # e.g. "en"
```

**Ownership and team**
```text
teamId            int
assignedUserId    int
assignedUser      str   # display name
ownershipId       int
ownershipScope    str   # observed: "PERSONAL"
pondId            int   # 0 if not in a pond
pondName          str or null
lenderUserId      int
```

**Pipeline**
```text
stage                     str   # human label, e.g. "New Leads", "Attempting Contact"
stageId                   int   # per-team integer ID
score                     int
assignCompletionStatus    bool
```

**Source**
```text
source        str   # human label, e.g. "Google", "Website", "Other"
leadSource    int   # per-team numeric source ID. -1 = manual/Other (quirk #30)
leadType      int   # values 1, 2, or -1 observed; meaning not officially decoded
leadTypes     list[int]
```

**Contact permissions**
```text
cannotText       bool
cannotCall       bool
cannotEmail      bool
unsubscription   bool
```

**Address**
```text
streetAddress   str   # often empty
city            str
state           str
zipCode         str
```

**Social and flags**
```text
facebook       str or null
twitter        str or null
privateFlag    bool
hiddenFlag     bool
referredBy     str or null
```

**Qualification**
```text
buyingTimeFrame    str or null   # values: "0-3", "3-6", "6-12", "12+", "Just Looking", "N/A"
sellingTimeFrame   str or null   # same value set
preQual            str or null
fthb               str or null   # first-time home buyer
houseToSell        str or null
mortgage           str           # observed: "N/A"
buyHouse           str           # observed: "N/A"
withBuyerAgent     str or null
withListingAgent   str           # observed: "N/A"
```

**Timestamps** (strings in `YYYY-MM-DDThh:mm:ssGMT` format, NOT full ISO 8601 with offset, quirk #32)
```text
createTime
assignTime
lastUpdateTime
lastTouch
lastVisit
```

**Sub-objects** (shapes documented below)
```text
tags                   list[obj]
groups                 list or null
segments               list or null
leadInquiry            object
leadPropertyList       list[obj]
leadFamilyMemberList   list or null
customAttributes       list[obj]
customRoleList         list[obj]   # always returns the full role catalog
opportunity            object or null
```

---

## `tags[]` row

```text
tagId            int
tagName          str
leadId           int
creatorUserId    int
visibleType      int or str
createTime       str
updateTime       str
```

Filter by tag client-side: `[t for t in lead["tags"] if t["tagName"] == "Buyer"]`.

Tag IDs are per-team and need to be discovered per account.

---

## `leadInquiry` object

This is the lead's saved-search criteria. Lofty's Auto Property Alerts feature uses it to auto-generate listing emails for the lead. Settable via `POST /v1.0/leads/{leadId}/inquiry` (see `extending.md`).

```text
priceMin         int    # -1 means unset (quirk #30)
priceMax         int    # -1 means unset
propertyType     list[str]
bedroomsMin      int    # -1 means unset
bedroomsMax      int    # -1 means unset
bathroomsMin     float or null
bathroomsMax     float or null
locations        list or null
id               int    # 0 if not saved
leadUserId       int
modifyByAgent    bool
createTime       str or null
updateTime       str or null
defaultValue     bool
```

Numeric fields use `-1` to mean "no value", NOT null. Filter with `if v > 0` not `if v is not None`.

---

## `leadPropertyList[]` row

Properties the lead is interested in (saved listings, requested showings, manually added). Modifiable via `POST /v1.0/leads/{leadId}/property`.

```text
id                int
autoListingId     int
listingId         str         # MLS ID, can be empty string
leadUserId        int
label             str         # see label values below
labelList         str         # comma-separated string of labels
labelType         str or null
listingStatus     str         # see status values below
propertySource    str         # see source values below
propertyType      str
streetAddress     str
city              str
state             str
zipCode           str
county            str
price             int         # -1 if unset
bedrooms          int
bathrooms         float
squareFeet        int
lotSize           float       # -1.0 if unset
floors            int         # -1 if unset
parkingSpace      int         # -1 if unset
siteListingUrl    str
pictureUrl        str
mailAddress       bool
note              str
createTime        str
```

Observed `label` values:
```text
High Interest
Home
Left Message
Saved Listing
Requested Showing
```

Observed `listingStatus` values:
```text
Active
Sold
Contingent
Coming Soon
""          # empty string when label is Requested Showing
```

Observed `propertySource` values:
```text
lead_inquiries
register_from_site
Manually Added
Leaved Message       # sic, Lofty typo
Saved
Requested Showing
```

Useful read-only filters:
```text
leads with a Requested Showing property
leads with a Saved Listing
leads watching Active listings
leads who registered from the site (propertySource = "register_from_site")
```

---

## `customAttributes[]` row

```text
attributeName    str    # team-defined name
attributeType    str    # e.g. "text"
value            str    # the actual stored value
params           any or null
```

Custom attribute names are per-team. Use `get_custom_fields()` to discover the team's set.

---

## `customRoleList[]` row

The role catalog (11 entries) is always returned on every lead read, even when nothing is assigned. Field name is `role`, NOT `roleName` (quirk #33).

```text
roleId       int
role         str
assigneeId   int           # 0 if no one assigned
assignee     str or null   # display name if assigned
```

Standard role catalog (roleId values appear consistent across teams; verify):

```text
 20  Referral Partner
 40  Buyer Agent
 50  Co-Agent
 60  LOA
 80  Transaction Coordinator
 90  Internal LO
100  Virtual Assistant (EVA)
110  Showing Assistant
120  Client Specialist
130  ISA
140  Assistant
```

To find who is assigned: `[r for r in lead["customRoleList"] if r["assigneeId"] > 0]`.

---

## `GET /v1.0/leads/{leadId}/activities` row

```text
type             str         # see activity types below
created          int         # epoch MILLISECONDS, not ISO string (quirk #32)
text             str         # freeform description
link             str         # property or page URL if applicable
listing          object or null   # listing snapshot if activity is property-related
pageName         str or null
picture          str or null
scheduledDate    str
```

Observed `type` values:
```text
Request          # property showing request
Browse           # browsed a listing
Favorite         # favorited a listing
Search           # ran a search
```

Convert the timestamp: `datetime.fromtimestamp(act["created"] / 1000)`.

Note: this endpoint returns a LIST directly, not a dict envelope (quirk #26). The starter's `get_lead_activities` handles both shapes.

No bulk activity endpoint exists (quirk #12). For cross-lead activity, subscribe to webhook list 3.

---

## The `-1` = unset convention (quirk #30)

Lofty uses `-1` as a sentinel for "no value" on numeric fields, instead of null:

- `leadInquiry.priceMin`, `priceMax`
- `leadInquiry.bedroomsMin`, `bedroomsMax`
- `leadPropertyList[].price`, `lotSize`, `floors`, `parkingSpace`
- `leadSource` on manually created leads

If you filter by "price greater than zero", use `if v > 0`, not `if v is not None`. Quirk #30 covers this in the quirks list.

---

## Per-team vs. cross-team data

Some fields are per-team integer IDs that will differ on every account:

- `stageId`
- `leadSource` (the integer, not the string)
- `tagId`
- Custom field names and IDs

The strings (`stage`, `source`, `tagName`) are stable enough for grep but the integers are per-team. When building a helper for a specific user's account, probe these once and cache them.

Some fields are consistent across teams (verify before relying on it):

- `customRoleList[]` roleId values (see role catalog above)
- The 12 webhook event type IDs (see quirks.md)
- Activity type strings (Browse, Favorite, Search, Request)
- buyingTimeFrame / sellingTimeFrame value set ("0-3", "3-6", "6-12", "12+", "Just Looking", "N/A")
