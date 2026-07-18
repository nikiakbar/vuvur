package com.example.vuvur.data

import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec

/**
 * Manages AES-256-GCM encryption/decryption using a PBKDF2-derived key.
 *
 * Unlike the Android Keystore approach, the key is derived from the user's passcode
 * and a random salt stored on disk. This means:
 * - The salt + encrypted files survive app uninstall (stored in external storage)
 * - After reinstall, entering the same passcode re-derives the exact same key
 * - No hardware key binding; security comes from the passcode + PBKDF2 iteration count
 */
object CryptoManager {

    private const val CIPHER_TRANSFORMATION = "AES/GCM/NoPadding"
    private const val KEY_ALGORITHM = "AES"
    private const val KDF_ALGORITHM = "PBKDF2WithHmacSHA256"
    private const val GCM_IV_LENGTH = 12   // bytes
    private const val GCM_TAG_LENGTH = 128 // bits
    private const val KDF_ITERATIONS = 100_000
    private const val KEY_SIZE_BITS = 256
    const val SALT_SIZE_BYTES = 16

    /**
     * Generates a cryptographically random salt.
     * Call this once when the offline store is first created; persist the result to salt.bin
     * in the external storage directory (so it survives uninstall alongside the encrypted files).
     */
    fun generateSalt(): ByteArray {
        val salt = ByteArray(SALT_SIZE_BYTES)
        SecureRandom().nextBytes(salt)
        return salt
    }

    /**
     * Derives an AES-256 key from [passcode] and [salt] using PBKDF2WithHmacSHA256.
     * The same inputs always produce the same key — this is intentional so that
     * reinstalling the app and re-entering the passcode restores access to cached files.
     */
    fun deriveKey(passcode: String, salt: ByteArray): SecretKey {
        val factory = SecretKeyFactory.getInstance(KDF_ALGORITHM)
        val spec = PBEKeySpec(passcode.toCharArray(), salt, KDF_ITERATIONS, KEY_SIZE_BITS)
        val rawKey = factory.generateSecret(spec).encoded
        spec.clearPassword()
        return SecretKeySpec(rawKey, KEY_ALGORITHM)
    }

    /**
     * Encrypts [plainBytes] using AES-256-GCM with [key].
     * @return A random 12-byte IV prepended to the ciphertext + GCM authentication tag.
     */
    fun encrypt(plainBytes: ByteArray, key: SecretKey): ByteArray {
        val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(plainBytes)
        return iv + ciphertext   // IV (12 bytes) || ciphertext || GCM tag (16 bytes)
    }

    /**
     * Decrypts [encryptedBytes] produced by [encrypt].
     * The first [GCM_IV_LENGTH] bytes are the IV; the rest is ciphertext + authentication tag.
     *
     * @throws javax.crypto.AEADBadTagException if the key is wrong or data is corrupt.
     */
    fun decrypt(encryptedBytes: ByteArray, key: SecretKey): ByteArray {
        val iv = encryptedBytes.copyOfRange(0, GCM_IV_LENGTH)
        val ciphertext = encryptedBytes.copyOfRange(GCM_IV_LENGTH, encryptedBytes.size)
        val cipher = Cipher.getInstance(CIPHER_TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(GCM_TAG_LENGTH, iv))
        return cipher.doFinal(ciphertext)
    }
}
