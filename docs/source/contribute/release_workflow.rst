==============================
Release & Hot-Fix Workflow
==============================

This document explains how to cut a new feature release or a hot-fix in the
`ostruct` project.  It is intentionally lightweight.

.. contents:: Table of Contents
   :local:
   :depth: 2

Branching model (TL;DR)
=======================

* **``main``** – the only long-lived branch.  All daily work happens here.
* **Tags** – every published version (``v1.1.0``, ``v1.1.1`` …) is an *annotated* git tag on
  ``main``.
* **Hot-fix branch** – created *only if* you must fix the current release *without*
  pulling in unreleased work that is already on ``main``.  Delete it right after the
  tag is pushed.

Workflow for a new feature release
----------------------------------

Before writing code
~~~~~~~~~~~~~~~~~~~
1.  Make sure you are on ``main`` and up-to-date::

        git switch main
        git pull --ff-only origin main

2.  Create a short feature branch *(optional but recommended)*::

        git switch -c feature/<short-name>

3.  Implement the feature, update tests, **update ``CHANGELOG.md`` incrementally**.
4.  Open a PR (even if you merge it yourself) – CI must be green.

Tagging the release
~~~~~~~~~~~~~~~~~~~
1.  Merge your PR into ``main``.
2.  Verify ``CHANGELOG.md`` and docs are ready.
3.  Tag and push::

        git switch main
        git pull --ff-only
        git tag -a v1.1.0 -m "v1.1.0: short summary of highlights"
        git push origin main v1.1.0

That's it—CI publishes to PyPI, updates Homebrew, builds Read the Docs, etc.

Workflow for a hot-fix release
------------------------------

Scenario A – fix is **already** on ``main`` and safe to release
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1.  Ensure ``CHANGELOG.md`` has a *Hot-fix* entry.
2.  Tag and push directly from ``main``::

        git switch main && git pull --ff-only
        git tag -a v1.1.1 -m "v1.1.1: urgent bug-fix …"
        git push origin main v1.1.1

Scenario B – fix must **not** include unreleased work on ``main``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1.  Create a throw-away branch from the last tag::

        git switch -c hotfix/v1.1.1 v1.1.0

2.  Cherry-pick or implement just the necessary commits.
3.  Update ``CHANGELOG.md`` in that branch.
4.  Tag & push::

        git tag -a v1.1.1 -m "v1.1.1: security hot-fix …"
        git push origin hotfix/v1.1.1 v1.1.1

5.  **After CI turns green**, delete the branch::

        git push origin --delete hotfix/v1.1.1
        git branch -D hotfix/v1.1.1

Do's and Don'ts
===============

Do ✓
-----
* Keep ``main`` in a releasable state; let CI protect you.
* Use **annotated tags** (`-a`) for every version – they drive dynamic versioning.
* Update the **CHANGELOG** steadily while you code.
* Delete merged or obsolete branches immediately.
* Test the published package with ``pipx install ostruct-cli==<version>``.

Don't ✗
--------
* ✗ Don't create long-lived ``release/x.y`` branches – history gets messy.
* ✗ Don't edit the ``version`` in ``pyproject.toml`` – tags control the version.
* ✗ Don't force-push to shared branches or tags.

Where to find this guide
========================

* **Docs:** ``docs/source/contribute/release_workflow.rst`` (rendered on Read the Docs).
* **Quick link in repo root:** The first section of ``RELEASE_CHECKLIST.md`` links back
  here for easy discovery.
