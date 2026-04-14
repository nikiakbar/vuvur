## 2026-04-13 - [Accessibility Improvements for Gallery and Viewer]
**Learning:** Adding keyboard navigation (`Enter`/`Space`) and clear `:focus-visible` styles significantly improves usability for users who cannot use a mouse.
**Action:** Always ensure interactive div elements have `tabIndex={0}`, `role="button"`, and appropriate `onKeyDown` handlers.
