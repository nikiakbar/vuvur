## 2026-04-13 - [Accessibility Improvements for Gallery and Viewer]
**Learning:** Adding keyboard navigation (`Enter`/`Space`) and clear `:focus-visible` styles significantly improves usability for users who cannot use a mouse.
**Action:** Always ensure interactive div elements have `tabIndex={0}`, `role="button"`, and appropriate `onKeyDown` handlers.

## 2026-04-14 - [Discoverability of Hover-Only Content]
**Learning:** Information hidden behind hover states (like image dimensions) is often inaccessible to keyboard users unless explicitly handled with `:focus-visible`.
**Action:** Ensure CSS rules that reveal content on `:hover` also include `:focus-visible` for the parent interactive element.
