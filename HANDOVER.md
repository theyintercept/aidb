# Learning Sequence Manager — Claude Code Handover Brief

## What this project is
A web-based tool for designing, reviewing and managing Victorian Numeracy learning sequences,
built around cognitive load theory. The database is complete and populated. We need to build
the web interface on top of it.

---

## Files to put in your project folder
- `learning_sequence_v2.db` — SQLite database, fully populated
- `schema_v2_1.sql` — schema reference

---

## Database summary
- **83 clusters** across Foundation (#101–125), Year 1 (#201–225), Year 2 (#301–333)
- **291 elements** — numbered with year prefix (Foundation=10xxx, Year 1=20xxx, Year 2=30xxx)
- **83 VC references** linking clusters to Victorian Curriculum 2.0 codes, with full descriptions
- **46 VC content descriptions** — master reference table, Foundation–Level 2 Mathematics
- Full lookup tables seeded: year_levels, strands, cpa_stages, resource_categories,
  file_formats, intrinsic_load_levels

## Key schema decisions to know
- Hierarchy: Year Level → Cluster → Element → Resource
- Elements belong to clusters via `cluster_elements` bridge table (many-to-many)
  — an element can appear in multiple clusters (bridging concept)
- `element_prerequisites` is a self-referential table: element → requires → element
- Intrinsic load on elements: LOW / MEDIUM / HIGH flag
- CPA stage on elements: C / P / A / CP / PA / CPA
- Resources attach to elements (not clusters), 1 resource → 1 element
- Resource pedagogical categories: Sandbox, Instructional Material, Guided Practice,
  Independent Practice, Extension, Activity, Retrieval Practice, Quiz
- File storage: PDF/DOC/images stored as BLOB in database; PPTX stored as file path
- VC references: each cluster can have multiple VC 2.0 codes linked via `vc_references`
- `vc_content_descriptions` is a standalone master reference (46 codes, not cluster-linked)

---

## Tech stack recommendation
- **Flask** (Python) — backend, already familiar from previous version
- **SQLite** — database (single file, no server needed)
- **Jinja2** — templating (comes with Flask)
- **Plain HTML/CSS + minimal JS** — keep it simple, no framework needed
- Run on **port 8080** (port 5000 conflicts on Mac)

---

## Interface requirements

### Navigation
- Sidebar or top nav: Foundation | Year 1 | Year 2
- Within each year level: list of clusters in order

### Cluster view
Shows:
- Cluster number, title, year level, strand
- Rationale (editable text area)
- Sequence notes (editable text area)
- List of elements in sequence order (draggable to reorder)
- VC 2.0 references linked to this cluster (code + description + link)
  — ability to add/remove VC references from the master list
- Published/draft toggle

### Element view
Shows:
- Element number, title, CPA stage, intrinsic load (LOW/MEDIUM/HIGH)
- Learning objective (editable)
- Teacher notes (editable)
- Audio script (editable)
- Which clusters this element belongs to
- Prerequisites (links to other elements) — add/remove
- Resources attached — list with upload capability
- Published/draft toggle

### Resource upload
- Upload PDF, DOC, image → stored as BLOB in database
- Upload PPTX → stored in /uploads folder, path recorded
- Tag with: resource category, audience (teacher/student/both), title, description
- PPTX displays as slideshow viewer (image-per-slide)

### VC 2.0 assignment
- Browse master list (vc_content_descriptions) filtered by strand/level
- Click to link a VC code to the current cluster
- Shows full description text to help decide

### Analysis views (later, not MVP)
- Prerequisite chain visualisation
- Intrinsic load distribution across a cluster
- Elements appearing in multiple clusters (bridging elements)

---

## MVP scope (build first)
1. Browse clusters by year level
2. View cluster detail with its elements
3. Edit cluster fields (title, rationale, sequence notes)
4. View element detail
5. Edit element fields (title, objective, teacher notes, CPA, intrinsic load)
6. Add/remove VC references on a cluster

Leave for later:
- Resource upload
- Prerequisites
- Slideshow viewer
- Analysis views

---

## Useful SQL views already in database
- `v_clusters` — clusters with element count and VC codes joined
- `v_elements` — elements with intrinsic load and CPA joined
- `v_resources` — resources without binary blob (safe for listings)
- `v_prerequisite_chains` — prerequisite relationships
- `v_bridging_elements` — elements appearing in multiple clusters
- `v_vc_references` — full VC reference detail with cluster context

---

## Notes on element numbers
Elements without IDs in the original flat file were auto-numbered in the 9000+ range
per year level (so Year 1 auto-elements = 29000+, Year 2 = 39000+).
These should be renumberable via the GUI.

## Notes on VC references
The `vc_references` table links clusters to VC codes with descriptions.
The `vc_content_descriptions` table is the master reference.
When adding a VC reference to a cluster, look up the code in `vc_content_descriptions`
and copy the description across into `vc_references`.
