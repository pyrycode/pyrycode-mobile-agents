# Security review of your own plan

Run this pass when the issue carries the `security-sensitive` label, after writing the plan and before committing it. The refiner applies the label. The pass appends a `## Security review` section to the plan, and the verifier fails a labelled ticket whose plan has none.

## Review as an adversary

For this pass you are not the designer. You are reviewing the plan for what a hostile actor, a buggy caller or a confused implementer could trigger, on the assumption that it has holes.

Two things make a self-review weak, and the pass exists to counter both:

- **You believe in the plan twice over.** You wrote it minutes ago and you are about to implement it. A sense that it looks fine is the cue to look harder.
- **A checklist can be walked without finding anything.** Writing "N/A" against each category is worth nothing. For each category, either name a concrete finding, with the symbol it lives in or a scenario the plan does not handle, or state the design decision that makes the category not apply. "Nothing user-controlled flows here" is itself a finding under trust boundaries, naming the symbol that enforces it.

Each plan is reviewed on its own. Do not cite another ticket's review in place of this one.

## Categories

For each, ask: given this plan, what is the worst thing that could be triggered?

### 1. Trust boundaries

- Where does data cross from untrusted to trusted? Relay socket to process, QR or paste-code payload to pairing state, daemon frame to parsed model to Compose, push payload to app state, file to memory.
- Is each boundary one explicit function or named type, or is parsing scattered across several places?
- Does the plan say what "trusted" means at each boundary, and can downstream code tell trusted from untrusted data, for example a sealed decoded type rather than a raw `String`?
- Daemon-authored text is untrusted relative to the UI. A new inbound verb that carries text into Compose needs a length bound and a render path that treats it as text, never as markup, a URL, a filename or a log line.

### 2. Tokens, secrets and credentials

- Generation: `SecureRandom`, not `kotlin.random.Random` or `java.util.Random`, with enough entropy.
- Storage: `EncryptedSharedPreferences` or Keystore-wrapped stores like the device static key and paired-server key stores under `data/crypto/`, with the threat model that justifies the choice. Plain `SharedPreferences` and plaintext files are not acceptable for tokens.
- Exposure: do tokens reach `Log.d`, `Timber`, error messages, crash reports or stack traces?
- Lifecycle: creation, storage, rotation and revocation all addressed. Is revocation possible, per device or all at once, and how does it propagate between daemon and phone?

### 3. Files and storage

- Path traversal: does any path include untrusted input, such as a QR payload, deep link, push body or daemon-supplied attachment filename, without canonicalising and checking `File.canonicalPath` against a known root?
- Check then use: an `exists` check followed by opening a caller-controlled path, and how the design prevents a swap in between.
- Scope: sensitive data in app-private storage such as `Context.filesDir`, not `getExternalFilesDir`, `MediaStore` or anything world-readable. The plan says so explicitly.
- Encryption at rest for secrets and decrypted message bodies: `EncryptedSharedPreferences`, `EncryptedFile`, or Room with SQLCipher. The plan names the choice.
- Atomic writes for state that a kill mid-write could corrupt, such as paired-server state, the conversations cache or drafts: write and rename, or `Files.move` with `ATOMIC_MOVE`.
- Backup: whether sensitive files are excluded through `android:dataExtractionRules` or `android:fullBackupContent`.

### 4. Android attack surface

- Exported components: what each exported `Activity`, `Service` or `BroadcastReceiver` accepts, whether extras are validated for type, length and shape, and whether `android:exported` is kept to the minimum.
- Deep links: host and path constraints on any `https://` or custom-scheme intent filter, such as a QR pairing fallback URL, so a third-party app cannot drive the handler with its own data.
- Pending intents use `PendingIntent.FLAG_IMMUTABLE` unless the receiver must change the extras.
- Push: a push payload wakes the connection. It never carries content the UI renders or a path the app opens.
- Content providers: the permission model, and path traversal in `Uri` parsing.
- WebView: whether JavaScript and file access are justified and minimised, and whether redirects are validated. A WebView that renders daemon-authored text is a MUST FIX.

### 5. Cryptography

- `SecureRandom` wherever randomness is security-relevant. Other random sources only for jitter, fixtures or animation.
- Standard primitives: TLS through OkHttp defaults, `MessageDigest.getInstance("SHA-256")`, Argon2 through `de.mkammerer:argon2-jvm` or `PBKDF2WithHmacSHA256` for key derivation. Hand-rolled crypto is a MUST FIX.
- The Noise handshake `Noise_IK_25519_ChaChaPoly_BLAKE2s` comes from the vendored `noise-java` under `com/southernstorm/noise/`, per ADR 0004, through `NoiseIkSession`. Hand-rolling any part of the handshake, key schedule or AEAD framing is a MUST FIX.
- Key storage in the Android Keystore, or `EncryptedSharedPreferences`, which uses it.
- Key and nonce reuse: Noise nonces are per-direction counters, so a reset without a rekey is catastrophic. Check that no `(key, nonce)` pair is reused across purposes or sessions.
- Comparing attacker-controlled values with secrets uses `MessageDigest.isEqual`, never `==` or `String.equals`.

### 6. Network and I/O

- Frame size: every inbound WebSocket message from the relay has a size cap. Lifting OkHttp's default without a reason opens a memory-exhaustion route for a hostile relay.
- Relay URL from the QR payload: validated before use, with `wss://` only, a host check and no embedded credentials. Otherwise a malicious QR points the phone at an attacker's endpoint.
- Headers: the phone sends `x-pyrycode-server` and `x-pyrycode-token` on the upgrade. Any daemon-supplied identifier the phone accepts gets the same presence, length and shape checks.
- Timeouts: `OkHttpClient.Builder()` sets `connectTimeout`, `readTimeout`, `writeTimeout` and `callTimeout`, and a ping with a liveness timeout tears down a dead connection. Defaults can hang on a slow or hostile relay.
- TLS: `ConnectionSpec.MODERN_TLS` or `RESTRICTED_TLS`, never `COMPATIBLE_TLS` or `ws://` in production.
- Certificate pinning for the relay, or a stated reason for not pinning.
- Reconnect: the relay supervisor's capped exponential backoff is kept, and an auth failure backs off rather than looping.
- Background jobs in `WorkManager` or `JobScheduler` set a network constraint and back off on auth failure.
- A per-message read deadline beyond the call timeout, against a slow server.

### 7. Errors, logs and telemetry

- User-facing errors in toasts, snackbars and banners are generic. Detail goes to debug logs only.
- Nothing leaks tokens, keys, Noise transcripts, full headers, file paths, internal state or stack traces. Crash reporters capture messages and stacks, so strip secrets first.
- The plan names what must never be logged, such as payloads, full headers, tokens, message bodies on encrypted paths and handshake material, and what must be, such as event type, server id, connection id and host.
- Telemetry: whether it aggregates identifiable data, and whether it is opt-in.
- Verbose logging is debug-only, so nothing leaks to Logcat in release builds.

### 8. Concurrency

- Every coroutine has an owning scope, `viewModelScope`, `lifecycleScope` or an application scope, and something that cancels it. Background work that outlives its ViewModel is a common leak.
- Suspension points cooperate with cancellation, and `withContext(NonCancellable)` appears only in cleanup.
- Several `Mutex`es are always taken in one documented order.
- No read of a `StateFlow` followed by a write across a suspension point without `update {}` or a held mutex.
- Process death mid-write or mid-send leaves recoverable state. `LifecycleConnectionDriver` closes the socket on background, and the plan's state survives that.
- Rapid foreground and background flips cannot leave two relay sockets open; the supervisor keeps a single live transport.
- No hot flow shared across collectors where a cold flow was meant, which would leak data between screens.

### 9. Threat model

The wire-protocol security model lives in the `pyrycode` repo, in `docs/protocol-mobile.md` under "Security model" and ADR 025. Check the design against each mobile-relevant threat, and name it as handled or as out of scope with who picks it up:

- **A malicious or compromised relay.** It cannot read inside the Noise session but sits on the path and can drop, delay, reorder or flood. The design must not leak plaintext or hang.
- **Token theft from disk** by an attacker with read access to app-private storage on a rooted device. Does Keystore wrapping actually raise the bar?
- **A hostile daemon frame**, malformed or oversized, from the daemon or something impersonating it inside the session. Every frame is decoded defensively and rendered as text.
- **UI-side leakage** through screenshots, accessibility services, screen overlays or a third-party keyboard during token entry.

## Decision

Classify each finding:

- **MUST FIX**: exploitable as designed. The plan changes before you commit it.
- **SHOULD FIX**: concerning but recoverable in implementation. Note it in the plan; you add the check in Phase B and the verifier checks it landed.
- **OUT OF SCOPE**: deferred to a named future ticket.

Any MUST FIX makes the verdict FAIL. Revise the plan, walk the categories again against the revised design, and do not commit until the verdict is PASS. With no MUST FIX the verdict is PASS: append the section below, commit the plan and go on to Phase B.

## Section to append to the plan

Add this at the end of `docs/specs/architecture/<ticket>-<slug>.md`:

```markdown
## Security review

**Verdict:** PASS

**Findings:**

- [Trust boundaries] No findings. The design has one explicit boundary at `PairingRepository`'s `validatePairingPayload`; downstream code holds parsed types only.
- [Tokens] SHOULD FIX. The plan does not name storage for the device token. Use `EncryptedSharedPreferences` in Phase B, never plain `SharedPreferences`; the verifier checks it.
- [Network & I/O] No findings. The plan reuses the `OkHttpClient` timeouts from `OkHttpFactory` and keeps the supervisor's backoff.
- [Concurrency] OUT OF SCOPE. Application-scope WebSocket lifecycle is deferred to ticket #N.
- [...]

**Reviewer:** builder (self-review per `builder/security-review.md`)
**Date:** <YYYY-MM-DD>
```
