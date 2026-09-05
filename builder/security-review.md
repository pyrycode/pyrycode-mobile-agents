# Security review pass — adversarial audit of your own plan

You only run this pass when the ticket carries the `security-sensitive` label. The refiner applies that label during refinement. When it's present, the plan you just wrote needs an adversarial re-read before you commit it and start implementing. This file is the checklist and the framing; it lives in the agents repo, so read it as `$AGENTS_REPO_PATH/builder/security-review.md` — it is not inside your worktree.

## Mindset shift

You are no longer the designer. You are an adversary reviewing the plan for exploitability, with the explicit assumption that **the plan has holes**. The default verdict is FAIL until you've walked every applicable category below and found nothing.

Two failure modes to actively resist:

1. **Self-bias.** You wrote this plan ten minutes ago, and in this pipeline you are also the one about to implement it. You believe in it twice over. The whole point of this pass is to find what you missed. If your gut says "this looks fine," that's the smell — go deeper, not shallower.
2. **Coverage theatre.** Walking the checklist and writing "✓ N/A" for each category is worth nothing. For each category, either name a concrete finding — naming the symbol it lives in, or a specific scenario the plan doesn't address — or explicitly state the design decision that makes the category not applicable.

## Categories — walk each one

For each category, the question to answer is: *given this plan, what's the worst thing a hostile actor (or a buggy caller, or a confused implementer) could trigger?*

### 1. Trust boundaries

- Where in the design does data cross from "untrusted" to "trusted"? (Relay socket → process, QR / paste-code payload → pairing state, daemon frame → parsed model → Compose, push payload → app state, file → memory.)
- Is the boundary explicit (single function, named type) or scattered (parsed in three places)?
- Who decides what "trusted" means for each boundary, and does the plan document it?
- Do downstream callers know they're now holding trusted vs untrusted data? (Type system signal — a sealed decoded type vs a raw `String`? Comment? Convention?)
- Daemon-authored text is untrusted relative to the UI. A new inbound verb that carries text into Compose needs a length bound and a render path that treats it as text, never as markup, a URL, a filename or a log line.

### 2. Tokens, secrets, credentials

- How are tokens generated (`SecureRandom` vs `kotlin.random.Random` / `java.util.Random`; sufficient entropy)?
- How are tokens stored (plain `SharedPreferences`? `EncryptedSharedPreferences`? Android Keystore-wrapped, like the device static key and paired-server key stores under `data/crypto/`? what's the threat model that justifies the storage choice)? Reject plain `SharedPreferences` and plaintext files for tokens on sight.
- Where do tokens appear in logs (`Log.d`, `Timber`), error messages, crash reports, or stack traces?
- Token lifecycle — creation, storage, rotation, revocation, expiry. Are all four addressed?
- For revocation: is it possible? Granular (per-device) or all-or-nothing? How is revocation propagated from the daemon to the phone (and vice versa)?

### 3. File / storage operations

- Path traversal — does any code path concatenate untrusted input (QR payload, deep link, push notification body, a daemon-supplied filename on an attachment frame) into a filesystem path without canonicalisation + boundary check (`File.canonicalPath` against a known root)?
- TOCTOU — does the plan do `File.exists()` then `File.inputStream()` (or similar check-then-use) on a path the caller controls? If so, how does the design prevent the swap-during-the-gap attack?
- Storage scope — is sensitive data in app-private storage (`Context.filesDir`, `Context.MODE_PRIVATE`) and NOT in `getExternalFilesDir` / `MediaStore` / world-readable locations? Does the plan say it explicitly?
- Encryption at rest — for secrets (device tokens, cached message bodies if E2E-decrypted): `EncryptedSharedPreferences`, `EncryptedFile` (AndroidX Security), or Room with SQLCipher? The plan must name the choice.
- Atomic writes — does the design use `File.renameTo` (or `Files.move(..., ATOMIC_MOVE)` on API 26+) for files that could leave partial state if the app is killed mid-write (paired-server state, conversations cache, draft state)?
- Backup / `allowBackup` — does the plan consider whether sensitive files should be excluded from auto-backup (`android:fullBackupContent` / `android:dataExtractionRules`)?

### 4. Inter-process / Android attack surface

- Intent handling — for every exported `Activity` / `Service` / `BroadcastReceiver`, what does it accept? Are extras validated (type, length, shape)? Is `android:exported` minimised?
- Deep links — if the plan adds an `<intent-filter>` that handles `https://` or a custom scheme (e.g. the QR-pair fallback URL), what host/path constraints prevent third-party apps from triggering the same handler with attacker-controlled data?
- Pending intents — `PendingIntent.FLAG_IMMUTABLE` for any pending intent whose extras shouldn't be modifiable by the receiver (mandatory on API 31+).
- Push — if the plan touches the FCM wake path, what does the app do with the payload? A push body must wake the connection, never carry content the UI renders or a path the app opens.
- Content providers — if the plan adds one, what's the permission model? Path traversal in `Uri` parsing?
- WebView — if the plan uses one, is `setJavaScriptEnabled(true)` justified? Is `setAllowFileAccess` minimized? Are deep-link redirects from the WebView validated? A WebView that renders daemon-authored text is a MUST FIX.

### 5. Cryptographic primitives

- RNG: `SecureRandom` everywhere randomness is security-relevant; `kotlin.random.Random` / `java.util.Random` is acceptable only for non-security uses (jitter, test fixtures, animation seeds).
- Primitives: pick standards (TLS via JSSE / OkHttp defaults, hashing via `MessageDigest.getInstance("SHA-256")`, key derivation via Argon2 — `de.mkammerer:argon2-jvm` — or `PBKDF2WithHmacSHA256` if Argon2 is overkill). Reject hand-rolled crypto on sight.
- Noise handshake: `Noise_IK_25519_ChaChaPoly_BLAKE2s` comes from the vendored `noise-java` library under `com/southernstorm/noise/` (ADR 0004) through `NoiseIkSession`. If the plan hand-rolls any part of the handshake, key schedule, or AEAD framing, that's a MUST FIX.
- Key storage — Android Keystore for hardware-backed keys; `EncryptedSharedPreferences` (uses Keystore under the hood) for the common case.
- Key / nonce reuse — does the design accidentally use the same key/nonce for two purposes or two sessions? Noise nonces are per-direction counters; a reset-without-rekey is catastrophic. Verify the plan never reuses a `(key, nonce)` pair.
- Constant-time comparison — is `MessageDigest.isEqual` (constant-time in modern JDK) used wherever attacker-controlled values are compared to secrets? Never `==` / `String.equals` for token compare.

### 6. Network & I/O

- Frame size limits — for the WebSocket connection to the relay, every inbound message needs a max-size cap. OkHttp's `WebSocket` reader has a default max; verify the plan doesn't lift it without justification. An uncapped frame is a memory-exhaustion vector from a hostile relay.
- Relay URL validation — the QR pairing payload carries the relay URL. Does the plan validate it before use: scheme allowlist (`wss://` only), host check, no embedded credentials? An unvalidated relay URL lets a malicious QR point the phone at an attacker-controlled endpoint.
- Header validation — for the daemon-side WS-upgrade, the phone supplies `x-pyrycode-server` and `x-pyrycode-token`. If the phone ever accepts daemon-supplied identifiers, the same presence / length / shape rule applies on receive.
- Timeout discipline — `OkHttpClient.Builder()` must set `.connectTimeout`, `.readTimeout`, `.writeTimeout`, and `.callTimeout`. Defaults can hang forever on a slow / hostile relay. Is there a ping/pong with a liveness timeout that tears down a dead connection?
- TLS configuration — `ConnectionSpec.MODERN_TLS` (TLS 1.2+), or `RESTRICTED_TLS` if appetite allows (TLS 1.3 only). Reject `COMPATIBLE_TLS` for production. Reject `ws://` for production.
- Certificate pinning — for the relay endpoint, does the plan pin the relay's certificate (or a CA path)? Pinning has tradeoffs (rotation pain) — if the plan rejects pinning, it should say why.
- Reconnect discipline — the relay supervisor already carries capped-exponential backoff. Does the plan keep it, and does an auth failure back off rather than spin into a token-exhaustion loop?
- Background work — for `WorkManager` / `JobScheduler` jobs that handle network I/O, is the network-type constraint set? Backoff on auth failure?
- Slow-server resistance — does the design have a per-message read deadline beyond the OkHttp call timeout?

### 7. Error messages, logs, telemetry

- What goes in error messages — generic for user-facing UI (Toast/Snackbar/banner), specific for `Timber.d` / Logcat?
- Do error messages leak: tokens, keys, Noise transcripts, full headers, file paths, internal state, stack traces? Crash reporters capture stack traces and message bodies — strip secrets first.
- Logs — what fields are MUST-NOT-log (payloads, full headers, tokens, message bodies on E2E paths, Noise handshake material), what fields are MUST-log (event type, server-id, conn-id, host)?
- Telemetry/metrics — do they aggregate user-identifiable data the user didn't consent to? Are analytics opt-in or opt-out, and does the plan say which?
- Logcat in release — is verbose logging planted only in debug, or does it leak to Logcat in release builds (visible to ADB / other apps with `READ_LOGS` on rooted devices)?

### 8. Concurrency

- Coroutine scope — for every coroutine the plan launches, which scope owns it (`viewModelScope`, `lifecycleScope`, application-scope), and what cancels it? Long-lived background work that outlives a `ViewModel` is a common leak.
- Cancellation safety — does the design check `isActive` / use cancellation-cooperative APIs at suspension points? Is `withContext(NonCancellable)` used only where genuinely needed (cleanup blocks)?
- Mutex ordering — if the design takes multiple `kotlinx.coroutines.sync.Mutex`es, is the order documented and consistent across call sites?
- Check-then-act on shared state — does the design read `StateFlow` / `MutableStateFlow` then mutate it across a suspension point, without `update {}` or a mutex held across both?
- Shutdown safety — what happens if the app is killed mid-write (process death, `onLowMemory`)? Mid-WebSocket-send? Are partial states recoverable on next start? `LifecycleConnectionDriver` closes the socket on background — does the plan's state survive that?
- Duplicate connections — can two relay sockets open at once (rapid foreground/background flips plus a stale one that never closed)? Does the design guarantee a single live transport through the supervisor?
- Hot vs cold flows — does the plan accidentally make a hot flow (subscriber-shared) where a cold flow (per-collector) was intended, leaking data across screens?

### 9. Threat model alignment

- The wire-protocol security model lives upstream in the `pyrycode` repo (`docs/protocol-mobile.md` § Security model, ADR 025). Does the design address each mobile-relevant threat?
- Mobile-specific threats to name and either address or explicitly defer:
  - **Malicious / compromised relay** — it is content-blind (it can't read inside the Noise session) but it is on-path: it can drop, delay, reorder, or flood. Does the design survive a hostile relay without leaking plaintext or hanging?
  - **Token theft from disk** — an attacker with read access to app-private storage on a rooted device. Does Keystore-wrapping actually raise the bar here?
  - **Hostile daemon frame** — the daemon (or something impersonating it inside the session) returns malformed or oversized data. Is every frame decoded defensively and rendered as text?
  - **UI-side leakage** — screenshot leakage, accessibility-service eavesdropping, screen-overlay attacks, third-party keyboard logging on token entry.
- If a threat is out of scope for this ticket, the plan should NAME it as out of scope and note who picks it up.

## Decision

After walking the categories, classify each finding:

- **MUST FIX** — exploitable as designed; the plan must change before you commit it.
- **SHOULD FIX** — concerning but recoverable downstream (you add the check in Phase B; the verifier checks it landed). Note in the plan; don't gate on it.
- **OUT OF SCOPE** — explicitly deferred to a future ticket. Name the future ticket.

Verdict:
- **Any MUST FIX** → FAIL. Revise the plan to address each, then re-run this checklist from the top. Do not commit the plan yet.
- **No MUST FIX** → PASS. Append the security-review section to the plan (format below), then commit it and proceed to Phase B.

## Output format — append to the plan

Add a new section at the end of `docs/specs/architecture/{ticket}-{slug}.md`:

```markdown
## Security review

**Verdict:** PASS

**Findings:**

- [Trust boundaries] No findings — design has a single explicit boundary at `PairingRepository`'s `validatePairingPayload`; downstream code holds parsed types only.
- [Tokens] SHOULD FIX — plan doesn't specify storage choice for the device token. Use `EncryptedSharedPreferences` in Phase B, never plain `SharedPreferences`; the verifier must check.
- [Network & I/O] No findings — plan inherits the `OkHttpClient` with timeouts from `OkHttpFactory`'s pattern and keeps the supervisor's backoff.
- [Concurrency] OUT OF SCOPE — application-scope WebSocket lifecycle deferred to ticket #N.
- [...]

**Reviewer:** builder (self-review per `builder/security-review.md`)
**Date:** <YYYY-MM-DD>
```

If verdict is FAIL, do NOT commit the plan yet. Revise inline, then re-run.
