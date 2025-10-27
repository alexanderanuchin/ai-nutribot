# Codex Diff Journal

## 2025-10-27 – commit d9ebc28

Summary: Align the frontend UI with the refreshed design tokens and theme system from the new UI kit.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/styles/index.css | Import tokens, define derived variables, and replace legacy palette values with token-driven mixes. | frontend | no |
| modify | frontend/src/pages/ResetPassword.tsx | Use design-token feedback colors. | frontend | no |
| modify | frontend/src/pages/Register.tsx | Apply token-based status colors for validation messaging. | frontend | no |
| modify | frontend/src/pages/Dashboard.tsx | Sync inline colors and separators with new palette. | frontend | no |
| modify | frontend/src/pages/Login.tsx | Replace hard-coded error tint with token color. | frontend | no |
| modify | frontend/src/pages/ForgotPassword.tsx | Align async states with token colors. | frontend | no |
| modify | frontend/src/ui/MenuCard.tsx | Move tag, border, and feedback styling to token palette. | frontend | no |
| modify | frontend/src/test/mocks/auth.ts | Use tokenized avatar accent. | frontend | no |
| modify | frontend/src/lib/telegram.ts | Respect global background token for Telegram WebApp shell. | frontend | no |
| modify | frontend/src/api/api.ts | Provide macro colors via theme tokens for UI consumers. | frontend | no |
| modify | frontend/src/components/ProfileSidebar.tsx | Recolor gradients and badges using token-driven variables. | frontend | no |
| modify | frontend/src/components/Logo.tsx | Bind SVG fills and strokes to logo token tones. | frontend | no |
| modify | frontend/src/utils/avatar.ts | Express preset gradients via theme variables. | frontend | no |
| modify | frontend/src/components/GridShimmerCanvas.tsx | Resolve glow/base colors from CSS tokens and react to theme changes. | frontend | no |
| create | docs/codex/DIFF.codex.md | Record traceability for the UI kit migration. | docs | no |

## 2025-10-27 – commit HEAD

Summary: Resolve duplicate keys in the sheet component and align base form controls with the UI kit token system.

| Action | Path | Reason | Impact | Restart/Migration |
| --- | --- | --- | --- | --- |
| modify | frontend/src/components/ui/Sheet.tsx | Add explicit keys to overlay and content for AnimatePresence to eliminate duplicate key warnings. | frontend | no |
| modify | frontend/src/styles/index.css | Update base element styles to consume UI kit tokens exclusively and refine default interactions. | frontend | no |
| modify | docs/codex/CHANGELOG.codex.md | Document the follow-up adjustments to the UI kit migration. | docs | no |
| modify | docs/codex/DIFF.codex.md | Record the additional frontend and documentation updates. | docs | no |
