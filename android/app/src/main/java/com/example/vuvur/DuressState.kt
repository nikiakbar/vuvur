package com.example.vuvur

/**
 * In-memory duress mode state.
 *
 * Activated when the user enters their passcode **in reverse** at the lock screen.
 * While active, the app behaves as if no media exists and makes no network calls,
 * providing plausible deniability.
 *
 * This state is NEVER written to disk — it lives only for the current process lifetime.
 * Killing and relaunching the app resets it to normal (requiring real passcode entry again).
 */
object DuressState {

    @Volatile
    var isActive: Boolean = false
        private set

    /**
     * Evaluates [entered] against [real] and [duress] codes.
     *
     * @return [UnlockResult.Real]   — correct passcode, normal unlock
     * @return [UnlockResult.Duress] — reversed passcode, activates duress mode then unlocks
     * @return [UnlockResult.Wrong]  — wrong passcode
     */
    fun evaluate(entered: String, real: String): UnlockResult {
        return when {
            entered == real -> {
                isActive = false // reset in case duress was previously active in the same session
                UnlockResult.Real
            }
            entered == real.reversed() && real != real.reversed() -> {
                // Only trigger duress if reversed code is meaningfully different
                // (palindromes like "123321" cannot have a distinct duress code)
                isActive = true
                UnlockResult.Duress
            }
            else -> UnlockResult.Wrong
        }
    }

    /** Deactivates duress mode. Called when app is relaunched or passcode re-entered correctly. */
    fun reset() {
        isActive = false
    }

    sealed interface UnlockResult {
        data object Real   : UnlockResult
        data object Duress : UnlockResult
        data object Wrong  : UnlockResult
    }
}
