# Security review pass — adversarial audit of your own spec

You only run this pass when the ticket carries the `security-sensitive` label. PO applies that label during refinement (see `po/CLAUDE.md`). When it's present, the spec you just wrote needs an adversarial re-read before ready:architect lands. This file is the checklist and the framing.

## Mindset shift

You are no longer the architect. You are an adversary reviewing the spec for exploitability, with the explicit assumption that **the spec has holes**. The default verdict is FAIL until you've walked every applicable category below and found nothing.

Two failure modes to actively resist:

1. **Self-bias.** You wrote this spec ten minutes ago. You believe in it. The whole point of this pass is to find what you missed. If your gut says "this looks fine," that's the smell — go deeper, not shallower.
2. **Coverage theatre.** Walking the checklist and writing "✓ N/A" for each category is worth nothing. For each category, either name a concrete finding (with file:line, or with a specific scenario the spec doesn't address) or explicitly state the design decision that makes the category not applicable.

## Categories — walk each one

For each category, the question to answer is: *given this spec, what's the worst thing a hostile actor (or a buggy caller, or a confused developer) could trigger?*

### 1. Trust boundaries

- Where in the design does data cross from "untrusted" to "trusted"? (Network → process, file → memory, subprocess stdout → parent state.)
- Is the boundary explicit (single function, named type) or scattered (parsed in three places)?
- Who decides what "trusted" means for each boundary, and does the spec document it?
- Do downstream callers know they're now holding trusted vs untrusted data? (Type system signal? Comment? Convention?)

### 2. Tokens, secrets, credentials

- How are tokens generated (`SecureRandom` vs `kotlin.random.Random` / `java.util.Random`; sufficient entropy)?
- How are tokens stored (plain `SharedPreferences`? `EncryptedSharedPreferences`? Android Keystore-wrapped? what's the threat model that justifies the storage choice)?
- Where do tokens appear in logs (`Log.d`, `Timber`), error messages, crash reports (Crashlytics), or stack traces?
- Token lifecycle — creation, storage, rotation, revocation, expiry. Are all four addressed?
- For revocation: is it possible? Granular (per-device) or all-or-nothing? How is revocation propagated from the binary to the phone (and vice versa)?

### 3. File / storage operations

- Path traversal — does any code path concatenate user input (QR payload, deep link, push notification body) into a filesystem path without canonicalisation + boundary check (`File.canonicalPath` against a known root)?
- TOCTOU — does the spec do `File.exists()` then `File.inputStream()` (or similar check-then-use) on a path the caller controls? If so, how does the design prevent the swap-during-the-gap attack?
- Storage scope — is sensitive data in app-private storage (`Context.filesDir`, `Context.MODE_PRIVATE`) and NOT in `getExternalFilesDir` / `MediaStore` / world-readable locations? Does the spec say it explicitly?
- Encryption at rest — for secrets (device tokens, cached message bodies if E2E-decrypted): `EncryptedSharedPreferences`, `EncryptedFile` (AndroidX Security), or Room with SQLCipher? Spec must name the choice.
- Atomic writes — does the design use `File.renameTo` (or `Files.move(..., ATOMIC_MOVE)` on API 26+) for files that could leave partial state if the app is killed mid-write (devices.json, conversations cache, draft state)?
- Backup / `allowBackup` — does the spec consider whether sensitive files should be excluded from auto-backup (`android:fullBackupContent` / `android:dataExtractionRules`)?

### 4. Inter-process / Android attack surface

- Intent handling — for every exported `Activity` / `Service` / `BroadcastReceiver`, what does it accept? Are extras validated (type, length, shape)? Is `android:exported` minimised?
- Deep links — if the spec adds a `<intent-filter>` that handles `https://` or a custom scheme (e.g. the QR-pair fallback URL), what host/path constraints prevent third-party apps from triggering the same handler with attacker-controlled data?
- Pending intents — `PendingIntent.FLAG_IMMUTABLE` for any pending intent whose extras shouldn't be modifiable by the receiver (mandatory on API 31+).
- Content providers — if the spec adds one, what's the permission model? Path traversal in `Uri` parsing?
- WebView — if the spec uses one, is `setJavaScriptEnabled(true)` justified? Is `setAllowFileAccess` minimized? Are deep-link redirects from the WebView validated?

### 5. Cryptographic primitives

- RNG: `SecureRandom` everywhere randomness is security-relevant; `kotlin.random.Random` / `java.util.Random` is acceptable only for non-security uses (jitter, test fixtures, animation seeds).
- Primitives: pick standards (TLS via JSSE / OkHttp defaults, hashing via `MessageDigest.getInstance("SHA-256")`, key derivation via Argon2 — `de.mkammerer:argon2-jvm` — or `PBKDF2WithHmacSHA256` if Argon2 is overkill). Reject hand-rolled crypto on sight.
- Key storage — Android Keystore for hardware-backed keys; `EncryptedSharedPreferences` (uses Keystore under the hood) for the common case.
- Key reuse — does the design accidentally use the same key/nonce for two purposes? Same key in `EncryptedSharedPreferences` and `EncryptedFile`?
- Constant-time comparison — is `MessageDigest.isEqual` (constant-time in modern JDK) used wherever attacker-controlled values are compared to secrets? Never `==` / `String.equals` for token compare.

### 6. Network & I/O

- Frame size limits — for the WebSocket connection to the relay, every inbound message needs a max-size cap. OkHttp's `WebSocket` reader has a default max; verify the spec doesn't lift it without justification.
- Header validation — for the binary's WS-upgrade, the phone supplies `x-pyrycode-server` and `x-pyrycode-token`. Does the spec validate presence, length, and shape on receive (binary-side; mobile is the sender, but if mobile ever accepts binary-supplied identifiers, same rule applies)?
- Timeout discipline — `OkHttpClient.Builder()` must set `.connectTimeout`, `.readTimeout`, `.writeTimeout`, and `.callTimeout`. Defaults can hang forever on a slow / hostile relay.
- TLS configuration — `ConnectionSpec.MODERN_TLS` (TLS 1.2+), or `RESTRICTED_TLS` if appetite allows (TLS 1.3 only). Reject `COMPATIBLE_TLS` for production.
- Certificate pinning — for the relay endpoint, does the spec pin the relay's certificate (or a CA path)? Pinning has tradeoffs (rotation pain) — if the spec rejects pinning, it should say why.
- Background work — for `WorkManager` / `JobScheduler` jobs that handle network I/O, is the network-type constraint set (`NetworkType.UNMETERED` etc.)? Backoff on auth failure to avoid token-exhaustion loops?
- Slow-server resistance — does the design have a per-message read deadline beyond the OkHttp call timeout?

### 7. Error messages, logs, telemetry

- What goes in error messages — generic for user-facing UI (Toast/Snackbar), specific for `Timber.d` / Logcat?
- Do error messages leak: tokens, full headers, file paths, internal state, stack traces? Crash reporters (Crashlytics, Sentry) capture stack traces and message bodies — strip secrets first.
- Logs — what fields are MUST-NOT-log (payloads, full headers, tokens, message bodies on E2E paths), what fields are MUST-log (event type, server-id, conn-id, host)?
- Telemetry/metrics — do they aggregate user-identifiable data the user didn't consent to? Are analytics opt-in or opt-out, and does the spec say which?
- Logcat in release — is `Timber` planted only in debug, or does verbose logging leak to Logcat in release builds (visible to ADB / other apps with `READ_LOGS` on rooted devices)?

### 8. Concurrency

- Coroutine scope — for every coroutine the spec launches, which scope owns it (`viewModelScope`, `lifecycleScope`, application-scope), and what cancels it? Long-lived background work that outlives a `ViewModel` is a common leak.
- Cancellation safety — does the design check `isActive` / use cancellation-cooperative APIs at suspension points? Is `withContext(NonCancellable)` used only where genuinely needed (cleanup blocks)?
- Mutex ordering — if the design takes multiple `kotlinx.coroutines.sync.Mutex`es, is the order documented and consistent across call sites?
- TOCTOU on shared state — does the design check-then-mutate `StateFlow` / `MutableStateFlow` without using `update {}` or holding a mutex across both?
- Shutdown safety — what happens if the app is killed mid-write (process death, `onLowMemory`)? Mid-WebSocket-send? Are partial states recoverable on next start?
- Hot vs cold flows — does the spec accidentally make a hot flow (subscriber-shared) where a cold flow (per-collector) was intended, leaking data across screens?

### 9. Threat model alignment

- The mobile wire-protocol spec lives in upstream `pyrycode/pyrycode/docs/protocol-mobile.md` § Security model (PR #188 once merged). Does the design address each mobile-relevant threat?
- Mobile-specific threats not covered by the protocol spec (UI screenshot leakage, accessibility-service eavesdropping, screen-overlay attacks, malicious deep links, third-party keyboard logging on token entry) — if any apply to this ticket, the spec must name them and either address or explicitly defer.
- If a threat is out of scope for this ticket, the spec should NAME it as out of scope and note who picks it up.

## Decision

After walking the categories, classify each finding:

- **MUST FIX** — exploitable as designed; spec must change before ready:architect.
- **SHOULD FIX** — concerning but recoverable downstream (developer adds a check, code-review catches it). Note in the spec; don't gate on it.
- **OUT OF SCOPE** — explicitly deferred to a future ticket. Name the future ticket.

Verdict:
- **Any MUST FIX** → FAIL. Revise the spec to address each, then re-run this checklist from the top. Do not mark ready:architect yet.
- **No MUST FIX** → PASS. Append the security-review section to the spec (format below), then proceed to ready:architect.

## Output format — append to the spec

Add a new section at the end of `docs/specs/architecture/{ticket}-{name}.md`:

```markdown
## Security review

**Verdict:** PASS

**Findings:**

- [Trust boundaries] No findings — design has a single explicit boundary at `data/PairingRepository.kt`'s `validatePairingPayload` function; downstream code holds parsed types only.
- [Tokens] SHOULD FIX — spec doesn't specify storage choice for the device token. Developer should use `EncryptedSharedPreferences`; code-review must check.
- [Network & I/O] No findings — spec inherits `OkHttpClient` with timeouts from `network/OkHttpFactory.kt`'s pattern.
- [Concurrency] OUT OF SCOPE — application-scope WebSocket lifecycle deferred to ticket #N.
- [...]

**Reviewer:** architect (self-review per `architect/security-review.md`)
**Date:** <YYYY-MM-DD>
```

If verdict is FAIL, do NOT commit the spec yet. Revise inline, then re-run.
