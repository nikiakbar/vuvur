package com.example.vuvur.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Environment
import com.example.vuvur.DuressState
import com.example.vuvur.MediaFile
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.UUID
import javax.crypto.AEADBadTagException
import javax.crypto.SecretKey

class StorageQuotaExceededException(limitGb: Float) :
    Exception("Offline storage quota of ${limitGb}GB exceeded")

class WrongPasscodeException :
    Exception("Wrong passcode — cannot decrypt cached files")

class OfflineRepository(
    private val settingsRepository: SettingsRepository
) {

    companion object {
        /** Folder name inside the base external directory for encrypted media blobs. */
        private const val MEDIA_SUBDIR = "offline"

        /** Salt file stored at the root of the base external directory. */
        private const val SALT_FILE = "salt.bin"

        /** Index file stored at the root of the base external directory. */
        private const val INDEX_FILE = "index.json"

        private val IMAGE_TYPES = setOf("image", "gif")
        private const val JPEG_QUALITY = 85
    }

    private val gson = Gson()
    private val indexType = object : TypeToken<List<OfflineMediaItem>>() {}.type

    // Shared OkHttp client for downloading media bytes
    private val httpClient = OkHttpClient.Builder().build()

    // ---------------------------------------------------------------------------
    // Index backed by a StateFlow so the rest of the app can react to changes.
    // ---------------------------------------------------------------------------

    private val _offlineItemsFlow = MutableStateFlow<List<OfflineMediaItem>>(emptyList())
    val offlineItemsFlow: StateFlow<List<OfflineMediaItem>> = _offlineItemsFlow.asStateFlow()

    /**
     * Must be called once (e.g. from Application.onCreate or OfflineViewModel.init)
     * to load the persisted index from disk into the StateFlow.
     * In duress mode this is skipped so the flow stays empty.
     */
    fun loadIndex(context: Context) {
        if (DuressState.isActive) return  // appear empty in duress mode
        val indexFile = File(getBaseDir(context), INDEX_FILE)
        if (indexFile.exists()) {
            try {
                val json = indexFile.readText()
                val items: List<OfflineMediaItem> = gson.fromJson(json, indexType) ?: emptyList()
                _offlineItemsFlow.value = items
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    // ---------------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------------

    /**
     * Downloads, compresses (images only), encrypts with the passcode-derived key,
     * and stores a media item in external storage.
     *
     * Skips silently if the item is already cached.
     * Enforces the user-configured storage quota (evicting oldest items first).
     *
     * @throws IllegalStateException if no passcode is set.
     * @throws StorageQuotaExceededException if the quota cannot be freed.
     */
    suspend fun saveMediaOffline(
        context: Context,
        mediaFile: MediaFile,
        apiUrl: String,
        apiKey: String?
    ): Result<Unit> = runCatching {
        // Silently ignore save requests in duress mode — no new items should be cached
        // while operating under duress (they might reveal that real data exists elsewhere).
        if (DuressState.isActive) return@runCatching

        val existingIndex = _offlineItemsFlow.value

        // Skip if already cached
        if (existingIndex.any { it.id == mediaFile.id }) return@runCatching

        // Require passcode
        val passcode = settingsRepository.passcodeFlow.first()
            ?: throw IllegalStateException("No passcode set — please set a passcode in Settings before caching offline media.")

        // Derive key (PBKDF2 from passcode + persisted salt)
        val key = getOrCreateKey(context, passcode)

        // Determine URL (use stream endpoint for full media content)
        val mediaUrl = "$apiUrl/api/stream/${mediaFile.id}"

        // Download
        val rawBytes = downloadBytes(mediaUrl, apiKey)
        val processedBytes = rawBytes

        // Enforce quota — evict oldest items if needed
        val limitGb = settingsRepository.offlineStorageLimitGbFlow.first()
        val limitBytes = (limitGb * 1024 * 1024 * 1024).toLong()
        var currentUsed = existingIndex.sumOf { it.sizeBytes }
        val estimatedNewSize = processedBytes.size.toLong() + 28L // +28: IV + GCM tag

        var updatedIndex = existingIndex
        if (currentUsed + estimatedNewSize > limitBytes) {
            val sortedByOldest = updatedIndex.sortedBy { it.savedAt }.toMutableList()
            while (currentUsed + estimatedNewSize > limitBytes && sortedByOldest.isNotEmpty()) {
                val oldest = sortedByOldest.removeAt(0)
                File(getMediaDir(context), oldest.fileName).delete()
                currentUsed -= oldest.sizeBytes
                updatedIndex = sortedByOldest.toList()
            }
            if (currentUsed + estimatedNewSize > limitBytes) {
                throw StorageQuotaExceededException(limitGb)
            }
        }

        // Encrypt
        val encryptedBytes = CryptoManager.encrypt(processedBytes, key)

        // Write to <externalBase>/offline/<uuid>
        val mediaDir = getMediaDir(context).apply { mkdirs() }
        val fileName = UUID.randomUUID().toString()
        val outFile = File(mediaDir, fileName)
        outFile.writeBytes(encryptedBytes)

        // Update index
        val newItem = OfflineMediaItem(
            id = mediaFile.id,
            fileName = fileName,
            type = mediaFile.type,
            width = mediaFile.width,
            height = mediaFile.height,
            savedAt = System.currentTimeMillis(),
            sizeBytes = outFile.length()
        )
        val newIndex = updatedIndex + newItem
        persistIndex(context, newIndex)
        _offlineItemsFlow.value = newIndex
    }

    /**
     * Decrypts a cached item to a temporary file for playback.
     * Returns the temp [File]; caller is responsible for deleting it after use.
     *
     * @throws WrongPasscodeException if the passcode produces the wrong key.
     */
    suspend fun decryptToTempFile(context: Context, item: OfflineMediaItem): File {
        // In duress mode, pretend decryption failed — the viewer screen will show
        // "Error decrypting file" which looks identical to a corrupt-file scenario.
        if (DuressState.isActive) throw IllegalStateException("Decryption unavailable")

        val passcode = settingsRepository.passcodeFlow.first()
            ?: throw IllegalStateException("No passcode set.")
        val key = loadExistingKey(context, passcode)
            ?: throw IllegalStateException("No salt file found — cache may have been deleted.")

        val encryptedFile = File(getMediaDir(context), item.fileName)
        val encryptedBytes = encryptedFile.readBytes()

        val plainBytes = try {
            CryptoManager.decrypt(encryptedBytes, key)
        } catch (e: AEADBadTagException) {
            throw WrongPasscodeException()
        }

        val ext = if (item.type.lowercase() in IMAGE_TYPES) "jpg" else "mp4"
        val tempFile = File(context.cacheDir, "offline_temp_${item.id}.$ext")
        tempFile.writeBytes(plainBytes)
        return tempFile
    }

    /**
     * Decrypts a cached image item for Coil display (no temp file — returns raw bytes).
     * Used by [OfflineMediaFetcher].
     */
    suspend fun decryptToBytes(context: Context, item: OfflineMediaItem): ByteArray {
        if (DuressState.isActive) throw IllegalStateException("Decryption unavailable")

        val passcode = settingsRepository.passcodeFlow.first()
            ?: throw IllegalStateException("No passcode set.")
        val key = loadExistingKey(context, passcode)
            ?: throw IllegalStateException("No salt file found.")

        val encryptedFile = File(getMediaDir(context), item.fileName)
        val encryptedBytes = encryptedFile.readBytes()

        return try {
            CryptoManager.decrypt(encryptedBytes, key)
        } catch (e: AEADBadTagException) {
            throw WrongPasscodeException()
        }
    }

    /**
     * Deletes a cached item from disk and removes it from the index.
     */
    suspend fun deleteOfflineItem(context: Context, item: OfflineMediaItem) {
        File(getMediaDir(context), item.fileName).delete()
        val newIndex = _offlineItemsFlow.value.filterNot { it.id == item.id }
        persistIndex(context, newIndex)
        _offlineItemsFlow.value = newIndex
    }

    /**
     * Deletes ALL cached media files, the index, and the salt.
     * After this call the user must re-cache everything; the salt will be regenerated
     * on the next save (producing a new key even with the same passcode).
     */
    suspend fun clearAllOfflineMedia(context: Context) {
        getMediaDir(context).listFiles()?.forEach { it.delete() }
        File(getBaseDir(context), INDEX_FILE).delete()
        File(getBaseDir(context), SALT_FILE).delete()
        _offlineItemsFlow.value = emptyList()
    }

    /**
     * Returns the total bytes consumed by all offline files on disk.
     */
    fun getTotalUsedBytes(context: Context): Long {
        return getMediaDir(context).listFiles()?.sumOf { it.length() } ?: 0L
    }

    /**
     * Migrates any leftover files from the old internal-storage location (filesDir/offline/).
     * Old files are encrypted with the Keystore key that is now gone — they cannot be
     * decrypted — so we simply delete them and clear the DataStore index.
     */
    suspend fun migrateFromOldInternalStorage(context: Context) {
        val oldDir = File(context.filesDir, "offline")
        if (oldDir.exists() && (oldDir.listFiles()?.isNotEmpty() == true)) {
            oldDir.deleteRecursively()
            // Clear any stale DataStore index entries
            settingsRepository.clearOfflineIndex()
        }
    }

    // ---------------------------------------------------------------------------
    // Directory helpers
    // ---------------------------------------------------------------------------

    /**
     * Root external directory: Documents/Vuvur/
     * This directory survives app uninstall on all Android versions.
     */
    private fun getBaseDir(context: Context): File {
        val base = context.getExternalFilesDir(null) ?: context.filesDir
        return File(base, "Vuvur").also { it.mkdirs() }
    }

    private fun getMediaDir(context: Context): File =
        File(getBaseDir(context), MEDIA_SUBDIR).also { it.mkdirs() }

    // ---------------------------------------------------------------------------
    // Key management — salt lives in the same external dir as the encrypted files
    // ---------------------------------------------------------------------------

    /**
     * Loads an existing salt and derives the key. Returns null if no salt file exists yet.
     */
    private fun loadExistingKey(context: Context, passcode: String): SecretKey? {
        val saltFile = File(getBaseDir(context), SALT_FILE)
        if (!saltFile.exists()) return null
        val salt = saltFile.readBytes()
        return CryptoManager.deriveKey(passcode, salt)
    }

    /**
     * Loads the existing salt (or creates one if this is the first save) and derives the key.
     */
    private fun getOrCreateKey(context: Context, passcode: String): SecretKey {
        val saltFile = File(getBaseDir(context), SALT_FILE)
        val salt = if (saltFile.exists()) {
            saltFile.readBytes()
        } else {
            CryptoManager.generateSalt().also { saltFile.writeBytes(it) }
        }
        return CryptoManager.deriveKey(passcode, salt)
    }

    // ---------------------------------------------------------------------------
    // Index persistence
    // ---------------------------------------------------------------------------

    private fun persistIndex(context: Context, items: List<OfflineMediaItem>) {
        val json = gson.toJson(items)
        File(getBaseDir(context), INDEX_FILE).writeText(json)
    }

    // ---------------------------------------------------------------------------
    // Private helpers
    // ---------------------------------------------------------------------------

    private fun downloadBytes(url: String, apiKey: String?): ByteArray {
        val requestBuilder = Request.Builder().url(url)
        apiKey?.let { requestBuilder.header("X-Api-Key", it) }
        val response = httpClient.newCall(requestBuilder.build()).execute()
        if (!response.isSuccessful) {
            throw Exception("Failed to download media: HTTP ${response.code}")
        }
        return response.body?.bytes() ?: throw Exception("Empty response body")
    }

    private fun compressImage(rawBytes: ByteArray): ByteArray {
        val bitmap = BitmapFactory.decodeByteArray(rawBytes, 0, rawBytes.size)
            ?: return rawBytes // fallback: store as-is if decode fails
        val out = ByteArrayOutputStream()
        bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, out)
        bitmap.recycle()
        return out.toByteArray()
    }
}
